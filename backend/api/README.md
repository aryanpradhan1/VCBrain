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

### In-Memory Storage

Currently uses in-memory dicts (`OPPORTUNITIES_DB`, `FOUNDERS_DB`).
In production, would use SQLite/Postgres with event-triggered score recomputation.

### Mocked Components

Components not yet built (awaiting other team members):
- **Claim Trust** (from Role C's Diligence/Validator)
- **Memo** (from Role C's Memo Synthesizer)
- **Adversarial View** (from Role C)
- **Portfolio Check** (from Role C)

API returns placeholder data for these. Once other modules are ready, just swap the mocks for real function calls.

### Running the API

```bash
cd /Users/aryanpradhan/Downloads/VCBrain/backend/api

# Set API key (required for scoring)
export OPENAI_API_KEY='your-key-here'

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

### File Structure

```
backend/api/
├── __init__.py
├── main.py           # FastAPI app (398 lines)
├── requirements.txt
└── README.md         # This file
```

### Next Steps

1. Replace mocked Trust/Memo/Adversarial/Portfolio with real modules when available
2. Add SQLite persistence (currently in-memory)
3. Add authentication/authorization (currently open)
4. Deploy to Railway/Render (after 1:00 AM if time allows)
