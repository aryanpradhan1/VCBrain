"""
Multi-Axis Scorer — Founder / Market / Idea-vs-Market
Each axis scored independently with LLM reasoning, never averaged.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Any, Literal
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

# This module reads OPENAI_API_KEY at import time (below), so it must be loaded before
# that regardless of entry point -- main.py loading backend/.env doesn't help when this
# module is imported directly (a standalone script, a test run, a REPL). Silent no-op if
# backend/.env doesn't exist.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")


# Type definitions matching the contract
class AxisScore(BaseModel):
    score: int  # 0-100 for Founder axis
    trend: Literal["improving", "declining", "stable"]
    rationale: str
    citations: List[str]


class AxisRating(BaseModel):
    rating: Literal["bullish", "neutral", "bear"]
    trend: Literal["improving", "declining", "stable"]
    rationale: str
    citations: List[str]


class FounderScore(BaseModel):
    value: int
    confidence_interval: int
    trend: Literal["improving", "declining", "stable"]


class MultiAxisOutput(BaseModel):
    founder_axis: AxisScore
    market_axis: AxisRating
    idea_vs_market_axis: AxisRating
    founder_score: FounderScore


# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4o-2024-11-20"  # Using latest available model


def score_founder_axis(signal_data: Dict[str, Any]) -> AxisScore:
    """
    Score the Founder axis using LLM reasoning.

    Evaluates:
    - Track record (prior experience, technical depth, execution history)
    - Public signals (GitHub consistency, launches, papers)
    - Demonstrated execution ability

    NOT evaluated here:
    - Market timing (that's Market axis)
    - Product-market fit (that's Idea-vs-Market axis)
    - Resilience/Coachability (comes from Interview Agent)
    """

    # Extract relevant data
    deck_claims = signal_data.get("deck_claims", [])
    public_signals = signal_data.get("public_signals", {})
    cold_start = signal_data.get("cold_start_flag", False)

    # Build context for the LLM
    github_context = ""
    if "github" in public_signals:
        gh = public_signals["github"]
        github_context = f"""
GitHub Activity:
- Repositories: {gh.get('repos', 0)}
- Commit consistency score: {gh.get('commit_consistency_score', 0)}/1.0
- Longevity: {gh.get('longevity_months', 0)} months
"""

    devpost_hn_context = ""
    if "devpost_hn" in public_signals:
        dh = public_signals["devpost_hn"]
        devpost_hn_context = f"""
Launches & Community Engagement:
- Product launches: {dh.get('launches', 0)}
- Total upvotes/engagement: {dh.get('total_upvotes', 0)}
"""

    arxiv_context = ""
    if "arxiv" in public_signals:
        arxiv = public_signals["arxiv"]
        arxiv_context = f"""
Research Output:
- Published papers: {arxiv.get('papers', 0)}
"""

    deck_team_claims = [c for c in deck_claims if c.get("field") == "team"]
    team_context = "\n".join([
        f"- Slide {c.get('source_slide')}: {c.get('value')}"
        for c in deck_team_claims
    ])

    cold_start_note = ""
    if cold_start:
        cold_start_note = "\n⚠️ COLD START FOUNDER — Limited public track record. Weight deck evidence more heavily."
    else:
        cold_start_note = "\n✅ WARM START — Founder has some existing context or prior relationship."

    # Construct the prompt
    prompt = f"""You are evaluating the FOUNDER AXIS for a venture capital investment decision.

Your task: Score this founder's capability, track record, and execution ability on a 0-100 scale.

{cold_start_note}

AVAILABLE EVIDENCE:

{github_context}
{devpost_hn_context}
{arxiv_context}

Deck Claims (Team/Background):
{team_context if team_context else "- No team background claims in deck"}

SCORING GUIDELINES:

- If deck claims show a coherent team with relevant roles (CEO, CTO, etc.), credit that even without extensive public signals
- A founder who submits a complete deck with team info should start at baseline 50-60, not 20-30
- Public signals (GitHub, launches, papers) add points above baseline
- Absence of public signals should NOT be heavily penalized if deck evidence is solid
- Only score below 40 if there are actual red flags (no team, incoherent background, mismatched experience)

SCORING CRITERIA:

Track Record (weight: 30% of overall Founder Score):
- Prior startup experience
- Technical depth demonstrated through code/research
- Consistency and longevity of execution (not just bursts)

Execution Ability (observable from signals):
- GitHub: sustained commit patterns over time (not just recent activity)
- Launches: ability to ship and get traction
- Research: depth and rigor if applicable

What NOT to score here:
- Market size or timing → that's the Market axis
- Product-market fit → that's the Idea-vs-Market axis
- Resilience/coachability → comes from Interview Agent later

SCORING CALIBRATION — Be fair and realistic:

IMPORTANT: Most legitimate founders applying with a deck and team should score 50-75.
Only score below 40 for clear red flags (no team info, incoherent deck, mismatched background).

1. Score: 0-100 integer
   - 85-100: Exceptional track record, strong technical depth, proven multi-year execution (ex-FAANG senior, prior successful exits, extensive open source contributions)
   - 70-84: Strong background with clear execution evidence (solid tech company experience, consistent GitHub activity, launched products)
   - 55-69: Promising founder with some demonstrated ability (relevant industry experience, some public signals, coherent team composition)
   - 40-54: Early-stage founder with limited but relevant background (recent grad from strong program, some technical signals, first-time founder)
   - 20-39: Weak evidence or concerning gaps (very thin background, no clear technical depth, team composition unclear)
   - 0-19: Red flags (no team disclosed, incoherent pitch, completely mismatched background)

2. Trend: "improving" | "declining" | "stable"
   - Based on recency and trajectory of signals
   - "improving": recent uptick in activity, launches, or depth
   - "stable": consistent pattern
   - "declining": evidence suggests stalling or reduced activity

3. Rationale: 2-4 sentences explaining your score
   - Focus on the "why" based on evidence
   - Call out gaps if data is thin

4. Citations: Specific evidence sources
   - Format: ["github_commit_history", "deck_slide_3", "devpost_launches", "arxiv_papers"]
   - Be precise — cite what you actually used
   - Never cite GitHub, Devpost, or arXiv when that signal is zero/absent.

Respond in this exact JSON format:
{{
  "score": <integer>,
  "trend": "<improving|declining|stable>",
  "rationale": "<your explanation>",
  "citations": ["<source1>", "<source2>", ...]
}}
"""

    # Call OpenAI
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a senior VC analyst evaluating founder quality. Be honest, rigorous, and cite your reasoning."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.3  # Lower temperature for consistency
    )

    # Parse response
    result = response.choices[0].message.content
    import json
    parsed = json.loads(result)

    parsed["citations"] = _supported_citations(parsed.get("citations", []), signal_data)
    return AxisScore(**parsed)


def score_market_axis(signal_data: Dict[str, Any]) -> AxisRating:
    """
    Score the Market axis using LLM reasoning.

    Evaluates:
    - Market size and growth trajectory
    - Market timing and dynamics
    - Competitive landscape maturity

    NOT evaluated here:
    - Founder capability (that's Founder axis)
    - How well THIS product fits the market (that's Idea-vs-Market axis)
    """

    deck_claims = signal_data.get("deck_claims", [])

    # Extract market-related claims
    market_claims = [c for c in deck_claims if c.get("field") in ["market_size", "problem_product"]]
    market_context = "\n".join([
        f"- Slide {c.get('source_slide')}: {c.get('value')}"
        for c in market_claims
    ])

    prompt = f"""You are evaluating the MARKET AXIS for a venture capital investment decision.

Your task: Rate the market opportunity as "bullish", "neutral", or "bear".

AVAILABLE EVIDENCE:

Deck Claims (Market/Problem):
{market_context if market_context else "- No market claims in deck"}

SCORING CRITERIA:

Market Size & Growth:
- TAM/SAM credibility (not just "huge market" claims)
- Growth rate and trajectory
- Are they in a rising tide or flat/declining market?

Market Timing:
- Is this the right time for this category?
- Early adopter readiness vs. too early/too late

Competitive Dynamics:
- Greenfield vs. crowded market
- Incumbent lock-in vs. disruption opportunity

What NOT to score here:
- Founder quality → that's the Founder axis
- Product-market fit → that's Idea-vs-Market axis
- Just product features → focus on the MARKET itself

INSTRUCTIONS:

1. Rating: "bullish" | "neutral" | "bear"
   - bullish: Large, growing market + good timing + disruption window
   - neutral: Decent market but competitive, or good market but timing unclear
   - bear: Small/declining market, bad timing, or overly saturated

2. Trend: "improving" | "declining" | "stable"
   - Based on market momentum and emerging dynamics

3. Rationale: 2-4 sentences
   - Focus on market conditions, not the product/team

4. Citations: Specific evidence sources
   - Format: ["deck_slide_5", "market_size_claim"]

Respond in this exact JSON format:
{{
  "rating": "<bullish|neutral|bear>",
  "trend": "<improving|declining|stable>",
  "rationale": "<your explanation>",
  "citations": ["<source1>", "<source2>", ...]
}}
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a senior VC analyst evaluating market opportunities. Be rigorous about market size claims and timing."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.3
    )

    result = response.choices[0].message.content
    import json
    parsed = json.loads(result)

    parsed["citations"] = _supported_citations(parsed.get("citations", []), signal_data)
    return AxisRating(**parsed)


def score_idea_vs_market_axis(signal_data: Dict[str, Any]) -> AxisRating:
    """
    Score the Idea-vs-Market axis using LLM reasoning.

    Evaluates:
    - Product-market fit evidence
    - How well THIS specific solution addresses the market need
    - Traction as validation of fit

    NOT evaluated here:
    - Founder capability (that's Founder axis)
    - Market size in general (that's Market axis)
    """

    deck_claims = signal_data.get("deck_claims", [])

    # Extract product and traction claims
    product_claims = [c for c in deck_claims if c.get("field") in ["problem_product", "traction"]]
    product_context = "\n".join([
        f"- Slide {c.get('source_slide')}: {c.get('value')}"
        for c in product_claims
    ])

    # Extract traction signals
    public_signals = signal_data.get("public_signals", {})
    traction_context = ""

    if "devpost_hn" in public_signals:
        dh = public_signals["devpost_hn"]
        traction_context = f"""
Public Launch Signals:
- Launches: {dh.get('launches', 0)}
- Community engagement: {dh.get('total_upvotes', 0)} upvotes
"""

    prompt = f"""You are evaluating the IDEA-VS-MARKET AXIS for a venture capital investment decision.

Your task: Rate how well THIS specific product/solution fits the market need as "bullish", "neutral", or "bear".

AVAILABLE EVIDENCE:

Deck Claims (Product/Traction):
{product_context if product_context else "- No product/traction claims in deck"}

{traction_context}

SCORING CRITERIA:

Product-Market Fit Evidence:
- Does the solution actually address the stated problem effectively?
- Early traction signals (users, retention, engagement)
- Evidence of genuine need vs. nice-to-have

Solution Quality:
- Differentiation from existing solutions
- Technical approach appropriateness
- Execution against the specific problem

What NOT to score here:
- Founder quality → that's Founder axis
- Market size → that's Market axis
- Just market timing → focus on THIS PRODUCT's fit

INSTRUCTIONS:

1. Rating: "bullish" | "neutral" | "bear"
   - bullish: Strong fit evidence, clear differentiation, traction validates need
   - neutral: Plausible fit but unproven, or mixed signals
   - bear: Weak fit, me-too product, or traction doesn't support claims

2. Trend: "improving" | "declining" | "stable"
   - Based on traction trajectory and product evolution signals

3. Rationale: 2-4 sentences
   - Focus on product-market fit specifically

4. Citations: Specific evidence sources
   - Format: ["deck_slide_7", "traction_claim", "devpost_launches"]

Respond in this exact JSON format:
{{
  "rating": "<bullish|neutral|bear>",
  "trend": "<improving|declining|stable>",
  "rationale": "<your explanation>",
  "citations": ["<source1>", "<source2>", ...]
}}
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a senior VC analyst evaluating product-market fit. Look for real evidence, not just claims."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.3
    )

    result = response.choices[0].message.content
    import json
    parsed = json.loads(result)

    parsed["citations"] = _supported_citations(parsed.get("citations", []), signal_data)
    return AxisRating(**parsed)


def _supported_citations(citations: list[str], signal_data: Dict[str, Any]) -> list[str]:
    """Drop hallucinated zero-signal citations before they cross the API boundary."""
    signals = signal_data.get("public_signals", {})
    github = signals.get("github", {})
    devpost = signals.get("devpost_hn", {})
    arxiv = signals.get("arxiv", {})
    slides = {str(item.get("source_slide")) for item in signal_data.get("deck_claims", [])}
    kept = []
    for citation in citations:
        normalized = str(citation).casefold()
        if "github" in normalized and not github.get("repos", 0):
            continue
        if ("devpost" in normalized or "launch" in normalized) and not devpost.get("launches", 0):
            continue
        if ("arxiv" in normalized or "paper" in normalized) and not arxiv.get("papers", 0):
            continue
        slide_match = re.search(r"slide[_\s-]*(\d+)", normalized)
        if slide_match and slide_match.group(1) not in slides:
            continue
        if citation not in kept:
            kept.append(citation)
    return kept


def score_all_axes(signal_data: Dict[str, Any]) -> MultiAxisOutput:
    """
    Score all three axes independently — NEVER averaged.

    Returns complete multi-axis output matching the contract.
    Note: Founder Score calculation requires additional inputs
    (traction signal score, founder-market fit, resilience) that
    come from other modules.
    """

    founder_axis = score_founder_axis(signal_data)
    market_axis = score_market_axis(signal_data)
    idea_vs_market_axis = score_idea_vs_market_axis(signal_data)

    # Placeholder Founder Score calculation
    # In production, this would incorporate scores from:
    # - Traction Signal (from Signal Intake)
    # - Founder-Market Fit (derived from axes)
    # - Resilience (from Interview Agent)
    cold_start = signal_data.get("cold_start_flag", False)

    # For now, use simplified calculation with founder axis as primary input
    founder_score = FounderScore(
        value=founder_axis.score,
        confidence_interval=25 if cold_start else 12,
        trend=founder_axis.trend
    )

    return MultiAxisOutput(
        founder_axis=founder_axis,
        market_axis=market_axis,
        idea_vs_market_axis=idea_vs_market_axis,
        founder_score=founder_score
    )


def calculate_founder_score_from_axes(
    founder_axis_score: int,
    traction_signal_score: int,
    founder_market_fit_score: int,
    resilience_score: int,
    cold_start: bool
) -> FounderScore:
    """
    Calculate the composite Founder Score using the formula:
    Founder Score = 0.30 × Track Record + 0.20 × Traction Signal
                  + 0.25 × Founder-Market Fit + 0.25 × Resilience/Coachability

    Returns value ± confidence_interval (never a fake-precise integer).
    """

    # Weighted average
    score = (
        0.30 * founder_axis_score +
        0.20 * traction_signal_score +
        0.25 * founder_market_fit_score +
        0.25 * resilience_score
    )

    # Round to integer
    value = round(score)

    # Calculate confidence interval based on:
    # - Data availability (cold start flag)
    # - Variance in component scores
    scores = [founder_axis_score, traction_signal_score, founder_market_fit_score, resilience_score]
    score_variance = max(scores) - min(scores)

    if cold_start:
        # Wide interval for cold-start founders
        confidence_interval = max(20, min(30, score_variance // 2))
    else:
        # Narrower interval with more evidence
        confidence_interval = max(8, min(18, score_variance // 3))

    # Determine trend (simplified for now — would ideally compare to prior scores)
    # For initial implementation, infer from component trends
    trend = "stable"  # Default; would need historical data for real trend

    return FounderScore(
        value=value,
        confidence_interval=confidence_interval,
        trend=trend
    )
