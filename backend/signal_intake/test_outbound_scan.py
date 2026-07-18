"""Tests for outbound scanning. Run with:
cd backend && python3 -m unittest signal_intake.test_outbound_scan -v

All network calls are mocked -- these don't hit GitHub/HN/arXiv/SMTP.
"""
import json
import os
import unittest
from unittest.mock import patch

from . import outbound_scan
from .schemas import PublicSignals

GITHUB_REPOS = [
    {
        "repo_id": 1,
        "name": "cool-repo",
        "owner": "priyar",
        "stars": 900,
        "language": "Python",
        "url": "https://github.com/priyar/cool-repo",
        "created_at": "2024-01-01T00:00:00Z",
        "pushed_at": "2026-07-10T00:00:00Z",
    }
]
HN_POSTS = [{"hn_id": 1, "title": "Show HN: thing", "url": "x", "points": 220, "author": "priyar", "time": 0}]
ARXIV_PAPERS = [
    {
        "arxiv_id": "1234.5678",
        "title": "A Paper",
        "authors": ["priyar"],
        "published": "2026-07-17T00:00:00+00:00",
        "url": "https://arxiv.org/abs/1234.5678",
    }
]


class BuildCandidatePoolTests(unittest.TestCase):
    def test_merges_three_sources_into_one_identity(self):
        candidates = outbound_scan.build_candidate_pool(GITHUB_REPOS, HN_POSTS, ARXIV_PAPERS)
        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]
        self.assertEqual(candidate["identity"], "priyar")
        self.assertEqual(candidate["sources"], ["arxiv", "devpost_hn", "github"])
        self.assertIsInstance(candidate["public_signals"], PublicSignals)
        self.assertEqual(candidate["public_signals"].github.repos, 1)
        self.assertEqual(candidate["public_signals"].devpost_hn.launches, 1)
        self.assertEqual(candidate["public_signals"].devpost_hn.total_upvotes, 220)
        self.assertEqual(candidate["public_signals"].arxiv.papers, 1)

    def test_no_overlap_produces_separate_candidates(self):
        other_hn = [{"hn_id": 2, "title": "x", "url": "y", "points": 5, "author": "someone_else", "time": 0}]
        candidates = outbound_scan.build_candidate_pool(GITHUB_REPOS, other_hn, [])
        self.assertEqual({c["identity"] for c in candidates}, {"priyar", "someone_else"})


class PartialFounderScoreTests(unittest.TestCase):
    def test_strong_public_signals_score_higher_than_weak(self):
        strong = PublicSignals(
            github={"repos": 10, "commit_consistency_score": 1.0, "longevity_months": 36},
            devpost_hn={"launches": 5, "total_upvotes": 500},
            arxiv={"papers": 3},
        )
        weak = PublicSignals()
        strong_score = outbound_scan.compute_partial_founder_score(strong)
        weak_score = outbound_scan.compute_partial_founder_score(weak)

        self.assertEqual(strong_score["value"], 50.0)  # maxes every component -> full 50
        self.assertEqual(weak_score["value"], 0.0)
        self.assertGreater(strong_score["value"], weak_score["value"])

    def test_should_activate_respects_threshold(self):
        self.assertTrue(outbound_scan.should_activate({"value": 45}, threshold=40))
        self.assertFalse(outbound_scan.should_activate({"value": 10}, threshold=40))


class ActivationEmailTests(unittest.TestCase):
    def test_draft_references_actual_signals_not_generic_boilerplate(self):
        candidate = {
            "identity": "priyar",
            "sources": ["github", "devpost_hn"],
            "public_signals": PublicSignals(
                github={"repos": 3, "commit_consistency_score": 0.5, "longevity_months": 12},
                devpost_hn={"launches": 1, "total_upvotes": 220},
            ),
        }
        email = outbound_scan.draft_activation_email(candidate, "priyar@example.com")
        self.assertEqual(email["to"], "priyar@example.com")
        self.assertIn("3 active repo", email["body"])
        self.assertIn("220 upvotes", email["body"])

    def test_send_without_smtp_env_logs_dry_run_instead_of_sending(self):
        email = {"to": "x@example.com", "subject": "s", "body": "b"}
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("EMAIL_SMTP_HOST", None)
            if os.path.exists(outbound_scan.OUTBOX_PATH):
                os.remove(outbound_scan.OUTBOX_PATH)
            result = outbound_scan.send_activation_email(email)

        self.assertEqual(result["status"], "dry_run_logged")
        with open(outbound_scan.OUTBOX_PATH, encoding="utf-8") as f:
            logged = json.loads(f.readline())
        self.assertEqual(logged["to"], "x@example.com")
        os.remove(outbound_scan.OUTBOX_PATH)


