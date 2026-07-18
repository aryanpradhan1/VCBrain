"""
Multi-Attribute Reasoning Query Parser

Converts natural language queries into structured filters for searching founders/opportunities.
Single LLM call resolves compound queries instead of manual filter building.

Examples:
- "technical founder, Berlin, AI infra, no prior VC backing"
- "climate tech, seed stage, strong GitHub, revenue > $10K"
- "MIT grad, healthcare, cold start"
"""

import os
from typing import Dict, List, Any, Optional
from openai import OpenAI
from pydantic import BaseModel


# Structured query output
class StructuredQuery(BaseModel):
    """
    Structured representation of a natural language query.
    Each field is optional and represents a filter criterion.
    """
    # Founder filters
    technical_founder: Optional[bool] = None
    founder_background: Optional[List[str]] = None  # e.g., ["MIT", "Meta", "PhD"]
    founder_score_min: Optional[int] = None
    founder_score_max: Optional[int] = None

    # Company/Market filters
    sectors: Optional[List[str]] = None
    geography: Optional[List[str]] = None
    stage: Optional[List[str]] = None

    # Traction filters
    revenue_min: Optional[int] = None  # In dollars
    revenue_max: Optional[int] = None
    users_min: Optional[int] = None
    github_repos_min: Optional[int] = None
    github_consistency_min: Optional[float] = None  # 0.0 to 1.0

    # Funding filters
    prior_funding: Optional[bool] = None  # True = has funding, False = no funding
    cold_start: Optional[bool] = None

    # Source filters
    sourcing_channel: Optional[str] = None  # "inbound" | "outbound"

    # Raw query for reference
    original_query: str


# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4o-2024-11-20"


