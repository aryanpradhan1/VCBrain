"""Tests for outbound scanning. Run with:
cd backend && PYTHONPATH=.. OPENAI_API_KEY=... python3 -m unittest signal_intake.test_outbound_scan -v

All network calls are mocked -- these don't hit GitHub/HN/arXiv/SMTP. OPENAI_API_KEY and
the repo root on PYTHONPATH are only needed because RealThesisFilterTests patches
backend.scoring.evaluate_thesis_fit directly, and importing backend.scoring (B's module)
instantiates a global OpenAI client at import time -- the function itself is still mocked,
no real call happens.
"""
import json
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from . import outbound_scan
from .schemas import PublicSignals, SignalIntakeOutput

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


class RealThesisFilterTests(unittest.TestCase):
    """Patches backend.scoring.evaluate_thesis_fit directly, not sys.modules injection,
    since backend.scoring is a real importable module here (unlike backend.api.db) --
    requires OPENAI_API_KEY to be set for the import machinery even though the function
    itself is mocked, same as this repo's other live-adjacent tests."""

    @patch("backend.scoring.evaluate_thesis_fit")
    def test_translates_thesis_output_into_filter_dict(self, mock_evaluate):
        from backend.scoring.thesis_engine import ThesisOutput

        mock_evaluate.return_value = ThesisOutput(
            thesis_match=True, match_type="adjacent_llm_judged", rationale="close enough"
        )
        result = outbound_scan._real_thesis_filter({"identity": "priyar"})

        self.assertEqual(
            result, {"thesis_match": True, "match_type": "adjacent_llm_judged", "rationale": "close enough"}
        )
        mock_evaluate.assert_called_once_with({"deck_claims": []})


class DeferThesisToConversionTests(unittest.TestCase):
    """_defer_thesis_to_conversion is apply_thesis_filter's actual default now --
    _real_thesis_filter is no longer used by default because it rejects every single
    outbound candidate (confirmed live: 5/5 real discovered candidates, 0 survivors)."""

    def test_always_passes_with_no_external_calls(self):
        result = outbound_scan._defer_thesis_to_conversion({"identity": "anyone"})
        self.assertTrue(result["thesis_match"])

    def test_is_the_actual_default_for_apply_thesis_filter(self):
        candidates = [{"identity": "a"}, {"identity": "b"}]
        filtered = outbound_scan.apply_thesis_filter(candidates)
        self.assertEqual(filtered, candidates)


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

    def test_identity_matching_is_case_insensitive(self):
        mixed_case_hn = [{"hn_id": 3, "title": "x", "url": "y", "points": 50, "author": "PriyaR", "time": 0}]
        candidates = outbound_scan.build_candidate_pool(GITHUB_REPOS, mixed_case_hn, [])
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["sources"], ["devpost_hn", "github"])
        self.assertEqual(candidates[0]["public_signals"].devpost_hn.launches, 1)

    def test_arxiv_only_counts_first_and_last_author_not_every_coauthor(self):
        many_author_paper = [
            {
                "arxiv_id": "9999.0001",
                "title": "Big Collab",
                "authors": ["Lead Author", "Middle One", "Middle Two", "Senior Author"],
                "published": "2026-07-17T00:00:00+00:00",
                "url": "https://arxiv.org/abs/9999.0001",
            }
        ]
        candidates = outbound_scan.build_candidate_pool([], [], many_author_paper)
        identities = {c["identity"] for c in candidates}
        self.assertEqual(identities, {"Lead Author", "Senior Author"})
        self.assertNotIn("Middle One", identities)
        self.assertNotIn("Middle Two", identities)

    def test_dedups_repeated_items_within_a_single_fetch(self):
        duplicated_repos = GITHUB_REPOS + GITHUB_REPOS  # same repo_id twice
        candidates = outbound_scan.build_candidate_pool(duplicated_repos, [], [])
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["public_signals"].github.repos, 1)


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

    def test_qualitative_signal_carries_a_near_empty_profile(self):
        empty = PublicSignals()
        strong_hit = {"signal_strength": 1.0, "evidence": "serial founder building a new startup", "source_url": "x"}
        score = outbound_scan.compute_partial_founder_score(empty, strong_hit)

        self.assertEqual(score["value"], outbound_scan.QUALITATIVE_MAX_BONUS)
        self.assertEqual(score["qualitative_bonus_applied"], outbound_scan.QUALITATIVE_MAX_BONUS)

    def test_qualitative_signal_adds_little_on_top_of_a_maxed_structural_profile(self):
        strong = PublicSignals(
            github={"repos": 10, "commit_consistency_score": 1.0, "longevity_months": 36},
            devpost_hn={"launches": 5, "total_upvotes": 500},
            arxiv={"papers": 3},
        )
        strong_hit = {"signal_strength": 1.0, "evidence": "founder", "source_url": "x"}
        score = outbound_scan.compute_partial_founder_score(strong, strong_hit)

        self.assertEqual(score["qualitative_bonus_applied"], 0.0)
        self.assertEqual(score["value"], 50.0)  # capped, not inflated past the partial scale

    def test_no_qualitative_hit_applies_no_bonus(self):
        empty = PublicSignals()
        no_hit = {"signal_strength": 0.0, "evidence": None, "source_url": None}
        score = outbound_scan.compute_partial_founder_score(empty, no_hit)
        self.assertEqual(score["value"], 0.0)


