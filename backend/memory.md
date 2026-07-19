# Memory Layer — Additional Role Rules (B)

You also own the shared persistence layer — this was missing from the original team split,
now assigned to you since /backend/api/ is the one place every module's output flows through.

Build this as /backend/api/db.py (or similar), a single SQLite database everyone else calls
into rather than building their own storage.

## Schema (first pass — expect to refine after initial merge)

**founders table:**
- founder_id (primary key)
- company_id
- founder_score_value (float)
- founder_score_interval (float)
- founder_score_trend (string: improving|declining|stable)
- cold_start_flag (bool)
- last_updated (timestamp)

**signals table** (every piece of evidence ever collected, timestamped, never overwritten):
- id (primary key, autoincrement)
- founder_id (foreign key)
- source (string: "deck"|"github"|"devpost_hn"|"arxiv"|"interview"|"diligence")
- payload (JSON blob — whatever that source's contract-shaped output was)
- timestamp

## Three functions everyone else calls (build these first)

1. `save_signal(founder_id, source, payload)` — A calls this every time Signal Intake
   finishes processing new evidence (deck parse, GitHub pull, etc.). Just inserts a row
   into signals — never deletes or overwrites, Memory keeps everything per the brief.

2. `recompute_founder_score(founder_id)` — triggered whenever C's Diligence output
   returns memory_update: true, OR whenever new evidence is saved. Pulls all signals
   for that founder, recomputes founder_score using the formula in /shared/contract.md
   (event-triggered recompute, EMA-style for numeric sub-scores, confidence interval
   narrows with more independent sources — no model training). Updates the founders
   table and stamps last_updated.

3. `get_founder(founder_id)` — returns the current founders row. This is what your own
   Multi-Axis Scorer reads for the persistent Founder Score, and what the
   /founders/:id/results endpoint serves to the founder-facing page.

## For right now, this sprint

Keep it simple: get these three functions working against SQLite, don't worry about
edge cases like concurrent writes or migrations yet. A and C should call save_signal()
and recompute_founder_score() from their own modules rather than touching the database
directly — you own the only code that talks to SQLite.

This is a first pass — expect to add more detail here (indexing, the exact EMA formula
implementation, how confidence-interval-narrowing is calculated) after the initial merge
once everyone's real output shapes are confirmed working end to end.