def parse_natural_language_query(query: str) -> StructuredQuery:
    """
    Parse a natural language query into structured filters.

    Single LLM call resolves all constraints in one pass.

    Args:
        query: Natural language search query

    Returns:
        StructuredQuery with extracted filters

    Examples:
        >>> parse_natural_language_query("technical founder, Berlin, AI infra")
        StructuredQuery(
            technical_founder=True,
            geography=["Berlin"],
            sectors=["AI/ML infrastructure"]
        )

        >>> parse_natural_language_query("revenue > $10K, no VC backing, seed stage")
        StructuredQuery(
            revenue_min=10000,
            prior_funding=False,
            stage=["seed"]
        )
    """

    prompt = f"""You are parsing a natural language search query into structured database filters.

USER QUERY:
"{query}"

Your task: Extract all filter criteria from this query and map them to the appropriate structured fields.

AVAILABLE FILTER FIELDS:

Founder Filters:
- technical_founder: boolean (mentions "technical", "engineer", "developer", "CS degree", etc.)
- founder_background: list of strings (universities, companies, credentials like "MIT", "Google", "PhD")
- founder_score_min: integer 0-100 (if they say "strong founder", "high score", estimate threshold)
- founder_score_max: integer 0-100 (if they say "weak founder", "low score", estimate threshold)

Company/Market Filters:
- sectors: list from ["AI/ML infrastructure", "Developer tools", "Enterprise SaaS", "Climate tech", "Healthcare tech", "Fintech", "Data infrastructure", "Cloud infrastructure"]
- geography: list of cities/countries ["US", "Canada", "Western Europe", "Berlin", "London", "San Francisco", etc.]
- stage: list from ["pre-seed", "seed", "Series A", "Series B+"]

Traction Filters:
- revenue_min: integer in dollars (extract from "revenue > $10K", "$5K MRR+", etc.)
- revenue_max: integer in dollars
- users_min: integer (extract from "1K+ users", "at least 500 users")
- github_repos_min: integer (extract from "active GitHub", "10+ repos")
- github_consistency_min: float 0.0-1.0 (extract from "strong GitHub", "consistent commits" → estimate 0.7+)

Funding Filters:
- prior_funding: boolean (True if "has funding"/"funded", False if "no VC"/"unfunded"/"bootstrapped")
- cold_start: boolean (True if "cold start"/"no track record"/"first-time founder")

Source Filters:
- sourcing_channel: "inbound" or "outbound" (if mentioned)

INSTRUCTIONS:
1. Extract ALL applicable filters from the query
2. Leave fields as null if not mentioned in the query
3. Be smart about synonyms (e.g., "AI" → "AI/ML infrastructure", "Berlin" → geography list)
4. For numeric thresholds, infer reasonable values (e.g., "strong GitHub" → repos_min: 5, consistency_min: 0.7)
5. Return ONLY the JSON, no explanation

Respond in this exact JSON format (omit fields that are null):
{{
  "technical_founder": true or false or null,
  "founder_background": ["string"] or null,
  "founder_score_min": integer or null,
  "founder_score_max": integer or null,
  "sectors": ["string"] or null,
  "geography": ["string"] or null,
  "stage": ["string"] or null,
  "revenue_min": integer or null,
  "revenue_max": integer or null,
  "users_min": integer or null,
  "github_repos_min": integer or null,
  "github_consistency_min": float or null,
  "prior_funding": true or false or null,
  "cold_start": true or false or null,
  "sourcing_channel": "string" or null,
  "original_query": "{query}"
}}
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a query parser that converts natural language to structured database filters. Be precise and conservative."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.2  # Low temperature for consistency
    )

    result = response.choices[0].message.content
    import json
    parsed = json.loads(result)

    return StructuredQuery(**parsed)


def match_opportunity(opportunity: Dict[str, Any], filters: StructuredQuery) -> tuple[bool, List[str]]:
    """
    Check if an opportunity matches the structured query filters.

    Args:
        opportunity: Opportunity data (Signal Intake output format)
        filters: Structured query filters

    Returns:
        (matches, reasons) - Whether it matches and why/why not
    """

    reasons = []
    matches = True

    # Founder filters
    if filters.technical_founder is not None:
        deck_claims = opportunity.get("deck_claims", [])
        team_claims = [c for c in deck_claims if c.get("field") == "team"]
        team_text = " ".join([c.get("value", "").lower() for c in team_claims])

        is_technical = any(kw in team_text for kw in ["engineer", "developer", "cs", "mit", "stanford", "phd", "technical", "code"])

        if filters.technical_founder and not is_technical:
            matches = False
            reasons.append("Not a technical founder")
        elif not filters.technical_founder and is_technical:
            matches = False
            reasons.append("Founder is technical (filter wants non-technical)")

    if filters.founder_background:
        deck_claims = opportunity.get("deck_claims", [])
        team_claims = [c for c in deck_claims if c.get("field") == "team"]
        team_text = " ".join([c.get("value", "") for c in team_claims])

        found_any = any(bg.lower() in team_text.lower() for bg in filters.founder_background)
        if not found_any:
            matches = False
            reasons.append(f"Founder background doesn't include {', '.join(filters.founder_background)}")

    # Sector filter
    if filters.sectors:
        # Extract sector from opportunity (reuse logic from thesis_engine)
        from .thesis_engine import extract_sector_from_claims
        sector = extract_sector_from_claims(opportunity.get("deck_claims", []))

        if sector not in filters.sectors:
            matches = False
            reasons.append(f"Sector '{sector}' not in {filters.sectors}")

    # Geography filter
    if filters.geography:
        # Simplified: assume US unless specified otherwise
        # In production, would extract from founder/company data
        geo = "US"  # Placeholder
        if geo not in filters.geography and not any(geo in g for g in filters.geography):
            matches = False
            reasons.append(f"Geography '{geo}' not in {filters.geography}")

    # Stage filter
    if filters.stage:
        # Infer stage from traction (simplified)
        deck_claims = opportunity.get("deck_claims", [])
        traction_claims = [c for c in deck_claims if c.get("field") == "traction"]

        import re
        revenue = 0
        for claim in traction_claims:
            value = claim.get("value", "")
            numbers = re.findall(r'\$?([\d,]+)k', value.lower())
            if numbers and ("mrr" in value.lower() or "arr" in value.lower()):
                revenue = int(numbers[0].replace(',', '')) * 1000

        if revenue < 5000:
            stage = "pre-seed"
        elif revenue < 50000:
            stage = "seed"
        else:
            stage = "Series A"

        if stage not in filters.stage:
            matches = False
            reasons.append(f"Stage '{stage}' not in {filters.stage}")

    # Revenue filter
    if filters.revenue_min is not None or filters.revenue_max is not None:
        deck_claims = opportunity.get("deck_claims", [])
        traction_claims = [c for c in deck_claims if c.get("field") == "traction"]

        import re
        revenue = 0
        for claim in traction_claims:
            value = claim.get("value", "")
            numbers = re.findall(r'\$?([\d,]+)k', value.lower())
            if numbers and ("mrr" in value.lower() or "arr" in value.lower()):
                revenue = int(numbers[0].replace(',', '')) * 1000

        if filters.revenue_min and revenue < filters.revenue_min:
            matches = False
            reasons.append(f"Revenue ${revenue:,} below minimum ${filters.revenue_min:,}")

        if filters.revenue_max and revenue > filters.revenue_max:
            matches = False
            reasons.append(f"Revenue ${revenue:,} above maximum ${filters.revenue_max:,}")

    # GitHub filters
    public_signals = opportunity.get("public_signals", {})
    github = public_signals.get("github", {})

    if filters.github_repos_min is not None:
        repos = github.get("repos", 0)
        if repos < filters.github_repos_min:
            matches = False
            reasons.append(f"GitHub repos {repos} below minimum {filters.github_repos_min}")

    if filters.github_consistency_min is not None:
        consistency = github.get("commit_consistency_score", 0)
        if consistency < filters.github_consistency_min:
            matches = False
            reasons.append(f"GitHub consistency {consistency:.2f} below minimum {filters.github_consistency_min:.2f}")

    # Prior funding filter
    if filters.prior_funding is not None:
        # Simplified: check if ask mentions "additional" or "follow-on"
        deck_claims = opportunity.get("deck_claims", [])
        ask_claims = [c for c in deck_claims if c.get("field") == "ask"]
        has_funding = any("follow" in c.get("value", "").lower() or "additional" in c.get("value", "").lower() for c in ask_claims)

        if filters.prior_funding and not has_funding:
            matches = False
            reasons.append("No prior funding (filter requires funded)")
        elif not filters.prior_funding and has_funding:
            matches = False
            reasons.append("Has prior funding (filter requires unfunded)")

    # Cold start filter
    if filters.cold_start is not None:
        cold_start = opportunity.get("cold_start_flag", False)
        if filters.cold_start != cold_start:
            matches = False
            reasons.append(f"Cold start: {cold_start} (filter wants {filters.cold_start})")

    # Sourcing channel filter
    if filters.sourcing_channel:
        channel = opportunity.get("sourcing_channel", "")
        if channel != filters.sourcing_channel:
            matches = False
            reasons.append(f"Channel '{channel}' doesn't match '{filters.sourcing_channel}'")

    if matches:
        reasons = ["All filters matched"]

    return (matches, reasons)
