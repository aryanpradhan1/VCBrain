"""FounderScore API: persistent applications around the locked agent contracts."""
from __future__ import annotations

import json
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Literal, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.diligence_memo import ClaimValidator, DiligenceMemoPipeline, MemoSynthesizer
from backend.diligence_memo.clients import OpenAIReasoningClient, TavilySearchClient
from backend.diligence_memo.interview import InterviewAgent, InterviewSession
from backend.scoring import calculate_founder_score_from_axes, evaluate_thesis_fit, match_opportunity, parse_natural_language_query, score_all_axes
from backend.signal_intake.deck_parser import assemble_signal_intake_output, extract_deck_claims
from backend.signal_intake.outbound_scan import run_outbound_pass
from backend.api.db import get_all_signals, list_outbound_leads as db_list_outbound_leads, save_outreach_event, save_signal

from backend.api.document_intake import (
    DocumentIntakeError,
    allowed_filename,
    copy_photo,
    copy_uploaded_file,
    extract_document,
)
from backend.api.presentation import build_enrichment, concise_memo, relevant_sources
from backend.api.source_enrichment import cache_verified_profile_avatars, enrich_submitted_people, fetch_site_metadata, github_profile_signal, search_press, submitted_link_sources, valid_public_url
from backend.api.store import ApplicationStore


ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT / "backend" / "data"
UPLOAD_ROOT = DATA_ROOT / "uploads"
MEDIA_ROOT = DATA_ROOT / "media"
FIXTURE_ROOT = ROOT / "shared" / "fixtures"
MAX_DOCUMENT_BYTES = 25 * 1024 * 1024
MAX_PHOTO_BYTES = 5 * 1024 * 1024
MAX_TEAM_MEMBERS = 8

for directory in (UPLOAD_ROOT, MEDIA_ROOT):
    directory.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="FounderScore API", description="Investor-grade founder diligence", version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/media", StaticFiles(directory=str(MEDIA_ROOT)), name="media")
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_ROOT)), name="uploads")

store = ApplicationStore(DATA_ROOT / "founderscore.sqlite3")
OPPORTUNITIES_DB: dict[str, dict[str, Any]] = {}
FOUNDERS_DB: dict[str, dict[str, Any]] = {}
_diligence_pipeline = DiligenceMemoPipeline(
    validator=ClaimValidator(search_client=TavilySearchClient(), reasoning_client=OpenAIReasoningClient()),
    memo=MemoSynthesizer(),
)
_interview_agent = InterviewAgent()


class AxisScoreResponse(BaseModel):
    score: int
    trend: Literal["improving", "declining", "stable"]
    rationale: str
    citations: list[str]


class AxisRatingResponse(BaseModel):
    rating: Literal["bullish", "neutral", "bear"]
    trend: Literal["improving", "declining", "stable"]
    rationale: str
    citations: list[str]


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
    investment_hypotheses: list[str]
    swot: dict[str, Any]
    problem_and_product: str
    traction_kpis: str


class MemoOptional(BaseModel):
    team_and_history: Optional[str] = None
    cap_table: Optional[str] = "Not disclosed"


class MemoResponse(BaseModel):
    required: MemoRequired
    optional_or_flagged: MemoOptional


class AdversarialView(BaseModel):
    challenges: list[str]


class PortfolioCheck(BaseModel):
    overlap: bool
    note: str


class SourceRecord(BaseModel):
    type: str
    title: str
    url: str
    excerpt: str = ""
    image_url: str | None = None
    favicon_url: str | None = None
    preview_url: str | None = None
    source: str = ""
    page: int | None = None
    retrieved_at: str | None = None


class DocumentRecord(BaseModel):
    kind: str
    title: str
    page: int | None = None
    text: str = ""
    preview_url: str | None = None
    image_urls: list[str] = Field(default_factory=list)
    file_url: str | None = None


class OpportunityResponse(BaseModel):
    # Locked frontend-consumption shape
    founder_id: str
    company_id: str
    company_name: str
    sourcing_channel: Literal["inbound", "outbound"]
    cold_start_flag: bool
    founder_score: FounderScoreResponse
    founder_axis: AxisScoreResponse
    market_axis: AxisRatingResponse
    idea_vs_market_axis: AxisRatingResponse
    claim_trust: list[ClaimTrust]
    memo: MemoResponse
    adversarial_view: AdversarialView
    portfolio_check: PortfolioCheck
    verdict: Literal["approve", "review", "decline"]
    amount_recommended: int
    # Application/source envelope. These do not alter any agent-owned contract.
    thesis: dict[str, Any] | None = None
    enrichment: dict[str, Any] = Field(default_factory=dict)
    sources: list[SourceRecord] = Field(default_factory=list)
    documents: list[DocumentRecord] = Field(default_factory=list)
    processing_trace: list[dict[str, Any]] = Field(default_factory=list)
    status: str = "ready"
    # Signal Intake owns this contract payload; forwarding it prevents the
    # frontend from rendering a different (and empty) GitHub summary than the
    # scorer used.
    public_signals: dict[str, Any] = Field(default_factory=dict)


class FounderResultsResponse(BaseModel):
    founder_score: FounderScoreResponse
    narrative: str


class DecisionRequest(BaseModel):
    decision: Literal["approve", "review", "decline"]


class ApplicationSubmission(BaseModel):
    company_id: str
    founder_id: str
    status: str
    status_url: str


class ApplicationStatus(BaseModel):
    company_id: str
    founder_id: str
    company_name: str
    status: str
    stage: str | None = None
    error_message: str | None = None
    opportunity_url: str | None = None


class ThesisConfig(BaseModel):
    sectors: list[str] = Field(min_length=1)
    stage: Literal["Pre-seed", "Seed", "Series A"]
    geos: list[str] = Field(min_length=1)
    check: Literal["$50K", "$100K", "$250K"]
    ownership: Literal["0.5–1%", "1–2%", "2–5%"]
    risk: Literal["Conservative", "Balanced", "Aggressive"]


class InterviewResponseRequest(BaseModel):
    response: str = Field(min_length=1, max_length=6000)


class InterviewView(BaseModel):
    session_id: str
    status: Literal["active", "completed"]
    question: str | None = None
    question_number: int
    total_questions: int
    completed: bool


class OutboundLead(BaseModel):
    founder_id: str
    company_id: str
    founder_score: FounderScoreResponse
    cold_start_flag: bool
    outreach_status: Literal["not_activated", "delivered_no_response", "declined", "converted"]
    last_event_at: str | None = None


