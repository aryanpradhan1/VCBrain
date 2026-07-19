# FounderScore — Contract (single source of truth)

Everything here is locked. Both the root `CLAUDE.md` and `AGENTS.md` are just pointers to this file — if the stack or a data shape changes at a sync point, edit only this file.

## What we're building, and why — read this before anything else, whichever module you own

This is a submission for Hack-Nation's 6th Global AI Hackathon, Maschmeyer Group's challenge track: "The VC Brain — Deploying $100K Checks in 24 Hours."

**The problem:** founders stay invisible until they know the right person. Their story is scattered across pitch decks, GitHub repos, half-built websites, social posts nobody's reading closely. Diligence takes weeks. Capital flows through networks, not merit. By the time a fund finally sees a founder clearly, dozens of equally strong ones have already given up waiting.

**What we're building:** a system that finds strong founders before they start fundraising, judges them fast and honestly, and gets a real $100K decision back to them within 24 hours — whether they were sourced (spotted on GitHub/Devpost/arXiv before they applied) or inbound (applied directly). Scope is Sourcing → Screening → Diligence → Decision. Portfolio monitoring, follow-on, fund ops, and exit are explicitly out of scope — don't build UI or logic for them.

**The mechanism that makes this more than a form and a spreadsheet:** every founder gets a **Founder Score** — a persistent, cross-application number, a credit score for founders, that never resets and gets sharper with every milestone (see the formula below). A founder who doesn't get funded this time still walks away with something real. This is the retention hook and the thing that makes the product defensible.

**The test that decides what gets built with AI and what doesn't:** "The bottleneck this replaces isn't a spreadsheet — it's an analyst's days of unstructured reading and judgment. Anything a spreadsheet could already do, we didn't build with AI. Everything we did build with AI is exactly the part a spreadsheet can't do." Screening's cheap pre-filter, raw signal stats, and the Thesis Engine's keyword gate stay rule-based on purpose — that's correct, not a shortcut. Multi-axis reasoning, Founder-Market Fit, the Interview Agent, and Diligence's cross-referencing are where AI is load-bearing — delete those and the product collapses into exactly the slow, network-gated status quo this is supposed to replace.

**How the judges are scoring it** (build in this priority order — see "Never cut first" at the bottom of this file too):
- Data Architecture and Intelligence — 30% — ingestion, dedup, and honesty about founders with no track record specifically.
- Investment Utility & Execution — 30% — does this produce a recommendation a human could act on within 24 hours.
- Intelligent Analysis and Trust — 25% — does the Trust Score actually surface evidence and uncertainty, not just assert a number.
- User Experience and Design — 15% — real, but protect the other three first if time runs short.

**The one UI rule every agent should know, even backend:** founders only ever see their Founder Score + a plain-language narrative — never the 3-axis scores, SWOT, or memo, which are the fund's confidential work product. Full detail and examples are in `/frontend/CLAUDE.md`, but every agent's output should assume this split exists downstream — e.g. the founder-facing API response is deliberately much thinner than the investor-facing one.

## Tech stack — locked before anyone codes

| Layer | Choice |
|---|---|
| Backend | FastAPI (Python) |
| LLM provider | OpenAI |
| Frontend | React + Vite + Tailwind + shadcn/ui |
| Data storage | SQLite |
| Deployment | Railway/Render (backend) + Vercel (frontend), only if time allows after 1:00 AM. Localhost + screen recording is the safe fallback — don't let deployment risk eat build time. |
| Dummy data | 3 synthetic decks (strong / cold-start / weak) + mocked public-signal fixtures, in `/shared/fixtures/`, written before Block 1 |

**Change process:** proposed only at a sync point, never mid-block unilaterally. One person (stack owner, likely B) is the only one who edits this table. Any change is logged in `/shared/CHANGELOG.md` with a timestamp. Hard rule: no stack changes after Block 2 (8:30 PM) except a genuine blocker — work around it instead of replatforming.

## Architecture — three layers

**Memory layer** — structured knowledge base (founders, decks, signals): extracted fields only, never raw scraped pages. Timestamped, deduplicated, source-tagged, persistent. Houses the Founder Score, recomputed event-triggered (EMA-style, confidence interval narrows with corroboration — never retraining). Diligence's gap-findings write back here, updating the founder's persistent record.

