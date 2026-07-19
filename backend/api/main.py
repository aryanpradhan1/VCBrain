"""
FounderScore API - FastAPI Glue

Assembles all agent outputs into the shapes the frontend expects:
- GET /opportunities/:id - full investor view
- GET /founders/:id/results - founder-facing lightweight view
- POST /opportunities/:id/decision - record decision
"""

import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# C owns the provider credentials. Load them before importing scoring, whose OpenAI
# client is initialized at module import time. ``override=True`` prevents a stale
# shell placeholder from masking the project-local configuration.
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / "diligence_memo" / ".env", override=True)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Any, Literal, Optional
import json

# Import scoring module
from backend.scoring import (
    score_all_axes,
    evaluate_thesis_fit,
    parse_natural_language_query,
    match_opportunity,
    calculate_founder_score_from_axes,
    MultiAxisOutput,
    ThesisOutput,
)

# Import C's diligence/trust/memo pipeline -- real calls, not ad-hoc mocks
from backend.diligence_memo import (
    ClaimValidator,
    DiligenceMemoPipeline,
    InterviewAgent,
    InterviewSession,
    MemoSynthesizer,
)
from backend.diligence_memo.clients import OpenAIReasoningClient, TavilySearchClient


app = FastAPI(
    title="FounderScore API",
    description="VC Brain - $100K investment decisions in 24 hours",
    version="1.0.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Response Models (Contract-Compliant) ====================

class AxisScoreResponse(BaseModel):
    score: int
    trend: Literal["improving", "declining", "stable"]
    rationale: str
    citations: List[str]


class AxisRatingResponse(BaseModel):
    rating: Literal["bullish", "neutral", "bear"]
    trend: Literal["improving", "declining", "stable"]
    rationale: str
    citations: List[str]


class FounderScoreResponse(BaseModel):
    value: int
    confidence_interval: int
    trend: Literal["improving", "declining", "stable"]


class ClaimTrust(BaseModel):
    claim: str
    confidence: Literal["high", "medium", "low"]
    evidence: str


class MemoRequired(BaseModel):
    company_snapshot: str
    investment_hypotheses: List[str]
    swot: Dict[str, Any]
    problem_and_product: str
    traction_kpis: str


class MemoOptional(BaseModel):
    team_and_history: Optional[str] = None
    cap_table: Optional[str] = "Not disclosed"


class MemoResponse(BaseModel):
    required: MemoRequired
    optional_or_flagged: MemoOptional


class AdversarialView(BaseModel):
    challenges: List[str]


class PortfolioCheck(BaseModel):
    overlap: bool
    note: str


class OpportunityResponse(BaseModel):
    """
    GET /opportunities/:id response
    Full investor-facing view
    """
    founder_id: str
    company_id: str
    company_name: str
    sourcing_channel: Literal["inbound", "outbound"]
    cold_start_flag: bool

    # Multi-axis scores (NEVER averaged)
    founder_score: FounderScoreResponse
    founder_axis: AxisScoreResponse
    market_axis: AxisRatingResponse
    idea_vs_market_axis: AxisRatingResponse

    # Trust and diligence
    claim_trust: List[ClaimTrust]

    # Memo and decision
    memo: MemoResponse
    adversarial_view: AdversarialView
    portfolio_check: PortfolioCheck
    verdict: Literal["approve", "review", "decline"]
    amount_recommended: int


class FounderResultsResponse(BaseModel):
    """
    GET /founders/:id/results response
    Founder-facing lightweight view (read-only)
    """
    founder_score: FounderScoreResponse
    narrative: str


class DecisionRequest(BaseModel):
    """
    POST /opportunities/:id/decision request
    """
    decision: Literal["approve", "review", "decline"]


class InterviewAnswerRequest(BaseModel):
    answer: str


class InterviewProgressResponse(BaseModel):
    question: Optional[str] = None
    question_number: int
    total_questions: int
    complete: bool


# ==================== In-Memory Storage (Demo) ====================
# In production, this would be SQLite/Postgres

# Keyed by company_id (not a synthetic id) -- the frontend links via
# `/opportunities/${opp.company_id}` (see frontend/src/pages/dashboard.jsx), so the
# lookup key here must match that exactly.
OPPORTUNITIES_DB: Dict[str, Dict[str, Any]] = {}
FOUNDERS_DB: Dict[str, Dict[str, Any]] = {}
INTERVIEW_SESSIONS: Dict[str, InterviewSession] = {}

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = PROJECT_ROOT / "shared" / "fixtures"
MEMORY_DB_PATH = Path(
    os.getenv("FOUNDER_SCORE_DB_PATH", str(Path(__file__).with_name("founderscore.sqlite3")))
)

# Real diligence/memo pipeline (C's module). Built once and reused -- validate() makes a
# Tavily search + OpenAI call per claim, so this must never run per-request.
_diligence_pipeline = DiligenceMemoPipeline(
    validator=ClaimValidator(
        search_client=TavilySearchClient(),
        reasoning_client=OpenAIReasoningClient(),
    ),
    memo=MemoSynthesizer(),
)


def _memory_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(MEMORY_DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_memory() -> None:
    """Create the persistent Memory tables owned by the API glue."""
    MEMORY_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _memory_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS gap_findings (
                company_id TEXT NOT NULL,
                founder_id TEXT NOT NULL,
                claim TEXT NOT NULL,
                issue TEXT NOT NULL,
                severity TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                PRIMARY KEY (company_id, claim, issue)
            );
            CREATE TABLE IF NOT EXISTS interview_results (
                founder_id TEXT PRIMARY KEY,
                questions_asked TEXT NOT NULL,
                response_pattern TEXT NOT NULL,
                resilience_score INTEGER NOT NULL,
                completed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS score_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                founder_id TEXT NOT NULL,
                value INTEGER NOT NULL,
                confidence_interval INTEGER NOT NULL,
                trend TEXT NOT NULL,
                event_type TEXT NOT NULL,
                recorded_at TEXT NOT NULL
            );
            """
        )


def persist_gap_findings(
    company_id: str, founder_id: str, diligence_output: Dict[str, Any]
) -> None:
    if not diligence_output.get("memory_update"):
        return
    recorded_at = datetime.now(timezone.utc).isoformat()
    rows = [
        (
            company_id,
            founder_id,
            item["claim"],
            item["issue"],
            item["severity"],
            recorded_at,
        )
        for item in diligence_output.get("flagged_claims", [])
    ]
    with _memory_connection() as connection:
        connection.executemany(
            """
            INSERT OR REPLACE INTO gap_findings
                (company_id, founder_id, claim, issue, severity, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


def _persist_interview_result(founder_id: str, result: Dict[str, Any]) -> None:
    completed_at = datetime.now(timezone.utc).isoformat()
    with _memory_connection() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO interview_results
                (founder_id, questions_asked, response_pattern, resilience_score, completed_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                founder_id,
                json.dumps(result["questions_asked"]),
                result["response_pattern"],
                result["resilience_score"],
                completed_at,
            ),
        )


def _traction_signal_score(signal_data: Dict[str, Any]) -> int:
    """Deterministic raw-signal component used by the locked Founder Score formula."""
    signals = signal_data.get("public_signals", {})
    github = signals.get("github", {})
    launches = signals.get("devpost_hn", {})
    arxiv = signals.get("arxiv", {})
    score = (
        min(int(github.get("repos", 0)), 10) * 3
        + round(float(github.get("commit_consistency_score", 0)) * 25)
        + min(int(launches.get("total_upvotes", 0)), 500) // 20
        + min(int(arxiv.get("papers", 0)), 4) * 5
    )
    return min(100, max(0, score))


def _recompute_founder_score(founder_id: str, resilience_score: int) -> None:
    founder = FOUNDERS_DB[founder_id]
    opportunity = OPPORTUNITIES_DB[founder["company_id"]]
    multi_axis = opportunity["multi_axis"]
    signal_data = opportunity["signal_data"]
    fit_scores = {"bullish": 80, "neutral": 55, "bear": 30}
    updated_score = calculate_founder_score_from_axes(
        founder_axis_score=multi_axis.founder_axis.score,
        traction_signal_score=_traction_signal_score(signal_data),
        founder_market_fit_score=fit_scores[multi_axis.idea_vs_market_axis.rating],
        resilience_score=resilience_score,
        cold_start=signal_data["cold_start_flag"],
    )
    previous_value = founder["founder_score"].value
    updated_score.trend = (
        "improving" if updated_score.value > previous_value else
        "declining" if updated_score.value < previous_value else
        "stable"
    )
    founder["founder_score"] = updated_score
    multi_axis.founder_score = updated_score
    with _memory_connection() as connection:
        connection.execute(
            """
            INSERT INTO score_history
                (founder_id, value, confidence_interval, trend, event_type, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                founder_id,
                updated_score.value,
                updated_score.confidence_interval,
                updated_score.trend,
                "interview_completed",
                datetime.now(timezone.utc).isoformat(),
            ),
        )


def load_fixture_data():
    """Load test fixtures into in-memory DB.

    Diligence/memo is computed once here, at startup, and cached -- NOT recomputed per
    request. Every opportunity needs the same real-shape assembly whether it's shown in
    the list or the detail view (see _assemble_opportunity below), so running the real
    Tavily+OpenAI pipeline per HTTP request would multiply cost with every dashboard
    refresh instead of once per opportunity per server lifetime.
    """
    fixtures = [
        "signal_intake_strong.json",
        "signal_intake_cold_start.json",
        "signal_intake_exact_match.json",
        "signal_intake_adjacent.json",
    ]

    for fixture_name in fixtures:
        try:
            with (FIXTURES_DIR / fixture_name).open(encoding="utf-8") as f:
                data = json.load(f)

                company_id = data["company_id"]
                founder_id = data["founder_id"]
                company_name = f"Company {company_id}"  # placeholder: no module in the
                # pipeline currently captures a real company name as a structured field

                multi_axis = score_all_axes(data)
                thesis = evaluate_thesis_fit(data)
                diligence_memo = _diligence_pipeline.run({
                    "company_name": company_name,
                    "sector": data.get("sector", "Not disclosed"),
                    "deck_claims": data.get("deck_claims", []),
                })
                persist_gap_findings(company_id, founder_id, diligence_memo["diligence"])

                OPPORTUNITIES_DB[company_id] = {
                    "signal_data": data,
                    "company_name": company_name,
                    "multi_axis": multi_axis,
                    "thesis": thesis,
                    "diligence_memo": diligence_memo,
                }

                FOUNDERS_DB[founder_id] = {
                    "founder_score": multi_axis.founder_score,
                    "company_id": company_id,
                }

        except FileNotFoundError:
            print(f"Warning: Fixture {fixture_name} not found")
            continue
        except Exception as e:
            print(f"Warning: Could not process fixture {fixture_name}: {e}")
            continue


# ==================== Endpoints ====================

@app.on_event("startup")
async def startup_event():
    """Load fixtures on startup"""
    print("Loading fixture data...")
    try:
        initialize_memory()
        load_fixture_data()
        print(f"Loaded {len(OPPORTUNITIES_DB)} opportunities")
    except Exception as e:
        print(f"Warning: Could not load fixtures: {e}")


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "FounderScore API"}


def _assemble_opportunity(company_id: str) -> OpportunityResponse:
    """Single assembly path for a full opportunity record -- used by both the list and
    detail endpoints, so the dashboard and the memo view are never fed two different
    shapes for the same company. Reads the diligence/memo output cached at startup by
    load_fixture_data() rather than recomputing it (see the cost note there)."""
    opp = OPPORTUNITIES_DB[company_id]
    signal_data = opp["signal_data"]
    multi_axis = opp["multi_axis"]
    thesis = opp["thesis"]
    diligence_memo = opp["diligence_memo"]

    claim_trust = [ClaimTrust(**item) for item in diligence_memo["trust"]["claim_trust"]]
    memo = MemoResponse(
        required=MemoRequired(**diligence_memo["memo"]["required"]),
        optional_or_flagged=MemoOptional(**diligence_memo["memo"]["optional_or_flagged"]),
    )
    adversarial_view = AdversarialView(**diligence_memo["adversarial_view"])
    portfolio_check = PortfolioCheck(**diligence_memo["portfolio_check"])

    # Thesis Engine is a gate: a non-match always declines regardless of what diligence
    # found, since an out-of-thesis company was never a candidate to fund. Otherwise C's
    # real diligence/memo verdict (grounded in flagged claims + evidence) is authoritative
    # -- not re-derived ad hoc from founder_score here.
    if not thesis.thesis_match:
        verdict = "decline"
    else:
        verdict = diligence_memo["verdict"]

    return OpportunityResponse(
        founder_id=signal_data["founder_id"],
        company_id=signal_data["company_id"],
        company_name=opp["company_name"],
        sourcing_channel=signal_data["sourcing_channel"],
        cold_start_flag=signal_data["cold_start_flag"],
        founder_score=FounderScoreResponse(**multi_axis.founder_score.dict()),
        founder_axis=AxisScoreResponse(**multi_axis.founder_axis.dict()),
        market_axis=AxisRatingResponse(**multi_axis.market_axis.dict()),
        idea_vs_market_axis=AxisRatingResponse(**multi_axis.idea_vs_market_axis.dict()),
        claim_trust=claim_trust,
        memo=memo,
        adversarial_view=adversarial_view,
        portfolio_check=portfolio_check,
        verdict=verdict,
        amount_recommended=diligence_memo["amount_recommended"] if verdict == "approve" else 0,
    )


@app.get("/opportunities/{company_id}", response_model=OpportunityResponse)
def get_opportunity(company_id: str):
    """
    Get full opportunity details (investor view)

    Returns complete multi-axis scores, memo, adversarial view, etc.
    """
    if company_id not in OPPORTUNITIES_DB:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    return _assemble_opportunity(company_id)


@app.get("/founders/{founder_id}/results", response_model=FounderResultsResponse)
def get_founder_results(founder_id: str):
    """
    Get founder-facing results (read-only, lightweight)

    Only shows Founder Score + narrative.
    Does NOT show memo, SWOT, or internal analysis.
    """
    if founder_id not in FOUNDERS_DB:
        raise HTTPException(status_code=404, detail="Founder not found")

    founder = FOUNDERS_DB[founder_id]
    founder_score = founder["founder_score"]

    # Generate narrative based on score
    if founder_score.value >= 70:
        narrative = f"Strong profile with demonstrated execution ability. Your Founder Score of {founder_score.value} reflects consistent technical depth and traction signals."
    elif founder_score.value >= 50:
        narrative = f"Solid foundation with room to strengthen. Your Founder Score of {founder_score.value} shows promise; consider building more public evidence of execution."
    else:
        narrative = f"Early-stage profile. Your Founder Score of {founder_score.value} indicates limited public track record. Focus on shipping, launching, and building in public."

    return FounderResultsResponse(
        founder_score=FounderScoreResponse(**founder_score.dict()),
        narrative=narrative
    )


@app.post(
    "/founders/{founder_id}/interview/start",
    response_model=InterviewProgressResponse,
)
def start_interview(founder_id: str):
    """Start or restart C's adaptive 5-question interview for this founder."""
    if founder_id not in FOUNDERS_DB:
        raise HTTPException(status_code=404, detail="Founder not found")
    company_id = FOUNDERS_DB[founder_id]["company_id"]
    claims = OPPORTUNITIES_DB[company_id]["signal_data"].get("deck_claims", [])
    session = InterviewAgent().start(claims, max_questions=5)
    INTERVIEW_SESSIONS[founder_id] = session
    question = session.next_question()
    return InterviewProgressResponse(
        question=question,
        question_number=1,
        total_questions=session.max_questions,
        complete=False,
    )


@app.post(
    "/founders/{founder_id}/interview/respond",
    response_model=InterviewProgressResponse,
)
def respond_to_interview(founder_id: str, request: InterviewAnswerRequest):
    """Record an answer, adapt the next question, and persist the completed result."""
    session = INTERVIEW_SESSIONS.get(founder_id)
    if session is None:
        raise HTTPException(status_code=409, detail="Interview has not been started")
    if not request.answer.strip():
        raise HTTPException(status_code=422, detail="Answer cannot be empty")
    try:
        session.record_response(request.answer)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if len(session.responses) == session.max_questions:
        result = session.result()
        _persist_interview_result(founder_id, result)
        _recompute_founder_score(founder_id, result["resilience_score"])
        INTERVIEW_SESSIONS.pop(founder_id, None)
        return InterviewProgressResponse(
            question=None,
            question_number=session.max_questions,
            total_questions=session.max_questions,
            complete=True,
        )

    question = session.next_question()
    return InterviewProgressResponse(
        question=question,
        question_number=len(session.questions_asked),
        total_questions=session.max_questions,
        complete=False,
    )


@app.post("/opportunities/{company_id}/decision")
def record_decision(company_id: str, request: DecisionRequest):
    """
    Record investment decision for an opportunity

    In production, this would update database and trigger notifications.
    """
    if company_id not in OPPORTUNITIES_DB:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # Mock: just return success
    return {
        "company_id": company_id,
        "decision": request.decision,
        "status": "recorded"
    }


@app.get("/opportunities", response_model=List[OpportunityResponse])
def list_opportunities(
    query: Optional[str] = None,
    thesis_filter: bool = False
):
    """
    List all opportunities with optional filtering.

    Returns a bare array of full opportunity records (same shape as
    GET /opportunities/{company_id}) -- frontend/src/lib/api.js calls .sort() directly
    on this response, and dashboard.jsx's Row renders founder_axis/claim_trust/etc.
    straight from each list item, so this can't be a slimmer projection.

    Args:
        query: Natural language query (e.g., "technical founder, AI infra")
        thesis_filter: If true, only show thesis matches
    """
    results = []

    for company_id, opp_data in OPPORTUNITIES_DB.items():
        signal_data = opp_data["signal_data"]
        thesis = opp_data["thesis"]

        # Apply thesis filter
        if thesis_filter and not thesis.thesis_match:
            continue

        # Apply natural language query filter
        if query:
            try:
                structured_query = parse_natural_language_query(query)
                matches, _ = match_opportunity(signal_data, structured_query)
                if not matches:
                    continue
            except Exception as e:
                print(f"Query parse error: {e}")

        results.append(_assemble_opportunity(company_id))

    return results


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