class OutboundScanTrigger(BaseModel):
    status: str
    detail: str


DEMO_PROFILES: dict[str, dict[str, Any]] = {
    "c001": {"founder_name": "Jordan Chen", "sector": "Developer tools", "stage": "Pre-seed", "geography": "Boston, US", "one_liner": "AI-assisted code review for production distributed systems."},
    "c002": {"founder_name": "Avery Brooks", "sector": "Climate", "stage": "Pre-seed", "geography": "Portland, US", "one_liner": "Carbon footprint tracking for small businesses."},
    "c003": {"founder_name": "Nadia Alvarez", "sector": "AI infrastructure", "stage": "Pre-seed", "geography": "San Francisco, US", "one_liner": "LLM inference optimization through compression and routing."},
    "c004": {"founder_name": "Marcus Lee", "sector": "Cloud infrastructure", "stage": "Pre-seed", "geography": "Seattle, US", "one_liner": "Multi-cloud workload orchestration and intelligent load balancing."},
    "c005": {"founder_name": "Sam Patel", "sector": "Consumer", "stage": "Pre-seed", "geography": "Chicago, US", "one_liner": "A restaurant discovery app for local dining."},
}

DEFAULT_THESIS_CONFIG = {
    "sectors": ["AI infrastructure", "Developer tools", "Robotics"],
    "stage": "Pre-seed",
    "geos": ["North America", "Europe"],
    "check": "$100K",
    "ownership": "1–2%",
    "risk": "Balanced",
}

_SECTOR_ENGINE_NAMES = {
    "AI infrastructure": "AI/ML infrastructure",
    "Healthcare": "Healthcare tech",
    "Climate": "Climate tech",
}
_GEO_ENGINE_NAMES = {
    "North America": ["US", "Canada"],
    "Europe": ["Western Europe"],
    "LATAM": ["LATAM"],
    "Africa": ["Africa"],
    "South Asia": ["South Asia"],
    "East Asia": ["East Asia"],
}


def _check_amount(check: str) -> int:
    return {"$50K": 50_000, "$100K": 100_000, "$250K": 250_000}[check]


def _parse_team_members(value: str) -> list[dict[str, str]]:
    """Keep optional cofounder identity records small and explicitly supplied."""
    if not value.strip():
        return []
    try:
        raw_members = json.loads(value)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="Team profiles must be valid form data.") from exc
    if not isinstance(raw_members, list) or len(raw_members) > MAX_TEAM_MEMBERS:
        raise HTTPException(status_code=422, detail=f"Add at most {MAX_TEAM_MEMBERS} team profiles.")
    members: list[dict[str, str]] = []
    for raw in raw_members:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name") or "").strip()[:120]
        if not name:
            continue
        member = {
            "name": name,
            "role": str(raw.get("role") or "Co-founder").strip()[:120],
            "linkedin": valid_public_url(str(raw.get("linkedin") or "")),
            "github": valid_public_url(str(raw.get("github") or "")),
            "arxiv": valid_public_url(str(raw.get("arxiv") or "")),
        }
        members.append({key: item for key, item in member.items() if item})
    return members


def _engine_thesis(config: dict[str, Any]) -> dict[str, Any]:
    """Translate the investor-facing settings into the deterministic engine's shape."""
    amount = _check_amount(config["check"])
    geographies = [item for geo in config["geos"] for item in _GEO_ENGINE_NAMES.get(geo, [geo])]
    return {
        "sectors": [_SECTOR_ENGINE_NAMES.get(sector, sector) for sector in config["sectors"]],
        "adjacent_sectors": ["Data infrastructure", "Cloud infrastructure", "DevOps", "Clean energy", "Biotech", "Insurtech"],
        "stage": [config["stage"].casefold()],
        "geography": geographies,
        "check_size_min": amount // 2,
        "check_size_max": int(amount * 1.5),
        "requirements": {"technical_founder": True, "min_team_size": 1, "max_team_size": 5},
    }


def current_thesis_config() -> dict[str, Any]:
    return store.get_thesis(DEFAULT_THESIS_CONFIG)


def _trace(stage: str, label: str, kind: str, summary: str, started: float) -> dict[str, Any]:
    return {"agent": stage, "label": label, "kind": kind, "summary": summary, "ms": max(1, round((time.monotonic() - started) * 1000))}


def _default_enrichment(profile: dict[str, Any], signal: dict[str, Any], photo_url: str | None = None) -> dict[str, Any]:
    claims = signal.get("deck_claims", [])
    by_field = {item.get("field"): item.get("value") for item in claims}
    problem_product = by_field.get("problem_product", "Founder-submitted deck is being processed.")
    enrichment = {
        "one_liner": profile.get("one_liner") or problem_product,
        "problem": problem_product,
        "solution": problem_product,
        "sector": profile.get("sector") or "Not disclosed",
        "stage": profile.get("stage") or "Not disclosed",
        "geography": profile.get("geography") or "Not disclosed",
        "website": valid_public_url(profile.get("website")),
        "founders": [{
            "name": profile.get("founder_name") or "Founder",
            "role": profile.get("founder_role") or "Founder",
            "avatar": photo_url,
            "background": by_field.get("team", "Not disclosed"),
            "linkedin": valid_public_url(profile.get("linkedin")),
            "github": valid_public_url(profile.get("github")),
            "x": valid_public_url(profile.get("x")),
            "ai_read": "Identity and public-source links were submitted by the founder; evidence is listed in the source ledger.",
        }],
        "pmf": {"signal": "early", "note": by_field.get("traction", "Not disclosed")},
    }
    # Keep the raw deck framing visible, but do not fabricate SAM/SOM merely to fill a chart.
    if by_field.get("market_size"):
        enrichment["market"] = {"basis": by_field["market_size"]}
    return enrichment