**Intelligence layer** — Thesis Engine (deterministic sector/stage/geography/check-size gate + LLM fit judgment for ambiguous matches); Multi-axis score (Founder/Market/Idea-vs-Market, LLM reasoning with per-axis citations, never averaged, each with an independent trend); Trust Score (per claim, confidence label + citation, contradictions flagged before reaching the investor).

**Experience layer** — investor dashboard (ranked list + momentum trend); memo and adversarial view as two distinct rendered artifacts; founder results page (separate, lightweight, read-only).

## Pipeline stages

- **Sourcing**: Inbound (apply: deck + name) + Outbound (bounded daily scan → thesis-filtered → partial Founder Score → activate above threshold → converge into one funnel)
- **Screening**: a fast, shallow 3-axis pass on readily-available signals — a real cheap scoring pass, not just a rule
- **Diligence**: truth-gap check — verifies evidence, logs gaps, writes back to Memory
- **Decision**: $100K recommendation + adversarial check + portfolio check (one-time overlap check against existing portfolio sectors)

## Founder Score

```
Founder Score = 0.30 × Track Record + 0.20 × Traction Signal
              + 0.25 × Founder-Market Fit + 0.25 × Resilience/Coachability
```

Reported as `value ± confidence_interval`, never a fake-precise integer. Updated event-triggered on new evidence — not model retraining.

## AI justification — what's rule-based vs. load-bearing AI

Rule-based, on purpose: Screen's cheap pre-filter, raw signal statistics, Thesis Engine's keyword gate. Load-bearing AI: multi-axis reasoning, Founder-Market Fit, the Interview Agent, Diligence's cross-referencing — delete these and the product collapses into a form and a spreadsheet, which is the actual test that matters.

## Data contracts — exact field names, do not rename

```json
// Signal Intake output
{
  "founder_id": "string",
  "company_id": "string",
  "deck_claims": [
    { "field": "market_size|traction|team|ask|problem_product", "value": "string", "source_slide": 4 }
  ],
  "public_signals": {
    "github": { "repos": 12, "commit_consistency_score": 0.7, "longevity_months": 18 },
    "devpost_hn": { "launches": 2, "total_upvotes": 340 },
    "arxiv": { "papers": 1 }
  },
  "sourcing_channel": "inbound|outbound",
  "cold_start_flag": true
}

// Thesis Engine output
{
  "thesis_match": true,
  "match_type": "exact|adjacent_llm_judged",
  "rationale": "string"
}

// Multi-Axis Scorer output — NEVER averaged
{
  "founder_axis": { "score": 72, "trend": "improving", "rationale": "string", "citations": ["string"] },
  "market_axis": { "rating": "bullish|neutral|bear", "trend": "stable", "rationale": "string", "citations": ["string"] },
  "idea_vs_market_axis": { "rating": "bullish|neutral|bear", "trend": "declining", "rationale": "string", "citations": ["string"] },
  "founder_score": { "value": 68, "confidence_interval": 15, "trend": "improving" }
}

// Interview Agent output
{
  "questions_asked": ["string"],
  "response_pattern": "engaged_updated|engaged_no_update|defensive|evasive",
  "resilience_score": 100
}

// Diligence/Validator output
{
  "flagged_claims": [
    { "claim": "market_size", "issue": "string", "severity": "low|medium|high" }
  ]
}

// Trust Score output — per claim, never per-company
{
  "claim_trust": [
    { "claim": "traction", "confidence": "high|medium|low", "evidence": "string" }
  ]
}

// Memo Synthesizer output — Appendix 1 structure
{
  "required": {
    "company_snapshot": "string", "investment_hypotheses": ["string"], "swot": {},
    "problem_and_product": "string", "traction_kpis": "string"
  },
  "optional_or_flagged": { "team_and_history": "string", "cap_table": "Not disclosed" },
  "adversarial_view": { "challenges": ["string"] },
  "portfolio_check": { "overlap": false, "note": "string" },
  "verdict": "approve|review|decline",
  "amount_recommended": 100000
}
```

