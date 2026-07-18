"""External claim verification and per-claim Trust Score generation."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable

from .clients import ExternalServiceError, ReasoningClient, SearchClient
from .models import ClaimTrust, DeckClaim, Evidence, FlaggedClaim, ValidationResult, normalize_claims

_NEGATION_TERMS = ("false", "incorrect", "no evidence", "disputed", "contradict")


class ClaimValidator:
    """Validate each claim independently and retain source-level provenance."""

    def __init__(
        self,
        search_client: SearchClient,
        reasoning_client: ReasoningClient | None = None,
        max_results_per_claim: int = 3,
    ) -> None:
        self.search_client = search_client
        self.reasoning_client = reasoning_client
        self.max_results_per_claim = max_results_per_claim

    def validate(
        self,
        company_name: str,
        raw_claims: list[dict[str, object] | DeckClaim],
    ) -> ValidationResult:
        claims = normalize_claims(raw_claims)
        result = ValidationResult()
        for claim in claims:
            evidence = self._search(company_name, claim)
            result.tavily_sources_checked.extend(
                source.url for source in evidence if source.url not in result.tavily_sources_checked
            )
            flagged, trust = self._assess(company_name, claim, evidence)
            if flagged is not None:
                result.flagged_claims.append(flagged)
            result.claim_trust.append(trust)
        result.memory_update = bool(result.flagged_claims)
        return result

    def _search(self, company_name: str, claim: DeckClaim) -> list[Evidence]:
        query = f'"{company_name}" {claim.field} {claim.value}'
        try:
            return self.search_client.search(query, self.max_results_per_claim)
        except ExternalServiceError:
            return []

    def _assess(
        self, company_name: str, claim: DeckClaim, evidence: list[Evidence]
    ) -> tuple[FlaggedClaim | None, ClaimTrust]:
        if self.reasoning_client and evidence:
            try:
                return self._llm_assess(company_name, claim, evidence)
            except (ExternalServiceError, KeyError, TypeError, ValueError, json.JSONDecodeError):
                pass
        return self._conservative_assess(claim, evidence)

    def _llm_assess(
        self, company_name: str, claim: DeckClaim, evidence: list[Evidence]
    ) -> tuple[FlaggedClaim | None, ClaimTrust]:
        payload = self.reasoning_client.json_completion(
            system=(
                "You are a skeptical venture diligence analyst. Evaluate only the supplied "
                "claim and evidence. Never infer facts absent from the evidence. Return JSON with "
                "confidence (high|medium|low), evidence_summary, contradiction (boolean), "
                "issue, and severity (low|medium|high)."
            ),
            user=json.dumps(
                {
                    "company_name": company_name,
                    "claim": {"field": claim.field, "value": claim.value},
                    "sources": [
                        {"title": item.title, "url": item.url, "content": item.content}
                        for item in evidence
                    ],
                }
            ),
        )
        confidence = str(payload["confidence"])
        severity = str(payload.get("severity", "medium"))
        if confidence not in {"high", "medium", "low"}:
            raise ValueError("invalid confidence")
        if severity not in {"low", "medium", "high"}:
            raise ValueError("invalid severity")
        citations = "; ".join(item.citation for item in evidence)
        summary = str(payload.get("evidence_summary") or "Evidence is inconclusive")
        trust = ClaimTrust(claim.field, confidence, f"{summary} Sources: {citations}")
        flagged = None
        if bool(payload.get("contradiction")):
            flagged = FlaggedClaim(
                claim.field,
                str(payload.get("issue") or "External evidence conflicts with the claim"),
                severity,
            )
        return flagged, trust

    @staticmethod
    def _conservative_assess(
        claim: DeckClaim, evidence: list[Evidence]
    ) -> tuple[FlaggedClaim | None, ClaimTrust]:
        if not evidence:
            return None, ClaimTrust(
                claim.field,
                "low",
                "No independent public evidence was available; the deck claim remains unverified.",
            )

        combined = " ".join(item.content.lower() for item in evidence)
        contradiction = any(term in combined for term in _NEGATION_TERMS)
        citations = "; ".join(item.citation for item in evidence)
        confidence = "high" if len(evidence) >= 2 and not contradiction else "medium"
        trust = ClaimTrust(
            claim.field,
            confidence,
            f"Independent public evidence was located. Sources: {citations}",
        )
        if contradiction:
            return (
                FlaggedClaim(
                    claim.field,
                    "At least one external source contains language that conflicts with the claim.",
                    "high",
                ),
                ClaimTrust(
                    claim.field,
                    "low",
                    f"Potential contradiction requires human review. Sources: {citations}",
                ),
            )
        return None, trust


def cited_urls(items: Iterable[Evidence]) -> list[str]:
    """Return stable, deduplicated URLs for memory provenance."""
    return list(dict.fromkeys(item.url for item in items if re.match(r"https?://", item.url)))