def _merged_public_signals(founder_id: str, current: dict[str, Any]) -> dict[str, Any]:
    """Blend this founder's accumulated Memory history (outbound-discovery GitHub/HN/arXiv
    signals recorded before they ever applied -- see /applications' ref param) into the
    public_signals actually fed to the Multi-Axis Scorer. Without this, an outbound-to-
    inbound conversion links identity and outreach status (already wired) but the
    founder's prior discovery evidence stays invisible to scoring -- this is what makes
    the convergence apply to the founder_score itself, not just bookkeeping.

    Each source's signal is a full snapshot, not incremental, so the richer one (by the
    source's own primary count) wins rather than summing -- summing could double-count
    the same repos/launches/papers across multiple recordings of the same evidence."""
    merged = {source: dict(payload) for source, payload in current.items()}
    richer_by = {"github": "repos", "devpost_hn": "launches", "arxiv": "papers"}
    for entry in get_all_signals(founder_id):
        source = entry["source"]
        count_field = richer_by.get(source)
        if not count_field:
            continue
        payload = {k: v for k, v in entry["payload"].items() if k not in ("company_id", "cold_start_flag")}
        if payload.get(count_field, 0) >= merged.get(source, {}).get(count_field, 0):
            merged[source] = payload
    return merged


def _analysis_for(
    signal: dict[str, Any], profile: dict[str, Any], traces: list[dict[str, Any]]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Returns (merged_signal, analysis) -- callers must store/display merged_signal, not
    their original signal, or the frontend would render a thinner public_signals summary
    than what the scorer actually used (exactly the failure mode the "Signal Intake owns
    this contract payload" comment on OpportunityResponse.public_signals warns against)."""
    signal = {**signal, "public_signals": _merged_public_signals(signal["founder_id"], signal["public_signals"])}
    started = time.monotonic()
    multi_axis = score_all_axes(signal)
    traces.append(_trace("scorer", "Multi-Axis Scorer", "ai", "Three independent axes scored from submitted deck and public signals.", started))
    started = time.monotonic()
    thesis = evaluate_thesis_fit(signal, _engine_thesis(current_thesis_config()))
    traces.append(_trace("thesis", "Thesis Engine", "rule", thesis.rationale, started))
    started = time.monotonic()
    diligence_memo = _diligence_pipeline.run({"company_name": profile["company_name"], "sector": profile.get("sector"), "deck_claims": signal.get("deck_claims", [])})
    traces.append(_trace("diligence", "Diligence", "ai", f"{len(diligence_memo['trust']['claim_trust'])} deck claims checked against bounded public sources.", started))
    verdict = "decline" if not thesis.thesis_match else diligence_memo["verdict"]
    traces.append({"agent": "memo", "label": "Memo Synthesizer", "kind": "ai", "summary": "Investment memo, trust assessment, and adversarial view assembled.", "ms": 1})
    analysis = {
        "multi_axis": multi_axis.model_dump(),
        "thesis": thesis.model_dump(),
        "diligence_memo": diligence_memo,
        "verdict": verdict,
    }
    return signal, analysis


def _cache_application(record: dict[str, Any]) -> None:
    if not record.get("signal") or not record.get("analysis"):
        return
    OPPORTUNITIES_DB[record["company_id"]] = record
    analysis = record["analysis"]
    FOUNDERS_DB[record["founder_id"]] = {"founder_score": analysis["multi_axis"]["founder_score"]}


def _public_reference_record(reference: dict[str, Any]) -> dict[str, Any]:
    """Compile a source-attributed public company reference into the API contract.

    These records are for demonstrating sourcing and network intelligence. Their
    scores are curated snapshots, clearly marked as references and excluded from
    a live check recommendation. Market SAM/SOM values remain labeled assumptions.
    """
    founders = list(reference["founders"])
    lead = founders[0]
    market = reference["market"]
    batch = reference["batch"]
    profile = {
        "company_name": reference["company_name"],
        "founder_name": lead["name"],
        "founder_role": lead["role"],
        "photo_url": lead["avatar"],
        "founder_background": lead["background"],
        "founder_affiliations": lead["affiliations"],
        "founder_ai_read": "Portrait, role, and biography are mapped from the cited official YC company profile.",
        "team_members": [
            {
                "name": founder["name"], "role": founder["role"], "photo_url": founder["avatar"],
                "background": founder["background"], "affiliations": founder["affiliations"],
                "ai_read": "Portrait, role, and biography are mapped from the cited official YC company profile.",
            }
            for founder in founders[1:]
        ],
        "sector": reference["sector"],
        "stage": "Public reference company",
        "geography": reference["geography"],
        "website": reference["website"],
        "reference_profile": True,
        "reference_label": "Curated public reference — not a current investment recommendation",
        "reference_problem": reference["problem"],
        "reference_solution": reference["solution"],
        "reference_traction": reference["traction"],
        "reference_competitors": reference["competitors"],
        "reference_market_method": market["basis"],
        "reference_batch": batch,
    }
    claims = [
        {"field": "team", "value": "; ".join(f"{f['name']} ({f['role']})" for f in founders) + f". {batch}.", "source_slide": 1, "source_label": "Official YC profile"},
        {"field": "problem_product", "value": reference["solution"], "source_slide": 2, "source_label": "Official YC profile"},
        {"field": "market_size", "value": f"TAM {market['tam']}. {market['basis']}", "source_slide": 3, "source_label": "External market benchmark"},
        {"field": "market_size", "value": f"SAM {market['sam']}. {market['basis']}", "source_slide": 4, "source_label": "FounderScore assumption model"},
        {"field": "market_size", "value": f"SOM {market['som']}. {market['basis']}", "source_slide": 5, "source_label": "FounderScore assumption model"},
        {"field": "traction", "value": reference["traction"], "source_slide": 6, "source_label": "Official YC profile"},
    ]
    signal = {
        "founder_id": reference["founder_id"], "company_id": reference["company_id"],
        "deck_claims": claims,
        # Company/project evidence is never mislabeled as a founder's personal
        # GitHub, launch, or paper count.
        "public_signals": {
            "github": {"repos": 0, "commit_consistency_score": 0.0, "longevity_months": 0},
            "devpost_hn": {"launches": 0, "total_upvotes": 0},
            "arxiv": {"papers": 0},
        },
        "sourcing_channel": "outbound", "cold_start_flag": False,
    }
    sources = [
        {
            "type": "company_website", "title": f"{reference['company_name']} · official website",
            "url": reference["website"], "excerpt": reference["solution"],
            "image_url": reference["logo_url"], "favicon_url": reference["logo_url"],
            "source": reference["company_name"], "page": None, "retrieved_at": "2026-07-18T00:00:00+00:00",
        },
        {
            "type": "public_reference", "title": f"yc_profile · {reference['company_name']} and founders",
            "url": reference["yc_url"], "excerpt": f"{batch}. {reference['traction']}",
            "image_url": lead["avatar"], "source": "Y Combinator", "page": 1, "retrieved_at": "2026-07-18T00:00:00+00:00",
        },
        {
            "type": "market_research", "title": f"market_model · {reference['sector']}",
            "url": market["url"], "excerpt": market["basis"], "source": "External benchmark + FounderScore assumptions",
            "page": 3, "retrieved_at": "2026-07-18T00:00:00+00:00",
        },
    ]
    if market.get("secondary_url"):
        sources.append({
            "type": "market_research", "title": f"market_model · {reference['sector']} serviceable segment",
            "url": market["secondary_url"], "excerpt": market["basis"], "source": "External market benchmark",
            "page": 4, "retrieved_at": "2026-07-18T00:00:00+00:00",
        })
    score = int(reference["founder_score"])
    market_rating = reference["market_rating"]
    idea_rating = reference["idea_rating"]
    analysis = {
        "verdict": "review",
        "multi_axis": {
            "founder_axis": {
                "score": score, "trend": "stable",
                "rationale": f"The official accelerator profile identifies the full founding team and specific prior execution signals. This {score} is a curated sourcing reference, not a live underwriting score.",
                "citations": ["yc_profile"],
            },
            "market_axis": {
                "rating": market_rating, "trend": "improving" if market_rating == "bullish" else "stable",
                "rationale": f"The external benchmark supports a meaningful {reference['sector']} category. SAM and SOM are visible assumptions, not company claims, and should be sensitivity-tested before investment.",
                "citations": ["market_model"],
            },
            "idea_vs_market_axis": {
                "rating": idea_rating, "trend": "stable",
                "rationale": f"{reference['solution']} The cited public profile supplies product context, while customer and retention diligence remains separate.",
                "citations": ["yc_profile"],
            },
            "founder_score": {"value": score, "confidence_interval": 10, "trend": "stable"},
        },
        "thesis": {"thesis_match": False, "match_type": "exact", "rationale": "Public sourcing reference; excluded from the current pre-seed check decision."},
        "diligence_memo": {
            "diligence": {"tavily_sources_checked": [market["url"], reference["yc_url"]], "flagged_claims": [], "memory_update": False},
            "trust": {"claim_trust": [
                {"claim": "team", "confidence": "high", "evidence": "Names, roles, portraits, and disclosed backgrounds are mapped from the official YC company profile."},
                {"claim": "problem_product", "confidence": "high", "evidence": "Product scope is mapped from the official YC and company profiles."},
                {"claim": "market_size", "confidence": "medium", "evidence": "TAM has an external benchmark; SAM and SOM are explicitly identified as FounderScore assumptions."},
                {"claim": "traction", "confidence": "medium", "evidence": "Accelerator-reported evidence is retained, but customer and revenue metrics are not independently audited here."},
            ]},
            "memo": {
                "required": {
                    "company_snapshot": f"{reference['company_name']} is a sourced public reference in {reference['sector']}.",
                    "investment_hypotheses": ["Technical founding-team signal", "Large category with a defined wedge", "Public execution evidence warrants deeper diligence"],
                    "swot": {
                        "strengths": ["Named team with public execution history", "Clear product wedge"],
                        "weaknesses": ["Reference profile is not a current data room"],
                        "opportunities": [market["basis"]],
                        "threats": [f"Competition: {', '.join(reference['competitors'])}"],
                    },
                    "problem_and_product": f"Problem: {reference['problem']} Solution: {reference['solution']}",
                    "traction_kpis": reference["traction"],
                },
                "optional_or_flagged": {
                    "team_and_history": "; ".join(f"{f['name']} — {f['background']}" for f in founders),
                    "cap_table": "Not disclosed in public reference",
                },
            },
            "adversarial_view": {"challenges": ["The public profile is useful for sourcing but cannot replace current customer, financial, legal, and technical diligence.", "SAM and SOM depend on explicit share assumptions and should be scenario-tested."]},
            "portfolio_check": {"overlap": False, "note": "Reference profile; run against the live portfolio before a decision."},
            "verdict": "review", "amount_recommended": 0,
        },
    }
    return {"profile": profile, "signal": signal, "sources": sources, "analysis": analysis}


def load_fixture_data() -> None:
    OPPORTUNITIES_DB.clear()
    FOUNDERS_DB.clear()
    fixture_names = [
        "signal_intake_strong.json", "signal_intake_cold_start.json", "signal_intake_exact_match.json",
        "signal_intake_adjacent.json", "signal_intake_reject.json",
    ]
    for fixture_name in fixture_names:
        payload = json.loads((FIXTURE_ROOT / fixture_name).read_text())
        company_id = payload["company_id"]
        profile = {**DEMO_PROFILES.get(company_id, {}), "company_name": DEMO_PROFILES.get(company_id, {}).get("one_liner", f"Company {company_id}").split(".")[0]}
        # Company labels are deliberately stable and human-readable for the demo data set.
        profile["company_name"] = {"c001": "Circuitline", "c002": "Kelpwise", "c003": "Ferrite", "c004": "Cloudspan", "c005": "Tableloop"}[company_id]
        existing = store.get(company_id)
        if existing and existing.get("analysis"):
            _cache_application(existing)
            continue
        traces = [{"agent": "screen", "label": "Screen", "kind": "rule", "summary": "Fixture is complete and passed required-input validation.", "ms": 1}]
        merged_signal, analysis = _analysis_for(payload, profile, traces)
        documents = [{"kind": "deck_fixture", "title": fixture_name, "page": item.get("source_slide"), "text": item.get("value", ""), "file_url": None} for item in payload.get("deck_claims", [])]
        sources = [{"type": "deck", "title": f"Deck slide {item.get('source_slide')}", "url": f"/opportunities/{company_id}", "excerpt": item.get("value", ""), "source": "Seeded pitch-deck fixture", "page": item.get("source_slide")} for item in payload.get("deck_claims", [])]
        store.upsert_application(company_id=company_id, founder_id=payload["founder_id"], company_name=profile["company_name"], status="ready", profile=profile, documents=documents, sources=sources, signal=merged_signal, analysis=analysis, trace=traces)
        _cache_application(store.get(company_id) or {})

    # These are intentionally separate from the synthetic early-stage fixtures:
    # each is a public reference profile with attributable sources and an explicit
    # "not an investment recommendation" marker in the UI. They make the sourcing
    # demo concrete without pretending a mature company is a live $100K candidate.
    reference_path = FIXTURE_ROOT / "curated_public_references.json"
    if reference_path.exists():
        for reference in json.loads(reference_path.read_text()):
            company_id = reference["company_id"]
            trace = [{
                "agent": "source", "label": "Curated public reference", "kind": "rule",
                "summary": "Official public company and project sources retained for sourcing-context demonstration; excluded from live underwriting.",
                "ms": 1,
            }]
            store.upsert_application(
                company_id=company_id,
                founder_id=reference["founder_id"],
                company_name=reference["company_name"],
                status="ready",
                profile=reference["profile"],
                documents=[],
                sources=reference["sources"],
                signal=reference["signal"],
                analysis=reference["analysis"],
                trace=trace,
            )
            _cache_application(store.get(company_id) or {})

    cohort_path = FIXTURE_ROOT / "curated_public_cohort.json"
    if cohort_path.exists():
        for reference in json.loads(cohort_path.read_text()):
            compiled = _public_reference_record(reference)
            trace = [{
                "agent": "source", "label": "Public-source graph", "kind": "rule",
                "summary": "Official accelerator, company, founder portrait, and market-source nodes mapped into the sourcing graph.",
                "ms": 1,
            }]
            store.upsert_application(
                company_id=reference["company_id"], founder_id=reference["founder_id"],
                company_name=reference["company_name"], status="ready", profile=compiled["profile"],
                documents=[], sources=compiled["sources"], signal=compiled["signal"],
                analysis=compiled["analysis"], trace=trace,
            )
            _cache_application(store.get(reference["company_id"]) or {})

    # Fixtures give the demo a useful starting state, but real applications are
    # the durable product data. Reload every completed record after a server
    # restart so a processed founder never vanishes from the pipeline merely
    # because the API process was restarted.
    for record in store.all():
        if record.get("status") == "ready" and record.get("signal") and record.get("analysis"):
            _cache_application(record)


@app.on_event("startup")
async def startup_event() -> None:
    print("Loading persisted applications and fixture seed data...")
    try:
        load_fixture_data()
        print(f"Loaded {len(OPPORTUNITIES_DB)} ready opportunities")
    except Exception as exc:
        print(f"Warning: fixture load failed: {exc}")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "FounderScore API"}


@app.get("/thesis", response_model=ThesisConfig)
def get_thesis() -> ThesisConfig:
    return ThesisConfig(**current_thesis_config())


@app.put("/thesis", response_model=ThesisConfig)
def update_thesis(config: ThesisConfig) -> ThesisConfig:
    """Persist settings for future application analyses; existing decisions stay auditable."""
    stored = store.set_thesis(config.model_dump())
    return ThesisConfig(**stored)


def _assemble_opportunity(company_id: str) -> OpportunityResponse:
    record = OPPORTUNITIES_DB[company_id]
    signal = record["signal"]
    analysis = record["analysis"]
    multi_axis = analysis["multi_axis"]
    diligence_memo = analysis["diligence_memo"]
    profile = record["profile"]
    documents = record.get("documents", [])
    preview_by_page = {document.get("page"): document.get("preview_url") for document in documents}
    sources = [
        {**source, "preview_url": source.get("preview_url") or preview_by_page.get(source.get("page"))}
        for source in record.get("sources", [])
    ]
    sources = relevant_sources(record["company_name"], sources, profile.get("website"))
    enrichment = build_enrichment(profile, signal, sources, record.get("trace", []))
    enrichment["news"] = [
        {"title": source["title"], "source": source.get("source") or "Public source", "date": (source.get("retrieved_at") or "")[:10], "url": source.get("url")}
        # Use the same company-specific, de-noised source set as the ledger.
        # Reading the raw record here previously reintroduced broad fundraising
        # roundups that had already been filtered out above.
        for source in sources
        if source.get("type") == "news"
    ]
    # Older persisted records created before the API envelope gained a top-level
    # verdict still retain the canonical diligence verdict. Read that fallback so a
    # single legacy record cannot break the entire opportunity list.
    verdict = record.get("decision") or analysis.get("verdict") or diligence_memo.get("verdict", "review")
    concise = concise_memo(record["company_name"], enrichment, analysis)
    return OpportunityResponse(
        founder_id=record["founder_id"], company_id=company_id, company_name=record["company_name"],
        sourcing_channel=signal["sourcing_channel"], cold_start_flag=signal["cold_start_flag"],
        founder_score=FounderScoreResponse(**multi_axis["founder_score"]),
        founder_axis=AxisScoreResponse(**multi_axis["founder_axis"]),
        market_axis=AxisRatingResponse(**multi_axis["market_axis"]),
        idea_vs_market_axis=AxisRatingResponse(**multi_axis["idea_vs_market_axis"]),
        claim_trust=[ClaimTrust(**item) for item in diligence_memo["trust"]["claim_trust"]],
        memo=MemoResponse(required=MemoRequired(**concise["required"]), optional_or_flagged=MemoOptional(**concise["optional_or_flagged"])),
        adversarial_view=AdversarialView(**diligence_memo["adversarial_view"]),
        portfolio_check=PortfolioCheck(**diligence_memo["portfolio_check"]),
        verdict=verdict,
        amount_recommended=diligence_memo["amount_recommended"] if verdict == "approve" else 0,
        thesis=analysis["thesis"], enrichment=enrichment, sources=sources,
        documents=documents, processing_trace=record.get("trace", []), status=record["status"],
        public_signals=signal.get("public_signals", {}),
    )


@app.get("/opportunities/{company_id}", response_model=OpportunityResponse)
def get_opportunity(company_id: str) -> OpportunityResponse:
    if company_id not in OPPORTUNITIES_DB:
        record = store.get(company_id)
        if record:
            if record.get("status") != "ready":
                raise HTTPException(status_code=409, detail="Application is still processing")
            if record.get("signal") and record.get("analysis"):
                _cache_application(record)
        if company_id in OPPORTUNITIES_DB:
            return _assemble_opportunity(company_id)
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return _assemble_opportunity(company_id)


@app.get("/founders/{founder_id}/results", response_model=FounderResultsResponse)
def get_founder_results(founder_id: str) -> FounderResultsResponse:
    founder = FOUNDERS_DB.get(founder_id)
    if not founder:
        raise HTTPException(status_code=404, detail="Founder not found")
    score = founder["founder_score"]
    narrative = (
        f"Your current Founder Score is {score['value']}. It is based on submitted information and corroborating public signals; additional evidence can narrow its confidence range."
    )
    return FounderResultsResponse(founder_score=FounderScoreResponse(**score), narrative=narrative)


def _session_for(record: dict[str, Any], session_record: dict[str, Any]) -> InterviewSession:
    session = _interview_agent.start(record["signal"].get("deck_claims", []))
    session.questions_asked = list(session_record["questions"])
    session.responses = list(session_record["responses"])
    return session


def _recompute_after_interview(record: dict[str, Any], interview_result: dict[str, Any]) -> None:
    """Recompute the persistent score without changing the independent axis judgments.

    The score composition uses the documented formula.  Its interview component is C's
    response-pattern score; the other components stay grounded in the already persisted
    axis and per-claim trust outputs, so completing an interview cannot overwrite a
    previously audited memo or fabricate new market evidence.
    """
    analysis = dict(record["analysis"])
    multi_axis = dict(analysis["multi_axis"])
    founder_axis = int(multi_axis["founder_axis"]["score"])
    trust = analysis["diligence_memo"]["trust"]["claim_trust"]
    confidence_points = {"high": 90, "medium": 60, "low": 30}
    traction_points = [confidence_points[item["confidence"]] for item in trust if item["claim"] == "traction"]
    traction_signal = round(sum(traction_points) / len(traction_points)) if traction_points else 50
    idea_rating = multi_axis["idea_vs_market_axis"]["rating"]
    founder_market_fit = {"bullish": 85, "neutral": 60, "bear": 30}[idea_rating]
    recomputed = calculate_founder_score_from_axes(
        founder_axis_score=founder_axis,
        traction_signal_score=traction_signal,
        founder_market_fit_score=founder_market_fit,
        resilience_score=int(interview_result["resilience_score"]),
        cold_start=bool(record["signal"].get("cold_start_flag")),
    )
    multi_axis["founder_score"] = recomputed.model_dump()
    analysis["multi_axis"] = multi_axis
    analysis["interview"] = interview_result
    trace = list(record.get("trace", []))
    trace.append({
        "agent": "interview",
        "label": "Interview Agent",
        "kind": "ai",
        "summary": f"{len(interview_result['questions_asked'])} adaptive questions completed · response pattern recorded · Founder Score recomputed.",
        "ms": 1,
    })
    sources = list(record.get("sources", []))
    sources.append({
        "type": "interview",
        "title": "Adaptive founder interview",
        "url": f"/founders/{record['founder_id']}/results",
        "excerpt": "Completed interview was scored by response pattern and used to recompute the persistent Founder Score.",
        "source": "FounderScore Interview Agent",
        "page": None,
        "retrieved_at": None,
    })
    store.update_processing(record["company_id"], status="ready", analysis=analysis, trace=trace, sources=sources)
    _cache_application(store.get(record["company_id"]) or {})


def _interview_view(session: dict[str, Any]) -> InterviewView:
    return InterviewView(
        session_id=session["session_id"],
        status=session["status"],
        question=session["questions"][-1] if session["status"] == "active" and session["questions"] else None,
        question_number=len(session["questions"]),
        total_questions=5,
        completed=session["status"] == "completed",
    )


@app.post("/founders/{founder_id}/interviews", response_model=InterviewView)
def start_or_resume_interview(founder_id: str) -> InterviewView:
    record = store.get_by_founder(founder_id)
    if not record or not record.get("signal"):
        raise HTTPException(status_code=404, detail="Founder application not found")
    latest = store.get_latest_interview(founder_id)
    if latest:
        return _interview_view(latest)
    session = _interview_agent.start(record["signal"].get("deck_claims", []), max_questions=5)
    first_question = session.next_question()
    if not first_question:
        raise HTTPException(status_code=422, detail="No interview question could be generated")
    created = store.create_interview(
        session_id=f"interview-{uuid.uuid4().hex[:12]}", company_id=record["company_id"], founder_id=founder_id, first_question=first_question
    )
    return _interview_view(created)


@app.post("/interviews/{session_id}/responses", response_model=InterviewView)
def record_interview_response(session_id: str, request: InterviewResponseRequest) -> InterviewView:
    saved = store.get_interview(session_id)
    if not saved:
        raise HTTPException(status_code=404, detail="Interview session not found")
    if saved["status"] == "completed":
        return _interview_view(saved)
    record = store.get(saved["company_id"])
    if not record or not record.get("signal"):
        raise HTTPException(status_code=404, detail="Application not found")
    session = _session_for(record, saved)
    try:
        session.record_response(request.response)
        next_question = session.next_question()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if next_question:
        updated = store.update_interview(session_id, status="active", questions=session.questions_asked, responses=session.responses)
        return _interview_view(updated)
    result = session.result()
    updated = store.update_interview(session_id, status="completed", questions=session.questions_asked, responses=session.responses, result=result)
    _recompute_after_interview(record, result)
    return _interview_view(updated)


@app.post("/opportunities/{company_id}/decision")
def record_decision(company_id: str, request: DecisionRequest) -> dict[str, str]:
    if company_id not in OPPORTUNITIES_DB:
        record = store.get(company_id)
        if record and record.get("status") == "ready" and record.get("signal") and record.get("analysis"):
            _cache_application(record)
        else:
            raise HTTPException(status_code=404, detail="Opportunity not found")
    store.set_decision(company_id, request.decision)
    OPPORTUNITIES_DB[company_id]["decision"] = request.decision
    return {"company_id": company_id, "decision": request.decision, "status": "recorded"}


@app.get("/opportunities", response_model=list[OpportunityResponse])
def list_opportunities(query: Optional[str] = None, thesis_filter: bool = False) -> list[OpportunityResponse]:
    results = []
    for company_id, record in OPPORTUNITIES_DB.items():
        if thesis_filter and not record["analysis"]["thesis"]["thesis_match"]:
            continue
        if query:
            try:
                structured_query = parse_natural_language_query(query)
                if not match_opportunity(record["signal"], structured_query)[0]:
                    continue
            except Exception:
                # The browser still performs its own simple text filter; a parser failure should not hide data.
                pass
        results.append(_assemble_opportunity(company_id))
    return results


def _process_application(company_id: str) -> None:
    record = store.get(company_id)
    if not record:
        return
    started = time.monotonic()
    traces = [{"agent": "screen", "label": "Screen", "kind": "rule", "summary": "Required founder identity, company name, and supporting document received.", "ms": 1, "stage": "queued"}]
    try:
        traces.append({"agent": "intake", "label": "Signal Intake", "kind": "ai", "summary": "Reading pages, slide text, and embedded deck images.", "ms": 1, "stage": "reading_deck"})
        store.update_processing(company_id, status="processing", trace=traces)
        document = record["documents"][0]
        document_path = UPLOAD_ROOT / document["stored_name"]
        text, extracted = extract_document(document_path, MEDIA_ROOT, company_id)
        for item in extracted:
            item["file_url"] = document.get("file_url")
            item["stored_name"] = document.get("stored_name")
        traces.append({**_trace("intake", "Signal Intake", "ai", f"Read {len(extracted)} page(s) or slide(s); extracting investment claims next.", started), "stage": "extracting_claims"})
        store.update_processing(company_id, status="processing", documents=extracted, trace=traces)
        claims = extract_deck_claims(document_path)
        signal_model = assemble_signal_intake_output(founder_id=record["founder_id"], company_id=company_id, deck_claims=claims, cold_start_flag=False)
        signal = signal_model.model_dump()
        # Record the deck evidence to Memory (backend/api/db.py) -- previously this only
        # happened for outbound-sourced signals, never for a real deck submission, so a
        # founder's Memory record was permanently incomplete even after they applied.
        save_signal(record["founder_id"], "deck", signal)
        traces.append({"agent": "intake", "label": "Signal Intake", "kind": "rule", "summary": f"{len(claims)} deck claims extracted; checking supplied profiles and company-specific coverage.", "ms": 1, "stage": "checking_sources"})
        store.update_processing(company_id, status="processing", signal=signal, documents=extracted, trace=traces)
        profile, people_sources = enrich_submitted_people(record["profile"])
        profile = cache_verified_profile_avatars(profile, MEDIA_ROOT, company_id)
        github, github_source = github_profile_signal(profile.get("github"))
        signal["public_signals"]["github"] = github
        sources = submitted_link_sources(profile)
        sources.extend(people_sources)
        if github_source:
            sources.append(github_source)
        site_source = fetch_site_metadata(profile.get("website"))
        if site_source:
            sources.append(site_source)
        sources.extend(search_press(record["company_name"], profile.get("website")))
        # A company site is commonly mentioned on the company LinkedIn result
        # rather than typed into the form. Promote only the company-matching
        # domain discovered by the bounded source scan, then retain its own
        # metadata as an auditable source for the investor view.
        discovered_website = build_enrichment(profile, signal, sources, traces).get("website")
        if discovered_website and not profile.get("website"):
            profile = {**profile, "website": discovered_website}
            discovered_site_source = fetch_site_metadata(discovered_website)
            if discovered_site_source:
                sources.append(discovered_site_source)
        sources.extend({
            "type": "deck", "title": item["title"], "url": document["file_url"], "excerpt": item.get("text", ""),
            "source": "Founder-uploaded document", "page": item.get("page"), "preview_url": item.get("preview_url"),
        } for item in extracted)
        traces.append({"agent": "scorer", "label": "Multi-Axis Scorer", "kind": "ai", "summary": "Scoring independent founder, market, and idea-versus-market axes.", "ms": 1, "stage": "scoring"})
        store.update_processing(company_id, status="processing", signal=signal, documents=extracted, sources=sources, trace=traces)
        store.upsert_application(
            company_id=company_id,
            founder_id=record["founder_id"],
            company_name=record["company_name"],
            status="processing",
            profile=profile,
            documents=extracted,
            sources=sources,
            signal=signal,
            trace=traces,
        )
        signal, analysis = _analysis_for(signal, profile, traces)
        store.update_processing(company_id, status="ready", signal=signal, analysis=analysis, documents=extracted, sources=sources, trace=traces)
        _cache_application(store.get(company_id) or {})
    except Exception as exc:
        store.update_processing(company_id, status="failed", trace=traces, error_message=str(exc)[:500])


def _refresh_existing_analysis(company_id: str) -> None:
    """Re-run public signals and reasoning for a completed record after pipeline fixes."""
    record = store.get(company_id)
    if not record or not record.get("signal"):
        return
    profile = dict(record["profile"])
    signal = dict(record["signal"])
    traces = list(record.get("trace", []))
    traces.append({"agent": "intake", "label": "Signal Intake", "kind": "ai", "summary": "Refreshing submitted profiles and company-specific source evidence.", "ms": 1, "stage": "checking_sources"})
    try:
        store.update_processing(company_id, status="processing", signal=signal, trace=traces)
        existing_sources = [source for source in record.get("sources", []) if source.get("type") == "deck"]
        discovered = build_enrichment(profile, signal, record.get("sources", []), traces).get("website")
        if discovered and not profile.get("website"):
            profile["website"] = discovered
        profile, people_sources = enrich_submitted_people(profile)
        profile = cache_verified_profile_avatars(profile, MEDIA_ROOT, company_id)
        github, github_source = github_profile_signal(profile.get("github"))
        signal["public_signals"]["github"] = github
        sources = submitted_link_sources(profile)
        sources.extend(people_sources)
        if github_source:
            sources.append(github_source)
        site_source = fetch_site_metadata(profile.get("website"))
        if site_source:
            sources.append(site_source)
        sources.extend(search_press(record["company_name"], profile.get("website")))
        sources.extend(existing_sources)
        traces.append({"agent": "scorer", "label": "Multi-Axis Scorer", "kind": "ai", "summary": "Recomputing independent axes with refreshed public signals and corrected thesis logic.", "ms": 1, "stage": "scoring"})
        store.upsert_application(company_id=company_id, founder_id=record["founder_id"], company_name=record["company_name"], status="processing", profile=profile, documents=record["documents"], sources=sources, signal=signal, trace=traces)
        signal, analysis = _analysis_for(signal, profile, traces)
        store.update_processing(company_id, status="ready", signal=signal, analysis=analysis, sources=sources, trace=traces)
        _cache_application(store.get(company_id) or {})
    except Exception as exc:
        store.update_processing(company_id, status="failed", trace=traces, error_message=str(exc)[:500])


@app.post("/opportunities/{company_id}/reprocess", response_model=ApplicationSubmission, status_code=202)
def reprocess_opportunity(company_id: str, background_tasks: BackgroundTasks) -> ApplicationSubmission:
    record = store.get(company_id)
    if not record or not record.get("signal"):
        raise HTTPException(status_code=404, detail="Completed opportunity not found")
    background_tasks.add_task(_refresh_existing_analysis, company_id)
    return ApplicationSubmission(company_id=company_id, founder_id=record["founder_id"], status="queued", status_url=f"/applications/{company_id}")


@app.post("/outbound/scan", response_model=OutboundScanTrigger, status_code=202)
def trigger_outbound_scan(background_tasks: BackgroundTasks) -> OutboundScanTrigger:
    """Manual trigger for the bounded outbound scan (GitHub/HN/arXiv -> Thesis filter ->
    partial score -> Activate -> outreach). Deliberately manual, not an automatic
    schedule -- this makes real Tavily/OpenAI calls and can send real email once
    EMAIL_SMTP_HOST is configured, so it shouldn't fire unattended without a conscious
    decision each time. Runs as a background task since a full pass can take minutes."""
    background_tasks.add_task(run_outbound_pass)
    return OutboundScanTrigger(status="started", detail="Outbound scan running in the background; check /outbound/leads shortly.")


@app.get("/outbound/leads", response_model=list[OutboundLead])
def list_outbound_leads() -> list[OutboundLead]:
    """Outbound-sourced candidates with at least one outreach event, most recent first.
    Distinct from /opportunities -- these haven't necessarily converted into a full
    deck-backed opportunity yet (see outreach_status)."""
    return [OutboundLead(**lead) for lead in db_list_outbound_leads()]


@app.get("/outbound/unsubscribe/{founder_id}", response_class=HTMLResponse)
def unsubscribe_outbound_lead(founder_id: str) -> str:
    """Landing page for the unsubscribe link in outbound_scan.draft_activation_email.
    Records 'declined' regardless of prior state -- an unsubscribe click is authoritative
    and should always be honored, even if we'd otherwise have called them 'converted'."""
    save_outreach_event(founder_id, "declined")
    return (
        "<html><body style='font-family: sans-serif; max-width: 480px; margin: 80px auto; text-align: center;'>"
        "<h2>You've been unsubscribed</h2>"
        "<p>We won't reach out to you again. Sorry for the noise.</p>"
        "</body></html>"
    )


@app.post("/applications", response_model=ApplicationSubmission, status_code=202)
def submit_application(
    background_tasks: BackgroundTasks,
    founder_name: str = Form(..., min_length=2, max_length=120),
    company_name: str = Form(..., min_length=2, max_length=120),
    deck: UploadFile = File(...),
    founder_role: str = Form("Founder", max_length=120),
    email: str = Form("", max_length=254),
    website: str = Form("", max_length=300),
    github: str = Form("", max_length=300),
    linkedin: str = Form("", max_length=300),
    x: str = Form("", max_length=300),
    devpost: str = Form("", max_length=300),
    product_hunt: str = Form("", max_length=300),
    arxiv: str = Form("", max_length=300),
    sector: str = Form("", max_length=100),
    stage: str = Form("Pre-seed", max_length=60),
    geography: str = Form("", max_length=120),
    team_members_json: str = Form("", max_length=12000),
    founder_photo: UploadFile | None = File(None),
    ref: str = Form("", max_length=200),
) -> ApplicationSubmission:
    """ref, when present, is an outbound candidate's founder_id (see the Apply link in
    outbound_scan.draft_activation_email) -- reusing it instead of minting a fresh one is
    what converges their outbound discovery history (GitHub/HN/arXiv signals, partial
    score) with this real deck submission under one founder_id, rather than starting a
    disconnected record. recompute_founder_score() already reads all signals for a
    founder_id regardless of source, so this "just works" once the id is shared."""
    if not deck.filename or not allowed_filename(deck.filename):
        raise HTTPException(status_code=415, detail="Upload a PDF, PPTX, DOCX, TXT, or Markdown document.")
    company_id = f"app-{uuid.uuid4().hex[:10]}"
    converted_from_outbound = bool(ref.strip())
    founder_id = ref.strip() if converted_from_outbound else f"founder-{uuid.uuid4().hex[:10]}"
    extension = Path(deck.filename).suffix.lower()
    stored_name = f"{company_id}{extension}"
    destination = UPLOAD_ROOT / stored_name
    try:
        copy_uploaded_file(deck, destination, MAX_DOCUMENT_BYTES)
        profile = {
            "founder_name": founder_name.strip(), "founder_role": founder_role.strip(), "email": email.strip(),
            "website": valid_public_url(website), "github": valid_public_url(github), "linkedin": valid_public_url(linkedin),
            "x": valid_public_url(x), "devpost": valid_public_url(devpost), "product_hunt": valid_public_url(product_hunt),
            "arxiv": valid_public_url(arxiv), "sector": sector.strip() or "Not disclosed", "stage": stage.strip() or "Not disclosed",
            "geography": geography.strip() or "Not disclosed", "company_name": company_name.strip(),
        }
        team_members = _parse_team_members(team_members_json)
        if team_members:
            profile["team_members"] = team_members
        if founder_photo and founder_photo.filename:
            photo_extension = Path(founder_photo.filename).suffix.lower() or ".jpg"
            photo_name = f"{company_id}-founder{photo_extension}"
            (MEDIA_ROOT / "founders").mkdir(parents=True, exist_ok=True)
            copy_photo(founder_photo, MEDIA_ROOT / "founders" / photo_name, MAX_PHOTO_BYTES)
            profile["photo_url"] = f"/media/founders/{photo_name}"
        document = {"kind": "uploaded_document", "title": deck.filename, "stored_name": stored_name, "file_url": f"/uploads/{stored_name}", "page": None, "text": ""}
        store.upsert_application(company_id=company_id, founder_id=founder_id, company_name=company_name.strip(), status="queued", profile=profile, documents=[document], sources=[], trace=[])
        if converted_from_outbound:
            save_outreach_event(founder_id, "converted", company_id=company_id, cold_start_flag=False)
    except DocumentIntakeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    background_tasks.add_task(_process_application, company_id)
    return ApplicationSubmission(company_id=company_id, founder_id=founder_id, status="queued", status_url=f"/applications/{company_id}")


@app.get("/applications/{company_id}", response_model=ApplicationStatus)
def application_status(company_id: str) -> ApplicationStatus:
    record = store.get(company_id)
    if not record:
        raise HTTPException(status_code=404, detail="Application not found")
    stage = record["trace"][-1].get("stage") if record.get("trace") else None
    return ApplicationStatus(company_id=company_id, founder_id=record["founder_id"], company_name=record["company_name"], status=record["status"], stage=stage, error_message=record["error_message"], opportunity_url=f"/opportunities/{company_id}" if record["status"] == "ready" else None)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
