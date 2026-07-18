"""Tests for deck parsing. Run with: cd backend && python3 -m unittest signal_intake.test_deck_parser -v

The OpenAI call is mocked so these run without network access or an API key. See
deck_parser.py's __main__ block for a real end-to-end run against the fixture deck.
"""
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from . import deck_parser
from .schemas import SignalIntakeOutput

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "shared" / "fixtures" / "decks" / "sample_deck_01.txt"

FAKE_CLAIMS_PAYLOAD = {
    "deck_claims": [
        {"field": "problem_product", "value": "Predicts restaurant no-shows using reservation + event/weather data", "source_slide": 1},
        {"field": "market_size", "value": "$2.1B US reservation software market, 14% YoY growth", "source_slide": 2},
        {"field": "traction", "value": "MRR $18,400, up from $6,100 three months ago; 34 restaurants live", "source_slide": 3},
        {"field": "team", "value": "CEO ex-OpenTable product lead; CTO ex-Uber ETA models", "source_slide": 4},
        {"field": "ask", "value": "$1.5M seed at $9M pre-money", "source_slide": 5},
    ]
}


def _mock_openai_client(payload: dict) -> MagicMock:
    client = MagicMock()
    message = SimpleNamespace(content=json.dumps(payload))
    choice = SimpleNamespace(message=message)
    client.chat.completions.create.return_value = SimpleNamespace(choices=[choice])
    return client


class SplitIntoSlidesTests(unittest.TestCase):
    def test_splits_fixture_into_five_slides(self):
        raw_text = deck_parser.load_deck_text(FIXTURE_PATH)
        slides = deck_parser.split_into_slides(raw_text)
        self.assertEqual([num for num, _ in slides], [1, 2, 3, 4, 5])
        self.assertIn("no-shows", slides[0][1])
        self.assertIn("$1.5M seed", slides[4][1])

    def test_no_markers_falls_back_to_single_slide(self):
        slides = deck_parser.split_into_slides("just some plain text, no markers")
        self.assertEqual(slides, [(1, "just some plain text, no markers")])


class ExtractDeckClaimsTests(unittest.TestCase):
    def test_extracts_claims_matching_contract_shape(self):
        client = _mock_openai_client(FAKE_CLAIMS_PAYLOAD)
        claims = deck_parser.extract_deck_claims(FIXTURE_PATH, client=client)

        self.assertEqual(len(claims), 5)
        fields = {c.field for c in claims}
        self.assertEqual(fields, {"market_size", "traction", "team", "ask", "problem_product"})
        for claim in claims:
            self.assertIsInstance(claim.source_slide, int)
            self.assertGreaterEqual(claim.source_slide, 1)

    def test_rejects_invalid_field_name(self):
        bad_payload = {"deck_claims": [{"field": "not_a_real_field", "value": "x", "source_slide": 1}]}
        client = _mock_openai_client(bad_payload)
        with self.assertRaises(ValueError):
            deck_parser.extract_deck_claims(FIXTURE_PATH, client=client)


class AssembleSignalIntakeOutputTests(unittest.TestCase):
    def test_output_matches_contract_envelope(self):
        client = _mock_openai_client(FAKE_CLAIMS_PAYLOAD)
        claims = deck_parser.extract_deck_claims(FIXTURE_PATH, client=client)
        output = deck_parser.assemble_signal_intake_output(
            founder_id="founder_1", company_id="company_1", deck_claims=claims
        )

        self.assertIsInstance(output, SignalIntakeOutput)
        self.assertEqual(output.sourcing_channel, "inbound")
        self.assertFalse(output.cold_start_flag)
        self.assertEqual(len(output.deck_claims), 5)
        # public_signals defaults to zeroed structure — outbound module fills this in later
        self.assertEqual(output.public_signals.github.repos, 0)


if __name__ == "__main__":
    unittest.main()
