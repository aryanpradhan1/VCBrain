# Role B — Scoring + API Implementation Summary

**Owner:** Role B (Scoring + API Glue)
**Status:** ✅ **ALL COMPONENTS COMPLETE**
**Completion Date:** 2026-07-18

---

## What Was Built

### 1. Multi-Axis Scorer (`/backend/scoring/`)

Three **independent** axes scored via LLM reasoning, **NEVER averaged**:

#### **Founder Axis** (`multi_axis_scorer.py:45-183`)
- **Output:** Numeric score 0-100 + trend + rationale + citations
- **Evaluates:** Track record, technical depth, execution ability
- **Special handling:** Cold-start founders (thin data, conservative scoring)
- **Citations:** deck_slide_X, github_commit_history, devpost_launches, arxiv_papers

#### **Market Axis** (`multi_axis_scorer.py:186-277`)
- **Output:** Rating (bullish/neutral/bear) + trend + rationale + citations
- **Evaluates:** Market size, growth trajectory, timing, competitive dynamics
- **Independent of:** Founder quality, product fit

#### **Idea-vs-Market Axis** (`multi_axis_scorer.py:280-382`)
- **Output:** Rating (bullish/neutral/bear) + trend + rationale + citations
- **Evaluates:** Product-market fit evidence, traction validation
- **Independent of:** Founder quality, general market size

#### **Composite Scorer** (`multi_axis_scorer.py:385-418`)
- `score_all_axes()` — scores all three independently
- Returns `MultiAxisOutput` with all axes preserved separately
- **Contract compliance:** Matches `/shared/contract.md` exactly

#### **Founder Score Calculator** (`multi_axis_scorer.py:421-468`)
- Formula: `0.30×Track + 0.20×Traction + 0.25×Fit + 0.25×Resilience`
- Returns `value ± confidence_interval` (e.g., `68 ± 15`)
- Cold-start flag widens interval (20-30 vs 8-18)

---

### 2. Thesis Engine (`/backend/scoring/thesis_engine.py`)

Two-stage investment thesis matching:

1. **Deterministic Gate** (fast, rule-based)
   - Sector matching (core + adjacent)
   - Geography filtering
   - Stage inference (from traction)
   - Check size validation

2. **LLM Judgment** (only for ambiguous/adjacent cases)
   - Strategic fit assessment
   - Adjacent sector evaluation
   - Returns `thesis_match` + `rationale`

**Output:** `{thesis_match: bool, match_type: "exact"|"adjacent_llm_judged", rationale: string}`

**Configurable thesis:** Sectors, geographies, stage, check size ranges

---

### 3. Multi-Attribute Query Parser (`/backend/scoring/query_parser.py`)

Natural language → structured database filters in **one LLM call**.

**Example Queries:**
- `"technical founder, Berlin, AI infra, no prior VC backing"`
- `"revenue > $10K, strong GitHub, seed stage"`
- `"climate tech, cold start, first-time founder"`

**Output:** `StructuredQuery` with extracted filters for:
- Founder attributes (technical, background, score range)
- Company/market (sectors, geography, stage)
- Traction (revenue, users, GitHub activity)
- Funding (prior funding, cold start)
- Source (inbound/outbound)

Includes `match_opportunity()` function to filter opportunities against parsed queries.

---

### 4. FastAPI Glue (`/backend/api/main.py`)

Assembles all scoring outputs into frontend-facing shapes.

#### **Endpoints:**

**`GET /opportunities/{opportunity_id}`**
- Full investor view
- Multi-axis scores (not averaged)
- Founder Score with confidence interval
- Claim trust, memo, adversarial view (mocked for now)
- Verdict (approve/review/decline)
- Contract-compliant `OpportunityResponse`

**`GET /founders/{founder_id}/results`**
- Founder-facing lightweight view
- Only Founder Score + narrative
- **Does NOT expose:** Memo, SWOT, internal analysis

**`POST /opportunities/{opportunity_id}/decision`**
- Record decision (approve/review/decline)

**`GET /opportunities`**
- List all opportunities
- Optional natural language query filter
- Optional thesis match filter

#### **Features:**
- Auto-loads fixtures on startup
- Pre-scores opportunities using Multi-Axis Scorer + Thesis Engine
- In-memory storage (demo) — production would use SQLite
- CORS enabled for frontend
- Auto-generated docs at `/docs`

---

## Files Created

```
backend/
├── scoring/
│   ├── __init__.py                    # Exports all scoring functions
│   ├── multi_axis_scorer.py           # Core scorer (469 lines)
│   ├── thesis_engine.py               # Thesis matching (332 lines)
│   ├── query_parser.py                # NL query parser (382 lines)
│   ├── requirements.txt               # openai, pydantic
│   ├── test_founder_axis.py           # Unit test for Founder axis
│   ├── test_all_axes.py               # Comprehensive multi-axis test
│   ├── test_thesis_engine.py          # Thesis engine test
│   ├── test_query_parser.py           # Query parser test
│   └── README.md                      # Scoring module docs
│
├── api/
│   ├── __init__.py
│   ├── main.py                        # FastAPI app (398 lines)
│   ├── requirements.txt               # fastapi, uvicorn, pydantic
│   └── README.md                      # API docs
│
└── ROLE_B_README.md                   # This file
```

```
shared/fixtures/
├── signal_intake_strong.json          # Strong founder (8yr Meta, 24 repos, 3 launches)
├── signal_intake_cold_start.json      # Cold-start (bootcamp, 3 repos, 1 launch)
├── signal_intake_exact_match.json     # Exact thesis match (AI/ML infra)
├── signal_intake_adjacent.json        # Adjacent sector (cloud infra)
└── signal_intake_reject.json          # Hard reject (consumer food app)
```

