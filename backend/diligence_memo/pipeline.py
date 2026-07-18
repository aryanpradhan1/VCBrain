"""Public orchestration boundary consumed by Person B's API glue."""

from __future__ import annotations

from typing import Any

from .memo import MemoSynthesizer
from .validator import ClaimValidator


class DiligenceMemoPipeline:
    def __init__(self, validator: ClaimValidator, memo: MemoSynthesizer | None = None) -> None:
        self.validator = validator
        self.memo = memo or MemoSynthesizer()

    def run(self, opportunity: dict[str, Any]) -> dict[str, Any]:
        company_name = str(opportunity.get("company_name") or "Unnamed company")
        claims = list(opportunity.get("deck_claims") or [])
        validation = self.validator.validate(company_name, claims)
        memo_output = self.memo.synthesize(opportunity, claims, validation)
        return {
            "diligence": validation.diligence_output(),
            "trust": validation.trust_output(),
            "memo": {
                "required": memo_output["required"],
                "optional_or_flagged": memo_output["optional_or_flagged"],
            },
            "adversarial_view": memo_output["adversarial_view"],
            "portfolio_check": memo_output["portfolio_check"],
            "verdict": memo_output["verdict"],
            "amount_recommended": memo_output["amount_recommended"],
        }
