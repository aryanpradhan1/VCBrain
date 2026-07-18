# FounderScore — Final Spec (VC Brain Track)

Core build: 3:30 PM → 2:00 AM (~10.5 hours). Finalization, video, pitch: 2:00 AM → 8:00 AM. Print this, keep it open, refer back at every sync point.

---

## 1. Tech Stack — Locked Before Anyone Codes

Per your mentor's advice: pick once, write it down, everyone builds against the same assumptions from minute one.

| Layer | Choice | Why |
|---|---|---|
| Backend | FastAPI (Python) | Fast to scaffold, strong for LLM-call orchestration and data wrangling |
| LLM provider | **Pick one now — write the exact model string in `/shared/contract.md` before Block 1 starts** | Every agent's reasoning quality and cost depends on this; don't let 4 people pick 4 different providers ad hoc |
| Frontend | React + Vite + Tailwind + shadcn/ui | Fast AI-agent scaffolding, and shadcn gives D a real component foundation instead of building primitives from scratch — critical given the Bloomberg-quality bar |
| Data storage | SQLite | Zero setup, sufficient for demo-scale persistence (Memory layer) |
| Deployment | Railway/Render (backend) + Vercel (frontend), only if time allows after 1:00 AM | Localhost + screen recording is the safe fallback — don't let deployment risk eat build time |
| Dummy data | 3 pre-written synthetic decks (strong/cold-start/weak) + mocked public-signal fixtures, written to `/shared/fixtures/` **before Block 1** | Everyone builds against the exact same fixtures from minute one — this is the literal thing your mentor flagged |

### Change process if the stack needs to shift mid-build
- Changes are proposed **only at a sync point**, never mid-block unilaterally.
- One person (suggest: whoever owns `/shared/contract.md`, likely B) is the **stack owner** — the only person who edits the locked table above.
- Any change gets logged immediately in `/shared/CHANGELOG.md` with a timestamp, so nobody builds against a stale assumption.
- **Hard rule: no stack changes after Block 2 (8:30 PM)** except a genuine blocker (e.g., an API is down). Past that point, work around it rather than replatforming.

---

## 1.5. Initial Architecture Setup — Do This First, 3:30–3:50 PM

One person drives (suggest B, since they own API glue), everyone else watches/confirms — a shared skeleton beats four people building slightly different starting points.

```bash
# 1. Repo
mkdir founderscore && cd founderscore
git init
git remote add origin <your-repo-url>

# 2. Folder structure — matches ownership in Section 7
mkdir -p backend/signal_intake backend/scoring backend/api backend/diligence_memo
mkdir -p shared/fixtures/decks shared/fixtures/public_signals
mkdir -p frontend
touch shared/contract.md shared/STATUS.md shared/CHANGELOG.md
touch backend/signal_intake/__init__.py backend/scoring/__init__.py backend/diligence_memo/__init__.py

# 3. Backend skeleton
cd backend
pip install fastapi uvicorn pydantic --break-system-packages
```

Create `backend/api/main.py` with a bare health check to confirm the skeleton boots:
```python
from fastapi import FastAPI
app = FastAPI(title="FounderScore")

@app.get("/health")
def health():
    return {"status": "ok"}
```

```bash
# 4. Frontend skeleton
cd ../frontend
npm create vite@latest . -- --template react
npm install
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npx shadcn@latest init
```

**5. Fill `/shared/contract.md`** with the locked tech stack table (Section 1) and every JSON contract shape (Section 4) — this file is the single source of truth both `CLAUDE.md` and `AGENTS.md` point to (Section 8).

**6. Write the fixtures now**, before anyone starts real logic: 3 synthetic decks (strong / cold-start / weak-idea) in `shared/fixtures/decks/`, and 2-3 mock public-signal blobs (fake GitHub/Devpost JSON matching the Signal Intake output contract) in `shared/fixtures/public_signals/`. This is what lets D build the dashboard and C build the Interview Agent before A's real ingestion pipeline exists.

```bash
# 7. Push the skeleton
git add .
git commit -m "Initial architecture skeleton"
git push -u origin main

# 8. Everyone branches off the shared skeleton
git checkout -b signal-intake      # A
git checkout -b scoring-thesis     # B
git checkout -b diligence-memo     # C
git checkout -b frontend           # D
```

