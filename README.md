# Scout

> AI-powered VC decision system that evaluates startup founders in 24 hours

Scout combines multi-axis scoring, thesis matching, claim validation, and adaptive interviewing to recommend $100K checks to early-stage startups — whether they applied directly or were found before they started fundraising.

## Overview

Scout automates the diligence process using AI agents while keeping every claim traceable to real evidence:

- **Multi-Axis Scoring**: Independent evaluation of Founder, Market, and Idea-vs-Market fit (never averaged into one number)
- **Thesis Engine**: Two-stage filtering (deterministic gate + LLM judgment) against fund investment criteria
- **Outbound Sourcing**: Bounded scanning of GitHub, Show HN, arXiv (and optionally Product Hunt) to find founders before they apply
- **Claim Validation**: Bounded public evidence checks via Tavily, with per-claim confidence and contradiction flagging
- **Adaptive Interview**: 4-5 question session that assesses founder resilience and updates the persistent score
- **Memory Layer**: Event-triggered, EMA-based scoring that accumulates evidence across every signal a founder generates over time

**Result:** an investment memo with verdict (approve/review/decline) and check recommendation, backed by cited evidence.

**On profile enrichment, precisely:** Scout does *not* search the web to guess who a founder is. LinkedIn/GitHub enrichment only activates for URLs a founder explicitly types into the apply form — matching the project's own rule to never infer identity from a search result.

---

## Architecture

### Tech stack

**Backend** (Python 3.9+, tested through 3.13)
- FastAPI, SQLite, Pydantic
- OpenAI — LLM reasoning for scoring, claim validation, interviews, thesis judgment
- Tavily — bounded web search for claim validation and outbound discovery
- People Data Labs — optional, exact-URL-only LinkedIn enrichment
- Product Hunt API — optional, official GraphQL API for outbound sourcing

**Frontend** (React 19, Node 20.19+/22.13+/24+ — see Prerequisites)
- React Router, Vite, Tailwind CSS 4, Framer Motion, Lucide React

### System architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│  Dashboard │ Memo View │ Founder Results │ Interview │ Thesis│
└────────────────────────┬────────────────────────────────────┘
                          │ REST API
┌────────────────────────▼────────────────────────────────────┐
│                     FastAPI Backend                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Signal Intake│  │   Scoring    │  │  Diligence   │      │
│  │              │  │              │  │              │      │
│  │ • Deck Parse │  │ • Multi-Axis │  │ • Validator  │      │
│  │ • Outbound   │  │ • Thesis     │  │ • Memo       │      │
│  │   Scan       │  │   Engine     │  │ • Interview  │      │
│  │ • Activate/  │  │ • Query      │  │              │      │
│  │   Outreach   │  │   Parser     │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Memory DB   │  │  App Store   │  │ Presentation │      │
│  │  (db.py)     │  │  (store.py)  │  │  (Enrichment)│      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

**Note on the two storage layers:** `db.py` (Memory layer — founders/signals, event-triggered EMA recompute) and `store.py` (ApplicationStore — the actual application/memo/decision records the frontend reads) are separate systems, not one unified store. Outbound-discovered signal history is merged into an application's scoring input at conversion time, but the two Founder Score computations otherwise run independently. Worth knowing if you're extending either.

---

## Getting started

### Prerequisites

