"""
Test script for Thesis Engine
Tests deterministic gate + LLM judgment for adjacent cases
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.scoring.thesis_engine import evaluate_thesis_fit, DEFAULT_THESIS


def test_exact_match():
    """Test exact thesis match (AI/ML infrastructure)"""
    print("\n" + "="*70)
    print("  TEST 1: EXACT MATCH (AI/ML Infrastructure)")
    print("="*70)

    with open("../../shared/fixtures/signal_intake_exact_match.json") as f:
        data = json.load(f)

    result = evaluate_thesis_fit(data)

    print(f"\n✓ Thesis Match: {result.thesis_match}")
    print(f"  Match Type: {result.match_type}")
    print(f"  Rationale: {result.rationale}")

    assert result.thesis_match is True, "Expected exact match to pass"
    assert result.match_type == "exact", "Expected match_type to be 'exact'"
    print("\n✅ Test passed")


def test_adjacent_sector():
    """Test adjacent sector requiring LLM judgment (Cloud infrastructure)"""
    print("\n" + "="*70)
    print("  TEST 2: ADJACENT SECTOR (Cloud Infrastructure)")
    print("="*70)

    with open("../../shared/fixtures/signal_intake_adjacent.json") as f:
        data = json.load(f)

    result = evaluate_thesis_fit(data)

    print(f"\n✓ Thesis Match: {result.thesis_match}")
    print(f"  Match Type: {result.match_type}")
    print(f"  Rationale: {result.rationale}")

    assert result.match_type == "adjacent_llm_judged", "Expected LLM judgment for adjacent sector"
    print("\n✅ Test passed (LLM made the call)")


def test_hard_reject():
    """Test hard reject (consumer food app, wrong sector + over budget)"""
    print("\n" + "="*70)
    print("  TEST 3: HARD REJECT (Consumer Food App)")
    print("="*70)

    with open("../../shared/fixtures/signal_intake_reject.json") as f:
        data = json.load(f)

    result = evaluate_thesis_fit(data)

    print(f"\n✓ Thesis Match: {result.thesis_match}")
    print(f"  Match Type: {result.match_type}")
    print(f"  Rationale: {result.rationale}")

    assert result.thesis_match is False, "Expected hard reject to fail"
    print("\n✅ Test passed (correctly rejected)")


def print_thesis_config():
    """Display current thesis configuration"""
    print("\n" + "="*70)
    print("  FUND THESIS CONFIGURATION")
    print("="*70)
    print(f"\nCore Sectors: {', '.join(DEFAULT_THESIS['sectors'])}")
    print(f"Adjacent Sectors: {', '.join(DEFAULT_THESIS['adjacent_sectors'])}")
    print(f"Stage: {', '.join(DEFAULT_THESIS['stage'])}")
    print(f"Geography: {', '.join(DEFAULT_THESIS['geography'])}")
    print(f"Check Size: ${DEFAULT_THESIS['check_size_min']:,} - ${DEFAULT_THESIS['check_size_max']:,}")
    print()


if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("\n⚠️  OPENAI_API_KEY not set")
        print("Note: Test 1 and Test 3 will work (deterministic only)")
        print("Test 2 requires API key (LLM judgment for adjacent sector)")
        print()

    print("\n" + "="*70)
    print("  🧪 THESIS ENGINE — COMPREHENSIVE TEST")
    print("="*70)

    print_thesis_config()

    try:
        test_exact_match()
        test_hard_reject()

        # Only run LLM test if API key is available
        if os.getenv("OPENAI_API_KEY"):
            test_adjacent_sector()
        else:
            print("\n⏭️  Skipping adjacent sector test (no API key)")

        print("\n" + "="*70)
        print("  ✅ ALL TESTS PASSED")
        print("="*70)
        print("\nKey Features Validated:")
        print("  • Deterministic gate filters by sector/stage/geo/check ✓")
        print("  • Exact matches pass immediately (no LLM needed) ✓")
        print("  • Hard rejects fail fast (no LLM wasted) ✓")
        if os.getenv("OPENAI_API_KEY"):
            print("  • Adjacent sectors trigger LLM judgment ✓")
        print()

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
