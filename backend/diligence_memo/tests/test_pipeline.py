from __future__ import annotations

import unittest

from backend.diligence_memo.interview import InterviewAgent
from backend.diligence_memo.memo import MemoSynthesizer
from backend.diligence_memo.models import Evidence
from backend.diligence_memo.pipeline import DiligenceMemoPipeline
from backend.diligence_memo.validator import ClaimValidator


class FakeSearch:
    def __init__(self, evidence: list[Evidence]) -> None:
        self.evidence = evidence

    def search(self, query: str, max_results: int = 3) -> list[Evidence]:
        return self.evidence[:max_results]


CLAIMS = [
    {"field": "traction", "value": "$50k ARR", "source_slide": 5},
    {"field": "problem_product", "value": "Automates fund diligence", "source_slide": 2},
    {"field": "team", "value": "Two repeat founders", "source_slide": 8},
]


class PipelineTests(unittest.TestCase):
    def test_verified_pipeline_matches_locked_shape(self) -> None:
        evidence = [
            Evidence("Launch", "https://example.com/launch", "Customer metrics confirm launch", 0.9),
            Evidence("Profile", "https://example.com/profile", "Founder and product profile", 0.8),
        ]
        pipeline = DiligenceMemoPipeline(
            ClaimValidator(FakeSearch(evidence)),
            MemoSynthesizer({"fintech"}),
        )
        output = pipeline.run(
            {
                "company_name": "Acme",
                "sector": "Fintech infrastructure",
                "deck_claims": CLAIMS,
            }
        )
        self.assertEqual(output["verdict"], "approve")
        self.assertEqual(output["amount_recommended"], 100000)
        self.assertTrue(output["portfolio_check"]["overlap"])
        self.assertEqual(len(output["trust"]["claim_trust"]), 3)
        self.assertFalse(output["diligence"]["memory_update"])
        self.assertNotIn("adversarial_view", output["memo"])

    def test_contradiction_is_flagged_and_written_back(self) -> None:
        evidence = [
            Evidence(
                "Correction",
                "https://example.com/correction",
                "The reported revenue is incorrect and disputed.",
                0.9,
            )
        ]
        output = DiligenceMemoPipeline(ClaimValidator(FakeSearch(evidence))).run(
            {"company_name": "Acme", "sector": "AI", "deck_claims": CLAIMS[:1]}
        )
        self.assertEqual(output["verdict"], "decline")
        self.assertTrue(output["diligence"]["memory_update"])
        self.assertEqual(output["diligence"]["flagged_claims"][0]["severity"], "high")
        self.assertEqual(output["trust"]["claim_trust"][0]["confidence"], "low")

    def test_no_evidence_stays_low_confidence_without_fabrication(self) -> None:
        output = DiligenceMemoPipeline(ClaimValidator(FakeSearch([]))).run(
            {"company_name": "ColdCo", "deck_claims": CLAIMS[:1]}
        )
        self.assertEqual(output["verdict"], "review")
        self.assertEqual(output["trust"]["claim_trust"][0]["confidence"], "low")
        self.assertEqual(output["memo"]["optional_or_flagged"]["cap_table"], "Not disclosed")


class InterviewTests(unittest.TestCase):
    def test_adaptive_interview_scores_updated_response(self) -> None:
        session = InterviewAgent().start(CLAIMS, max_questions=2)
        self.assertIn("substantiate", session.next_question())
        session.record_response(
            "You are right; we updated the metric because customer data showed annualization was wrong."
        )
        self.assertIsNotNone(session.next_question())
        session.record_response(
            "The revised source is our billing export, which an investor can independently inspect."
        )
        result = session.result()
        self.assertEqual(result["response_pattern"], "engaged_updated")
        self.assertEqual(result["resilience_score"], 90)
        self.assertEqual(len(result["questions_asked"]), 2)

    def test_short_answers_are_evasive(self) -> None:
        session = InterviewAgent().start(CLAIMS, max_questions=2)
        session.next_question()
        session.record_response("Trust us.")
        session.next_question()
        session.record_response("Later.")
        self.assertEqual(session.result()["response_pattern"], "evasive")


if __name__ == "__main__":
    unittest.main()
