"""
Scoring Module - Multi-Axis Scorer + Thesis Engine + Query Parser
Independent LLM-based scoring with citations, never averaged
"""

from .multi_axis_scorer import (
    score_founder_axis,
    score_market_axis,
    score_idea_vs_market_axis,
    score_all_axes,
    calculate_founder_score_from_axes,
    AxisScore,
    AxisRating,
    FounderScore,
    MultiAxisOutput,
)

from .thesis_engine import (
    evaluate_thesis_fit,
    ThesisOutput,
    DEFAULT_THESIS,
)

from .query_parser import (
    parse_natural_language_query,
    match_opportunity,
    StructuredQuery,
)

__all__ = [
    # Multi-Axis Scorer
    "score_founder_axis",
    "score_market_axis",
    "score_idea_vs_market_axis",
    "score_all_axes",
    "calculate_founder_score_from_axes",
    "AxisScore",
    "AxisRating",
    "FounderScore",
    "MultiAxisOutput",
    # Thesis Engine
    "evaluate_thesis_fit",
    "ThesisOutput",
    "DEFAULT_THESIS",
    # Query Parser
    "parse_natural_language_query",
    "match_opportunity",
    "StructuredQuery",
]
