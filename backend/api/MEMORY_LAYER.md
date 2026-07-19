# Memory Layer — Implementation Documentation

**Owner:** Role B
**Status:** ✅ Complete and integrated
**Location:** `/backend/api/db.py`

---

## What Is This?

The **Memory Layer** is the persistent storage system that everyone else in the project depends on. Instead of each module maintaining its own database, this provides **one shared SQLite database** with three simple functions:

1. `save_signal()` — Save new evidence
2. `recompute_founder_score()` — Update score from all signals
3. `get_founder()` — Read current founder record

---

## Database Schema

### **`founders` table** (current state)

Stores the current computed Founder Score for each founder.

| Column | Type | Description |
|--------|------|-------------|
| `founder_id` | TEXT PRIMARY KEY | Unique founder identifier |
| `company_id` | TEXT | Associated company |
| `founder_score_value` | REAL | Current score (0-100) |
| `founder_score_interval` | REAL | Confidence interval (±) |
| `founder_score_trend` | TEXT | 'improving'\|'declining'\|'stable' |
| `cold_start_flag` | BOOLEAN | True if limited track record |
| `last_updated` | TIMESTAMP | When score was last recomputed |

### **`signals` table** (append-only log)

Historical log of all evidence ever collected. **Never deleted or updated.**

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Auto-incrementing ID |
| `founder_id` | TEXT | Foreign key to founders |
| `source` | TEXT | 'deck'\|'github'\|'devpost_hn'\|'arxiv'\|'interview'\|'diligence' |
| `payload` | TEXT | JSON blob of signal data |
| `timestamp` | TIMESTAMP | When signal was recorded |

**Indexes:**
- `idx_signals_founder` on `founder_id`
- `idx_signals_timestamp` on `timestamp DESC`

---

## The 3 Core Functions

### 1. `save_signal(founder_id, source, payload)`

**What it does:** Appends new evidence to the database and triggers score recomputation.

**Parameters:**
- `founder_id` (str): Unique founder identifier
- `source` (str): One of: `deck`, `github`, `devpost_hn`, `arxiv`, `interview`, `diligence`
- `payload` (dict): Signal data (contract-shaped JSON)

**Side effects:**
- Inserts row into `signals` table
- Creates founder record if doesn't exist
- Calls `recompute_founder_score()` automatically

**Example usage:**
```python
from backend.api.db import save_signal

# After parsing a pitch deck
save_signal("f001", "deck", {
    "deck_claims": [...],
    "cold_start_flag": False
})

# After scanning GitHub
save_signal("f001", "github", {
    "repos": 24,
    "commit_consistency_score": 0.85,
    "longevity_months": 48
})
```

**Who calls it:**
- Signal Intake (Role A): After parsing deck, after GitHub scan
- Diligence (Role C): After validation if `memory_update: true`
- Interview Agent (Role C): After interview session

---

### 2. `recompute_founder_score(founder_id)`

**What it does:** Recalculates Founder Score from all signals using EMA formula.

**Formula:**
```
Founder Score = 0.30 × Track Record + 0.20 × Traction Signal
              + 0.25 × Founder-Market Fit + 0.25 × Resilience
```

**How it works:**
1. Fetches ALL signals for the founder (chronologically)
2. Extracts component scores from each signal:
   - **Track Record:** From deck (team claims), GitHub (longevity, consistency), arXiv (papers)
   - **Traction:** From deck (traction claims), Devpost/HN (launches, upvotes)
   - **Founder-Market Fit:** From deck (team background × product alignment)
   - **Resilience:** From Interview Agent
3. Applies **EMA (Exponential Moving Average)** to each component
   - Recent signals weighted higher (α = 0.3)
   - Smooths out noise while prioritizing new evidence
4. Calculates confidence interval:
   - **Narrows** with more independent sources
   - **Widens** if scores are inconsistent (high variance)
   - **Widens** for cold-start founders
5. Determines trend by comparing to previous score
6. Updates `founders` table

**Returns:**
```python
{
    "value": 78,
    "confidence_interval": 12,
    "trend": "improving"
}
```

**Called automatically by:** `save_signal()`

**Can also be called manually:** When Diligence finds `memory_update: true`

---

### 3. `get_founder(founder_id)`

**What it does:** Retrieves current founder record from database.

**Returns:**
```python
{
    "founder_id": "f001",
    "company_id": "c001",
    "founder_score": {
        "value": 78,
        "confidence_interval": 12,
        "trend": "improving"
    },
    "cold_start_flag": False,
    "last_updated": "2026-07-18T15:30:00"
}
```

**Raises:** `ValueError` if founder not found

**Example usage:**
```python
from backend.api.db import get_founder

founder = get_founder("f001")
print(f"Score: {founder['founder_score']['value']} ± {founder['founder_score']['confidence_interval']}")
```

**Who calls it:**
- API endpoints: `/founders/:id/results`
- Multi-Axis Scorer: To read persistent score
- Frontend: Dashboard display