def _mock_openai_classifier(is_founder_intent: bool, confidence: str = "high"):
    payload = {"is_founder_intent": is_founder_intent, "confidence": confidence}
    client = MagicMock()
    message = SimpleNamespace(content=json.dumps(payload))
    choice = SimpleNamespace(message=message)
    client.chat.completions.create.return_value = SimpleNamespace(choices=[choice])
    return client


class ClassifyFounderIntentTests(unittest.TestCase):
    def test_negated_mention_is_not_classified_as_founder_intent(self):
        # This is the real false-positive case that live-tested keyword matching missed:
        # "co-founder" appears in the text, but the person explicitly did NOT have one.
        client = _mock_openai_classifier(is_founder_intent=False)
        result = outbound_scan._classify_founder_intent(
            "torvalds", "He didn't have a co-founder. No VC funding.", client=client
        )
        self.assertFalse(result["matched"])
        self.assertEqual(result["signal_strength"], 0.0)

    def test_genuine_founder_mention_maps_confidence_to_signal_strength(self):
        client = _mock_openai_classifier(is_founder_intent=True, confidence="medium")
        result = outbound_scan._classify_founder_intent(
            "priyar", "Priya is currently building her own startup in stealth", client=client
        )
        self.assertTrue(result["matched"])
        self.assertEqual(result["signal_strength"], 0.6)


