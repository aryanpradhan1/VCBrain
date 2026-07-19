"""External claim verification and per-claim Trust Score generation."""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from collections.abc import Iterable
from urllib.parse import urlparse

from .clients import ExternalServiceError, ReasoningClient, SearchClient
from .models import ClaimTrust, DeckClaim, Evidence, FlaggedClaim, ValidationResult, normalize_claims

_NEGATION_TERMS = ("false", "incorrect", "no evidence", "disputed", "contradict")
_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "for",
        "in",
        "is",
        "of",
        "on",
        "the",
        "to",
        "with",
    }
)


class ClaimValidator:
    """Validate each claim independently and retain source-level provenance."""

    def __init__(
        self,
        search_client: SearchClient,
        reasoning_client: ReasoningClient | None = None,
        max_results_per_claim: int = 3,
        max_parallel_claims: int = 3,
    ) -> None:
        self.search_client = search_client
        self.reasoning_client = reasoning_client
        self.max_results_per_claim = max_results_per_claim
        # Keep provider pressure bounded: a large deck should finish promptly without
        # turning into an unbounded burst of Tavily/OpenAI requests.
        self.max_parallel_claims = max(1, min(max_parallel_claims, 5))

    def validate(
        self,
        company_name: str,
        raw_claims: list[dict[str, object] | DeckClaim],
    ) -> ValidationResult:
        claims = normalize_claims(raw_claims)
        result = ValidationResult()
        if not claims:
            return result

        # Results are consumed in original claim order, so trust rows and source order
        # remain deterministic even though external requests are concurrent.
        with ThreadPoolExecutor(max_workers=min(self.max_parallel_claims, len(claims))) as executor:
            checked = list(executor.map(lambda claim: self._validate_claim(company_name, claim), claims))
        for evidence, flagged, trust in checked:
            for url in cited_urls(evidence):
                if url not in result.tavily_sources_checked:
                    result.tavily_sources_checked.append(url)
            if flagged is not None:
                result.flagged_claims.append(flagged)
            result.claim_trust.append(trust)
        result.memory_update = bool(result.flagged_claims)
        return result

    def _validate_claim(
        self, company_name: str, claim: DeckClaim
    ) -> tuple[list[Evidence], FlaggedClaim | None, ClaimTrust]:
        evidence = self._search(company_name, claim)
        flagged, trust = self._assess(company_name, claim, evidence)
        return evidence, flagged, trust

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
        return self._conservative_assess(company_name, claim, evidence)

    def _llm_assess(
        self, company_name: str, claim: DeckClaim, evidence: list[Evidence]
    ) -> tuple[FlaggedClaim | None, ClaimTrust]:
        payload = self.reasoning_client.json_completion(
            system=(
                "You are a skeptical venture diligence analyst. Evaluate only the supplied "
                "claim and evidence, about this specific company and this specific claim -- "
                "not evidence that merely shares keywords with an unrelated person, company, "
                "or product. 'Sources exist' is not the same as 'sources confirm': confidence "
                "must reflect whether the evidence actually corroborates THIS claim about THIS "
                "company, not how many sources were returned by the search.\n"
                "- confidence=high only if at least one source explicitly names this company "
                "(or this claim's specific person/number/fact) and confirms the claim.\n"
                "- confidence=medium if sources are plausibly on-topic (right industry, "
                "similar claim) but don't explicitly confirm this company's specific claim.\n"
                "- confidence=low if the sources are about a different company or person, "
                "don't mention this claim's specifics, or no usable evidence exists -- even "
                "if several sources were returned, confidence must be low unless one of them "
                "actually verifies this exact claim.\n"
                "Never infer facts absent from the evidence. Return JSON with "
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
        confidence = payload["confidence"]
        severity = payload.get("severity", "medium")
        if confidence not in {"high", "medium", "low"}:
            raise ValueError("invalid confidence")
        if severity not in {"low", "medium", "high"}:
            raise ValueError("invalid severity")
        contradiction = payload.get("contradiction")
        if not isinstance(contradiction, bool):
            raise TypeError("contradiction must be a boolean")
        citations = "; ".join(item.citation for item in evidence)
        summary = str(payload.get("evidence_summary") or "Evidence is inconclusive")
        trust = ClaimTrust(claim.field, confidence, f"{summary} Sources: {citations}")
        flagged = None
        if contradiction:
            flagged = FlaggedClaim(
                claim.field,
                str(payload.get("issue") or "External evidence conflicts with the claim"),
                severity,
            )
        return flagged, trust

    @staticmethod
    def _conservative_assess(
        company_name: str, claim: DeckClaim, evidence: list[Evidence]
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
        # Claim-field keyword overlap alone (e.g. "google", "engineer") matches evidence
        # about a completely different, unrelated company or person just as easily as it
        # matches real corroboration -- also requiring the company's own name to appear
        # closes that false-positive (found live: a claim about "CEO worked at Google" was
        # rated high-confidence off a real but unrelated person's LinkedIn profile that
        # also said "ex-Google software engineer").
        relevant_evidence = [
            item
            for item in evidence
            if _evidence_supports_claim(claim, item) and _evidence_mentions_company(company_name, item)
        ]
        independent_hosts = {
            urlparse(item.url).hostname.casefold()
            for item in relevant_evidence
            if urlparse(item.url).hostname
        }
        confidence = "high" if len(independent_hosts) >= 2 and not contradiction else "medium"
        if not relevant_evidence and not contradiction:
            return None, ClaimTrust(
                claim.field,
                "low",
                f"Sources were located but did not specifically support the claim. Sources: {citations}",
            )
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


def _evidence_supports_claim(claim: DeckClaim, evidence: Evidence) -> bool:
    """Require claim-specific lexical support before raising conservative trust."""
    claim_tokens = {
        token
        for token in re.findall(r"[a-z0-9]+", f"{claim.field} {claim.value}".casefold())
        if len(token) >= 3 and token not in _STOP_WORDS
    }
    evidence_tokens = set(
        re.findall(
            r"[a-z0-9]+",
            f"{evidence.title} {evidence.content}".casefold(),
        )
    )
    return bool(claim_tokens & evidence_tokens)


def _evidence_mentions_company(company_name: str, evidence: Evidence) -> bool:
    """Require the company's own name to actually appear in the evidence before treating
    it as relevant corroboration. Claim-field keyword overlap alone (e.g. "google",
    "engineer") is satisfied just as easily by a source about a different, unrelated
    company or person -- this closes that gap without needing an LLM call, for the
    no-reasoning-client fallback path."""
    name_tokens = {
        token for token in re.findall(r"[a-z0-9]+", company_name.casefold()) if len(token) >= 3 and token not in _STOP_WORDS
    }
    if not name_tokens:
        return True  # nothing distinctive to check against; don't over-reject on a blank/generic name
    evidence_text = f"{evidence.title} {evidence.content}".casefold()
    return any(token in evidence_text for token in name_tokens)
