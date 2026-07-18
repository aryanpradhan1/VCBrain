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

OPPORTUNITIES_DB: Dict[str, Dict[str, Any]] = {}
FOUNDERS_DB: Dict[str, Dict[str, Any]] = {}


def load_fixture_data():
    """Load test fixtures into in-memory DB"""
    fixtures = [
        "signal_intake_strong.json",
        "signal_intake_cold_start.json",
        "signal_intake_exact_match.json",
        "signal_intake_adjacent.json",
    ]

    for i, fixture_name in enumerate(fixtures):
        try:
            with open(f"../../shared/fixtures/{fixture_name}") as f:
                data = json.load(f)

                # Score this opportunity
                multi_axis = score_all_axes(data)
                thesis = evaluate_thesis_fit(data)

                # Store in DB
                opp_id = f"opp_{i+1}"
                founder_id = data["founder_id"]

                OPPORTUNITIES_DB[opp_id] = {
                    "signal_data": data,
                    "multi_axis": multi_axis,
                    "thesis": thesis,
                }

                FOUNDERS_DB[founder_id] = {
                    "founder_score": multi_axis.founder_score,
                }

        except FileNotFoundError:
            print(f"Warning: Fixture {fixture_name} not found")
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


@app.get("/opportunities/{opportunity_id}", response_model=OpportunityResponse)
def get_opportunity(opportunity_id: str):
    """
    Get full opportunity details (investor view)

    Returns complete multi-axis scores, memo, adversarial view, etc.
    """
    if opportunity_id not in OPPORTUNITIES_DB:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    opp = OPPORTUNITIES_DB[opportunity_id]
    signal_data = opp["signal_data"]
    multi_axis = opp["multi_axis"]
    thesis = opp["thesis"]

    # Mock data for components not yet built
    # (Diligence/Validator, Trust Score, Memo Synthesizer, Interview Agent)

    # Extract company name from deck claims
    problem_claims = [c for c in signal_data.get("deck_claims", [])
                      if c.get("field") == "problem_product"]
    company_name = f"Company {opportunity_id}"  # Placeholder

    # Mock claim trust (would come from Diligence module)
    claim_trust = [
        ClaimTrust(claim="traction", confidence="high", evidence="deck_slide_7"),
        ClaimTrust(claim="market_size", confidence="medium", evidence="deck_slide_5"),
    ]

    # Mock memo (would come from Memo Synthesizer)
    memo = MemoResponse(
        required=MemoRequired(
            company_snapshot=f"Early-stage company in {signal_data.get('sourcing_channel')} pipeline",
            investment_hypotheses=[
                "Strong technical founder with execution track record",
                "Growing market with favorable dynamics"
            ],
            swot={
                "strengths": ["Technical team", "Early traction"],
                "weaknesses": ["Limited market data"],
                "opportunities": ["Market expansion"],
                "threats": ["Competition"]
            },
            problem_and_product=problem_claims[0].get("value") if problem_claims else "Not specified",
            traction_kpis="See deck slide 7"
        ),
        optional_or_flagged=MemoOptional(
            cap_table="Not disclosed",
            team_and_history="See deck slide 3"
        )
    )

    # Mock adversarial view
    adversarial_view = AdversarialView(
        challenges=["Market size claims need validation", "Competitive moat unclear"]
    )

    # Mock portfolio check
    portfolio_check = PortfolioCheck(
        overlap=False,
        note="No sector overlap with existing portfolio"
    )

    # Determine verdict based on thesis + founder score
    if not thesis.thesis_match:
        verdict = "decline"
    elif multi_axis.founder_score.value >= 70:
        verdict = "approve"
    else:
        verdict = "review"

    return OpportunityResponse(
        founder_id=signal_data["founder_id"],
        company_id=signal_data["company_id"],
        company_name=company_name,
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
        amount_recommended=100000 if verdict == "approve" else 0
    )


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


@app.post("/opportunities/{opportunity_id}/decision")
def record_decision(opportunity_id: str, request: DecisionRequest):
    """
    Record investment decision for an opportunity

    In production, this would update database and trigger notifications.
    """
    if opportunity_id not in OPPORTUNITIES_DB:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # Mock: just return success
    return {
        "opportunity_id": opportunity_id,
        "decision": request.decision,
        "status": "recorded"
    }


@app.get("/opportunities")
def list_opportunities(
    query: Optional[str] = None,
    thesis_filter: bool = False
):
    """
    List all opportunities with optional filtering

    Args:
        query: Natural language query (e.g., "technical founder, AI infra")
        thesis_filter: If true, only show thesis matches
    """
    results = []

    for opp_id, opp_data in OPPORTUNITIES_DB.items():
        signal_data = opp_data["signal_data"]
        multi_axis = opp_data["multi_axis"]
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

        results.append({
            "opportunity_id": opp_id,
            "founder_id": signal_data["founder_id"],
            "company_id": signal_data["company_id"],
            "founder_score": multi_axis.founder_score.value,
            "confidence_interval": multi_axis.founder_score.confidence_interval,
            "trend": multi_axis.founder_score.trend,
            "thesis_match": thesis.thesis_match,
            "sourcing_channel": signal_data["sourcing_channel"],
            "cold_start_flag": signal_data["cold_start_flag"],
        })

    return {"count": len(results), "opportunities": results}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