## Frontend-consumption shape — build fixtures and screens against this exactly

B's API glue assembles the per-agent contracts above into one object per opportunity. Match this shape in `/shared/fixtures/` from minute one — swapping the mock for the real endpoint later is then a no-op.

```json
// GET /opportunities/:id
{
  "founder_id": "string", "company_id": "string", "company_name": "string",
  "sourcing_channel": "inbound|outbound", "cold_start_flag": false,
  "founder_score": { "value": 68, "confidence_interval": 15, "trend": "improving" },
  "founder_axis": { "score": 72, "trend": "improving", "rationale": "string", "citations": ["string"] },
  "market_axis": { "rating": "bullish|neutral|bear", "trend": "stable", "rationale": "string", "citations": ["string"] },
  "idea_vs_market_axis": { "rating": "bullish|neutral|bear", "trend": "declining", "rationale": "string", "citations": ["string"] },
  "claim_trust": [{ "claim": "string", "confidence": "high|medium|low", "evidence": "string" }],
  "memo": {
    "required": { "company_snapshot": "string", "investment_hypotheses": ["string"], "swot": {}, "problem_and_product": "string", "traction_kpis": "string" },
    "optional_or_flagged": { "cap_table": "Not disclosed" }
  },
  "adversarial_view": { "challenges": ["string"] },
  "portfolio_check": { "overlap": false, "note": "string" },
  "verdict": "approve|review|decline",
  "amount_recommended": 100000
}

// GET /founders/:id/results — the founder-facing read-only page. Nothing else, ever.
{
  "founder_score": { "value": 68, "confidence_interval": 15, "trend": "improving" },
  "narrative": "string"
}

// POST /opportunities/:id/decision
{ "decision": "approve" | "review" | "decline" }
```

## Application and evidence envelope — API Glue ownership

The agent outputs above remain locked and unchanged. API Glue persists the application
context that surrounds them so the investor UI can render the exact submitted document
and evidence trail without inventing profile fields or storing raw scraped pages.

```json
// POST /applications — multipart/form-data
// Required: founder_name, company_name, email, deck (PDF|PPTX|DOCX|TXT|MD)
// Optional: founder_role, sector, stage, geography, founder_photo, website,
// github, linkedin, x, devpost, product_hunt, arxiv
{ "company_id": "app-…", "founder_id": "founder-…", "status": "queued", "status_url": "/applications/app-…" }

// GET /applications/:company_id — safe progress view for the applicant
{ "company_id": "app-…", "founder_id": "founder-…", "company_name": "string", "status": "queued|processing|ready|failed", "error_message": "string|null" }
```

`GET /opportunities/:id` may additionally include the following API-assembled fields:

```json
{
  "thesis": { "thesis_match": true, "match_type": "exact", "rationale": "string" },
  "enrichment": {
    "one_liner": "string", "problem": "string", "solution": "string",
    "sector": "string", "stage": "string", "geography": "string",
    "website": "https://…", "founders": [], "market": {}, "pmf": {}, "agent_trace": []
  },
  "sources": [{ "type": "deck|github|news|…", "title": "string", "url": "string", "excerpt": "string", "page": 3, "retrieved_at": "ISO-8601" }],
  "documents": [{ "kind": "deck_slide|document", "title": "string", "page": 3, "text": "string", "preview_url": "/media/…" }],
  "processing_trace": []
}
```

Source rule: use founder-confirmed URLs plus a bounded company-name press search. Store
URLs, timestamps, extracted fields, and short evidence excerpts only — never raw public
HTML/pages. Use an uploaded headshot or a consented public avatar; never guess identity
from a search result.

## Fixtures — 3 archetypes, every screen must handle all three

- **strong**: founder score 80+, all three axes bullish, high-confidence trust claims throughout, `sourcing_channel: "inbound"`, `cold_start_flag: false`
- **cold-start**: `cold_start_flag: true`, wide interval (e.g. `38 ± 24`), founder/market axis rationales explicitly note thin public data, low-confidence trust claims, `verdict: "review"`
- **weak**: mid-to-low founder score, at least one `bear` axis, at least one flagged/contradicted claim, non-empty `adversarial_view.challenges`, `verdict: "decline"`
