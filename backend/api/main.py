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
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.diligence_memo import ClaimValidator, DiligenceMemoPipeline, MemoSynthesizer
from backend.diligence_memo.clients import OpenAIReasoningClient, TavilySearchClient
from backend.scoring import evaluate_thesis_fit, match_opportunity, parse_natural_language_query, score_all_axes
from backend.signal_intake.deck_parser import assemble_signal_intake_output, extract_deck_claims

from backend.api.document_intake import (
    DocumentIntakeError,
    allowed_filename,
    copy_photo,
    copy_uploaded_file,
    extract_document,
)
from backend.api.source_enrichment import fetch_site_metadata, github_profile_signal, search_press, submitted_link_sources, valid_public_url
from backend.api.store import ApplicationStore


ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT / "backend" / "data"
UPLOAD_ROOT = DATA_ROOT / "uploads"
MEDIA_ROOT = DATA_ROOT / "media"
FIXTURE_ROOT = ROOT / "shared" / "fixtures"
MAX_DOCUMENT_BYTES = 25 * 1024 * 1024
MAX_PHOTO_BYTES = 5 * 1024 * 1024

for directory in (UPLOAD_ROOT, MEDIA_ROOT):
    directory.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="FounderScore API", description="Investor-grade founder diligence", version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
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
    error_message: str | None = None
    opportunity_url: str | None = None


DEMO_PROFILES: dict[str, dict[str, Any]] = {
    "c001": {"founder_name": "Jordan Chen", "sector": "Developer tools", "stage": "Pre-seed", "geography": "Boston, US", "one_liner": "AI-assisted code review for production distributed systems."},
    "c002": {"founder_name": "Avery Brooks", "sector": "Climate", "stage": "Pre-seed", "geography": "Portland, US", "one_liner": "Carbon footprint tracking for small businesses."},
    "c003": {"founder_name": "Nadia Alvarez", "sector": "AI infrastructure", "stage": "Pre-seed", "geography": "San Francisco, US", "one_liner": "LLM inference optimization through compression and routing."},
    "c004": {"founder_name": "Marcus Lee", "sector": "Cloud infrastructure", "stage": "Pre-seed", "geography": "Seattle, US", "one_liner": "Multi-cloud workload orchestration and intelligent load balancing."},
    "c005": {"founder_name": "Sam Patel", "sector": "Consumer", "stage": "Pre-seed", "geography": "Chicago, US", "one_liner": "A restaurant discovery app for local dining."},
}


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


def _analysis_for(signal: dict[str, Any], profile: dict[str, Any], traces: list[dict[str, Any]]) -> dict[str, Any]:
    started = time.monotonic()
    multi_axis = score_all_axes(signal)
    traces.append(_trace("scorer", "Multi-Axis Scorer", "ai", "Three independent axes scored from submitted deck and public signals.", started))
    started = time.monotonic()
    thesis = evaluate_thesis_fit(signal)
    traces.append(_trace("thesis", "Thesis Engine", "rule", thesis.rationale, started))
    started = time.monotonic()
    diligence_memo = _diligence_pipeline.run({"company_name": profile["company_name"], "sector": profile.get("sector"), "deck_claims": signal.get("deck_claims", [])})
    traces.append(_trace("diligence", "Diligence", "ai", f"{len(diligence_memo['trust']['claim_trust'])} deck claims checked against bounded public sources.", started))
    verdict = "decline" if not thesis.thesis_match else diligence_memo["verdict"]
    traces.append({"agent": "memo", "label": "Memo Synthesizer", "kind": "ai", "summary": "Investment memo, trust assessment, and adversarial view assembled.", "ms": 1})
    return {
        "multi_axis": multi_axis.model_dump(),
        "thesis": thesis.model_dump(),
        "diligence_memo": diligence_memo,
        "verdict": verdict,
    }


def _cache_application(record: dict[str, Any]) -> None:
    if not record.get("signal") or not record.get("analysis"):
        return
    OPPORTUNITIES_DB[record["company_id"]] = record
    analysis = record["analysis"]
    FOUNDERS_DB[record["founder_id"]] = {"founder_score": analysis["multi_axis"]["founder_score"]}


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
        analysis = _analysis_for(payload, profile, traces)
        documents = [{"kind": "deck_fixture", "title": fixture_name, "page": item.get("source_slide"), "text": item.get("value", ""), "file_url": None} for item in payload.get("deck_claims", [])]
        sources = [{"type": "deck", "title": f"Deck slide {item.get('source_slide')}", "url": f"/opportunities/{company_id}", "excerpt": item.get("value", ""), "source": "Seeded pitch-deck fixture", "page": item.get("source_slide")} for item in payload.get("deck_claims", [])]
        store.upsert_application(company_id=company_id, founder_id=payload["founder_id"], company_name=profile["company_name"], status="ready", profile=profile, documents=documents, sources=sources, signal=payload, analysis=analysis, trace=traces)
        _cache_application(store.get(company_id) or {})


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


