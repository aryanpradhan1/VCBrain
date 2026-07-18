"""Pydantic models mirroring the contract's data shapes (see /shared/contract.md).

Field names here must match the contract exactly — extra="forbid" so a typo'd or
invented field raises at validation time instead of silently shipping.
"""
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

DeckClaimField = Literal["market_size", "traction", "team", "ask", "problem_product"]


class DeckClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: DeckClaimField
    value: str
    source_slide: int


class GithubSignals(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repos: int = 0
    commit_consistency_score: float = 0.0
    longevity_months: int = 0


class DevpostHnSignals(BaseModel):
    model_config = ConfigDict(extra="forbid")

    launches: int = 0
    total_upvotes: int = 0


class ArxivSignals(BaseModel):
    model_config = ConfigDict(extra="forbid")

    papers: int = 0


class PublicSignals(BaseModel):
    model_config = ConfigDict(extra="forbid")

    github: GithubSignals = Field(default_factory=GithubSignals)
    devpost_hn: DevpostHnSignals = Field(default_factory=DevpostHnSignals)
    arxiv: ArxivSignals = Field(default_factory=ArxivSignals)


class SignalIntakeOutput(BaseModel):
    """Matches the "Signal Intake output" block in /shared/contract.md exactly."""

    model_config = ConfigDict(extra="forbid")

    founder_id: str
    company_id: str
    deck_claims: list[DeckClaim]
    public_signals: PublicSignals = Field(default_factory=PublicSignals)
    sourcing_channel: Literal["inbound", "outbound"]
    cold_start_flag: bool
