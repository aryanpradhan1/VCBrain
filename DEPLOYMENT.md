# Scout — Deployment Spec

Two hosts, deploy the backend first (the frontend needs its URL). Do not deploy the
backend to Vercel — it's a stateful FastAPI app (SQLite + background tasks + a
multi-minute real-API-driven startup), not a fit for serverless.

## 1. Backend → Railway

1. railway.app → sign in with GitHub → **New Project → Deploy from GitHub repo** → this repo.
2. This is a monorepo — Railway won't auto-detect correctly. Set explicitly:
   - **Root Directory**: `backend/api`
   - **Build Command**: `pip install -r ../requirements.txt` (not `backend/api/requirements.txt` — that file is now just a pointer to the one complete list at `backend/requirements.txt`)
   - **Start Command**: `python3 -m uvicorn main:app --host 0.0.0.0 --port $PORT`
3. **Variables** (Railway dashboard, not committed anywhere):
   ```
   OPENAI_API_KEY=...
   TAVILY_API_KEY=...
   ```
   Real values are in `backend/.env` locally (gitignored — ask whoever has it, or generate fresh keys). Everything else in `backend/.env.example` is optional and degrades gracefully if unset.
4. **Add a persistent volume** (Settings → Volumes) mounted at `/app/backend/data`. Without this, `backend/data/founderscore.sqlite3` resets on every redeploy — you lose every persisted application, interview, and decision.
5. Deploy. First boot is slow — it runs the real diligence pipeline (real Tavily + OpenAI calls) against every seeded fixture before the health check goes green. This is normal, not a hang.
6. Copy the public URL (`https://*.up.railway.app`) once live — needed for step 2.4.

## 2. Frontend → Vercel

1. vercel.com → sign in with GitHub → **Add New → Project** → this repo.
2. **Root Directory**: `frontend` (same monorepo issue).
3. Build settings should auto-detect (Vite: `npm run build`, output `dist`). Node version is pinned via `frontend/package.json`'s `engines` field (`^20.19.0 || ^22.13.0 || >=24`) — Vercel should pick it up automatically; if it doesn't, set it explicitly in Project Settings → Node.js Version.
4. **Environment Variables**: `VITE_API_URL` = the Railway URL from step 1.6.
5. Deploy.

## 3. Close the loop — CORS

Back in Railway, add one more variable now that the real Vercel domain exists:
```
ALLOWED_ORIGINS=https://your-actual-domain.vercel.app
```
`backend/api/main.py` already reads this (comma-separated if you need more than one) and additionally allow-lists every `*.vercel.app` preview URL automatically via regex — PR/branch previews work without touching this again.

## Verify it's actually working, not just "deployed"

- `https://<railway-url>/health` → `{"status":"ok","service":"Scout API"}`
- `https://<railway-url>/docs` → interactive API docs load
- `https://<railway-url>/opportunities` → returns real seeded data, not an empty array
- Open the Vercel URL → dashboard loads real opportunities (not stuck on loading/error) → click into one → memo renders → decision buttons work
- Check browser console for CORS errors on first load — if present, `ALLOWED_ORIGINS` is wrong or hasn't redeployed yet (Railway needs a redeploy after adding/changing an env var)

## Known gaps to know about before relying on this in front of anyone

- **`POST /outbound/scan` is manual, not scheduled** — nothing runs it automatically; there's no cron here or on Railway. If you want live outbound sourcing during a demo, someone has to hit that endpoint (or wire a Railway cron trigger separately — not currently set up).
- **`backend/api/source_enrichment.py`'s `enrich_team_members_from_deck`** does name-based identity discovery (Tavily search by parsed name) that contradicts the project's own "never guess identity from a search result" rule and could attach the wrong person's profile to a memo. Flagged, not fixed — a product decision, not mine to make unilaterally.
- **Two separate Founder Score systems** (`backend/api/db.py`'s Memory layer vs. `store.py` + `calculate_founder_score_from_axes`, which is what's actually displayed) aren't unified — see `README.md`'s Known Limitations section for the full list, keep it in sync if you fix any of these.
