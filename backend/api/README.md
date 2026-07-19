## FounderScore API — FastAPI Glue

**Status:** ✅ All contract endpoints implemented

### What's Built

FastAPI application (`main.py`) that assembles all scoring module outputs into frontend-facing shapes.

### Endpoints

#### 1. `GET /opportunities/{opportunity_id}`
Full investor-facing view with:
- Multi-axis scores (Founder/Market/Idea-vs-Market) — **not averaged**
- Founder Score with confidence interval
- Claim trust ratings (mocked, awaiting Diligence module)
- Investment memo (mocked, awaiting Memo Synthesizer)
- Adversarial view (mocked)
- Portfolio check (mocked)
- Verdict (approve/review/decline)

**Response format:** Matches `/shared/contract.md` `OpportunityResponse` exactly

#### 2. `GET /founders/{founder_id}/results`
Founder-facing lightweight view (read-only):
- Founder Score with confidence interval
- Plain-language narrative

**Does NOT expose:** Memo, SWOT, internal analysis (investor-only)

#### 3. `POST /opportunities/{opportunity_id}/decision`
Record investment decision (approve/review/decline)

#### 4. `GET /opportunities`
List all opportunities with optional filters:
- `?query=technical founder, AI infra` — natural language search
- `?thesis_filter=true` — only thesis matches

### How It Works

1. **Startup:** Loads fixtures from `/shared/fixtures/` and pre-scores them
2. **On Request:** Assembles multi-axis output + thesis match + mocked components
3. **Filtering:** Uses Query Parser for natural language search
4. **Verdict Logic:**
   - Decline if thesis doesn't match
   - Approve if Founder Score ≥ 70
   - Review otherwise

### Storage

Applications, analysis results, and interview sessions persist through the API's
SQLite application store under `backend/data/`; the in-memory maps are only a
runtime cache for fast endpoint reads.

### Role C Integration

Claim validation, per-claim Trust Score, Memo Synthesizer, Adversarial View,
Portfolio Check, and the Interview Agent call Role C's package directly. Diligence
is run during processing, never on dashboard refreshes.

### Running the API

```bash
cd /Users/aryanpradhan/Downloads/VCBrain/backend/api

# Required for scoring; Tavily is used for bounded public evidence checks.
export OPENAI_API_KEY='your-key-here'
export TAVILY_API_KEY='your-key-here'

# Optional: enrich an exact LinkedIn URL that a founder explicitly supplied.
# No LinkedIn login, credentials, or name-based people search is used.
export PEOPLE_DATA_LABS_API_KEY='your-key-here'

# Start server
python3 main.py

# Or with uvicorn directly
uvicorn main:app --reload
```

Server starts at `http://localhost:8000`

**Test endpoints:**
- `http://localhost:8000/health` — health check
- `http://localhost:8000/opportunities` — list all
- `http://localhost:8000/opportunities/opp_1` — view opportunity
- `http://localhost:8000/founders/f001/results` — founder view

### API Documentation

FastAPI auto-generates docs:
- Interactive docs: `http://localhost:8000/docs`
- OpenAPI spec: `http://localhost:8000/openapi.json`

### Integration with Frontend

Frontend (Role D) should:
1. Call `GET /opportunities` for dashboard list
2. Call `GET /opportunities/:id` for detailed view
3. Call `POST /opportunities/:id/decision` to record decisions
4. Call `GET /founders/:id/results` for founder-facing page

All responses match the contract exactly — no reshaping needed.

### Dependencies

```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.0.0
```

Plus scoring module dependencies (openai, pydantic).

### Optional profile enrichment

When `PEOPLE_DATA_LABS_API_KEY` is set, the intake service can look up an **exact
LinkedIn `/in/` URL supplied in the application** using People Data Labs. A returned
record is accepted only if its LinkedIn identity matches that submitted URL. The app
stores only a small display-safe subset (portrait URL, headline/current role, provider
status); it does not store the provider's full person record. The result is cached on
the application so reprocessing does not repeat a billable lookup.

### File Structure

```
backend/api/
├── __init__.py
├── main.py           # FastAPI app (398 lines)
├── requirements.txt
└── README.md         # This file
```

### Next Steps

1. Add authentication/authorization (currently open)
2. Move active opportunity/session storage into SQLite for multi-process deployment
3. Deploy to Railway/Render (after 1:00 AM if time allows)