**9. Smoke test before writing any real logic:** confirm `uvicorn backend.api.main:app --reload` boots and returns `{"status": "ok"}` at `/health`, and `npm run dev` in `/frontend` loads a blank page with no errors. Both booting cleanly is the actual end of Kickoff — only then split into your four branches.

---

## 2. Team Split — Rebalanced for the Bloomberg-Quality UI Requirement

| Person | Owns | Core hours (of ~10.5h available) |
|---|---|---|
| **A** | Signal Intake — deck ingestion (LLM extraction) + bounded outbound scanning (GitHub Trending, Show HN, arXiv-by-category, Thesis-filtered) + dedup/enrich/tag-by-source | ~7.5h |
| **B** | Multi-Axis Scorer (LLM reasoning, per-axis citations, not averaged) + Thesis Engine (deterministic gate + LLM fit judgment) + Multi-Attribute Reasoning query parser + FastAPI glue/deployment | ~8h |
| **C** | Diligence/Validator + Trust Score (per-claim) + Memo Synthesizer (Appendix 1 structure) + Interview Agent | ~8h |
| **D** | **Frontend only** — investor dashboard, memo view, adversarial view, founder results page, portfolio check display — full time budget, no agent-building duties | ~10h |

**Why D gets the full window with no other responsibilities:** you told me UI needs to be Bloomberg quality — that's a real, demo-defining bar, and it's also 15% of your judged score that a sharp visual pass can capture almost entirely. Splitting D's attention across an agent build too would directly undercut the one thing you specifically asked to protect. C absorbs the Interview Agent instead, since it's the same shape of work as their other reasoning agents (structured prompt design, not UI).

---

## 3. Architecture — Mapped to the Diagram's Three Layers

**Memory layer**
- Structured knowledge base: founders, decks, signals — extracted fields only, never raw scraped pages
- Timestamped, deduplicated, source-tagged, persistent
- Houses Founder Score — recomputed on new evidence (event-triggered, EMA-style updates, confidence interval narrows with corroboration — no retraining)
- Diligence's gap-findings write back here, updating the founder's persistent record

**Intelligence layer**
- **Thesis Engine** — deterministic sector/stage/geography/check-size gate + LLM fit judgment for ambiguous matches
- **Multi-axis score** — Founder / Market / Idea-vs-Market, LLM reasoning with per-axis citations, never averaged, each with independent trend
- **Trust Score** — per claim, confidence label + citation, contradictions flagged before reaching the investor

**Experience layer**
- Investor dashboard — ranked list + momentum trend
- Decision-ready outputs — memo and adversarial view as **two distinct rendered artifacts**
- Founder results page — separate, lightweight, read-only

**Pipeline stages**
- **Sourcing:** Inbound (Apply: deck + name) + Outbound (bounded daily scan → Thesis-filtered → partial Founder Score → Activate above threshold → Converge into one funnel)
- **Screening:** a fast, shallow 3-axis pass using only readily-available signals — a real (cheap) scoring pass, not just a rule
- **Diligence:** truth-gap check — verifies evidence, logs gaps, writes back to Memory
- **Decision:** $100K recommendation + adversarial check + portfolio check (one-time overlap check against existing portfolio sectors)

---

## 4. Data Contracts — Lock These Field Names Now

