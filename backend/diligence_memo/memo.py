"""Appendix-1 memo, adversarial view, and portfolio overlap synthesis."""

from __future__ import annotations

from typing import Any

from .models import ValidationResult, normalize_claims

DEFAULT_PORTFOLIO_SECTORS = frozenset({"fintech", "healthtech", "developer tools"})


class MemoSynthesizer:
    def __init__(self, portfolio_sectors: set[str] | frozenset[str] | None = None) -> None:
        self.portfolio_sectors = {
            item.casefold() for item in (portfolio_sectors or DEFAULT_PORTFOLIO_SECTORS)
        }

    def synthesize(
        self,
        company: dict[str, Any],
        raw_claims: list[dict[str, Any]],
        validation: ValidationResult,
    ) -> dict[str, Any]:
        claims = normalize_claims(raw_claims)
        by_field = {claim.field: claim.value for claim in claims}
        company_name = str(company.get("company_name") or "Unnamed company")
        sector = str(company.get("sector") or "Not disclosed")
        snapshot = f"{company_name} operates in {sector}."
        problem_product = by_field.get("problem_product", "Not disclosed")
        traction = by_field.get("traction", "Not disclosed")
        hypotheses = self._hypotheses(company_name, by_field, validation)
        swot = self._swot(by_field, validation)
        optional = {
            "team_and_history": by_field.get("team", "Not disclosed"),
            "cap_table": str(company.get("cap_table") or "Not disclosed"),
        }
        adversarial = self._adversarial_view(by_field, validation)
        portfolio = self._portfolio_check(sector)
        verdict = self._verdict(validation, traction)
        return {
            "required": {
                "company_snapshot": snapshot,
                "investment_hypotheses": hypotheses,
                "swot": swot,
                "problem_and_product": problem_product,
                "traction_kpis": traction,
            },
            "optional_or_flagged": optional,
            "adversarial_view": adversarial,
            "portfolio_check": portfolio,
            "verdict": verdict,
            "amount_recommended": 100000,
        }

    @staticmethod
    def _hypotheses(
        company_name: str, claims: dict[str, str], validation: ValidationResult
    ) -> list[str]:
        hypotheses = []
        if claims.get("problem_product"):
            hypotheses.append(
                f"{company_name}'s product may address the stated customer problem if adoption is validated."
            )
        if claims.get("traction"):
            hypotheses.append("Reported traction may indicate early demand, subject to verification.")
        if not hypotheses:
            hypotheses.append("Insufficient evidence to form a strong investment hypothesis.")
        if validation.flagged_claims:
            hypotheses.append("Resolution of flagged claim contradictions is a condition of conviction.")
        return hypotheses

    @staticmethod
    def _swot(claims: dict[str, str], validation: ValidationResult) -> dict[str, list[str]]:
        strengths = ["Founder-provided traction signal"] if claims.get("traction") else []
        weaknesses = [f"Unresolved {item.claim} issue" for item in validation.flagged_claims]
        if not claims.get("team"):
            weaknesses.append("Team history not disclosed")
        return {
            "strengths": strengths or ["No independently verified strength yet"],
            "weaknesses": weaknesses or ["Evidence remains limited"],
            "opportunities": [claims.get("market_size", "Market opportunity not disclosed")],
            "threats": ["Execution and market-adoption risk"],
        }

    @staticmethod
    def _adversarial_view(
        claims: dict[str, str], validation: ValidationResult
    ) -> dict[str, list[str]]:
        if validation.flagged_claims:
            challenges = [
                f"The {item.claim} claim may not withstand diligence: {item.issue}"
                for item in validation.flagged_claims
            ]
        else:
            strongest = "traction" if claims.get("traction") else "market_size"
            value = claims.get(strongest, "the central investment claim")
            challenges = [
                f"Skeptic's view: {value} is founder-reported and may not predict durable demand."
            ]
        return {"challenges": challenges}

    def _portfolio_check(self, sector: str) -> dict[str, Any]:
        normalized = sector.casefold()
        matches = sorted(item for item in self.portfolio_sectors if item in normalized)
        overlap = bool(matches)
        note = (
            f"Potential sector overlap with current portfolio: {', '.join(matches)}."
            if overlap
            else "No direct sector overlap found in the configured portfolio list."
        )
        return {"overlap": overlap, "note": note}

    @staticmethod
    def _verdict(validation: ValidationResult, traction: str) -> str:
        if any(item.severity == "high" for item in validation.flagged_claims):
            return "decline"
        low_trust = sum(item.confidence == "low" for item in validation.claim_trust)
        if validation.flagged_claims or low_trust or traction == "Not disclosed":
            return "review"
        return "approve"
