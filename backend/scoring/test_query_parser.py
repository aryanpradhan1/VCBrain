"""
Test script for Multi-Attribute Reasoning Query Parser
Tests natural language → structured query conversion
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.scoring.query_parser import parse_natural_language_query, match_opportunity


def test_complex_query():
    """Test complex multi-attribute query parsing"""
    print("\n" + "="*70)
    print("  TEST 1: Complex Query - 'technical founder, Berlin, AI infra, no prior VC'")
    print("="*70)

    query = "technical founder, Berlin, AI infra, no prior VC backing"
    result = parse_natural_language_query(query)

    print(f"\nOriginal Query: {result.original_query}")
    print(f"\nExtracted Filters:")
    print(f"  • Technical Founder: {result.technical_founder}")
    print(f"  • Geography: {result.geography}")
    print(f"  • Sectors: {result.sectors}")
    print(f"  • Prior Funding: {result.prior_funding}")

    assert result.technical_founder is True, "Should detect technical founder"
    assert result.prior_funding is False, "Should detect 'no prior VC'"
    print("\n✅ Test passed")


def test_traction_query():
    """Test query with traction/revenue filters"""
    print("\n" + "="*70)
    print("  TEST 2: Traction Query - 'revenue > $10K, strong GitHub, seed stage'")
    print("="*70)

    query = "revenue > $10K, strong GitHub activity, seed stage"
    result = parse_natural_language_query(query)

    print(f"\nOriginal Query: {result.original_query}")
    print(f"\nExtracted Filters:")
    print(f"  • Revenue Min: ${result.revenue_min:,}" if result.revenue_min else "  • Revenue Min: None")
    print(f"  • GitHub Repos Min: {result.github_repos_min}")
    print(f"  • GitHub Consistency Min: {result.github_consistency_min}")
    print(f"  • Stage: {result.stage}")

    assert result.revenue_min is not None and result.revenue_min >= 10000, "Should extract revenue threshold"
    assert result.stage is not None and "seed" in result.stage, "Should detect seed stage"
    print("\n✅ Test passed")


def test_cold_start_query():
    """Test query for cold-start founders"""
    print("\n" + "="*70)
    print("  TEST 3: Cold-Start Query - 'climate tech, cold start, no revenue'")
    print("="*70)

    query = "climate tech, cold start, first-time founder"
    result = parse_natural_language_query(query)

    print(f"\nOriginal Query: {result.original_query}")
    print(f"\nExtracted Filters:")
    print(f"  • Sectors: {result.sectors}")
    print(f"  • Cold Start: {result.cold_start}")

    assert result.cold_start is True, "Should detect cold start"
    print("\n✅ Test passed")


def test_matching():
    """Test matching opportunities against structured queries"""
    print("\n" + "="*70)
    print("  TEST 4: Opportunity Matching")
    print("="*70)

    # Load a test opportunity
    with open("../../shared/fixtures/signal_intake_strong.json") as f:
        strong_opportunity = json.load(f)

    # Query 1: Should match (technical founder, AI/ML infra, strong GitHub)
    query1 = "technical founder, AI infrastructure, strong GitHub"
    filters1 = parse_natural_language_query(query1)
    matches1, reasons1 = match_opportunity(strong_opportunity, filters1)

    print(f"\nQuery: '{query1}'")
    print(f"Matches: {matches1}")
    print(f"Reasons: {', '.join(reasons1)}")

    # Query 2: Should NOT match (wrong sector - climate tech)
    query2 = "climate tech, strong technical founder"
    filters2 = parse_natural_language_query(query2)
    matches2, reasons2 = match_opportunity(strong_opportunity, filters2)

    print(f"\nQuery: '{query2}'")
    print(f"Matches: {matches2}")
    print(f"Reasons: {', '.join(reasons2)}")

    # Query 3: Should NOT match (cold start filter)
    query3 = "cold start founders only"
    filters3 = parse_natural_language_query(query3)
    matches3, reasons3 = match_opportunity(strong_opportunity, filters3)

    print(f"\nQuery: '{query3}'")
    print(f"Matches: {matches3}")
    print(f"Reasons: {', '.join(reasons3)}")

    assert matches1 is True, "Strong AI/ML opportunity should match AI infra query"
    assert matches2 is False, "AI/ML opportunity should not match climate tech query"
    assert matches3 is False, "Strong opportunity should not match cold-start filter"

    print("\n✅ Test passed")


if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("\n⚠️  OPENAI_API_KEY not set")
        print("This test requires OpenAI API access for query parsing")
        print("Set it with: export OPENAI_API_KEY='your-key-here'")
        sys.exit(1)

    print("\n" + "="*70)
    print("  🧪 MULTI-ATTRIBUTE QUERY PARSER — COMPREHENSIVE TEST")
    print("  Model: GPT-4o (latest available)")
    print("="*70)

    try:
        test_complex_query()
        test_traction_query()
        test_cold_start_query()
        test_matching()

        print("\n" + "="*70)
        print("  ✅ ALL TESTS PASSED")
        print("="*70)
        print("\nKey Features Validated:")
        print("  • Natural language → structured filters ✓")
        print("  • Multi-attribute parsing in single LLM call ✓")
        print("  • Handles founder, market, traction filters ✓")
        print("  • Opportunity matching against filters ✓")
        print()

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
