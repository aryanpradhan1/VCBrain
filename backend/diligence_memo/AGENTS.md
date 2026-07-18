# Diligence and Memo - Role Rules

You are building Person C's Diligence/Validator, per-claim Trust Score, Memo Synthesizer, Adversarial View, Portfolio Check, and Interview Agent for FounderScore.

- Only modify files inside `/backend/diligence_memo/`. Never modify another person's folder.
- Read and follow `/shared/contract.md`; do not rename locked fields or alter output shapes.
- Call other modules only through the documented contract.
- Use `/shared/fixtures/` as read-only test and mock input when fixtures are available.
- Trust is scored per claim with evidence, never as a company-wide number.
- Missing memo information must be explicitly flagged and never fabricated.
- Keep `adversarial_view` separate from memo prose.
- Score interviews by response pattern, not by content correctness.
