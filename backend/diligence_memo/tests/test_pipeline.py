from __future__ import annotations

import unittest
from unittest.mock import patch
import json
from io import BytesIO
from urllib.error import HTTPError

from backend.diligence_memo.interview import InterviewAgent
from backend.diligence_memo.memo import MemoSynthesizer
from backend.diligence_memo.models import Evidence
from backend.diligence_memo.pipeline import DiligenceMemoPipeline
from backend.diligence_memo.validator import ClaimValidator
from backend.diligence_memo.clients import (
    ExternalServiceError,
    OpenAIReasoningClient,
    TavilySearchClient,
)


class FakeSearch:
    def __init__(self, evidence: list[Evidence]) -> None:
        self.evidence = evidence

    def search(self, query: str, max_results: int = 3) -> list[Evidence]:
        return self.evidence[:max_results]


class FailingSearch:
    def search(self, query: str, max_results: int = 3) -> list[Evidence]:
        raise ExternalServiceError("search unavailable")


class FakeReasoning:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def json_completion(self, system: str, user: str) -> dict[str, object]:
        return self.payload


CLAIMS = [
    {"field": "traction", "value": "$50k ARR", "source_slide": 5},
    {"field": "problem_product", "value": "Automates fund diligence", "source_slide": 2},
    {"field": "team", "value": "Two repeat founders", "source_slide": 8},
]