- **Python 3.9+** (developed and tested primarily on 3.9.6 — no 3.10+-only syntax is required)
- **Node.js `^20.19.0 || ^22.13.0 || >=24`** — a plain `node -v` showing v20.14 or similar **will fail** to run the frontend dev server (a real, previously-hit issue: Vite's `rolldown` engine needs this range). Use [nvm](https://github.com/nvm-sh/nvm):
  ```bash
  nvm install 24
  nvm use 24
  ```
- An OpenAI API key and a Tavily API key (both required — nothing runs without them)

### 1. Clone

```bash
git clone https://github.com/aryanpradhan1/VCBrain.git
cd VCBrain
```

### 2. Backend setup

```bash
cd backend
pip3 install -r requirements.txt      # one complete list — installs everything every backend module needs

cp .env.example .env
# then edit backend/.env and fill in OPENAI_API_KEY and TAVILY_API_KEY at minimum.
# Everything else in that file is optional and degrades gracefully if left blank
# (cold-outreach sending, Product Hunt, People Data Labs, outbound scan pool sizes).
```

`backend/.env` is the **one** canonical env file — `backend/api/main.py` loads it automatically on startup regardless of which directory you run `uvicorn` from. You no longer need to `export` anything by hand. (`backend/api/requirements.txt` and `backend/scoring/requirements.txt` still exist as subsets for running those modules standalone, but `backend/requirements.txt` is the one to install for running the app.)

### 3. Frontend setup

```bash
cd ../frontend
nvm use 24          # see Prerequisites — required, not optional
npm install
```

No frontend `.env` is required to point at a local backend — `VITE_API_URL` defaults sensibly, or set it explicitly:
```bash
echo 'VITE_API_URL=http://localhost:8000' > .env
```

### Running it

**Terminal 1 — backend** (first boot takes a few minutes: it runs the real diligence pipeline — real Tavily + OpenAI calls — against every seeded fixture)
```bash
cd backend/api
python3 main.py
```
Runs at http://localhost:8000. Interactive API docs at http://localhost:8000/docs.

**Terminal 2 — frontend**
```bash
cd frontend
nvm use 24
npm run dev
```
Runs at http://localhost:5173.

Open http://localhost:5173.

---

## Project structure

```
VCBrain/
├── backend/
│   ├── .env.example              # canonical env template — copy to backend/.env
│   ├── requirements.txt          # the one complete install target
│   ├── api/                      # FastAPI application (API glue)
│   │   ├── main.py               # routes, pipeline orchestration, loads backend/.env
│   │   ├── db.py                 # Memory layer (founders/signals, EMA recompute)
│   │   ├── store.py              # application storage (SQLite)
│   │   ├── presentation.py       # enrichment shaping for the UI
│   │   ├── source_enrichment.py  # exact-URL profile enrichment, press search
│   │   └── document_intake.py    # deck text/image extraction
│   ├── scoring/                  # Multi-Axis Scorer, Thesis Engine, Query Parser
│   ├── diligence_memo/           # Claim Validator, Trust Score, Memo Synthesizer, Interview Agent
│   └── signal_intake/            # Deck parsing (inbound) + GitHub/HN/arXiv/Product Hunt scanning (outbound)
├── frontend/
│   └── src/
│       ├── pages/                 # dashboard, memo, founder-results, interview, thesis, apply, network
│       ├── components/
│       └── lib/                   # API client
├── shared/
│   ├── fixtures/                  # seed/demo data
│   └── contract.md                # locked data contract — the source of truth for every shape above
└── README.md
```

---

## API reference

Full interactive docs at `/docs` once the backend is running. Core endpoints:

| Endpoint | Purpose |
|---|---|
| `GET /opportunities` | List, with optional `?query=` (natural-language) or `?thesis_filter=true` |
| `GET /opportunities/{company_id}` | Full investor view — scores, memo, trust, adversarial view, portfolio check |
| `POST /opportunities/{company_id}/decision` | Record approve/review/decline |
| `POST /applications` | Submit a new application (multipart: deck + founder info) |
| `GET /applications/{company_id}` | Poll processing status |
| `GET /founders/{founder_id}/results` | Founder-facing view — score, interval, trend, narrative **only** |
| `GET /thesis` / `PUT /thesis` | Read/write the fund's investment thesis |
| `POST /founders/{founder_id}/interviews` | Start/resume an adaptive interview |
| `POST /interviews/{session_id}/responses` | Submit an interview answer |
| `POST /outbound/scan` | Manually trigger a bounded outbound scan (not scheduled — see Known limitations) |
| `GET /outbound/leads` | Outbound-sourced candidates and their outreach status |
| `GET /outbound/unsubscribe/{founder_id}` | Unsubscribe landing page linked from outreach emails |

---

## Testing

Test files across the backend use two different styles — run each the way it's actually written, not with pytest (not a project dependency):

**`unittest`-based suites** (from `backend/`, with `backend/.env` populated):
```bash
cd backend
python3 -m unittest signal_intake.test_deck_parser signal_intake.test_outbound_scan
python3 -m unittest diligence_memo.tests.test_pipeline
python3 -m unittest api.test_source_enrichment
```

**Standalone scripts** (print their own pass/fail, run directly — some make real API calls):
```bash
cd backend/scoring
python3 test_thesis_engine.py
python3 test_all_axes.py
python3 test_founder_axis.py
python3 test_query_parser.py
python3 test_rescore.py

cd ../api
python3 test_team_discovery.py
```

```bash
curl http://localhost:8000/health   # quick liveness check
```

---

## How it works

### Processing pipeline

```
1. SOURCING
   Inbound:  founder applies with a deck + name
   Outbound: bounded GitHub/HN/arXiv/Product Hunt scan → partial score → Activate
             above threshold → cold outreach → converges into the same funnel if
             the founder applies via the emailed link

2. SCREENING / SCORING
   Deck claims extracted → Multi-Axis Scorer evaluates Founder/Market/Idea
   independently (never averaged) → Thesis Engine gates on sector/stage/geo/check
   size → persistent Founder Score computed from the locked formula

3. DILIGENCE
   Claim Validator cross-references each deck claim against bounded Tavily
   evidence → per-claim Trust Score (confidence + evidence) → contradictions
   flagged → Memo Synthesizer assembles the Appendix-1 memo + adversarial view
   + portfolio check

4. INTERVIEW (optional, founder-initiated)
   4-5 adaptive questions challenge specific deck claims → response pattern
   classified → resilience score → persistent Founder Score recomputed

5. DECISION
   Auto-decline if thesis doesn't match; otherwise the diligence verdict
   (approve/review/decline) stands, with a check amount recommendation
```

### Founder Score formula

```
Founder Score = 0.30 × Track Record + 0.20 × Traction Signal
              + 0.25 × Founder-Market Fit + 0.25 × Resilience/Coachability
```

Reported as `value ± confidence_interval`, recomputed on new evidence — never via model retraining.

---

## Known limitations (accurate as of the last working session — check before citing in pitch materials)

- **Outbound scanning is manual, not scheduled.** `POST /outbound/scan` runs on request; there is no cron/scheduler anywhere in the codebase yet, despite the contract describing a "bounded daily scan."
- **Devpost is not integrated** — no public API exists for it without scraping, which this project deliberately avoids; only GitHub, Show HN, arXiv, and (optionally) Product Hunt are live.
- **The two storage layers aren't fully unified** (see Architecture note above) — `db.py`'s Memory layer and the application store that actually drives investor-facing scores are separate systems with a partial bridge, not one system.
- **`founder_score.trend` on the main scoring path is currently hardcoded to `"stable"`** — per-axis trends are real LLM judgments, but the aggregate trend does not yet reflect real historical momentum.
- **Cap table and financials are always reported as "Not disclosed"** — there's no code path that captures them from anything yet.
- **Portfolio check compares against a hardcoded 3-sector list**, not a real, configurable portfolio.

---

## Team

Aryan Pradhan · Shrishant Hattarki · Anay Apte · Subash Skanthakumar

Built for Hack Nation's Global AI Hackathon, Maschmeyer Group's "VC Brain" challenge track.