```json
// Signal Intake output
{
  "founder_id": "string",
  "company_id": "string",
  "deck_claims": [{ "field": "market_size|traction|team|ask|problem_product", "value": "string", "source_slide": 4 }],
  "public_signals": {
    "github": { "repos": 12, "commit_consistency_score": 0.7, "longevity_months": 18 },
    "devpost_hn": { "launches": 2, "total_upvotes": 340 },
    "arxiv": { "papers": 1 }
  },
  "sourcing_channel": "inbound|outbound",
  "cold_start_flag": true
}

// Thesis Engine output
{ "thesis_match": true, "match_type": "exact|adjacent_llm_judged", "rationale": "string" }

// Multi-Axis Scorer output — NOT averaged
{
  "founder_axis": { "score": 72, "trend": "improving", "rationale": "...", "citations": ["deck_slide_3", "github_commit_history"] },
  "market_axis": { "rating": "bullish|neutral|bear", "trend": "stable", "rationale": "...", "citations": [...] },
  "idea_vs_market_axis": { "rating": "bullish|neutral|bear", "trend": "declining", "rationale": "...", "citations": [...] },
  "founder_score": { "value": 68, "confidence_interval": 15, "trend": "improving" }
}

// Interview Agent output
{ "questions_asked": ["..."], "response_pattern": "engaged_updated|engaged_no_update|defensive|evasive", "resilience_score": 100 }

// Diligence/Validator output
{ "flagged_claims": [{ "claim": "market_size", "issue": "string", "severity": "medium" }], "memory_update": true }

// Trust Score output — per claim, not per company
{ "claim_trust": [{ "claim": "traction", "confidence": "high|medium|low", "evidence": "string" }] }

// Memo Synthesizer output — Appendix 1 structure
{
  "required": { "company_snapshot": "...", "investment_hypotheses": ["..."], "swot": {...}, "problem_and_product": "...", "traction_kpis": "..." },
  "optional_or_flagged": { "team_and_history": "...", "cap_table": "Not disclosed", "financials": "Unavailable at this stage" },
  "adversarial_view": { "challenges": ["string"] },
  "portfolio_check": { "overlap": false, "note": "string" },
  "verdict": "approve|review|decline", "amount_recommended": 100000
}
```

---

## 5. Per-Person Build Steps

### A — Signal Intake
1. Deck parsing: LLM extraction of claims with source-slide citations.
2. Outbound scan: pull GitHub Trending, Show HN, arXiv recent (cs.AI, date-windowed) — small bounded lists only, never unbounded crawling.
3. Apply Thesis Engine's filter **before** scoring anything, to keep the candidate pool small.
4. Dedup/enrich/tag by source; write only structured fields to Memory, never raw pages.
5. Compute partial Founder Score for outbound candidates from public signals alone (Track Record + Traction Signal sub-scores only).
6. Trigger Activate (cold outreach) only above threshold.

### B — Multi-Axis Scorer + Thesis Engine + Query Parser + Glue
1. Build the LLM reasoning prompt for each axis independently — Founder, Market, Idea-vs-Market — each producing score/rating, trend, rationale, and citations. **Do not average these into one number.**
2. Thesis Engine: deterministic gate first (cheap), LLM fit judgment only for ambiguous/adjacent matches.
3. Multi-Attribute Reasoning: one LLM call resolving a compound query (e.g., "technical founder, Berlin, AI infra, no prior VC backing") against structured Memory fields in one pass.
4. Once other agents' endpoints exist (even mocked), assemble the FastAPI app wiring everything together to the contract shapes above.
5. Handle deployment once the assembled API is stable.

### C — Diligence/Validator + Trust Score + Memo Synthesizer + Interview Agent
1. Validator: cross-reference extracted claims against available external signals, flag contradictions, write gap-findings back to Memory.
2. Trust Score: per-claim confidence label with cited evidence — never a single company-wide number.
3. Memo Synthesizer: assemble Appendix 1's required sections fully; for optional sections, either populate from evidence or explicitly flag ("Cap table: not disclosed") — never fabricate.
4. Adversarial view: a **separate** structured output (not folded into memo prose) — the Skeptic's specific counter-argument to the strongest claim.
5. Portfolio check: simple one-time comparison against a small hardcoded list of "current portfolio sectors."
6. Interview Agent: 4-5 adaptive questions challenging specific deck claims; score by response pattern, not content correctness.

### D — Frontend (Bloomberg-quality bar)
**Design direction — lean into the brief's own language ("Bloomberg-level analytical depth") literally:** dark, dense, institutional — not a friendly consumer SaaS look. Near-black background, functional color only for status (green/amber/red), monospace numerals for all data, small-multiple sparklines for trend, minimal rounded corners, information density over whitespace.

**Required features:**
1. Investor dashboard — ranked applicant list with momentum trend (sparkline or trend arrow per row)
2. Click into an applicant → full memo view (Appendix 1 structure) + Founder Score + non-averaged 3-axis display + per-claim Trust Score citations
3. **Adversarial view rendered as its own distinct panel**, not buried in the memo
4. Portfolio check indicator
5. Thesis Engine configuration screen (sectors, stage, geography, check size, ownership targets, risk appetite)
6. Interview Agent live-session view (question/response stream)
7. Separate, much simpler founder-facing results page (read-only, just their Founder Score + one line of context)
8. Loading, error, and empty states for every panel

