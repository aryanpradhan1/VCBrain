"""
Thesis Engine — Investment Thesis Matching

Two-stage filter:
1. Deterministic gate (sector/stage/geography/check-size) — plain if/else, no LLM
2. LLM judgment for ambiguous/adjacent matches only
"""

import os
from typing import Dict, List, Any, Literal
from openai import OpenAI
from pydantic import BaseModel


# Type definitions matching the contract
class ThesisOutput(BaseModel):
    thesis_match: bool
    match_type: Literal["exact", "adjacent_llm_judged"]
    rationale: str


# Investment thesis configuration
# In production, this would be loaded from database or config file
DEFAULT_THESIS = {
    "sectors": [
        "AI/ML infrastructure",
        "Developer tools",
        "Enterprise SaaS",
        "Climate tech",
        "Healthcare tech",
        "Fintech"
    ],
    "adjacent_sectors": [
        "Data infrastructure",
        "Cloud infrastructure",
        "DevOps",
        "Clean energy",
        "Biotech",
        "Insurtech"
    ],
    "stage": ["pre-seed", "seed"],
    "geography": ["US", "Canada", "Western Europe"],
    "check_size_min": 50000,
    "check_size_max": 150000,
    "requirements": {
        "technical_founder": True,  # At least one technical co-founder
        "min_team_size": 1,
        "max_team_size": 5
    }
}


# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4o-2024-11-20"


def extract_sector_from_claims(deck_claims: List[Dict[str, Any]]) -> str:
    """
    Extract the company's sector from deck claims.
    Looks at problem/product claims to infer sector.
    """
    problem_claims = [
        c.get("value", "") for c in deck_claims
        if c.get("field") in ["problem_product", "market_size"]
    ]

    if not problem_claims:
        return "unknown"

    # Simple keyword-based sector detection
    # Order matters - check more specific sectors first
    combined = " ".join(problem_claims).lower()

    # Check adjacent/specific sectors first before broader categories
    if any(kw in combined for kw in ["cloud", "multi-cloud", "aws", "azure", "gcp", "hosting"]):
        return "Cloud infrastructure"
    elif any(kw in combined for kw in ["data warehouse", "data pipeline", "analytics", "etl"]):
        return "Data infrastructure"
    elif any(kw in combined for kw in ["ai", "ml", "machine learning", "artificial intelligence", "llm"]):
        return "AI/ML infrastructure"
    elif any(kw in combined for kw in ["developer", "devops", "code", "api"]):
        return "Developer tools"
    elif any(kw in combined for kw in ["enterprise", "b2b", "saas", "workflow"]):
        return "Enterprise SaaS"
    elif any(kw in combined for kw in ["climate", "carbon", "sustainability", "renewable", "clean energy"]):
        return "Climate tech"
    elif any(kw in combined for kw in ["health", "medical", "biotech", "pharma"]):
        return "Healthcare tech"
    elif any(kw in combined for kw in ["fintech", "finance", "payment", "banking"]):
        return "Fintech"

    return "unknown"


def extract_ask_amount(deck_claims: List[Dict[str, Any]]) -> int:
    """
    Extract the funding ask amount from deck claims.
    Returns 0 if not found.
    """
    ask_claims = [c for c in deck_claims if c.get("field") == "ask"]

    if not ask_claims:
        return 0

    # Simple extraction: look for numbers in the claim
    import re
    for claim in ask_claims:
        value = claim.get("value", "")
        # Look for patterns like "$100K", "$100,000", "100k"
        numbers = re.findall(r'\$?([\d,]+)k', value.lower())
        if numbers:
            return int(numbers[0].replace(',', '')) * 1000

        numbers = re.findall(r'\$?([\d,]+)', value)
        if numbers:
            return int(numbers[0].replace(',', ''))

    return 0


