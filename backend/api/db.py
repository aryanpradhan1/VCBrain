"""
Memory Layer - Persistent Storage for FounderScore

Provides three core functions everyone else calls:
1. save_signal(founder_id, source, payload) - Append new evidence
2. recompute_founder_score(founder_id) - Event-triggered score update
3. get_founder(founder_id) - Retrieve current founder record

SQLite-based, single database everyone shares.
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import math

# Database path (same directory as db.py)
DB_PATH = Path(__file__).parent / "founderscore.db"


def _get_connection() -> sqlite3.Connection:
    """Get database connection with row factory for dict-like access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn


def _migrate_signals_table_for_outreach(conn: sqlite3.Connection) -> None:
    """SQLite can't ALTER a CHECK constraint in place. If an existing signals table still
    has the pre-outreach-tracking constraint, rebuild it (rename -> recreate -> copy rows
    -> drop) so 'outreach' becomes a valid source without losing any existing signals.
    No-op if the table doesn't exist yet (fresh install) or is already migrated."""
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='signals'").fetchone()
    if row is None or "'outreach'" in row[0]:
        return
    conn.execute("ALTER TABLE signals RENAME TO signals_pre_outreach_migration")
    conn.execute("""
        CREATE TABLE signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            founder_id TEXT NOT NULL,
            source TEXT NOT NULL CHECK(source IN ('deck', 'github', 'devpost_hn', 'arxiv', 'interview', 'diligence', 'outreach')),
            payload TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (founder_id) REFERENCES founders(founder_id)
        )
    """)
    conn.execute(
        "INSERT INTO signals (id, founder_id, source, payload, timestamp) "
        "SELECT id, founder_id, source, payload, timestamp FROM signals_pre_outreach_migration"
    )
    conn.execute("DROP TABLE signals_pre_outreach_migration")
    conn.commit()