class ResolveContactEmailTests(unittest.TestCase):
    @patch("requests.get")
    def test_falls_back_to_commit_email_when_profile_email_private(self, mock_get):
        def fake_get(url, **kwargs):
            if url.endswith("/users/priyar"):
                return _FakeResponse(200, {"email": None})
            if url.endswith("/users/priyar/repos"):
                return _FakeResponse(200, [{"name": "cool-repo"}])
            if url.endswith("/repos/priyar/cool-repo/commits"):
                return _FakeResponse(200, [{"commit": {"author": {"email": "priya@realmail.com"}}}])
            raise AssertionError(f"unexpected URL {url}")

        mock_get.side_effect = fake_get
        contact = outbound_scan.resolve_contact_email("priyar")
        self.assertEqual(contact, {"channel": "email", "value": "priya@realmail.com", "source": "github_commit"})

    @patch("requests.get")
    def test_skips_github_noreply_commit_emails(self, mock_get):
        def fake_get(url, **kwargs):
            if url.endswith("/users/priyar"):
                return _FakeResponse(200, {"email": None})
            if url.endswith("/users/priyar/repos"):
                return _FakeResponse(200, [{"name": "cool-repo"}])
            if url.endswith("/repos/priyar/cool-repo/commits"):
                return _FakeResponse(
                    200, [{"commit": {"author": {"email": "123+priyar@users.noreply.github.com"}}}]
                )
            raise AssertionError(f"unexpected URL {url}")

        mock_get.side_effect = fake_get
        with patch.object(outbound_scan, "_resolve_contact_via_tavily", return_value=None):
            contact = outbound_scan.resolve_contact_email("priyar")
        self.assertEqual(contact["channel"], "none")

    @patch.dict(os.environ, {"TAVILY_API_KEY": "fake-key"})
    @patch.object(outbound_scan, "TavilyClient")
    @patch("requests.get")
    def test_tavily_fallback_extracts_email_from_snippet(self, mock_get, mock_tavily_cls):
        mock_get.return_value = _FakeResponse(200, {"email": None})
        with patch.object(outbound_scan, "_resolve_email_from_commits", return_value=None):
            mock_client = mock_tavily_cls.return_value
            mock_client.search.return_value = {
                "results": [{"url": "https://example.com", "content": "reach me at priya@realmail.com anytime"}]
            }
            contact = outbound_scan.resolve_contact_email("priyar")
        self.assertEqual(contact, {"channel": "email", "value": "priya@realmail.com", "source": "tavily"})

    @patch.dict(os.environ, {"TAVILY_API_KEY": "fake-key"})
    @patch.object(outbound_scan, "TavilyClient")
    @patch("requests.get")
    def test_tavily_fallback_returns_social_url_when_no_email_found(self, mock_get, mock_tavily_cls):
        mock_get.return_value = _FakeResponse(200, {"email": None})
        with patch.object(outbound_scan, "_resolve_email_from_commits", return_value=None):
            mock_client = mock_tavily_cls.return_value
            mock_client.search.return_value = {"results": [{"url": "https://twitter.com/priyar", "content": "bio"}]}
            contact = outbound_scan.resolve_contact_email("priyar")
        self.assertEqual(contact, {"channel": "social", "value": "https://twitter.com/priyar", "source": "tavily"})


class _FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class RunOutboundPassTests(unittest.TestCase):
    @patch.object(outbound_scan, "resolve_contact_email", return_value={"channel": "none", "value": None, "source": None})
    @patch.object(outbound_scan, "fetch_arxiv_recent", return_value=ARXIV_PAPERS)
    @patch.object(outbound_scan, "fetch_show_hn", return_value=HN_POSTS)
    @patch.object(outbound_scan, "fetch_github_trending", return_value=GITHUB_REPOS)
    def test_full_pass_with_no_public_email_skips_send(self, *_mocks):
        results = outbound_scan.run_outbound_pass()
        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertEqual(result["identity"], "priyar")
        if result["activated"]:
            self.assertEqual(result["outreach"]["status"], "no_public_contact_found")

    @patch.object(outbound_scan, "fetch_arxiv_recent", return_value=[])
    @patch.object(outbound_scan, "fetch_show_hn", return_value=[])
    @patch.object(outbound_scan, "fetch_github_trending", return_value=GITHUB_REPOS)
    def test_thesis_filter_excludes_non_matches(self, *_mocks):
        results = outbound_scan.run_outbound_pass(thesis_filter_fn=lambda c: {"thesis_match": False})
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
