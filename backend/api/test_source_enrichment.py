"""Tests for bounded, consent-safe public-source enrichment."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from backend.api.source_enrichment import _pdl_person_enrichment, cache_verified_profile_avatars, enrich_submitted_people


class PeopleDataLabsEnrichmentTests(unittest.TestCase):
    @patch.dict(os.environ, {"PEOPLE_DATA_LABS_API_KEY": "test-key"})
    @patch("backend.api.source_enrichment.requests.get")
    def test_exact_submitted_linkedin_match_yields_display_safe_metadata(self, get: MagicMock) -> None:
        response = MagicMock(status_code=200)
        response.json.return_value = {
            "status": 200,
            "likelihood": 10,
            "data": {
                "full_name": "Ada Lovelace",
                "linkedin_url": "https://www.linkedin.com/in/ada-lovelace/",
                "image": "https://images.example.com/ada.jpg",
                "headline": "Founder",
                "job_title": "CEO",
                "job_company_name": "Analytical Engines",
                "experience": [
                    {"title": {"name": "Engineer"}, "company": {"name": "Royal Society"}},
                    {"title": "CEO", "company": "Analytical Engines"},
                ],
                "education": [{"school": {"name": "University of London"}, "degrees": ["Mathematics"]}],
            },
        }
        get.return_value = response

        state, source = _pdl_person_enrichment("linkedin.com/in/ada-lovelace", None, "Ada Lovelace")

        self.assertEqual(state["status"], "matched")
        self.assertEqual(state["image_url"], "https://images.example.com/ada.jpg")
        self.assertEqual(state["affiliations"], ["Engineer · Royal Society", "CEO · Analytical Engines", "University of London · Mathematics"])
        self.assertEqual(source["source"], "People Data Labs · exact submitted profile")
        self.assertEqual(get.call_args.kwargs["headers"]["X-Api-Key"], "test-key")

    @patch.dict(os.environ, {"PEOPLE_DATA_LABS_API_KEY": "test-key"})
    @patch("backend.api.source_enrichment.requests.get")
    def test_identity_mismatch_never_attaches_a_portrait(self, get: MagicMock) -> None:
        response = MagicMock(status_code=200)
        response.json.return_value = {
            "status": 200,
            "data": {"linkedin_url": "https://linkedin.com/in/someone-else", "image": "https://images.example.com/wrong.jpg"},
        }
        get.return_value = response

        state, source = _pdl_person_enrichment("https://linkedin.com/in/ada-lovelace", None, "Ada Lovelace")

        self.assertEqual(state["status"], "identity_mismatch")
        self.assertIsNone(source)
        self.assertNotIn("image_url", state)

    @patch.dict(os.environ, {"PEOPLE_DATA_LABS_API_KEY": "test-key"})
    @patch("backend.api.source_enrichment.requests.get")
    def test_cached_profile_is_not_retrieved_again(self, get: MagicMock) -> None:
        profile = {
            "founder_name": "Ada Lovelace",
            "linkedin": "https://linkedin.com/in/ada-lovelace",
            "profile_enrichment": {"provider": "people_data_labs", "status": "matched", "image_url": "https://images.example.com/ada.jpg"},
        }

        updated, sources = enrich_submitted_people(profile)

        self.assertEqual(updated["linkedin_avatar_url"], "https://images.example.com/ada.jpg")
        self.assertEqual(sources, [])
        get.assert_not_called()

    @patch("backend.api.source_enrichment.requests.get")
    def test_verified_portrait_is_cached_for_reliable_display(self, get: MagicMock) -> None:
        image = MagicMock(status_code=200, headers={"content-type": "image/jpeg"})
        image.iter_content.return_value = [b"image-bytes"]
        get.return_value = image
        profile = {
            "profile_enrichment": {
                "provider": "people_data_labs",
                "status": "matched",
                "image_url": "https://images.example.com/ada.jpg",
            }
        }

        with tempfile.TemporaryDirectory() as directory:
            updated = cache_verified_profile_avatars(profile, Path(directory), "company-1")
            self.assertEqual(updated["linkedin_avatar_url"], "/media/avatars/company-1-founder.jpg")
            self.assertTrue((Path(directory) / "avatars" / "company-1-founder.jpg").exists())


if __name__ == "__main__":
    unittest.main()