---

## 6. Timeline — 3:30 PM to 8:00 AM

| Time | Block | What happens |
|---|---|---|
| 3:30–3:50 PM | **Kickoff** | Confirm stack table, write fixtures to `/shared/fixtures/`, confirm folder ownership, paste contract into every agent |
| 3:50–6:00 PM | **Build Block 1** | A: deck parsing + scan scaffolding. B: Multi-Axis prompt design against mocked data. C: Validator/Trust/Memo scaffolding against mocked data. D: dashboard layout + design system locked in |
| 6:00–6:20 PM | **Sync 1** | Merge, smoke test against contract |
| 6:20–8:30 PM | **Build Block 2** | Real deck extraction + bounded outbound scan live. Multi-Axis Scorer live with real citations. Diligence/Trust/Memo deepened. Dashboard wired to real (not mocked) data |
| 8:30–8:50 PM | **Sync 2** | Merge, smoke test |
| 8:50–11:00 PM | **Build Block 3** | Interview Agent built + integrated. Thesis Engine + query parser complete. Adversarial view + portfolio check wired. Founder results page built |
| 11:00–11:20 PM | **Sync 3** | Merge, full smoke test |
| 11:20 PM–1:00 AM | **Build Block 4** | End-to-end integration testing, Memory persistence/recompute verified, cold-start path explicitly tested |
| 1:00 AM | **Feature freeze** | No new features past this point |
| 1:00–2:00 AM | **Polish only** | Bug fixes; D uses this hour purely for final Bloomberg-quality visual pass |
| 2:00–2:20 AM | **Record backup demo** | Insurance while everything's freshly working |
| 2:20–3:20 AM | **Finalize written memo/submission doc** | Fill in real screenshots, real numbers |
| 3:20–3:30 AM | Short break | |
| 3:30–5:00 AM | **Tech stack video** | Architecture walkthrough, show non-averaged 3-axis live, show which pieces are deliberately not AI and why |
| 5:00–6:15 AM | **Demo/pitch video** | 2-3 min final cut, scripted, backup demo as insurance |
| 6:15–7:45 AM | Buffer/rest | Whoever needs it, take it here — nobody needs to be awake for this stretch |
| 7:45–8:00 AM | **Submit** | |

---

## 7. Git Workflow & Avoiding Merge Conflicts

- One feature branch per person, named after their domain (`signal-intake`, `scoring-thesis`, `diligence-memo`, `frontend`)
- **Commit every 30-45 minutes**, even mid-task
- **Merge only at the 4 scheduled sync points** — resolve conflicts together, not solo
- Folder ownership, strictly enforced:
  ```
  /backend/signal_intake/     ← A only
  /backend/scoring/            ← B only (Multi-Axis, Thesis, Query Parser)
  /backend/api/                ← B only (glue)
  /backend/diligence_memo/     ← C only (Validator, Trust, Memo, Interview)
  /frontend/                   ← D only
  /shared/contract.md          ← stack owner only, group-approved changes
  /shared/fixtures/             ← locked before Block 1, don't edit after
  /shared/STATUS.md            ← everyone updates at any handoff
  /shared/CHANGELOG.md          ← stack owner logs any locked-decision change
  ```
- Tell every coding agent explicitly: *"Only modify files inside [your folder]. Do not touch other folders. Call other modules only via the documented contract."*
- Run a quick contract smoke test at every sync point before declaring anything merged.

---

## 8. How to Run Your Coding Agents — Exact Steps, Split by Tool

Three of you are on **Claude Code**, one is on **Codex** (including D on Claude Code for frontend). These two tools read different instruction files automatically, so "just paste the contract in" isn't precise enough — here's exactly what each person does.

### The one rule that matters most: one canonical source of truth
Both tools' instruction files should be short pointers to `/shared/contract.md`, not full copies of it. If the contract changes at a sync point (per Section 1's change process), you only edit one file — `/shared/contract.md` — not four different agent config files that can drift out of sync with each other.

### For the 3 people on Claude Code (A, B, C or D — whichever 3 of you)

**Setup, once, before Block 1:**
```bash
npm install -g @anthropic-ai/claude-code
cd founderscore/                    # repo root
claude                              # launches Claude Code
/init                               # scaffolds a starter CLAUDE.md — do this first
```

