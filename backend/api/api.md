# API Glue — Role Rules (B)

@shared/contract.md

You are assembling the FastAPI app that wires every agent's endpoint into the single
aggregated shape the frontend expects — see "Frontend-consumption shape" in
/shared/contract.md (GET /opportunities/:id, GET /founders/:id/results,
POST /opportunities/:id/decision). Only modify files inside /backend/api/.

Build against each agent's documented contract shape as soon as it's written down — don't
wait for every agent to be finished. Mock whichever aren't ready yet using /shared/fixtures/.

Once stable, you also own deployment (Railway/Render) if time allows after 1:00 AM.