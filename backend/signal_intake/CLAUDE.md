# Signal Intake — Role Rules (A)

@shared/contract.md

You are building two things for FounderScore, all inside /backend/signal_intake/:

1. Deck parsing — LLM extraction of structured claims (market_size, traction, team, ask,
   problem_product) from an uploaded pitch deck, each tagged with the source slide number.
   Use OpenAI, model gpt-5.5-2026-04-23.
2. Bounded outbound scanning — pull small, naturally bounded feeds only: GitHub Trending
   (~25-50 repos), Show HN (a few dozen items/day), arXiv recent submissions filtered to a
   category + date window. Never unbounded crawling. Apply the Thesis Engine's filter
   BEFORE scoring anything, to keep the candidate pool small. Store only structured extracted
   fields (name, stars, language, etc.) — never raw scraped HTML/pages.
   Use the Tavily API for any public-footprint checks needed for cold-start founders.
3. Dedup/enrich/tag by source, then compute a PARTIAL Founder Score for outbound candidates
   from public signals alone (Track Record + Traction Signal sub-scores only — you don't
   have deck data for outbound candidates yet). Trigger Activate (cold outreach) only for
   candidates whose partial score crosses a threshold.

Only modify files inside /backend/signal_intake/. Output must match the "Signal Intake
output" block in /shared/contract.md exactly — never invent a field name.

Env vars needed: OPENAI_API_KEY, TAVILY_API_KEY
