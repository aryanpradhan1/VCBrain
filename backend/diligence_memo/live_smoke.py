"""Low-cost live smoke test for C's complete diligence-to-memo pipeline."""

from __future__ import annotations

import json
from typing import Any

from .clients import OpenAIReasoningClient, TavilySearchClient
from .memo import MemoSynthesizer
from .pipeline import DiligenceMemoPipeline
from .validator import ClaimValidator


class ReasoningProbe:
    def __init__(self) -> None:
        self.client = OpenAIReasoningClient()
        self.succeeded = False

    def json_completion(self, system: str, user: str) -> dict[str, Any]:
        result = self.client.json_completion(system, user)
        self.succeeded = True
        return result


def main() -> None:
    reasoning = ReasoningProbe()
    pipeline = DiligenceMemoPipeline(
        ClaimValidator(TavilySearchClient(), reasoning),
        MemoSynthesizer({"artificial intelligence"}),
    )
    output = pipeline.run(
        {
            "company_name": "OpenAI",
            "sector": "Artificial intelligence",
            "deck_claims": [
                {
                    "field": "problem_product",
                    "value": "Develops artificial intelligence systems and products",
                    "source_slide": 2,
                }
            ],
        }
    )
    expected = {
        "diligence",
        "trust",
        "memo",
        "adversarial_view",
        "portfolio_check",
        "verdict",
        "amount_recommended",
    }
    if set(output) != expected:
        raise RuntimeError("Pipeline output does not match C's public handoff shape")
    sources = output["diligence"]["tavily_sources_checked"]
    if not sources:
        raise RuntimeError("Tavily returned no usable evidence")
    if not reasoning.succeeded:
        raise RuntimeError("OpenAI reasoning did not complete")
    print(
        json.dumps(
            {
                "status": "ok",
                "tavily_sources_checked": len(sources),
                "openai_reasoning": "ok",
                "claim_trust_count": len(output["trust"]["claim_trust"]),
                "memo_required_sections": sorted(output["memo"]["required"]),
                "adversarial_challenges": len(output["adversarial_view"]["challenges"]),
                "portfolio_check_present": bool(output["portfolio_check"]),
                "verdict": output["verdict"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