def _assemble_opportunity(company_id: str) -> OpportunityResponse:
    record = OPPORTUNITIES_DB[company_id]
    signal = record["signal"]
    analysis = record["analysis"]
    multi_axis = analysis["multi_axis"]
    diligence_memo = analysis["diligence_memo"]
    profile = record["profile"]
    photo_url = profile.get("photo_url")
    enrichment = _default_enrichment(profile, signal, photo_url)
    enrichment["agent_trace"] = record.get("trace", [])
    enrichment["news"] = [
        {"title": source["title"], "source": source.get("source") or "Public source", "date": (source.get("retrieved_at") or "")[:10], "url": source.get("url")}
        for source in record.get("sources", [])
        if source.get("type") == "news"
    ]
    verdict = record.get("decision") or analysis["verdict"]
    return OpportunityResponse(
        founder_id=record["founder_id"], company_id=company_id, company_name=record["company_name"],
        sourcing_channel=signal["sourcing_channel"], cold_start_flag=signal["cold_start_flag"],
        founder_score=FounderScoreResponse(**multi_axis["founder_score"]),
        founder_axis=AxisScoreResponse(**multi_axis["founder_axis"]),
        market_axis=AxisRatingResponse(**multi_axis["market_axis"]),
        idea_vs_market_axis=AxisRatingResponse(**multi_axis["idea_vs_market_axis"]),
        claim_trust=[ClaimTrust(**item) for item in diligence_memo["trust"]["claim_trust"]],
        memo=MemoResponse(required=MemoRequired(**diligence_memo["memo"]["required"]), optional_or_flagged=MemoOptional(**diligence_memo["memo"]["optional_or_flagged"])),
        adversarial_view=AdversarialView(**diligence_memo["adversarial_view"]),
        portfolio_check=PortfolioCheck(**diligence_memo["portfolio_check"]),
        verdict=verdict,
        amount_recommended=diligence_memo["amount_recommended"] if verdict == "approve" else 0,
        thesis=analysis["thesis"], enrichment=enrichment, sources=record.get("sources", []),
        documents=record.get("documents", []), processing_trace=record.get("trace", []), status=record["status"],
    )


@app.get("/opportunities/{company_id}", response_model=OpportunityResponse)
def get_opportunity(company_id: str) -> OpportunityResponse:
    if company_id not in OPPORTUNITIES_DB:
        record = store.get(company_id)
        if record and record.get("status") != "ready":
            raise HTTPException(status_code=409, detail="Application is still processing")
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


@app.post("/opportunities/{company_id}/decision")
def record_decision(company_id: str, request: DecisionRequest) -> dict[str, str]:
    if company_id not in OPPORTUNITIES_DB:
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
    traces = [{"agent": "screen", "label": "Screen", "kind": "rule", "summary": "Required founder identity, company name, and supporting document received.", "ms": 1}]
    try:
        store.update_processing(company_id, status="processing", trace=traces)
        document = record["documents"][0]
        document_path = UPLOAD_ROOT / document["stored_name"]
        text, extracted = extract_document(document_path, MEDIA_ROOT, company_id)
        for item in extracted:
            item["file_url"] = document.get("file_url")
        traces.append(_trace("intake", "Signal Intake", "ai", f"Extracted text and source references from {len(extracted)} page(s) or slide(s).", started))
        claims = extract_deck_claims(document_path)
        signal_model = assemble_signal_intake_output(founder_id=record["founder_id"], company_id=company_id, deck_claims=claims, cold_start_flag=False)
        signal = signal_model.model_dump()
        github, github_source = github_profile_signal(record["profile"].get("github"))
        signal["public_signals"]["github"] = github
        sources = submitted_link_sources(record["profile"])
        if github_source:
            sources.append(github_source)
        site_source = fetch_site_metadata(record["profile"].get("website"))
        if site_source:
            sources.append(site_source)
        sources.extend(search_press(record["company_name"]))
        sources.extend({"type": "deck", "title": item["title"], "url": document["file_url"], "excerpt": item.get("text", ""), "source": "Founder-uploaded document", "page": item.get("page")} for item in extracted)
        analysis = _analysis_for(signal, record["profile"], traces)
        store.update_processing(company_id, status="ready", signal=signal, analysis=analysis, documents=extracted, sources=sources, trace=traces)
        _cache_application(store.get(company_id) or {})
    except Exception as exc:
        store.update_processing(company_id, status="failed", trace=traces, error_message=str(exc)[:500])


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
    founder_photo: UploadFile | None = File(None),
) -> ApplicationSubmission:
    if not deck.filename or not allowed_filename(deck.filename):
        raise HTTPException(status_code=415, detail="Upload a PDF, PPTX, DOCX, TXT, or Markdown document.")
    company_id = f"app-{uuid.uuid4().hex[:10]}"
    founder_id = f"founder-{uuid.uuid4().hex[:10]}"
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
        if founder_photo and founder_photo.filename:
            photo_extension = Path(founder_photo.filename).suffix.lower() or ".jpg"
            photo_name = f"{company_id}-founder{photo_extension}"
            (MEDIA_ROOT / "founders").mkdir(parents=True, exist_ok=True)
            copy_photo(founder_photo, MEDIA_ROOT / "founders" / photo_name, MAX_PHOTO_BYTES)
            profile["photo_url"] = f"/media/founders/{photo_name}"
        document = {"kind": "uploaded_document", "title": deck.filename, "stored_name": stored_name, "file_url": f"/uploads/{stored_name}", "page": None, "text": ""}
        store.upsert_application(company_id=company_id, founder_id=founder_id, company_name=company_name.strip(), status="queued", profile=profile, documents=[document], sources=[], trace=[])
    except DocumentIntakeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    background_tasks.add_task(_process_application, company_id)
    return ApplicationSubmission(company_id=company_id, founder_id=founder_id, status="queued", status_url=f"/applications/{company_id}")


@app.get("/applications/{company_id}", response_model=ApplicationStatus)
def application_status(company_id: str) -> ApplicationStatus:
    record = store.get(company_id)
    if not record:
        raise HTTPException(status_code=404, detail="Application not found")
    return ApplicationStatus(company_id=company_id, founder_id=record["founder_id"], company_name=record["company_name"], status=record["status"], error_message=record["error_message"], opportunity_url=f"/opportunities/{company_id}" if record["status"] == "ready" else None)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
