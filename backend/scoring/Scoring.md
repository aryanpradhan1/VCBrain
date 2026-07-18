# Scoring & Thesis — Role Rules (B)

@shared/contract.md

You are building three things for FounderScore, all inside /backend/scoring/:

1. Multi-Axis Scorer — Founder / Market / Idea-vs-Market, LLM reasoning (OpenAI, model
   gpt-5.5-2026-04-23), NEVER averaged. Each axis independently scored with a rating/score,
   a trend (improving/declining/stable), a rationale, and citations pointing to the exact
   deck slide or signal that drove the conclusion. This is NOT a trained classifier — do not
   suggest training a model on any dataset. The reasoning itself is the product.
2. Thesis Engine — a deterministic gate first (sector/stage/geography/check-size match,
   plain if/else, no LLM), then an LLM judgment call only for ambiguous/adjacent matches.
3. Multi-Attribute Reasoning query parser — one LLM call resolving a compound natural-
   language query (e.g. "technical founder, Berlin, AI infra, no prior VC backing") against
   structured fields in one pass, not five manual filters.

Only modify files inside /backend/scoring/. Output must match the "Multi-Axis Scorer output"
block in /shared/contract.md exactly — never invent a field name.

Build against /shared/fixtures/ until A's real Signal Intake output exists — mock it in the
same shape as the "Signal Intake output" contract block.

Env var needed: OPENAI_API_KEY