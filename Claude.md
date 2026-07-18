# FounderScore — Project Rules

@shared/contract.md

- Tech stack is locked in `/shared/contract.md` — do not suggest alternatives without a sync-point discussion.
- Build fixtures live in `/shared/fixtures/` — use these for all test/mock data.
- Folder ownership is strict: only modify files inside your own folder (`/backend/signal_intake/`, `/backend/scoring/`, `/backend/api/`, `/backend/diligence_memo/`, `/frontend/`). Call other modules only via the documented contract in `/shared/contract.md`.
- Commit every 30–45 minutes. Merge only at the four scheduled sync points.
