"""
FounderScore API - FastAPI Glue

Assembles all agent outputs into the shapes the frontend expects:
- GET /opportunities/:id - full investor view
- GET /founders/:id/results - founder-facing lightweight view
- POST /opportunities/:id/decision - record decision
"""

import sys
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

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
    MultiAxisOutput,
    ThesisOutput,
)

# Import C's diligence/trust/memo pipeline -- real calls, not ad-hoc mocks
from backend.diligence_memo import ClaimValidator, DiligenceMemoPipeline, MemoSynthesizer
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


# ==================== In-Memory Storage (Demo) ====================
# In production, this would be SQLite/Postgres

# Keyed by company_id (not a synthetic id) -- the frontend links via
# `/opportunities/${opp.company_id}` (see frontend/src/pages/dashboard.jsx), so the
# lookup key here must match that exactly.
OPPORTUNITIES_DB: Dict[str, Dict[str, Any]] = {}
FOUNDERS_DB: Dict[str, Dict[str, Any]] = {}

# Real diligence/memo pipeline (C's module). Built once and reused -- validate() makes a
# Tavily search + OpenAI call per claim, so this must never run per-request.
_diligence_pipeline = DiligenceMemoPipeline(
    validator=ClaimValidator(
        search_client=TavilySearchClient(),
        reasoning_client=OpenAIReasoningClient(),
    ),
    memo=MemoSynthesizer(),
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
            with open(f"../../shared/fixtures/{fixture_name}") as f:
                data = json.load(f)

                company_id = data["company_id"]
                founder_id = data["founder_id"]
                company_name = f"Company {company_id}"  # placeholder: no module in the
                # pipeline currently captures a real company name as a structured field

                multi_axis = score_all_axes(data)
                thesis = evaluate_thesis_fit(data)
                diligence_memo = _diligence_pipeline.run(
                    {"company_name": company_name, "deck_claims": data.get("deck_claims", [])}
                )

                OPPORTUNITIES_DB[company_id] = {
                    "signal_data": data,
                    "company_name": company_name,
                    "multi_axis": multi_axis,
                    "thesis": thesis,
                    "diligence_memo": diligence_memo,
                }

                FOUNDERS_DB[founder_id] = {
                    "founder_score": multi_axis.founder_score,
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