def init_db() -> None:
    """
    Initialize database schema.
    Called automatically on module import - safe to call multiple times.
    """
    conn = _get_connection()

    # Founders table - current state
    conn.execute("""
        CREATE TABLE IF NOT EXISTS founders (
            founder_id TEXT PRIMARY KEY,
            company_id TEXT,
            founder_score_value REAL,
            founder_score_interval REAL,
            founder_score_trend TEXT CHECK(founder_score_trend IN ('improving', 'declining', 'stable')),
            cold_start_flag BOOLEAN,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    _migrate_signals_table_for_outreach(conn)

    # Signals table - append-only log (never delete/update)
    # 'outreach' source: outbound cold-email lifecycle events (sent/declined/converted),
    # logged the same append-only way as any other evidence -- see save_outreach_event()
    # and get_outreach_status() below.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            founder_id TEXT NOT NULL,
            source TEXT NOT NULL CHECK(source IN ('deck', 'github', 'devpost_hn', 'arxiv', 'interview', 'diligence', 'outreach')),
            payload TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (founder_id) REFERENCES founders(founder_id)
        )
    """)

    # Indexes for performance
    conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_founder ON signals(founder_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals(timestamp DESC)")

    conn.commit()
    conn.close()


# Initialize on module import
init_db()


def save_signal(founder_id: str, source: str, payload: Dict[str, Any]) -> None:
    """
    Save a new signal and trigger score recomputation.

    This is the primary write function - everyone else calls this to add evidence.
    Signals are NEVER overwritten (append-only), per the Memory layer spec.

    Args:
        founder_id: Unique founder identifier
        source: One of: deck, github, devpost_hn, arxiv, interview, diligence
        payload: Dict containing the signal data (contract-shaped)

    Side effects:
        - Inserts row into signals table
        - Calls recompute_founder_score(founder_id) automatically
        - Creates founder record if doesn't exist

    Example:
        save_signal("f001", "deck", {"deck_claims": [...], "cold_start_flag": False})
        save_signal("f001", "github", {"repos": 24, "commit_consistency_score": 0.85})
    """
    conn = _get_connection()

    # Ensure founder exists (upsert company_id and cold_start_flag if in payload)
    company_id = payload.get("company_id")
    cold_start = payload.get("cold_start_flag", False)

    conn.execute("""
        INSERT INTO founders (founder_id, company_id, cold_start_flag, founder_score_value, founder_score_interval, founder_score_trend)
        VALUES (?, ?, ?, 0, 30, 'stable')
        ON CONFLICT(founder_id) DO UPDATE SET
            company_id = COALESCE(excluded.company_id, founders.company_id),
            cold_start_flag = COALESCE(excluded.cold_start_flag, founders.cold_start_flag)
    """, (founder_id, company_id, cold_start))

    # Insert signal (append-only)
    conn.execute("""
        INSERT INTO signals (founder_id, source, payload)
        VALUES (?, ?, ?)
    """, (founder_id, source, json.dumps(payload)))

    conn.commit()
    conn.close()

    # Trigger score recomputation
    recompute_founder_score(founder_id)


def recompute_founder_score(founder_id: str) -> Dict[str, Any]:
    """
    Event-triggered recomputation of Founder Score from all signals.

    Implements the formula from contract.md:
        Founder Score = 0.30 × Track Record + 0.20 × Traction Signal
                      + 0.25 × Founder-Market Fit + 0.25 × Resilience/Coachability

    Uses EMA (Exponential Moving Average) style updates:
        - More recent signals weighted higher
        - Confidence interval narrows with more independent sources
        - Trend determined by comparing to previous score

    Args:
        founder_id: Founder to recompute score for

    Returns:
        Dict with updated score: {value, confidence_interval, trend}

    Side effects:
        - Updates founders table with new score
        - Sets last_updated timestamp
    """
    conn = _get_connection()

    # Get all signals for this founder, ordered by time
    cursor = conn.execute("""
        SELECT source, payload, timestamp
        FROM signals
        WHERE founder_id = ?
        ORDER BY timestamp ASC
    """, (founder_id,))

    signals = [(row['source'], json.loads(row['payload']), row['timestamp']) for row in cursor]

    if not signals:
        # No signals yet, return default
        return {"value": 0, "confidence_interval": 30, "trend": "stable"}

    # Get previous score for trend calculation
    cursor = conn.execute("""
        SELECT founder_score_value FROM founders WHERE founder_id = ?
    """, (founder_id,))
    row = cursor.fetchone()
    previous_score = row['founder_score_value'] if row else 0

    # Get cold_start_flag
    cursor = conn.execute("""
        SELECT cold_start_flag FROM founders WHERE founder_id = ?
    """, (founder_id,))
    row = cursor.fetchone()
    cold_start = bool(row['cold_start_flag']) if row else False

    # Extract component scores from signals
    track_record_scores = _extract_track_record_scores(signals)
    traction_scores = _extract_traction_scores(signals)
    founder_market_fit_scores = _extract_founder_market_fit_scores(signals)
    resilience_scores = _extract_resilience_scores(signals)

    # Calculate EMA for each component
    track_record = _calculate_ema(track_record_scores) if track_record_scores else 0
    traction = _calculate_ema(traction_scores) if traction_scores else 0
    founder_market_fit = _calculate_ema(founder_market_fit_scores) if founder_market_fit_scores else 0
    resilience = _calculate_ema(resilience_scores) if resilience_scores else 50  # Neutral default

    # Apply formula
    founder_score_value = (
        0.30 * track_record +
        0.20 * traction +
        0.25 * founder_market_fit +
        0.25 * resilience
    )

    founder_score_value = round(founder_score_value)

    # Calculate confidence interval (narrows with more signals)
    num_independent_sources = len(set(s[0] for s in signals))  # Count unique sources
    all_component_scores = (track_record_scores + traction_scores +
                           founder_market_fit_scores + resilience_scores)
    score_variance = _calculate_variance(all_component_scores) if all_component_scores else 20

    confidence_interval = _calculate_confidence_interval(
        num_sources=num_independent_sources,
        variance=score_variance,
        cold_start=cold_start
    )

    # Determine trend
    if previous_score == 0:
        trend = "stable"
    elif founder_score_value > previous_score + 5:
        trend = "improving"
    elif founder_score_value < previous_score - 5:
        trend = "declining"
    else:
        trend = "stable"

    # Update founders table
    conn.execute("""
        UPDATE founders
        SET founder_score_value = ?,
            founder_score_interval = ?,
            founder_score_trend = ?,
            last_updated = CURRENT_TIMESTAMP
        WHERE founder_id = ?
    """, (founder_score_value, confidence_interval, trend, founder_id))

    conn.commit()
    conn.close()

    return {
        "value": founder_score_value,
        "confidence_interval": confidence_interval,
        "trend": trend
    }


def get_founder(founder_id: str) -> Dict[str, Any]:
    """
    Retrieve current founder record from persistent storage.

    Args:
        founder_id: Founder to retrieve

    Returns:
        Dict with founder data: {
            founder_id, company_id, founder_score, cold_start_flag, last_updated
        }

    Raises:
        ValueError: If founder not found

    Example:
        founder = get_founder("f001")
        print(f"Score: {founder['founder_score']['value']} ± {founder['founder_score']['confidence_interval']}")
    """
    conn = _get_connection()

    cursor = conn.execute("""
        SELECT * FROM founders WHERE founder_id = ?
    """, (founder_id,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        raise ValueError(f"Founder {founder_id} not found in database")

    return {
        "founder_id": row['founder_id'],
        "company_id": row['company_id'],
        "founder_score": {
            "value": int(row['founder_score_value']) if row['founder_score_value'] else 0,
            "confidence_interval": int(row['founder_score_interval']) if row['founder_score_interval'] else 30,
            "trend": row['founder_score_trend'] or "stable"
        },
        "cold_start_flag": bool(row['cold_start_flag']),
        "last_updated": row['last_updated']
    }


def get_all_signals(founder_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve all signals for a founder (for debugging/audit trail).

    Args:
        founder_id: Founder to get signals for

    Returns:
        List of signal dicts with source, payload, timestamp
    """
    conn = _get_connection()

    cursor = conn.execute("""
        SELECT source, payload, timestamp
        FROM signals
        WHERE founder_id = ?
        ORDER BY timestamp DESC
    """, (founder_id,))

    signals = []
    for row in cursor:
        signals.append({
            "source": row['source'],
            "payload": json.loads(row['payload']),
            "timestamp": row['timestamp']
        })

    conn.close()
    return signals


# ==================== Outbound Outreach Lifecycle ====================
# State machine: sent -> {delivered_no_response | declined | converted}
# Logged as append-only 'outreach' signals (never overwritten), same pattern as any
# other evidence -- current status is derived by reading the latest outreach signal.

_OUTREACH_EVENTS = ("sent", "declined", "converted")


def save_outreach_event(
    founder_id: str,
    event: str,
    *,
    company_id: Optional[str] = None,
    cold_start_flag: Optional[bool] = None,
    detail: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Record an outbound-outreach lifecycle event ('sent', 'declined', or 'converted').

    Thin wrapper over save_signal() with source='outreach' -- company_id/cold_start_flag
    are threaded through the same way every other signal does (see save_signal's upsert),
    which is what makes 'converted' work: passing the real company_id here overwrites the
    outbound-discovery placeholder (e.g. "pending_<identity>") on the founders row.

    Args:
        founder_id: Founder this event is about.
        event: One of 'sent', 'declined', 'converted'.
        company_id: Pass the real company_id on a 'converted' event to replace the
            placeholder set at discovery time.
        cold_start_flag: Usually left None (unchanged) except on conversion, where the
            founder now has real deck evidence and is no longer cold-start.
        detail: Optional extra context (e.g. {"session": "...", "source_url": "..."}).
    """
    if event not in _OUTREACH_EVENTS:
        raise ValueError(f"Unknown outreach event {event!r}; expected one of {_OUTREACH_EVENTS}")
    payload: Dict[str, Any] = {"event": event, **(detail or {})}
    if company_id is not None:
        payload["company_id"] = company_id
    if cold_start_flag is not None:
        payload["cold_start_flag"] = cold_start_flag
    save_signal(founder_id, "outreach", payload)


def get_outreach_status(founder_id: str) -> Dict[str, Any]:
    """
    Current outreach status for a founder, derived from their latest 'outreach' signal.

    Returns:
        {"status": "not_activated" | "sent" | "delivered_no_response" | "declined" | "converted",
         "last_event_at": str | None}

    "sent" and "delivered_no_response" are the same underlying event ('sent') --
    "delivered_no_response" is just the read-side label once enough time has passed
    with no decline/conversion, since there is no separate delivery webhook here.
    """
    conn = _get_connection()
    cursor = conn.execute(
        """
        SELECT source, payload, timestamp FROM signals
        WHERE founder_id = ? AND source = 'outreach'
        ORDER BY id DESC LIMIT 1
        """,
        (founder_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {"status": "not_activated", "last_event_at": None}

    payload = json.loads(row["payload"])
    event = payload.get("event")
    status = "delivered_no_response" if event == "sent" else event
    return {"status": status, "last_event_at": row["timestamp"]}


def list_outbound_leads() -> List[Dict[str, Any]]:
    """
    All founders who have at least one outreach event, with their current status.

    This is the read side for a dashboard "outbound leads" view -- founders sourced via
    outbound_scan.py that haven't necessarily converted into a full deck-backed
    opportunity yet. Excludes anyone with no outreach history at all (e.g. outbound
    candidates who were recorded to Memory but never crossed the Activate threshold).

    Returns:
        List of {founder_id, company_id, founder_score, cold_start_flag, outreach_status,
        last_event_at}, most recently updated first.
    """
    conn = _get_connection()
    founder_ids = [
        row["founder_id"]
        for row in conn.execute(
            "SELECT DISTINCT founder_id FROM signals WHERE source = 'outreach'"
        )
    ]
    conn.close()

    leads = []
    for founder_id in founder_ids:
        try:
            founder = get_founder(founder_id)
        except ValueError:
            continue
        status = get_outreach_status(founder_id)
        leads.append({**founder, "outreach_status": status["status"], "last_event_at": status["last_event_at"]})

    leads.sort(key=lambda lead: lead["last_event_at"] or "", reverse=True)
    return leads


# ==================== Helper Functions for Score Calculation ====================

def _extract_track_record_scores(signals: List[Tuple]) -> List[float]:
    """
    Extract Track Record component from signals.

    Track Record comes from:
    - Deck: team background (experience, education, prior startups)
    - GitHub: longevity, repo count, consistency
    - arXiv: research publications
    """
    scores = []

    for source, payload, _ in signals:
        if source == "deck":
            # Parse team claims for experience indicators
            deck_claims = payload.get("deck_claims", [])
            team_claims = [c for c in deck_claims if c.get("field") == "team"]

            for claim in team_claims:
                value = claim.get("value", "").lower()
                score = 30  # Base score

                # Boost for big tech companies
                if any(company in value for company in ["google", "meta", "facebook", "amazon", "microsoft", "apple"]):
                    score += 20

                # Boost for years of experience
                if "10 years" in value or "10+ years" in value:
                    score += 15
                elif any(f"{i} years" in value for i in range(5, 10)):
                    score += 10
                elif any(f"{i} years" in value for i in range(2, 5)):
                    score += 5

                # Boost for education
                if any(school in value for school in ["mit", "stanford", "harvard", "phd"]):
                    score += 10

                # Boost for prior exits
                if "acquired" in value or "exit" in value:
                    score += 15

                scores.append(min(100, score))

        elif source == "github":
            github = payload
            longevity = github.get("longevity_months", 0)
            repos = github.get("repos", 0)
            consistency = github.get("commit_consistency_score", 0)

            score = 20  # Base
            score += min(30, longevity)  # Up to 30 points for longevity
            score += min(20, repos * 2)  # 2 points per repo, max 20
            score += consistency * 30    # Consistency score is 0-1, scale to 0-30

            scores.append(min(100, score))

        elif source == "arxiv":
            papers = payload.get("papers", 0)
            score = min(100, 50 + papers * 10)  # 50 base + 10 per paper
            scores.append(score)

    return scores


def _extract_traction_scores(signals: List[Tuple]) -> List[float]:
    """
    Extract Traction Signal component from signals.

    Traction comes from:
    - Deck: traction claims (users, revenue, growth)
    - Devpost/HN: launches, upvotes
    """
    scores = []

    for source, payload, _ in signals:
        if source == "deck":
            deck_claims = payload.get("deck_claims", [])
            traction_claims = [c for c in deck_claims if c.get("field") == "traction"]

            for claim in traction_claims:
                value = claim.get("value", "").lower()
                score = 10  # Base

                # Revenue indicators
                if "mrr" in value or "arr" in value:
                    score += 30

                # User count
                if "10,000" in value or "10k" in value:
                    score += 20
                elif "1,000" in value or "1k" in value:
                    score += 10

                # Growth indicators
                if "%" in value and "mom" in value:
                    score += 15

                # Retention
                if "retention" in value and any(str(i) in value for i in range(80, 100)):
                    score += 15

                scores.append(min(100, score))

        elif source == "devpost_hn":
            launches = payload.get("launches", 0)
            upvotes = payload.get("total_upvotes", 0)

            score = 20  # Base
            score += min(30, launches * 10)  # 10 points per launch
            score += min(50, upvotes / 10)    # 1 point per 10 upvotes

            scores.append(min(100, score))

    return scores


def _extract_founder_market_fit_scores(signals: List[Tuple]) -> List[float]:
    """
    Extract Founder-Market Fit component.

    This would ideally come from Multi-Axis Scorer output stored as a signal.
    For now, infer from deck problem/product alignment with team background.
    """
    scores = []

    for source, payload, _ in signals:
        if source == "deck":
            deck_claims = payload.get("deck_claims", [])
            team_claims = [c for c in deck_claims if c.get("field") == "team"]
            product_claims = [c for c in deck_claims if c.get("field") == "problem_product"]

            if team_claims and product_claims:
                team_text = " ".join([c.get("value", "") for c in team_claims]).lower()
                product_text = " ".join([c.get("value", "") for c in product_claims]).lower()

                score = 40  # Base

                # Check for domain alignment
                if "ai" in product_text and any(kw in team_text for kw in ["ml", "ai", "machine learning"]):
                    score += 30
                elif "developer" in product_text and any(kw in team_text for kw in ["engineer", "developer"]):
                    score += 30
                elif "healthcare" in product_text and any(kw in team_text for kw in ["medical", "health", "biotech"]):
                    score += 30

                scores.append(min(100, score))

    return scores


def _extract_resilience_scores(signals: List[Tuple]) -> List[float]:
    """
    Extract Resilience/Coachability component.

    Comes from Interview Agent output.
    Default to neutral (50) if no interview data.
    """
    scores = []

    for source, payload, _ in signals:
        if source == "interview":
            resilience = payload.get("resilience_score", 50)
            scores.append(resilience)

    return scores if scores else [50]  # Default neutral


def _calculate_ema(scores: List[float], alpha: float = 0.3) -> float:
    """
    Calculate Exponential Moving Average.

    More recent scores weighted higher (EMA style).

    Args:
        scores: List of scores in chronological order
        alpha: Smoothing factor (0.3 = 30% weight to new, 70% to history)

    Returns:
        EMA score
    """
    if not scores:
        return 0.0

    ema = scores[0]
    for score in scores[1:]:
        ema = alpha * score + (1 - alpha) * ema

    return ema


def _calculate_variance(scores: List[float]) -> float:
    """Calculate variance in scores (measure of consistency)."""
    if len(scores) < 2:
        return 0.0

    mean = sum(scores) / len(scores)
    variance = sum((x - mean) ** 2 for x in scores) / len(scores)
    return math.sqrt(variance)  # Standard deviation


def _calculate_confidence_interval(num_sources: int, variance: float, cold_start: bool) -> int:
    """
    Calculate confidence interval based on evidence quantity and consistency.

    Narrows as we get more independent sources.
    Widens if scores are inconsistent (high variance).

    Args:
        num_sources: Number of independent signal sources
        variance: Score variance (standard deviation)
        cold_start: Whether this is a cold-start founder

    Returns:
        Confidence interval (5-30 range)
    """
    # Base interval
    base = 25 if cold_start else 15

    # Reduce with more sources (max 60% reduction)
    source_factor = min(num_sources / 8, 0.6)
    interval = base * (1 - source_factor)

    # Increase if scores inconsistent
    variance_penalty = min(variance / 5, 10)  # Cap at +10
    interval += variance_penalty

    # Clamp to reasonable range
    return max(5, min(30, int(interval)))