---

## Confidence Interval Logic

**How it works:**

```python
def _calculate_confidence_interval(num_sources, variance, cold_start):
    # Start with base interval
    base = 25 if cold_start else 15

    # Reduce as we get more independent sources
    source_factor = min(num_sources / 8, 0.6)  # Max 60% reduction
    interval = base * (1 - source_factor)

    # Increase if scores are inconsistent
    variance_penalty = min(variance / 5, 10)
    interval += variance_penalty

    # Clamp to 5-30 range
    return max(5, min(30, int(interval)))
```

**Examples:**
- **Cold-start, 1 source:** `38 ± 25` (wide — we're unsure)
- **Cold-start, 3 sources:** `42 ± 18` (narrowing)
- **Established, 5+ sources:** `78 ± 8` (tight — high confidence)
- **Inconsistent scores:** `65 ± 22` (wider — conflicting evidence)

---

## EMA (Exponential Moving Average) Formula

**Why EMA?**
- Gives more weight to recent evidence
- Smooths out noise from outliers
- Prevents single bad signal from tanking the score

**Implementation:**
```python
def _calculate_ema(scores, alpha=0.3):
    ema = scores[0]  # Start with oldest
    for score in scores[1:]:
        ema = alpha * score + (1 - alpha) * ema
    return ema
```

**Example:**
```
Signals over time: [50, 60, 70, 80]
Simple average: (50+60+70+80)/4 = 65
EMA (α=0.3): 50 → 53 → 58.1 → 65.7
```

EMA result (65.7) is closer to recent scores (70, 80) than simple average (65).

---

## Integration Points

### **Signal Intake (Role A) Integration**

```python
# In backend/signal_intake/deck_parser.py (or wherever A processes data)

from backend.api.db import save_signal

# After parsing a deck
parsed_data = parse_deck(deck_file)
save_signal(
    founder_id=parsed_data.founder_id,
    source="deck",
    payload=parsed_data.dict()
)

# After GitHub scan
github_data = scan_github(username)
save_signal(
    founder_id=founder_id,
    source="github",
    payload=github_data
)
```

### **Diligence (Role C) Integration**

```python
# In backend/api/main.py (after diligence runs)

diligence_memo = _diligence_pipeline.run({...})

# Check if diligence found new evidence
if diligence_memo.get("memory_update"):
    save_signal(
        founder_id=founder_id,
        source="diligence",
        payload=diligence_memo["diligence"]
    )
    # Score recomputed automatically
```

### **API Endpoints Integration**

Already integrated in `main.py`:
- `load_fixture_data()` calls `save_signal()` for each fixture
- `/founders/:id/results` calls `get_founder()` to read from DB
- `/founders/:id/signals` calls `get_all_signals()` for audit trail

---

## File Location

```
backend/api/
├── db.py              # Memory Layer implementation (this file)
├── main.py            # API that uses Memory Layer
├── founderscore.db    # SQLite database file (auto-created)
└── MEMORY_LAYER.md    # This documentation
```

---

## Testing

### **Manual Test:**
```python
from backend.api.db import save_signal, get_founder

# Save some signals
save_signal("test_founder", "deck", {"deck_claims": [], "cold_start_flag": True})
save_signal("test_founder", "github", {"repos": 10, "commit_consistency_score": 0.6, "longevity_months": 12})

# Read back
founder = get_founder("test_founder")
print(founder)
```

### **API Test:**
```bash
# Start server
python3 main.py

# Check founder results
curl http://localhost:8000/founders/f001/results

# View signal audit trail
curl http://localhost:8000/founders/f001/signals
```

---

## Database File

The database is a single file: `founderscore.db`

**To view it:**
```bash
# Command line
sqlite3 founderscore.db
.tables
SELECT * FROM founders;
.exit

# Or use DB Browser for SQLite (GUI)
```

**To reset it:**
```bash
rm founderscore.db
# Restart server - it will recreate automatically
```

---

## Production Considerations

**Current implementation is hackathon-ready, but for production you'd add:**

1. **Migrations:** Use Alembic to version schema changes
2. **Connection pooling:** Reuse connections instead of open/close per query
3. **Transactions:** Wrap multi-step operations in transactions
4. **Locking:** Handle concurrent writes properly
5. **Indexes:** Add more indexes for common queries
6. **Backups:** Automated backups of the database file

**For now:** Single-threaded, single-server, demo scale = SQLite is perfect!

---

## Summary

**What we built:**
- ✅ Persistent SQLite database with 2 tables
- ✅ 3 core functions (save, recompute, get)
- ✅ EMA-based score updates
- ✅ Confidence interval narrowing
- ✅ Append-only signal logging
- ✅ Integrated into API endpoints
- ✅ Ready for Signal Intake & Diligence to use

**Total code:** ~460 lines in `db.py`

**Database file:** Auto-created on first run

**Zero external dependencies:** Uses built-in `sqlite3`

**Ready to demo!** 🚀