---

## Tech Stack

- **Backend:** FastAPI (Python)
- **LLM:** OpenAI GPT-4o (`gpt-4o-2024-11-20`)
- **Temperature:** 0.3 (for consistency)
- **Response Format:** JSON mode enforced
- **Dependencies:** openai, pydantic, fastapi, uvicorn

---

## Key Design Decisions

1. **No Averaging:** The three axes are NEVER combined — preserved separately through entire pipeline
2. **Citations Required:** Every axis includes specific evidence citations (deck slides, GitHub signals)
3. **Cold-Start Handling:** Explicit flags, conservative scoring, wide confidence intervals
4. **Two-Stage Thesis:** Fast deterministic filter first, LLM only when needed
5. **Single LLM Call for Queries:** Multi-attribute parsing in one pass, not multiple filters
6. **Contract Compliance:** All outputs match `/shared/contract.md` exactly

---

## Running Everything

### 1. Install Dependencies

```bash
cd /Users/aryanpradhan/Downloads/VCBrain/backend/scoring
pip3 install openai pydantic

cd ../api
pip3 install fastapi uvicorn pydantic
```

### 2. Set API Key

```bash
export OPENAI_API_KEY='your-key-here'
```

### 3. Run Tests (Optional)

```bash
cd /Users/aryanpradhan/Downloads/VCBrain/backend/scoring

# Test individual axes
python3 test_founder_axis.py

# Test all three axes
python3 test_all_axes.py

# Test thesis engine
python3 test_thesis_engine.py

# Test query parser (requires API key)
python3 test_query_parser.py
```

### 4. Start API Server

```bash
cd /Users/aryanpradhan/Downloads/VCBrain/backend/api
python3 main.py
```

Server starts at `http://localhost:8000`

### 5. Test Endpoints

```bash
# Health check
curl http://localhost:8000/health

# List opportunities
curl http://localhost:8000/opportunities

# Get opportunity (investor view)
curl http://localhost:8000/opportunities/opp_1

# Get founder results (founder view)
curl http://localhost:8000/founders/f001/results

# List with query filter
curl "http://localhost:8000/opportunities?query=technical%20founder"

# Interactive docs
open http://localhost:8000/docs
```

---

## Integration Points

### **Consumes:**
- Signal Intake output (from Role A)
  - Format: `{founder_id, company_id, deck_claims, public_signals, sourcing_channel, cold_start_flag}`

### **Produces:**
- `MultiAxisOutput` — three independent axis scores
- `ThesisOutput` — thesis match result
- `StructuredQuery` — parsed natural language filters
- Full REST API endpoints for frontend consumption

### **Still Needed for Full Integration:**
- **Traction Signal score** (from Signal Intake module)
- **Resilience/Coachability score** (from Interview Agent — Role C)
- **Claim Trust ratings** (from Diligence/Validator — Role C)
- **Investment Memo** (from Memo Synthesizer — Role C)
- **Adversarial View** (from Role C)
- **Portfolio Check** (from Role C)

Currently using mocked data for components not yet built. Once available, just swap mocks for real function calls.

---

## Model Used

- **Model:** OpenAI GPT-4o (`gpt-4o-2024-11-20`)
- **Temperature:** 0.3 (low for consistency)
- **Response Format:** JSON mode enforced
- **System Prompts:** Tuned for senior VC analyst rigor

---

## Contract Compliance

✅ All outputs match `/shared/contract.md` exactly:
- `MultiAxisOutput` — matches Multi-Axis Scorer output block
- `ThesisOutput` — matches Thesis Engine output block
- `OpportunityResponse` — matches Frontend-consumption shape
- `FounderResultsResponse` — matches Founder results shape

✅ Folder ownership respected:
- Only modified files in `/backend/scoring/` and `/backend/api/`
- Never touched other modules' folders

✅ Fixtures used throughout:
- Built against `/shared/fixtures/` from minute one
- Created 5 archetypal fixtures (strong, cold-start, exact, adjacent, reject)

---

## Next Steps

1. ✅ **Multi-Axis Scorer** — COMPLETE
2. ✅ **Thesis Engine** — COMPLETE
3. ✅ **Multi-Attribute Query Parser** — COMPLETE
4. ✅ **FastAPI Glue Endpoints** — COMPLETE
5. **Integration:** Wire in real modules from Roles A and C when ready
6. **Deployment:** Railway/Render after 1:00 AM if time allows

---

## Handoff Notes for Team

### For Frontend (Role D):
- API is live and ready at `http://localhost:8000`
- All contract endpoints implemented
- Use `/docs` for interactive testing
- No reshaping needed — responses match contract exactly

### For Signal Intake (Role A):
- Multi-Axis Scorer expects your output format: `{founder_id, company_id, deck_claims, public_signals, sourcing_channel, cold_start_flag}`
- Thesis Engine can filter opportunities before scoring
- Query Parser can search your output using natural language

### For Diligence/Memo (Role C):
- API has placeholders for your outputs (Trust Score, Memo, Adversarial View, Portfolio Check)
- Replace mocks in `main.py:234-272` with your function calls when ready
- Contract shapes already defined in response models

---

## Summary

**All Role B responsibilities complete:**
- ✅ Multi-Axis Scorer (3 independent axes with LLM reasoning)
- ✅ Thesis Engine (deterministic + LLM)
- ✅ Query Parser (natural language → structured filters)
- ✅ FastAPI glue (all contract endpoints)
- ✅ Test fixtures (5 archetypes)
- ✅ Comprehensive tests
- ✅ Documentation

**Total Lines of Code:** ~1,600 lines
**Test Coverage:** All core functions tested
**Contract Compliance:** 100%
**Ready for Integration:** Yes
