"""Internal typed models that preserve the locked JSON field names."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Severity = Literal["low", "medium", "high"]
Confidence = Literal["high", "medium", "low"]
ResponsePattern = Literal[
    "engaged_updated", "engaged_no_update", "defensive", "evasive"
]


@dataclass(frozen=True)
class DeckClaim:
    field: str
    value: str
    source_slide: int | None = None


@dataclass(frozen=True)
class Evidence:
    title: str
    url: str
    content: str
    score: float = 0.0

    @property
    def citation(self) -> str:
        return f"{self.title} ({self.url})"


@dataclass(frozen=True)
class FlaggedClaim:
    claim: str
    issue: str
    severity: Severity


@dataclass(frozen=True)
class ClaimTrust:
    claim: str
    confidence: Confidence
    evidence: str


@dataclass
class ValidationResult:
    flagged_claims: list[FlaggedClaim] = field(default_factory=list)
    tavily_sources_checked: list[str] = field(default_factory=list)
    memory_update: bool = False
    claim_trust: list[ClaimTrust] = field(default_factory=list)

    def diligence_output(self) -> dict[str, Any]:
        return {
            "flagged_claims": [asdict(item) for item in self.flagged_claims],
            "tavily_sources_checked": self.tavily_sources_checked,
            "memory_update": self.memory_update,
        }

    def trust_output(self) -> dict[str, Any]:
        return {"claim_trust": [asdict(item) for item in self.claim_trust]}


def normalize_claims(raw_claims: list[dict[str, Any] | DeckClaim]) -> list[DeckClaim]:
    claims: list[DeckClaim] = []
    for raw in raw_claims:
        if isinstance(raw, DeckClaim):
            claims.append(raw)
            continue
        field_name = str(raw.get("field", "")).strip()
        value = str(raw.get("value", "")).strip()
        if not field_name or not value:
            continue
        slide = raw.get("source_slide")
        claims.append(
            DeckClaim(
                field=field_name,
                value=value,
                source_slide=slide if isinstance(slide, int) else None,
            )
        )
    return claims
