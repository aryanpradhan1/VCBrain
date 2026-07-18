"""Claim-specific adaptive interview flow and response-pattern scoring."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .models import DeckClaim, ResponsePattern, normalize_claims

_UPDATE_MARKERS = ("updated", "revised", "changed", "new data", "you are right")
_DEFENSIVE_MARKERS = ("obviously", "you don't understand", "ridiculous", "no need")
_EVIDENCE_MARKERS = ("because", "data", "customer", "metric", "source", "evidence")


@dataclass
class InterviewSession:
    claims: list[DeckClaim]
    max_questions: int = 5
    questions_asked: list[str] = field(default_factory=list)
    responses: list[str] = field(default_factory=list)

    def next_question(self) -> str | None:
        if len(self.questions_asked) >= self.max_questions:
            return None
        index = len(self.questions_asked)
        claim = self.claims[index % len(self.claims)] if self.claims else None
        response = self.responses[-1] if self.responses else ""
        if response and len(response.split()) < 8:
            question = "What specific evidence would let an investor independently verify that answer?"
        elif response and not any(marker in response.casefold() for marker in _EVIDENCE_MARKERS):
            question = "Which measurable result most strongly supports your last answer, and over what period?"
        elif claim:
            question = self._challenge(claim)
        else:
            question = "What is the strongest falsifiable claim behind this company, and what evidence supports it?"
        self.questions_asked.append(question)
        return question

    def record_response(self, response: str) -> None:
        if not self.questions_asked:
            raise ValueError("Ask a question before recording a response")
        if len(self.responses) >= len(self.questions_asked):
            raise ValueError("The current question already has a response")
        self.responses.append(response.strip())

    def result(self) -> dict[str, Any]:
        pattern = classify_response_pattern(self.responses)
        scores = {
            "engaged_updated": 90,
            "engaged_no_update": 70,
            "defensive": 35,
            "evasive": 15,
        }
        return {
            "questions_asked": self.questions_asked.copy(),
            "response_pattern": pattern,
            "resilience_score": scores[pattern],
        }

    @staticmethod
    def _challenge(claim: DeckClaim) -> str:
        prompts = {
            "market_size": "What assumption would reduce your stated market size the most, and why?",
            "traction": f"What independent records substantiate this traction claim: {claim.value}?",
            "team": "What missing capability on the founding team creates the greatest execution risk?",
            "ask": "Which milestone will this financing achieve, and what happens if it takes twice as long?",
            "problem_product": "What customer behavior would prove that this problem is not urgent enough?",
        }
        return prompts.get(
            claim.field,
            f"What evidence could falsify your claim about {claim.field}: {claim.value}?",
        )


class InterviewAgent:
    def start(
        self, raw_claims: list[dict[str, Any] | DeckClaim], max_questions: int = 5
    ) -> InterviewSession:
        if not 2 <= max_questions <= 5:
            raise ValueError("max_questions must be between 2 and 5")
        return InterviewSession(normalize_claims(raw_claims), max_questions=max_questions)


def classify_response_pattern(responses: list[str]) -> ResponsePattern:
    text = " ".join(responses).casefold()
    if not responses or not text.strip():
        return "evasive"
    if any(marker in text for marker in _DEFENSIVE_MARKERS):
        return "defensive"
    substantive = sum(len(re.findall(r"\w+", response)) >= 8 for response in responses)
    if substantive < max(1, len(responses) // 2):
        return "evasive"
    if any(marker in text for marker in _UPDATE_MARKERS):
        return "engaged_updated"
    return "engaged_no_update"
