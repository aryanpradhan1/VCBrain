"""
Test script for Founder axis scorer
"""

import json
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.scoring.multi_axis_scorer import score_founder_axis


def test_strong_founder():
    """Test scoring against a strong founder profile"""
    print("\n" + "="*60)
    print("Testing STRONG founder profile")
    print("="*60)

    with open("../../shared/fixtures/signal_intake_strong.json") as f:
        data = json.load(f)

    result = score_founder_axis(data)

    print(f"\nScore: {result.score}/100")
    print(f"Trend: {result.trend}")
    print(f"\nRationale:")
    print(f"  {result.rationale}")
    print(f"\nCitations:")
    for citation in result.citations:
        print(f"  - {citation}")

    assert result.score >= 60, f"Expected strong founder to score >=60, got {result.score}"
    print("\n✓ Test passed")


def test_cold_start_founder():
    """Test scoring against a cold-start founder profile"""
    print("\n" + "="*60)
    print("Testing COLD-START founder profile")
    print("="*60)

    with open("../../shared/fixtures/signal_intake_cold_start.json") as f:
        data = json.load(f)

    result = score_founder_axis(data)

    print(f"\nScore: {result.score}/100")
    print(f"Trend: {result.trend}")
    print(f"\nRationale:")
    print(f"  {result.rationale}")
    print(f"\nCitations:")
    for citation in result.citations:
        print(f"  - {citation}")

    assert result.score <= 65, f"Expected cold-start founder to score <=65, got {result.score}"
    print("\n✓ Test passed")


if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY environment variable not set")
        sys.exit(1)

    print("\n🧪 Testing Founder Axis Scorer")
    print("Model: GPT-4o (latest available)")

    try:
        test_strong_founder()
        test_cold_start_founder()

        print("\n" + "="*60)
        print("✅ All tests passed!")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