def deterministic_gate(
    signal_data: Dict[str, Any],
    thesis: Dict[str, Any] = None
) -> tuple[bool, str, str]:
    """
    Stage 1: Deterministic filtering based on hard criteria.

    Returns:
        (passes_gate, match_type, reason)
        - passes_gate: True if passes, False if hard reject
        - match_type: "exact" | "adjacent" | "reject"
        - reason: explanation of the decision
    """

    if thesis is None:
        thesis = DEFAULT_THESIS

    deck_claims = signal_data.get("deck_claims", [])

    # 1. Check sector
    sector = extract_sector_from_claims(deck_claims)

    exact_sector_match = sector in thesis["sectors"]
    adjacent_sector_match = sector in thesis.get("adjacent_sectors", [])

    if sector == "unknown":
        return (True, "adjacent", "Sector unclear from deck, requires LLM judgment")

    if not exact_sector_match and not adjacent_sector_match:
        return (False, "reject", f"Sector '{sector}' not in thesis (core or adjacent)")

    # 2. Check geography (simplified - would need better extraction in production)
    # For now, default to US unless specified otherwise
    geography = "US"  # Placeholder - would extract from founder/company data

    if geography not in thesis["geography"]:
        return (False, "reject", f"Geography '{geography}' not in thesis")

    # 3. Check stage (simplified - infer from traction)
    # If they have significant revenue/users, likely beyond seed
    traction_claims = [c for c in deck_claims if c.get("field") == "traction"]
    has_revenue = any("$" in c.get("value", "") and ("MRR" in c.get("value", "") or "ARR" in c.get("value", ""))
                      for c in traction_claims)

    revenue_amount = 0
    if has_revenue:
        # Extract revenue amount (simplified)
        import re
        for claim in traction_claims:
            value = claim.get("value", "")
            numbers = re.findall(r'\$?([\d,]+)k', value)
            if numbers:
                revenue_amount = int(numbers[0].replace(',', '')) * 1000

    # Pre-seed: < $5K MRR, Seed: $5K-$50K MRR, beyond seed: > $50K
    if revenue_amount > 50000:
        return (False, "reject", "Stage too late (revenue suggests Series A+)")

    # 4. Check ask amount
    ask_amount = extract_ask_amount(deck_claims)

    if ask_amount > 0:  # Only check if ask is specified
        if ask_amount < thesis["check_size_min"]:
            return (False, "reject", f"Ask ${ask_amount:,} below minimum check ${thesis['check_size_min']:,}")
        # The deck's raise is the total round, not necessarily this fund's check. A
        # larger round can still accommodate the fund's configured check size, so it is
        # a sizing note for the partner—not a thesis rejection.

    # If we got here, it's either exact or adjacent
    round_note = ""
    if ask_amount > thesis["check_size_max"]:
        round_note = f"; total raise ${ask_amount:,} exceeds this fund's typical check but can accommodate a partial check"
    if exact_sector_match:
        return (True, "exact", f"Exact match: {sector}, {geography}, appropriate stage{round_note}")
    else:
        return (True, "adjacent", f"Adjacent sector: {sector} — requires LLM judgment for fit")


def llm_judgment(
    signal_data: Dict[str, Any],
    deterministic_reason: str,
    thesis: Dict[str, Any] = None
) -> tuple[bool, str]:
    """
    Stage 2: LLM judgment for ambiguous/adjacent cases.

    Only called when deterministic gate returns "adjacent".

    Returns:
        (matches_thesis, rationale)
    """

    if thesis is None:
        thesis = DEFAULT_THESIS

    deck_claims = signal_data.get("deck_claims", [])
    sector = extract_sector_from_claims(deck_claims)

    # Build context from deck claims
    problem_claims = [c for c in deck_claims if c.get("field") in ["problem_product", "market_size"]]
    problem_context = "\n".join([
        f"- {c.get('value')}"
        for c in problem_claims
    ])

    team_claims = [c for c in deck_claims if c.get("field") == "team"]
    team_context = "\n".join([
        f"- {c.get('value')}"
        for c in team_claims
    ])

    prompt = f"""You are evaluating whether an investment opportunity fits the fund's thesis.

FUND THESIS (Core Focus):
{', '.join(thesis['sectors'])}

Adjacent sectors considered case-by-case:
{', '.join(thesis.get('adjacent_sectors', []))}

Stage: {', '.join(thesis['stage'])}
Geography: {', '.join(thesis['geography'])}

CANDIDATE COMPANY:

Inferred Sector: {sector}
Deterministic Filter Result: {deterministic_reason}

Problem/Product:
{problem_context if problem_context else "- Not specified"}

Team:
{team_context if team_context else "- Not specified"}

TASK:

The deterministic filter marked this as "adjacent" — it's not a perfect match but close enough to warrant deeper judgment.

Decide: Does this opportunity fit the fund's thesis well enough to proceed to scoring?

Consider:
1. Is the sector truly adjacent (strategic fit) or just labeled wrong?
2. Does the team's background suggest they can execute in this space?
3. Is there a clear path to the fund's core thesis areas (e.g., builds infra that will serve AI/ML use cases)?

Respond with JSON:
{{
  "thesis_match": true or false,
  "rationale": "2-3 sentences explaining your decision, focusing on strategic fit"
}}
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a senior VC partner evaluating thesis fit. Be selective but fair."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.3
    )

    result = response.choices[0].message.content
    import json
    parsed = json.loads(result)

    return (parsed["thesis_match"], parsed["rationale"])


def evaluate_thesis_fit(
    signal_data: Dict[str, Any],
    thesis: Dict[str, Any] = None
) -> ThesisOutput:
    """
    Main entry point: evaluates investment opportunity against fund thesis.

    Two-stage process:
    1. Deterministic gate (fast, rule-based)
    2. LLM judgment for ambiguous cases (only when needed)

    Returns ThesisOutput matching the contract.
    """

    # Stage 1: Deterministic filtering
    passes_gate, match_type, reason = deterministic_gate(signal_data, thesis)

    if match_type == "reject":
        return ThesisOutput(
            thesis_match=False,
            match_type="exact",  # Even rejects are "exact" non-matches
            rationale=reason
        )

    if match_type == "exact":
        return ThesisOutput(
            thesis_match=True,
            match_type="exact",
            rationale=reason
        )

    # Stage 2: LLM judgment for adjacent cases
    matches, llm_rationale = llm_judgment(signal_data, reason, thesis)

    return ThesisOutput(
        thesis_match=matches,
        match_type="adjacent_llm_judged",
        rationale=llm_rationale
    )