class PipelineTests(unittest.TestCase):
    def test_verified_pipeline_matches_locked_shape(self) -> None:
        evidence = [
            Evidence(
                "Company report",
                "https://example.com/launch",
                "Acme reports $50k ARR, automates fund diligence, and has two repeat founders",
                0.9,
            ),
            Evidence(
                "Company profile",
                "https://industry.example/profile",
                "Traction is 50k ARR for a diligence product led by repeat founders",
                0.8,
            ),
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

        self.assertEqual(
            set(output),
            {
                "diligence",
                "trust",
                "memo",
                "adversarial_view",
                "portfolio_check",
                "verdict",
                "amount_recommended",
            },
        )
        self.assertEqual(
            set(output["diligence"]),
            {"flagged_claims", "tavily_sources_checked", "memory_update"},
        )
        self.assertEqual(set(output["trust"]), {"claim_trust"})
        self.assertEqual(set(output["memo"]), {"required", "optional_or_flagged"})

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

    def test_search_failure_degrades_to_unverified_review(self) -> None:
        output = DiligenceMemoPipeline(ClaimValidator(FailingSearch())).run(
            {"company_name": "ColdCo", "deck_claims": CLAIMS[:1]}
        )
        self.assertEqual(output["verdict"], "review")
        self.assertEqual(output["diligence"]["tavily_sources_checked"], [])
        self.assertEqual(output["trust"]["claim_trust"][0]["confidence"], "low")

    def test_sources_checked_only_contains_unique_http_urls(self) -> None:
        evidence = [
            Evidence("One", "https://example.com/source", "Supporting evidence"),
            Evidence("Duplicate", "https://example.com/source", "More evidence"),
            Evidence("Invalid", "javascript:alert(1)", "Not a source"),
        ]
        result = ClaimValidator(FakeSearch(evidence)).validate("Acme", CLAIMS[:1])
        self.assertEqual(result.tavily_sources_checked, ["https://example.com/source"])

    def test_unrelated_sources_do_not_raise_claim_confidence(self) -> None:
        evidence = [
            Evidence("Weather", "https://example.com/weather", "A sunny forecast"),
            Evidence("Sports", "https://example.com/sports", "The home team won"),
        ]
        result = ClaimValidator(FakeSearch(evidence)).validate("Acme", CLAIMS[:1])
        self.assertEqual(result.claim_trust[0].confidence, "low")
        self.assertIn("did not specifically support", result.claim_trust[0].evidence)

    def test_duplicate_host_sources_are_not_independent_corroboration(self) -> None:
        evidence = [
            Evidence("ARR report", "https://example.com/report", "Acme reached 50k ARR"),
            Evidence("ARR repost", "https://example.com/repost", "Acme reports 50k ARR"),
        ]
        result = ClaimValidator(FakeSearch(evidence)).validate("Acme", CLAIMS[:1])
        self.assertEqual(result.claim_trust[0].confidence, "medium")

    def test_keyword_overlap_on_a_different_company_does_not_raise_confidence(self) -> None:
        # Found live: a claim's field/value tokens (e.g. "google", "engineer") can match
        # evidence that is genuinely about a real source, real person -- just not this
        # company. Lexical overlap on generic terms shouldn't count as corroboration
        # unless the evidence actually names the company being diligenced.
        team_claim = [{"field": "team", "value": "CEO worked as a software engineer at Google", "source_slide": 3}]
        evidence = [
            Evidence(
                "Unrelated exec bio",
                "https://example.com/other-ceo",
                "Jane Doe is CEO of Widgets Inc, ex-Google software engineer with 6 years experience",
            ),
            Evidence(
                "Another unrelated bio",
                "https://another.example/profile",
                "John Smith, software engineer, formerly at Google, now runs a different startup",
            ),
        ]
        result = ClaimValidator(FakeSearch(evidence)).validate("Acme", team_claim)
        self.assertEqual(result.claim_trust[0].confidence, "low")

    def test_string_false_from_reasoning_falls_back_conservatively(self) -> None:
        reasoning = FakeReasoning(
            {
                "confidence": "high",
                "evidence_summary": "Supported",
                "contradiction": "false",
                "severity": "low",
            }
        )
        validator = ClaimValidator(
            FakeSearch(
                [Evidence("One", "https://example.com/source", "Acme reports supporting traction evidence")]
            ),
            reasoning,
        )
        result = validator.validate("Acme", CLAIMS[:1])
        self.assertEqual(result.claim_trust[0].confidence, "medium")
        self.assertEqual(result.flagged_claims, [])


class InterviewTests(unittest.TestCase):
    def test_short_answer_follow_ups_are_claim_specific_and_do_not_repeat(self) -> None:
        session = InterviewAgent().start(CLAIMS, max_questions=5)
        questions = []
        for answer in ("two people", "check google", "hi", "not sure", "later"):
            question = session.next_question()
            if question is None:
                break
            questions.append(question)
            session.record_response(answer)

        self.assertEqual(len(questions), 5)
        self.assertEqual(len(set(questions)), 5)
        self.assertTrue(any("traction" in item.casefold() for item in questions))
        self.assertTrue(any("customer" in item.casefold() for item in questions))

    def test_adaptive_interview_scores_updated_response(self) -> None:
        session = InterviewAgent().start(CLAIMS, max_questions=4)
        self.assertIn("substantiate", session.next_question())
        session.record_response(
            "You are right; we updated the metric because customer data showed annualization was wrong."
        )
        self.assertIsNotNone(session.next_question())
        session.record_response(
            "The revised source is our billing export, which an investor can independently inspect."
        )
        session.next_question()
        session.record_response(
            "Customer evidence identifies the missing capability and explains why it matters."
        )
        session.next_question()
        session.record_response(
            "The source data includes a measurable cohort result over the last six months."
        )
        result = session.result()
        self.assertEqual(result["response_pattern"], "engaged_updated")
        self.assertEqual(result["resilience_score"], 90)
        self.assertEqual(len(result["questions_asked"]), 4)

    def test_short_answers_are_evasive(self) -> None:
        session = InterviewAgent().start(CLAIMS, max_questions=4)
        for answer in ("Trust us.", "Later.", "Not now.", "It works."):
            session.next_question()
            session.record_response(answer)
        self.assertEqual(session.result()["response_pattern"], "evasive")

    def test_invalid_question_limits_are_rejected(self) -> None:
        for limit in (2, 3, 6):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                InterviewAgent().start(CLAIMS, max_questions=limit)

    def test_response_cannot_be_recorded_before_question(self) -> None:
        session = InterviewAgent().start([], max_questions=4)
        with self.assertRaises(ValueError):
            session.record_response("A premature answer")

    def test_result_requires_completed_interview(self) -> None:
        session = InterviewAgent().start(CLAIMS, max_questions=4)
        session.next_question()
        session.record_response("Customer data supports this answer with a measurable result.")
        with self.assertRaises(ValueError):
            session.result()

    def test_defensive_response_pattern(self) -> None:
        session = InterviewAgent().start(CLAIMS, max_questions=4)
        session.next_question()
        session.record_response(
            "Obviously you don't understand the detailed customer evidence we already provided."
        )
        for _ in range(3):
            session.next_question()
            session.record_response(
                "Customer data provides specific evidence for the metric over six months."
            )
        self.assertEqual(session.result()["response_pattern"], "defensive")


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.body = json.dumps(payload).encode("utf-8")

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


class ClientTests(unittest.TestCase):
    @patch("backend.diligence_memo.clients.urlopen")
    def test_tavily_response_is_normalized(self, urlopen: object) -> None:
        urlopen.return_value = FakeResponse(  # type: ignore[attr-defined]
            {
                "results": [
                    {
                        "title": "ARR source",
                        "url": "https://example.com/arr",
                        "content": "Acme reached $50k ARR",
                        "score": 0.91,
                    },
                    {"title": "Missing URL", "content": "ignored"},
                ]
            }
        )
        evidence = TavilySearchClient("test-key").search("Acme traction")
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0].url, "https://example.com/arr")
        self.assertEqual(evidence[0].score, 0.91)

    @patch("backend.diligence_memo.clients.urlopen")
    def test_openai_response_extracts_json_output(self, urlopen: object) -> None:
        urlopen.return_value = FakeResponse(  # type: ignore[attr-defined]
            {
                "output": [
                    {
                        "content": [
                            {
                                "type": "output_text",
                                "text": json.dumps(
                                    {
                                        "confidence": "high",
                                        "contradiction": False,
                                    }
                                ),
                            }
                        ]
                    }
                ]
            }
        )
        result = OpenAIReasoningClient("test-key").json_completion("system", "user")
        self.assertEqual(result["confidence"], "high")
        self.assertIs(result["contradiction"], False)
        request = urlopen.call_args.args[0]  # type: ignore[attr-defined]
        request_payload = json.loads(request.data.decode("utf-8"))
        self.assertIn("JSON", request_payload["input"])

    @patch("backend.diligence_memo.clients.urlopen")
    def test_malformed_http_json_raises_service_error(self, urlopen: object) -> None:
        response = FakeResponse({})
        response.body = b"not-json"
        urlopen.return_value = response  # type: ignore[attr-defined]
        with self.assertRaises(ExternalServiceError):
            TavilySearchClient("test-key").search("Acme traction")

    def test_missing_api_keys_fail_without_network_call(self) -> None:
        with self.assertRaises(ExternalServiceError):
            TavilySearchClient("").search("Acme traction")
        with self.assertRaises(ExternalServiceError):
            OpenAIReasoningClient("").json_completion("system", "user")

    @patch("backend.diligence_memo.clients.urlopen")
    def test_provider_error_keeps_sanitized_diagnostics(self, urlopen: object) -> None:
        body = json.dumps(
            {
                "error": {
                    "type": "invalid_request_error",
                    "param": "input",
                    "message": "Input is invalid",
                }
            }
        ).encode("utf-8")
        urlopen.side_effect = HTTPError(  # type: ignore[attr-defined]
            "https://api.openai.com/v1/responses",
            400,
            "Bad Request",
            {},
            BytesIO(body),
        )
        with self.assertRaisesRegex(
            ExternalServiceError,
            r"HTTP 400; type=invalid_request_error; param=input; message=Input is invalid",
        ):
            OpenAIReasoningClient("test-key").json_completion("system", "user")


if __name__ == "__main__":
    unittest.main()