**Then edit the generated root `CLAUDE.md`** to include:
```markdown
# FounderScore — Project Rules

@shared/contract.md

- Tech stack is locked in /shared/contract.md — do not suggest alternatives without asking.
- Build fixtures live in /shared/fixtures/ — use these for all test/mock data.
```
The `@shared/contract.md` line is a real Claude Code feature — it auto-imports that file's content into every session automatically, so nobody has to manually re-paste the contract each time it's referenced.

**Then, each person adds a second, nested `CLAUDE.md` inside their own owned folder** (e.g. `/backend/signal_intake/CLAUDE.md` for A) with only their role's specifics:
```markdown
# Signal Intake — Role Rules

You are building Signal Intake for FounderScore.
Only modify files inside /backend/signal_intake/. Never touch other folders.
Call other modules only via the documented contract in /shared/contract.md.
Fixtures for this module: /shared/fixtures/decks/, /shared/fixtures/public_signals/
```
Claude Code loads the root `CLAUDE.md` every session, and this nested one automatically loads too whenever Claude reads/writes a file inside that folder — so the folder restriction is reinforced right where it matters, not just stated once at the start.

### For the 1 person on Codex

**Setup, once, before Block 1:**
```bash
npm i -g @openai/codex
export OPENAI_API_KEY="your-key"    # or authenticate via ChatGPT OAuth instead
cd founderscore/
codex
/init                               # scaffolds a starter AGENTS.md
```

**Edit the generated root `AGENTS.md`** — Codex reads this file the way Claude Code reads `CLAUDE.md`, but does **not** reliably read `CLAUDE.md` itself, so this needs its own copy of the pointer (not just a shared link):
```markdown
# FounderScore — Project Rules

See /shared/contract.md for the full locked data contract and tech stack — read it before writing any code.
Build fixtures live in /shared/fixtures/ — use these for all test/mock data.
```

**Then add a subdirectory `AGENTS.md`** inside your own owned folder, same pattern as Claude Code's nested file:
```markdown
# [Your Module] — Role Rules

You are building [Multi-Axis Scorer / Diligence & Memo / whichever module] for FounderScore.
Only modify files inside [your folder path]. Never touch other folders.
Call other modules only via the documented contract in /shared/contract.md.
```

### Keeping both in sync without duplicating work
Only `/shared/contract.md` is the real source of truth. The root `CLAUDE.md` and root `AGENTS.md` are both just short pointers to it (a few lines each) — if the contract changes at a sync point, edit `/shared/contract.md` once and both tools pick up the change automatically next session. Don't maintain the contract's actual content in more than one place.

### Mocking the boundary, regardless of tool
D builds frontend against hand-written mock JSON matching the contract shape from minute one; C's Interview Agent can be tested standalone before A/B's real data is wired in. If someone's agent gets rate-limited, refer to your existing Token/Usage Contingency Plan — separate accounts, API key backup, or switch tools for that stretch.

---

## 9. Cut List — Never Cut First

1. **Never cut:** non-averaged 3-axis scoring, per-claim Trust Score, cold-start Interview Agent path — these are your core differentiation and the most heavily weighted judging criteria
2. First cut if behind: Multi-Attribute Reasoning's full natural-language depth — fall back to simple structured filters
3. Second cut: Interview Agent's adaptive follow-up count — drop to 2 fixed challenge questions
4. Third cut: outbound sourcing's scan breadth — narrow to GitHub Trending only, drop Show HN/arXiv
5. Dashboard polish is the last thing to cut, not the first — given the explicit Bloomberg-quality bar, protect D's hours before trimming anything visual

---

## 10. Recap — AI Justification & Founder Score Formula

**Not everything needs AI, and that's correct, not a shortcut:** Screen's cheap pre-filter, raw signal statistics, and Thesis Engine's keyword gate stay rule-based. Multi-axis reasoning, Founder-Market Fit, the Interview Agent, and Diligence's cross-referencing are where AI is load-bearing — delete it and the product collapses into a form and a spreadsheet, which is the actual test that matters.

**Founder Score:**
```
Founder Score = 0.30 × Track Record + 0.20 × Traction Signal
              + 0.25 × Founder-Market Fit + 0.25 × Resilience/Coachability
```
Reported as `Score ± confidence interval`, updated by event-triggered recomputation over growing evidence — not model retraining.
