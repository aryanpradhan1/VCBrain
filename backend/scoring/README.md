# Multi-Axis Scorer — Implementation Summary

**Status:** ✅ Founder, Market, and Idea-vs-Market axes fully implemented

## What's Built

### 1. Founder Axis (`score_founder_axis()`)
- **Output:** Numeric score 0-100 + trend + rationale + citations
- **Evaluates:**
  - Track record (prior experience, technical depth)
  - Execution ability (GitHub consistency, launches, research)
  - Cold-start flag handling (scores conservatively, notes data gaps)
- **NOT evaluated:** Market timing, product-market fit, resilience (those belong to other axes/agents)

### 2. Market Axis (`score_market_axis()`)
- **Output:** Rating (bullish/neutral/bear) + trend + rationale + citations
- **Evaluates:**
  - Market size and growth trajectory
  - Market timing and dynamics
  - Competitive landscape maturity
- **NOT evaluated:** Founder quality, product-market fit

### 3. Idea-vs-Market Axis (`score_idea_vs_market_axis()`)
- **Output:** Rating (bullish/neutral/bear) + trend + rationale + citations
- **Evaluates:**
  - Product-market fit evidence
  - How well THIS solution addresses the market need
  - Traction as validation of fit
- **NOT evaluated:** Founder capability, general market size

### 4. Composite Function (`score_all_axes()`)
- Scores all three axes independently
- **NEVER averages axes together** (contract requirement)
- Returns `MultiAxisOutput` with all three axes preserved separately
- Includes placeholder Founder Score calculation

### 5. Founder Score Calculator (`calculate_founder_score_from_axes()`)
- Implements the locked formula:
  ```
  Founder Score = 0.30 × Track Record + 0.20 × Traction Signal
                + 0.25 × Founder-Market Fit + 0.25 × Resilience
  ```
- Returns `value ± confidence_interval` (not fake-precise integers)
- Confidence interval widens for cold-start founders
- Will integrate with Signal Intake (traction) and Interview Agent (resilience) later

## Key Design Decisions

1. **Independence:** Each axis has its own LLM prompt, clearly scoped to avoid overlap
2. **Citations:** Every axis cites specific evidence (deck slides, GitHub signals, etc.)
3. **No Averaging:** The three axes are NEVER combined — they stay separate through the entire pipeline
4. **Cold-Start Handling:** Founder axis explicitly notes thin data, scores conservatively
5. **Contract Compliance:** Output shapes match `/shared/contract.md` exactly

## Files Created

```
backend/scoring/
├── __init__.py                  # Exports all functions and types
├── multi_axis_scorer.py         # Core implementation (469 lines)
├── requirements.txt             # openai, pydantic
├── test_founder_axis.py         # Unit test for Founder axis
├── test_all_axes.py             # Comprehensive test for all three axes
└── README.md                    # This file
```

## Test Fixtures Created

```
shared/fixtures/
├── signal_intake_strong.json        # Strong founder (8yr exp, acquisitions, high consistency)
└── signal_intake_cold_start.json    # Cold-start founder (bootcamp, 6mo history)
```

## How to Test

```bash
cd backend/scoring

# Set API key
export OPENAI_API_KEY='your-key-here'

# Test individual axis
python3 test_founder_axis.py

# Test all three axes together
python3 test_all_axes.py
```

## Usage Example

```python
from backend.scoring import score_all_axes
import json

# Load signal data (from Signal Intake agent)
with open("shared/fixtures/signal_intake_strong.json") as f:
    signal_data = json.load(f)

# Score all axes
result = score_all_axes(signal_data)

print(f"Founder: {result.founder_axis.score}/100 ({result.founder_axis.trend})")
print(f"Market: {result.market_axis.rating} ({result.market_axis.trend})")
print(f"Idea-vs-Market: {result.idea_vs_market_axis.rating} ({result.idea_vs_market_axis.trend})")
print(f"Founder Score: {result.founder_score.value} ± {result.founder_score.confidence_interval}")
```

## Integration Points

**Consumes:**
- Signal Intake output (deck claims, public signals, cold-start flag)

**Produces:**
- `MultiAxisOutput` matching the contract exactly
- Ready for API glue to assemble into `/opportunities/:id` endpoint

**Still Needed for Full Founder Score:**
- Traction Signal score (from Signal Intake)
- Resilience/Coachability score (from Interview Agent)

## Model Used

- OpenAI GPT-4o (`gpt-4o-2024-11-20`)
- Temperature: 0.3 (for consistency)
- JSON response format enforced
- System prompts tuned for VC analyst rigor

## Additional Components Built

### Thesis Engine (`thesis_engine.py`)
Two-stage investment thesis matching:
1. **Deterministic gate** — sector/stage/geography/check-size (fast rule-based filtering)
2. **LLM judgment** — only for ambiguous/adjacent cases

Output: `{thesis_match, match_type, rationale}`

Matches opportunities against configurable thesis (sectors, geographies, stage, check size).

### Multi-Attribute Query Parser (`query_parser.py`)
Natural language → structured database filters in one LLM call.

**Example queries:**
- "technical founder, Berlin, AI infra, no prior VC backing"
- "revenue > $10K, strong GitHub, seed stage"
- "climate tech, cold start, first-time founder"

Outputs `StructuredQuery` with extracted filters for all dimensions (founder, market, traction, etc.).

## Next Steps

1. ✅ Multi-Axis Scorer — COMPLETE
2. ✅ Thesis Engine — COMPLETE
3. ✅ Multi-Attribute Query Parser — COMPLETE
4. ✅ FastAPI glue endpoints — COMPLETE (see `/backend/api/`)
5. Integration test with Signal Intake output when Role A's module is ready
