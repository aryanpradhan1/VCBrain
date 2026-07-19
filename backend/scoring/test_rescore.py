#!/usr/bin/env python3
"""Test rescoring with updated rubric."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import json
import sqlite3
from backend.scoring.multi_axis_scorer import score_all_axes

def test_rescore():
    """Rescore Jvala with the new rubric."""
    print("=" * 60)
    print("Testing Updated Founder Score Rubric")
    print("=" * 60)

    # Get the application
    conn = sqlite3.connect('backend/data/founderscore.sqlite3')
    cursor = conn.cursor()
    cursor.execute("SELECT signal_json FROM applications WHERE company_id = 'app-c07538e3e2'")
    row = cursor.fetchone()

    if not row:
        print("❌ Application not found")
        return

    signal = json.loads(row[0])

    print("\nInput data:")
    print(f"  Cold start: {signal.get('cold_start_flag')}")
    print(f"  GitHub repos: {signal.get('public_signals', {}).get('github', {}).get('repos', 0)}")
    team_claims = [c for c in signal.get('deck_claims', []) if c.get('field') == 'team']
    print(f"  Team claims: {len(team_claims)}")
    if team_claims:
        print(f"    {team_claims[0].get('value')[:80]}...")

    print("\n🔄 Rescoring with updated rubric...")
    print("   (This will make an OpenAI API call)")

    try:
        result = score_all_axes(signal)

        print(f"\n✅ New Score Results:")
        print(f"   Founder Score: {result.founder_score.value} ± {result.founder_score.confidence_interval}")
        print(f"   Trend: {result.founder_score.trend}")
        print(f"\n   Founder Axis: {result.founder_axis.score}/100")
        print(f"   Rationale: {result.founder_axis.rationale}")

        if result.founder_score.value < 40:
            print(f"\n⚠️  WARNING: Still scoring below 40! This should be at least 50-60 for a legitimate application.")
        elif result.founder_score.value >= 50:
            print(f"\n✅ Good! Score is now in the reasonable range (50+)")

    except Exception as e:
        print(f"\n❌ Error: {e}")

    conn.close()

if __name__ == "__main__":
    test_rescore()
