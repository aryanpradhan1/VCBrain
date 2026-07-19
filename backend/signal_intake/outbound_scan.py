"""Bounded outbound scanning + partial Founder Score + Activate (cold outreach).

Scope (CLAUDE.md items 2-3): pull small, naturally bounded feeds only (GitHub, Show HN,
arXiv) via official APIs -- never unbounded crawling, never raw HTML/page scraping.
Dedup/enrich/tag by source, compute a partial Founder Score from public signals alone
(Track Record + Traction Signal only -- rule-based, per the contract's AI-justification
section: "raw signal statistics" stay rule-based, not LLM, which also keeps this whole
pass at zero LLM cost). Trigger Activate (cold outreach) only above a threshold.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree as ET

import requests
from openai import OpenAI
from tavily import TavilyClient

from .schemas import ArxivSignals, DevpostHnSignals, GithubSignals, PublicSignals, SignalIntakeOutput

MODEL = "gpt-5.5-2026-04-23"

# Hard caps -- every fetch below is bounded by one of these, never by pagination.
GITHUB_LIMIT = int(os.environ.get("OUTBOUND_GITHUB_LIMIT", 50))
HN_LIMIT = int(os.environ.get("OUTBOUND_HN_LIMIT", 30))
ARXIV_LIMIT = int(os.environ.get("OUTBOUND_ARXIV_LIMIT", 30))
PRODUCT_HUNT_LIMIT = int(os.environ.get("OUTBOUND_PRODUCT_HUNT_LIMIT", 20))

# Internal Activate-gating threshold. NOT part of the published contract shapes -- this
# score only decides whether to cold-outreach a candidate, it never crosses a module
# boundary. Scale is 0-50 (see compute_partial_founder_score's docstring).
#
# Set to 25 (50% of max) as a reasoned demo default, not a validated one -- we don't have
# real outreach-response data yet to actually tune this against (see the earlier
# discussion on validating thresholds through the persistent store). 40 (80% of max) was
# checked against real candidates and proved too conservative for a demo: it requires
# near-maximum on both Track Record AND Traction simultaneously, which real discovered
# candidates rarely hit (live-tested examples scored 2.7-19.2 out of 50 with thin/typical
# signals). 25 still requires genuinely solid combined signal, not just "found via GitHub"
# noise, while being achievable enough to actually demonstrate the Activate path firing.
# Revisit once real response-rate data exists to validate against.
ACTIVATION_THRESHOLD = 25

OUTBOX_PATH = os.path.join(os.path.dirname(__file__), "activation_outbox.jsonl")

_GITHUB_API = "https://api.github.com"
_HN_API = "https://hacker-news.firebaseio.com/v0"
_ARXIV_API = "http://export.arxiv.org/api/query"

_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_GITHUB_NOREPLY_RE = re.compile(r"^\d+\+.*@users\.noreply\.github\.com$")


# ---------------------------------------------------------------------------
# Fetchers -- bounded, structured-fields-only, official read APIs (no HTML scraping)
# ---------------------------------------------------------------------------

def fetch_github_trending(limit: int = GITHUB_LIMIT, pushed_within_days: int = 7) -> list[dict]:
    """Proxy for GitHub's un-API'd Trending page: repos pushed in the last N days,
    sorted by stars, a single bounded page (no pagination loop)."""
    since = (datetime.now(timezone.utc) - timedelta(days=pushed_within_days)).strftime("%Y-%m-%d")
    resp = requests.get(
        f"{_GITHUB_API}/search/repositories",
        params={"q": f"pushed:>{since}", "sort": "stars", "order": "desc", "per_page": min(limit, 50)},
        headers={"Accept": "application/vnd.github+json"},
        timeout=10,
    )
    resp.raise_for_status()
    items = resp.json().get("items", [])[:limit]
    return [
        {
            "repo_id": item["id"],
            "name": item["name"],
            "owner": item["owner"]["login"],
            "stars": item["stargazers_count"],
            "language": item.get("language"),
            "url": item["html_url"],
            "created_at": item["created_at"],
            "pushed_at": item["pushed_at"],
        }
        for item in items
    ]


def fetch_show_hn(limit: int = HN_LIMIT) -> list[dict]:
    """Official HN Firebase API. Only the first `limit` story IDs are ever fetched in
    detail -- bounded regardless of how many Show HN posts exist that day."""
    ids_resp = requests.get(f"{_HN_API}/showstories.json", timeout=10)
    ids_resp.raise_for_status()
    story_ids = ids_resp.json()[:limit]

    stories = []
    for story_id in story_ids:
        item_resp = requests.get(f"{_HN_API}/item/{story_id}.json", timeout=10)
        item_resp.raise_for_status()
        item = item_resp.json()
        if not item:
            continue
        stories.append(
            {
                "hn_id": item.get("id"),
                "title": item.get("title"),
                "url": item.get("url"),
                "points": item.get("score", 0),
                "author": item.get("by"),
                "time": item.get("time"),
            }
        )
    return stories


_PRODUCT_HUNT_API = "https://api.producthunt.com/v2/api/graphql"
_PRODUCT_HUNT_QUERY = """
query RecentPosts($first: Int!) {
  posts(first: $first, order: RANKING) {
    edges { node { id name url votesCount createdAt user { username } } }
  }
}
"""


def fetch_product_hunt_recent(limit: int = PRODUCT_HUNT_LIMIT) -> list[dict]:
    """Official Product Hunt API v2 (GraphQL) -- bounded via `first`, single page, no
    pagination. Requires PRODUCT_HUNT_API_TOKEN, a new credential not in the original
    contract's env var list (OPENAI_API_KEY/TAVILY_API_KEY only) -- returns [] rather than
    raising if it isn't configured, so this degrades gracefully instead of breaking the
    rest of a scan (same pattern as the email-sending path elsewhere in this module).

    Shaped identically to fetch_show_hn's output (same keys, including reusing the
    "hn_id" name) so it can feed the exact same devpost_hn aggregation in
    build_candidate_pool without a second code path -- the locked contract's
    public_signals only has one "devpost_hn" bucket, not a separate Product Hunt one, so
    this combines into it rather than adding a new signal category (which would be a
    contract change). "ph-" prefix on the id avoids collisions with real HN story ids in
    the same merged list."""
    token = os.environ.get("PRODUCT_HUNT_API_TOKEN")
    if not token:
        return []

    resp = requests.post(
        _PRODUCT_HUNT_API,
        json={"query": _PRODUCT_HUNT_QUERY, "variables": {"first": min(limit, 50)}},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=10,
    )
    resp.raise_for_status()
    edges = resp.json().get("data", {}).get("posts", {}).get("edges", [])[:limit]
    return [
        {
            "hn_id": f"ph-{edge['node']['id']}",
            "title": edge["node"].get("name"),
            "url": edge["node"].get("url"),
            "points": edge["node"].get("votesCount", 0),
            "author": (edge["node"].get("user") or {}).get("username"),
            "time": edge["node"].get("createdAt"),
        }
        for edge in edges
    ]


def fetch_arxiv_recent(category: str = "cs.AI", days: int = 2, limit: int = ARXIV_LIMIT) -> list[dict]:
    """Official arXiv API -- max_results caps the request itself, then results are
    further filtered client-side to the date window."""
    resp = requests.get(
        _ARXIV_API,
        params={
            "search_query": f"cat:{category}",
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": min(limit, 50),
        },
        timeout=10,
    )
    resp.raise_for_status()
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(resp.text)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    papers = []
    for entry in root.findall("atom:entry", ns):
        published = datetime.strptime(
            entry.find("atom:published", ns).text, "%Y-%m-%dT%H:%M:%SZ"
        ).replace(tzinfo=timezone.utc)
        if published < cutoff:
            continue
        papers.append(
            {
                "arxiv_id": entry.find("atom:id", ns).text.rsplit("/", 1)[-1],
                "title": entry.find("atom:title", ns).text.strip(),
                "authors": [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)],
                "published": published.isoformat(),
                "url": entry.find("atom:id", ns).text,
            }
        )
    return papers[:limit]


# ---------------------------------------------------------------------------
# Thesis Engine integration point -- B owns the real filter (see contract's "Thesis
# Engine output" shape). This is a pass-through placeholder until that endpoint exists.
# ---------------------------------------------------------------------------

def _real_thesis_filter(candidate: dict) -> dict:
    """Calls B's real Thesis Engine (backend/scoring/thesis_engine.py) with empty
    deck_claims. Kept for when a candidate genuinely has deck_claims to evaluate (e.g. a
    future flow that carries real proxy claims through), but NOT used as the default
    anymore -- see _defer_thesis_to_conversion for why. Lazy-imported for the same reason
    as the Memory-layer calls -- keeps this module (and its tests) usable independent of
    whether that branch is checked out."""
    from backend.scoring import evaluate_thesis_fit

    thesis_output = evaluate_thesis_fit({"deck_claims": candidate.get("deck_claims", [])})
    return {
        "thesis_match": thesis_output.thesis_match,
        "match_type": thesis_output.match_type,
        "rationale": thesis_output.rationale,
    }


def _defer_thesis_to_conversion(candidate: dict) -> dict:
    """Default thesis_filter_fn for outbound candidates: does NOT call the deck-based
    Thesis Engine at all. Confirmed live (not just in theory): with deck_claims=[],
    evaluate_thesis_fit() has nothing to reason about and rejects every single candidate,
    100% of the time -- a full trace of 5 real discovered candidates through the pipeline
    showed 0 survivors, not "occasional false negatives." Running a broken filter that
    always says no is worse than running no filter -- it silently kills outbound sourcing
    entirely while looking like it's working.

    Real thesis evaluation happens naturally once/if this candidate converts (applies with
    a real deck via /applications' ref param) -- main.py's existing pipeline already calls
    evaluate_thesis_fit on real deck_claims at that point (see _analysis_for). Until then,
    pool size / cost is controlled by the fetch limits (OUTBOUND_*_LIMIT env vars) and the
    partial-score Activation threshold, not by thesis fit -- which is the honest position,
    since sector/stage/geography fit genuinely can't be assessed from public signals alone."""
    return {
        "thesis_match": True,
        "match_type": "exact",
        "rationale": "Deferred to conversion -- no deck data yet to evaluate sector/stage/geography fit against.",
    }


def apply_thesis_filter(candidates: list[dict], thesis_filter_fn=None) -> list[dict]:
    """Filter the candidate pool BEFORE scoring, per CLAUDE.md item 2. Defaults to
    _defer_thesis_to_conversion (see its docstring for why) -- pass an explicit
    thesis_filter_fn to override (e.g. in tests, or _real_thesis_filter if deck_claims are
    ever genuinely available). Any override must accept a candidate dict and return
    {"thesis_match": bool, ...} per the contract shape."""
    filter_fn = thesis_filter_fn or _defer_thesis_to_conversion
    return [c for c in candidates if filter_fn(c).get("thesis_match")]


# ---------------------------------------------------------------------------
# Dedup / enrich / tag by source -> one candidate per identity
# ---------------------------------------------------------------------------

def _dedup_by_key(items: list[dict], key: str) -> list[dict]:
    """Guards against the same item appearing twice within a single fetch result (e.g. a
    retried request) inflating that owner's counts. Not about cross-run history -- Memory
    (B's signals table) is explicitly append-only across runs by design; this is just
    protecting the in-memory aggregation for one pass from a duplicated row."""
    seen = set()
    deduped = []
    for item in items:
        if item[key] in seen:
            continue
        seen.add(item[key])
        deduped.append(item)
    return deduped


def _github_signals_for_owner(owner_key: str, repos: list[dict]) -> GithubSignals:
    owner_repos = [r for r in repos if r["owner"].casefold() == owner_key]
    if not owner_repos:
        return GithubSignals()
    now = datetime.now(timezone.utc)
    longevity = max(
        (now - datetime.strptime(r["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)).days // 30
        for r in owner_repos
    )
    recently_pushed = sum(
        1
        for r in owner_repos
        if (now - datetime.strptime(r["pushed_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)).days <= 30
    )
    return GithubSignals(
        repos=len(owner_repos),
        commit_consistency_score=round(recently_pushed / len(owner_repos), 2),
        longevity_months=longevity,
    )


def build_candidate_pool(github_repos: list[dict], hn_posts: list[dict], arxiv_papers: list[dict]) -> list[dict]:
    """Dedup/enrich/tag by source (CLAUDE.md item 3): merges the three bounded feeds into
    one candidate per identity, tagged with which sources contributed.

    Identity matching is case-insensitive (GitHub/HN handles are effectively
    case-insensitive on the platforms themselves, so "PriyaR" and "priyar" are almost
    certainly the same account) but still exact-match otherwise -- no fuzzy matching. That
    matters most for arXiv: authors are listed as full human names ("Priya Raman"), a
    fundamentally different format from GitHub/HN handles ("priyar"), so those almost never
    collide by string equality. That's intentional: under-merging (missing that two records
    are the same person) is the safe failure mode here, over-merging (fuzzy-combining two
    different people's evidence into one profile) corrupts Memory in a way that's much
    harder to detect and undo later. Cross-referencing arXiv full names against GitHub/HN
    handles for the same real person is a real gap, not solved here -- it needs actual
    identity resolution (e.g. matching against a bio/profile field), not string comparison.

    Only a paper's first and last author are counted as candidates, not every co-author --
    a full author list is not a list of founder candidates, and treating every name as one
    previously inflated a single 20-author paper into 20 candidates from one signal."""
    github_repos = _dedup_by_key(github_repos, "repo_id")
    hn_posts = _dedup_by_key(hn_posts, "hn_id")
    arxiv_papers = _dedup_by_key(arxiv_papers, "arxiv_id")

    canonical: dict[str, str] = {}  # casefolded key -> first-seen original casing
    identities: dict[str, set[str]] = {}

    def _register(raw_identity: str, source: str) -> None:
        key = raw_identity.casefold()
        canonical.setdefault(key, raw_identity)
        identities.setdefault(key, set()).add(source)

    for repo in github_repos:
        _register(repo["owner"], "github")
    for post in hn_posts:
        if post.get("author"):
            _register(post["author"], "devpost_hn")
    for paper in arxiv_papers:
        lead_authors = {paper["authors"][0], paper["authors"][-1]} if paper["authors"] else set()
        for author in lead_authors:
            _register(author, "arxiv")

    candidates = []
    for key, sources in identities.items():
        identity = canonical[key]
        hn_for_identity = [p for p in hn_posts if (p.get("author") or "").casefold() == key]
        arxiv_for_identity = [
            p for p in arxiv_papers if p["authors"] and key in {p["authors"][0].casefold(), p["authors"][-1].casefold()}
        ]

        public_signals = PublicSignals(
            github=_github_signals_for_owner(key, github_repos),
            devpost_hn=DevpostHnSignals(
                launches=len(hn_for_identity),
                total_upvotes=sum(p["points"] for p in hn_for_identity),
            ),
            arxiv=ArxivSignals(papers=len(arxiv_for_identity)),
        )
        candidates.append({"identity": identity, "sources": sorted(sources), "public_signals": public_signals})
    return candidates


def assemble_outbound_signal_intake_output(candidate: dict) -> SignalIntakeOutput:
    """Wraps an outbound candidate into the real SignalIntakeOutput contract shape --
    unified with deck_parser.assemble_signal_intake_output's inbound path, instead of
    outbound candidates living in a separate ad-hoc dict shape indefinitely.

    company_id uses a clearly-documented placeholder convention: f"pending_{identity}".
    company_id is required and non-optional in the locked contract, and no company is
    known yet pre-conversion (this is a person, not a company, until they respond) -- so
    *something* honest has to go there. "pending_" makes it unambiguous to any downstream
    reader that this isn't a real company_id, and keeping the identity in it keeps each
    placeholder unique (no collisions in Memory/founders-table keying). Once a candidate
    converts (applies with a deck, names their company), whatever assembles the real
    opportunity record should replace this with a real company_id -- that promotion step
    doesn't live here."""
    return SignalIntakeOutput(
        founder_id=candidate["identity"],
        company_id=f"pending_{candidate['identity']}",
        deck_claims=[],
        public_signals=candidate["public_signals"],
        sourcing_channel="outbound",
        cold_start_flag=True,
    )


# ---------------------------------------------------------------------------
# Partial Founder Score -- rule-based structural signals, plus a qualitative
# founder-intent check (Tavily) inverse-weighted against how much structural data exists
# ---------------------------------------------------------------------------

QUALITATIVE_MAX_BONUS = 10  # points, out of the 0-50 partial scale

_FOUNDER_INTENT_JSON_SCHEMA = {
    "name": "founder_intent_classification",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "is_founder_intent": {"type": "boolean"},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        },
        "required": ["is_founder_intent", "confidence"],
        "additionalProperties": False,
    },
}
_CONFIDENCE_TO_STRENGTH = {"high": 1.0, "medium": 0.6, "low": 0.3}

_CLASSIFY_INSTRUCTIONS = """You are checking whether a short web snippet indicates that a specific \
person is genuinely founding or building their own startup right now -- not merely mentioned near \
words like "founder" or "co-founder" in an unrelated or negating context (e.g. "he didn't have a \
co-founder", an article about founders in general that isn't about this person, a job posting \
mentioning "CEO", or incidental usage). Only classify is_founder_intent=true if the snippet is \
genuinely about this specific person actively founding or building something themselves."""


def _classify_founder_intent(identity: str, snippet: str, client: OpenAI | None = None) -> dict:
    """LLM classification of one search snippet -- replaces naive keyword matching, which
    produced a real false positive in live testing (matched "co-founder" inside "he didn't
    have a co-founder"). Short, single-snippet prompt to keep the added cost as small as
    possible while still catching negation/irrelevant-context cases keyword matching
    can't -- accuracy prioritized over the extra per-candidate cost, per explicit
    direction."""
    client = client or OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": f"{_CLASSIFY_INSTRUCTIONS}\n\nPerson: {identity}\nSnippet: {snippet}"}],
        response_format={"type": "json_schema", "json_schema": _FOUNDER_INTENT_JSON_SCHEMA},
    )
    payload = json.loads(response.choices[0].message.content)
    if not payload["is_founder_intent"]:
        return {"matched": False, "signal_strength": 0.0}
    return {"matched": True, "signal_strength": _CONFIDENCE_TO_STRENGTH[payload["confidence"]]}


def search_founder_intent(identity: str, client: OpenAI | None = None) -> dict:
    """Qualitative founder-intent check via Tavily -- general web search, not a LinkedIn
    integration: LinkedIn's login wall means it rarely surfaces full profile content, this
    does better on personal sites/Twitter/press. Each returned snippet is classified by a
    short LLM call (see _classify_founder_intent), stopping at the first genuine match, in
    Tavily's relevance order. Returns signal_strength on 0.0-1.0 (not a hard boolean) so
    the caller can weight it rather than treat one hit as certain.

    Gated at the call site to run for every post-Thesis-filter candidate, not gated behind
    a structural-score floor -- a candidate with near-zero GitHub/HN/arXiv signal is
    exactly the case this is meant to catch, so filtering on structural strength first
    would exclude the population it exists for."""
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return {"signal_strength": 0.0, "evidence": None, "source_url": None}

    tavily_client = TavilyClient(api_key=api_key)
    response = tavily_client.search(f"{identity} startup founder building", max_results=3)

    for result in response.get("results", []):
        content = result.get("content", "")
        if not content:
            continue
        classification = _classify_founder_intent(identity, content, client=client)
        if classification["matched"]:
            return {
                "signal_strength": classification["signal_strength"],
                "evidence": content[:280],
                "source_url": result.get("url"),
            }
    return {"signal_strength": 0.0, "evidence": None, "source_url": None}


def _track_record_subscore(github: GithubSignals) -> float:
    repo_component = min(github.repos, 10) / 10 * 40
    longevity_component = min(github.longevity_months, 36) / 36 * 30
    consistency_component = github.commit_consistency_score * 30
    return repo_component + longevity_component + consistency_component


def _traction_subscore(devpost_hn: DevpostHnSignals, arxiv: ArxivSignals) -> float:
    launch_component = min(devpost_hn.launches, 5) / 5 * 40
    upvote_component = min(devpost_hn.total_upvotes, 500) / 500 * 40
    paper_component = min(arxiv.papers, 3) / 3 * 20
    return launch_component + upvote_component + paper_component


def _qualitative_bonus(structural_value: float, qualitative_signal: dict) -> float:
    """Inverse-weighted: the thinner the structural (hard-data) signal already is, the
    more a qualitative founder-intent hit can contribute -- so it can carry a near-empty
    profile toward Activate on its own, while adding little on top of an already-strong
    structural profile (where it'd just be redundant corroboration)."""
    structural_strength = min(structural_value / 50, 1.0)
    qualitative_weight = 1.0 - structural_strength
    return round(qualitative_signal["signal_strength"] * qualitative_weight * QUALITATIVE_MAX_BONUS, 1)


def compute_partial_founder_score(public_signals: PublicSignals, qualitative_signal: dict | None = None) -> dict:
    """Track Record (0.30) + Traction Signal (0.20) from structural public signals -- the
    other two components of the locked Founder Score formula (Founder-Market Fit,
    Resilience/Coachability) need deck/interview data outbound candidates don't have yet.
    Reported on the true 0-50 partial scale (0.30 + 0.20 weight budget) rather than
    rescaled to 0-100, so it never reads as more complete than it is. This is an internal
    gating value only -- it is not the published Multi-Axis Scorer founder_score contract
    shape.

    qualitative_signal (from search_founder_intent) is optional and additive, capped so
    the total never exceeds the 0-50 scale -- see _qualitative_bonus for the weighting."""
    track_record = _track_record_subscore(public_signals.github)
    traction = _traction_subscore(public_signals.devpost_hn, public_signals.arxiv)
    structural_value = round(0.30 * track_record + 0.20 * traction, 1)

    bonus = _qualitative_bonus(structural_value, qualitative_signal) if qualitative_signal else 0.0

    return {
        "value": min(round(structural_value + bonus, 1), 50),
        "max_possible": 50,
        "trend": "new",
        "qualitative_bonus_applied": bonus,
    }


def should_activate(partial_score: dict, threshold: float = ACTIVATION_THRESHOLD) -> bool:
    return partial_score["value"] >= threshold


# ---------------------------------------------------------------------------
# Activate: cold outreach for candidates that cross the threshold
# ---------------------------------------------------------------------------

def _resolve_email_from_commits(identity: str, repo_sample_limit: int = 3, commits_per_repo: int = 5) -> str | None:
    """Fallback #2: Git embeds the author's email in every commit even when the GitHub
    profile email is private. Checks a small bounded sample of the identity's most
    recently pushed public repos -- never their full history."""
    repos_resp = requests.get(
        f"{_GITHUB_API}/users/{identity}/repos",
        params={"sort": "pushed", "per_page": repo_sample_limit},
        timeout=10,
    )
    if repos_resp.status_code != 200:
        return None

    for repo in repos_resp.json()[:repo_sample_limit]:
        commits_resp = requests.get(
            f"{_GITHUB_API}/repos/{identity}/{repo['name']}/commits",
            params={"author": identity, "per_page": commits_per_repo},
            timeout=10,
        )
        if commits_resp.status_code != 200:
            continue
        for commit in commits_resp.json():
            email = commit.get("commit", {}).get("author", {}).get("email")
            if email and not _GITHUB_NOREPLY_RE.match(email):
                return email
    return None


def _resolve_contact_via_tavily(identity: str) -> dict | None:
    """Fallback #3, last resort: Tavily is already provisioned in the contract for
    cold-start public-footprint checks. One bounded search, no LLM call involved --
    regex-scans the returned snippets for an email; if none, falls back to the top
    result's URL as a manual-follow-up contact (e.g. a personal site or social profile)."""
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return None

    client = TavilyClient(api_key=api_key)
    response = client.search(f"{identity} github contact email personal site", max_results=3)
    results = response.get("results", [])

    for result in results:
        match = _EMAIL_RE.search(result.get("content", ""))
        if match:
            return {"channel": "email", "value": match.group(0), "source": "tavily"}

    if results:
        return {"channel": "social", "value": results[0]["url"], "source": "tavily"}
    return None


def resolve_contact_email(identity: str) -> dict:
    """Only called for candidates that already crossed the Activate threshold -- a
    handful of calls, not run across the whole pool. Tries, in order: public GitHub
    profile email -> Git commit author email (bounded sample) -> Tavily footprint search.
    Never fabricates an address -- returns channel "none" if nothing is found.
    Returns {"channel": "email"|"social"|"none", "value": str|None, "source": str|None}."""
    resp = requests.get(f"{_GITHUB_API}/users/{identity}", timeout=10)
    if resp.status_code == 200:
        profile_email = resp.json().get("email")
        if profile_email:
            return {"channel": "email", "value": profile_email, "source": "github_profile"}

    commit_email = _resolve_email_from_commits(identity)
    if commit_email:
        return {"channel": "email", "value": commit_email, "source": "github_commit"}

    tavily_contact = _resolve_contact_via_tavily(identity)
    if tavily_contact:
        return tavily_contact

    return {"channel": "none", "value": None, "source": None}


# CAN-SPAM baseline for unsolicited commercial email: a physical mailing address is
# legally required in the body, not optional polish. The opt-out mechanism is now a real,
# working unsubscribe link (see draft_activation_email) instead of a static line, so only
# the address remains a placeholder.
# DEMO VALUE -- not a real registered fund address. Fine for proving the send mechanism
# works in a demo; must be replaced with the fund's real legal name/address before this
# is ever used for actual outreach beyond a demo.
_MAILING_ADDRESS_LINE = "FounderScore Fund (Demo) — 123 Demo St, Demo City, ST 00000"


# Frontend/backend base URLs for the two links every outreach email carries. Localhost
# defaults match local dev; override via env for a real deployment.
APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:5173")
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")


def draft_activation_email(candidate: dict, to_email: str) -> dict:
    """Template-based, no LLM call -- keeps this step at zero marginal API cost so it can
    run on every activated candidate without adding to the money/token budget.

    Carries two trackable, per-candidate links, both keyed by the candidate's identity
    (their founder_id, per assemble_outbound_signal_intake_output):
    - Apply link (?ref=<founder_id>) -- lets a real submission through /applications link
      back to this candidate's existing outbound Memory history instead of becoming a
      disconnected new founder_id. This is the actual outbound-to-inbound convergence
      mechanism, not just a courtesy link.
    - Unsubscribe link -- backend records the decline (see main.py's
      /outbound/unsubscribe/{founder_id}) so outreach status reflects it."""
    identity = candidate["identity"]
    sources = ", ".join(candidate["sources"])
    signals = candidate["public_signals"]
    highlights = []
    if signals.github.repos:
        highlights.append(f"{signals.github.repos} active repo(s) on GitHub")
    if signals.devpost_hn.launches:
        highlights.append(
            f"{signals.devpost_hn.launches} Show HN launch(es), {signals.devpost_hn.total_upvotes} upvotes"
        )
    if signals.arxiv.papers:
        highlights.append(f"{signals.arxiv.papers} recent arXiv paper(s)")

    apply_link = f"{APP_BASE_URL}/apply?ref={identity}"
    unsubscribe_link = f"{API_BASE_URL}/outbound/unsubscribe/{identity}"

    subject = f"Came across your work on {sources} — quick intro?"
    body = (
        f"Hi {identity},\n\n"
        f"I came across your work via {sources} and wanted to reach out directly — "
        f"{'; '.join(highlights) if highlights else 'your public activity caught our attention'}.\n\n"
        "We're an early-stage fund and would love to hear more about what you're building. "
        f"If you'd like to share more (deck, details), you can apply directly here: {apply_link}\n\n"
        "Best,\nFounderScore\n\n"
        f"--\n{_MAILING_ADDRESS_LINE}\n"
        f"Don't want to hear from us? Unsubscribe: {unsubscribe_link}"
    )
    return {"to": to_email, "subject": subject, "body": body}


def send_activation_email(email: dict) -> dict:
    """Until EMAIL_SMTP_HOST is set, this logs a dry run to activation_outbox.jsonl
    instead of dispatching anything. Once set (see backend/signal_intake/.env), this
    dispatches for real via _send_via_smtp -- draft_activation_email's body includes a demo
    mailing address (_MAILING_ADDRESS_LINE); replace it with the fund's real legal address
    before this is used for anything beyond a demo."""
    if not os.environ.get("EMAIL_SMTP_HOST"):
        record = {**email, "status": "dry_run_logged", "logged_at": datetime.now(timezone.utc).isoformat()}
        with open(OUTBOX_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        return record
    return _send_via_smtp(email)


def _send_via_smtp(email: dict) -> dict:
    import smtplib
    from email.mime.text import MIMEText

    msg = MIMEText(email["body"])
    msg["Subject"] = email["subject"]
    msg["From"] = os.environ["EMAIL_FROM"]
    msg["To"] = email["to"]

    with smtplib.SMTP(os.environ["EMAIL_SMTP_HOST"], int(os.environ.get("EMAIL_SMTP_PORT", 587))) as server:
        server.starttls()
        server.login(os.environ["EMAIL_FROM"], os.environ["EMAIL_SMTP_PASSWORD"])
        server.send_message(msg)
    return {**email, "status": "sent", "sent_at": datetime.now(timezone.utc).isoformat()}


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def _record_signal_intake_in_memory(output: SignalIntakeOutput) -> None:
    """Persist via B's shared Memory layer (backend/api/db.py) -- unified with
    deck_parser.record_deck_claims_in_memory: both the inbound and outbound paths now
    persist through the same SignalIntakeOutput shape instead of two different
    representations. Memory accumulates evidence from minute one, before conversion, per
    the contract's Memory layer description ("structured knowledge base ... timestamped,
    deduplicated, source-tagged, persistent") -- outbound candidates don't wait until they
    have a real company_id to start being recorded.

    Lazy-imported, same reasoning as deck_parser.record_deck_claims_in_memory: keeps this
    module importable and its own tests runnable whether or not db.py exists yet on the
    branch being run.

    db.py's save_signal() reads company_id/cold_start_flag from each individual payload
    (it upserts the founders row on every call, not just once), so those two fields are
    included in every payload here -- passing only the bare sub-signal dict would silently
    drop them (verified live: they came back as None/False until this was added)."""
    from backend.api.db import recompute_founder_score, save_signal

    identity_fields = {"company_id": output.company_id, "cold_start_flag": output.cold_start_flag}
    signals = output.public_signals
    if signals.github.repos:
        save_signal(output.founder_id, "github", {**signals.github.model_dump(), **identity_fields})
    if signals.devpost_hn.launches:
        save_signal(output.founder_id, "devpost_hn", {**signals.devpost_hn.model_dump(), **identity_fields})
    if signals.arxiv.papers:
        save_signal(output.founder_id, "arxiv", {**signals.arxiv.model_dump(), **identity_fields})
    recompute_founder_score(output.founder_id)


def _log_outreach_sent(output: SignalIntakeOutput) -> None:
    """Records the 'sent' outreach lifecycle event via B's Memory layer (see
    backend/api/db.py's save_outreach_event/get_outreach_status) -- this is what lets the
    frontend show outbound status (delivered/declined/converted) instead of outreach being
    invisible once the email leaves. Lazy-imported for the same reason as every other
    backend.api.db call in this module."""
    from backend.api.db import save_outreach_event

    save_outreach_event(
        output.founder_id, "sent", company_id=output.company_id, cold_start_flag=output.cold_start_flag
    )


def run_outbound_pass(thesis_filter_fn=None) -> list[dict]:
    """End-to-end scaffold: fetch (bounded) -> dedup/tag -> Thesis filter -> assemble the
    real SignalIntakeOutput -> qualitative founder-intent search + partial score ->
    Activate above threshold -> draft + (dry-run) send. Returns one summary dict per
    candidate in the post-filter pool, each carrying its unified "signal_intake_output"
    (see assemble_outbound_signal_intake_output) -- outbound candidates are no longer a
    separate ad-hoc shape from the inbound deck path, both produce the same contract
    object. Every post-filter candidate is written to Memory (see
    _record_signal_intake_in_memory) regardless of whether they're activated -- the
    filtered pool is the evidence worth keeping, Activate is a separate downstream
    decision on top of it.

    The qualitative Tavily search runs for every candidate that survives dedup + the
    Thesis filter -- gated on pool membership, not on structural score, since gating on
    structural strength would exclude exactly the near-zero-hard-data candidates the
    qualitative check exists to catch. Cost is bounded by dedup + the Thesis filter
    already shrinking the pool, not by a second filter on top."""
    github_repos = fetch_github_trending()
    # Product Hunt shares the contract's single devpost_hn bucket with Show HN (see
    # fetch_product_hunt_recent's docstring) -- combined here, not a separate pool.
    # Returns [] on its own if PRODUCT_HUNT_API_TOKEN isn't configured.
    hn_posts = fetch_show_hn() + fetch_product_hunt_recent()
    arxiv_papers = fetch_arxiv_recent()

    candidates = build_candidate_pool(github_repos, hn_posts, arxiv_papers)
    candidates = apply_thesis_filter(candidates, thesis_filter_fn)

    results = []
    for candidate in candidates:
        signal_output = assemble_outbound_signal_intake_output(candidate)
        _record_signal_intake_in_memory(signal_output)
        qualitative_signal = search_founder_intent(candidate["identity"])
        partial_score = compute_partial_founder_score(candidate["public_signals"], qualitative_signal)
        activated = should_activate(partial_score)
        outreach = None

        if activated:
            contact = resolve_contact_email(candidate["identity"])
            if contact["channel"] == "email":
                email = draft_activation_email(candidate, contact["value"])
                outreach = send_activation_email(email)
                outreach["contact_source"] = contact["source"]
                _log_outreach_sent(signal_output)
            elif contact["channel"] == "social":
                outreach = {
                    "status": "manual_followup_needed",
                    "contact_url": contact["value"],
                    "source": contact["source"],
                }
            else:
                outreach = {"status": "no_public_contact_found"}

        results.append(
            {
                "signal_intake_output": signal_output,
                "sources": candidate["sources"],
                "qualitative_signal": qualitative_signal,
                "partial_score": partial_score,
                "activated": activated,
                "outreach": outreach,
            }
        )
    return results


if __name__ == "__main__":
    for result in run_outbound_pass():
        print(json.dumps({**result, "signal_intake_output": result["signal_intake_output"].model_dump()}, indent=2))