class FetchProductHuntRecentTests(unittest.TestCase):
    def test_returns_empty_without_token_and_makes_no_request(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PRODUCT_HUNT_API_TOKEN", None)
            with patch("requests.post") as mock_post:
                result = outbound_scan.fetch_product_hunt_recent()
        self.assertEqual(result, [])
        mock_post.assert_not_called()

    @patch.dict(os.environ, {"PRODUCT_HUNT_API_TOKEN": "fake-token"})
    @patch("requests.post")
    def test_shape_matches_show_hn_for_shared_aggregation(self, mock_post):
        mock_post.return_value.json.return_value = {
            "data": {
                "posts": {
                    "edges": [
                        {
                            "node": {
                                "id": "123",
                                "name": "Cool Launch",
                                "url": "https://producthunt.com/posts/cool-launch",
                                "votesCount": 88,
                                "createdAt": "2026-07-19T00:00:00Z",
                                "user": {"username": "priyar"},
                            }
                        }
                    ]
                }
            }
        }
        mock_post.return_value.raise_for_status = lambda: None
        result = outbound_scan.fetch_product_hunt_recent()
        self.assertEqual(
            result,
            [
                {
                    "hn_id": "ph-123",
                    "title": "Cool Launch",
                    "url": "https://producthunt.com/posts/cool-launch",
                    "points": 88,
                    "author": "priyar",
                    "time": "2026-07-19T00:00:00Z",
                }
            ],
        )

    def test_merges_into_devpost_hn_bucket_alongside_show_hn(self):
        ph_post = {"hn_id": "ph-1", "title": "x", "url": "y", "points": 40, "author": "priyar", "time": 0}
        combined = HN_POSTS + [ph_post]
        candidates = outbound_scan.build_candidate_pool(GITHUB_REPOS, combined, [])
        candidate = next(c for c in candidates if c["identity"] == "priyar")
        # HN_POSTS already gives priyar 1 launch/220 points; the PH post adds a second.
        self.assertEqual(candidate["public_signals"].devpost_hn.launches, 2)
        self.assertEqual(candidate["public_signals"].devpost_hn.total_upvotes, 260)


class SearchFounderIntentTests(unittest.TestCase):
    @patch.dict(os.environ, {"TAVILY_API_KEY": "fake-key"})
    @patch.object(outbound_scan, "TavilyClient")
    def test_returns_first_genuinely_matching_result(self, mock_tavily_cls):
        mock_tavily_cls.return_value.search.return_value = {
            "results": [
                {"url": "https://x.com/a", "content": "unrelated bio, nothing here"},
                {"url": "https://x.com/b", "content": "Priya just launched her own startup"},
            ]
        }
        # Two different snippets need two different classifications -- a fixed
        # return_value would classify both the same way regardless of content.
        client = _mock_openai_classifier(is_founder_intent=True, confidence="high")
        client.chat.completions.create.side_effect = [
            SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
                content=json.dumps({"is_founder_intent": False, "confidence": "low"})
            ))]),
            SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
                content=json.dumps({"is_founder_intent": True, "confidence": "high"})
            ))]),
        ]
        result = outbound_scan.search_founder_intent("priyar", client=client)
        self.assertEqual(result["signal_strength"], 1.0)
        self.assertEqual(result["source_url"], "https://x.com/b")

    @patch.dict(os.environ, {"TAVILY_API_KEY": "fake-key"})
    @patch.object(outbound_scan, "TavilyClient")
    def test_no_genuine_match_returns_zero_signal(self, mock_tavily_cls):
        mock_tavily_cls.return_value.search.return_value = {
            "results": [{"url": "https://x.com/priyar", "content": "unrelated bio"}]
        }
        client = _mock_openai_classifier(is_founder_intent=False)
        result = outbound_scan.search_founder_intent("priyar", client=client)
        self.assertEqual(result["signal_strength"], 0.0)
        self.assertIsNone(result["evidence"])

    def test_missing_api_key_returns_zero_signal_without_calling_tavily_or_openai(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TAVILY_API_KEY", None)
            result = outbound_scan.search_founder_intent("priyar")
        self.assertEqual(result["signal_strength"], 0.0)


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

    def test_draft_includes_can_spam_and_tracking_links(self):
        candidate = {
            "identity": "priyar",
            "sources": ["github"],
            "public_signals": PublicSignals(github={"repos": 1, "commit_consistency_score": 0.5, "longevity_months": 1}),
        }
        email = outbound_scan.draft_activation_email(candidate, "priyar@example.com")
        self.assertIn(outbound_scan._MAILING_ADDRESS_LINE, email["body"])
        # Apply link carries the candidate's identity so a real submission can link back
        # to this outbound record instead of becoming a disconnected new founder_id.
        self.assertIn(f"{outbound_scan.APP_BASE_URL}/apply?ref=priyar", email["body"])
        self.assertIn(f"{outbound_scan.API_BASE_URL}/outbound/unsubscribe/priyar", email["body"])

    def test_real_send_dispatches_once_placeholders_are_replaced(self):
        email = {
            "to": "x@example.com",
            "subject": "s",
            "body": "Real Fund LLC, 123 Main St. Reply STOP to unsubscribe.",
        }
        env = {
            "EMAIL_SMTP_HOST": "smtp.example.com",
            "EMAIL_FROM": "fund@example.com",
            "EMAIL_SMTP_PASSWORD": "pw",
        }
        with patch.dict(os.environ, env):
            with patch("smtplib.SMTP") as mock_smtp:
                mock_server = mock_smtp.return_value.__enter__.return_value
                result = outbound_scan.send_activation_email(email)

        self.assertEqual(result["status"], "sent")
        mock_server.send_message.assert_called_once()


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
    @patch.object(
        outbound_scan,
        "search_founder_intent",
        return_value={"signal_strength": 0.0, "evidence": None, "source_url": None},
    )
    @patch.object(outbound_scan, "_record_signal_intake_in_memory")
    @patch.object(outbound_scan, "resolve_contact_email", return_value={"channel": "none", "value": None, "source": None})
    @patch.object(outbound_scan, "fetch_arxiv_recent", return_value=ARXIV_PAPERS)
    @patch.object(outbound_scan, "fetch_show_hn", return_value=HN_POSTS)
    @patch.object(outbound_scan, "fetch_github_trending", return_value=GITHUB_REPOS)
    def test_full_pass_with_no_public_email_skips_send(self, *_mocks):
        results = outbound_scan.run_outbound_pass()
        self.assertEqual(len(results), 1)
        result = results[0]
        signal_output = result["signal_intake_output"]
        self.assertEqual(signal_output.founder_id, "priyar")
        self.assertEqual(signal_output.company_id, "pending_priyar")
        self.assertEqual(signal_output.sourcing_channel, "outbound")
        self.assertTrue(signal_output.cold_start_flag)
        if result["activated"]:
            self.assertEqual(result["outreach"]["status"], "no_public_contact_found")

    @patch.object(outbound_scan, "fetch_arxiv_recent", return_value=[])
    @patch.object(outbound_scan, "fetch_show_hn", return_value=[])
    @patch.object(outbound_scan, "fetch_github_trending", return_value=GITHUB_REPOS)
    def test_thesis_filter_excludes_non_matches(self, *_mocks):
        results = outbound_scan.run_outbound_pass(thesis_filter_fn=lambda c: {"thesis_match": False})
        self.assertEqual(results, [])

    @patch.object(outbound_scan, "should_activate", return_value=True)
    @patch.object(outbound_scan, "search_founder_intent", return_value={"signal_strength": 0.0, "evidence": None, "source_url": None})
    @patch.object(outbound_scan, "_record_signal_intake_in_memory")
    @patch.object(outbound_scan, "send_activation_email", return_value={"status": "dry_run_logged"})
    @patch.object(outbound_scan, "resolve_contact_email", return_value={"channel": "email", "value": "priyar@example.com", "source": "github_profile"})
    @patch.object(outbound_scan, "fetch_arxiv_recent", return_value=[])
    @patch.object(outbound_scan, "fetch_show_hn", return_value=[])
    @patch.object(outbound_scan, "fetch_github_trending", return_value=GITHUB_REPOS)
    def test_activated_candidate_logs_outreach_sent_event(self, *_mocks):
        fake_db = MagicMock()
        with patch.dict(sys.modules, {"backend.api.db": fake_db}):
            results = outbound_scan.run_outbound_pass()

        self.assertTrue(results[0]["activated"])
        fake_db.save_outreach_event.assert_called_once_with(
            "priyar", "sent", company_id="pending_priyar", cold_start_flag=True
        )


class AssembleOutboundSignalIntakeOutputTests(unittest.TestCase):
    def test_wraps_candidate_into_real_contract_shape(self):
        candidate = {
            "identity": "priyar",
            "sources": ["github", "devpost_hn"],
            "public_signals": PublicSignals(
                github={"repos": 3, "commit_consistency_score": 0.5, "longevity_months": 12},
                devpost_hn={"launches": 1, "total_upvotes": 220},
            ),
        }
        output = outbound_scan.assemble_outbound_signal_intake_output(candidate)

        self.assertIsInstance(output, SignalIntakeOutput)
        self.assertEqual(output.founder_id, "priyar")
        self.assertEqual(output.company_id, "pending_priyar")  # documented placeholder, not fabricated data
        self.assertEqual(output.deck_claims, [])
        self.assertEqual(output.sourcing_channel, "outbound")
        self.assertTrue(output.cold_start_flag)
        self.assertEqual(output.public_signals.github.repos, 3)


class RecordSignalIntakeInMemoryTests(unittest.TestCase):
    def test_saves_one_signal_per_contributing_source_and_recomputes(self):
        candidate = {
            "identity": "priyar",
            "sources": ["github", "devpost_hn"],
            "public_signals": PublicSignals(
                github={"repos": 3, "commit_consistency_score": 0.5, "longevity_months": 12},
                devpost_hn={"launches": 1, "total_upvotes": 220},
            ),
        }
        output = outbound_scan.assemble_outbound_signal_intake_output(candidate)

        fake_db = MagicMock()
        with patch.dict(sys.modules, {"backend.api.db": fake_db}):
            outbound_scan._record_signal_intake_in_memory(output)

        self.assertEqual(fake_db.save_signal.call_count, 2)
        # company_id/cold_start_flag must ride along on every payload -- db.py's
        # save_signal() upserts the founders row from each individual call's payload,
        # not just once, so omitting them here would silently drop them (a real bug this
        # test caught live before this assertion existed).
        fake_db.save_signal.assert_any_call(
            "priyar",
            "github",
            {
                "repos": 3,
                "commit_consistency_score": 0.5,
                "longevity_months": 12,
                "company_id": "pending_priyar",
                "cold_start_flag": True,
            },
        )
        fake_db.save_signal.assert_any_call(
            "priyar",
            "devpost_hn",
            {"launches": 1, "total_upvotes": 220, "company_id": "pending_priyar", "cold_start_flag": True},
        )
        fake_db.recompute_founder_score.assert_called_once_with("priyar")


if __name__ == "__main__":
    unittest.main()
