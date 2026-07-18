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
from tavily import TavilyClient

from .schemas import ArxivSignals, DevpostHnSignals, GithubSignals, PublicSignals

# Hard caps -- every fetch below is bounded by one of these, never by pagination.
GITHUB_LIMIT = 50
HN_LIMIT = 30
ARXIV_LIMIT = 30

# Internal Activate-gating threshold. NOT part of the published contract shapes -- this
# score only decides whether to cold-outreach a candidate, it never crosses a module
# boundary. Scale is 0-50 (see compute_partial_founder_score's docstring).
ACTIVATION_THRESHOLD = 40

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

def apply_thesis_filter(candidates: list[dict], thesis_filter_fn=None) -> list[dict]:
    """Filter the candidate pool BEFORE scoring, per CLAUDE.md item 2. Swap
    `thesis_filter_fn` for the real Thesis Engine call at a sync point; it must accept a
    candidate dict and return {"thesis_match": bool, ...} per the contract shape."""
    if thesis_filter_fn is None:
        return candidates
    return [c for c in candidates if thesis_filter_fn(c).get("thesis_match")]


# ---------------------------------------------------------------------------
# Dedup / enrich / tag by source -> one candidate per identity
# ---------------------------------------------------------------------------

def _github_signals_for_owner(owner: str, repos: list[dict]) -> GithubSignals:
    owner_repos = [r for r in repos if r["owner"] == owner]
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
    one candidate per identity (GitHub username / HN author / arXiv author-name -- these
    are treated as distinct identity namespaces, so this is a heuristic merge, not a
    verified real-world identity match), tagged with which sources contributed."""
    identities: dict[str, set[str]] = {}

    for repo in github_repos:
        identities.setdefault(repo["owner"], set()).add("github")
    for post in hn_posts:
        if post.get("author"):
            identities.setdefault(post["author"], set()).add("devpost_hn")
    for paper in arxiv_papers:
        for author in paper["authors"]:
            identities.setdefault(author, set()).add("arxiv")

    candidates = []
    for identity, sources in identities.items():
        hn_for_identity = [p for p in hn_posts if p.get("author") == identity]
        arxiv_for_identity = [p for p in arxiv_papers if identity in p["authors"]]

        public_signals = PublicSignals(
            github=_github_signals_for_owner(identity, github_repos),
            devpost_hn=DevpostHnSignals(
                launches=len(hn_for_identity),
                total_upvotes=sum(p["points"] for p in hn_for_identity),
            ),
            arxiv=ArxivSignals(papers=len(arxiv_for_identity)),
        )
        candidates.append({"identity": identity, "sources": sorted(sources), "public_signals": public_signals})
    return candidates


# ---------------------------------------------------------------------------
# Partial Founder Score -- rule-based, public signals only
# ---------------------------------------------------------------------------

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


def compute_partial_founder_score(public_signals: PublicSignals) -> dict:
    """Track Record (0.30) + Traction Signal (0.20) only -- the other two components of
    the locked Founder Score formula (Founder-Market Fit, Resilience/Coachability) need
    deck/interview data outbound candidates don't have yet. Reported on the true 0-50
    partial scale (0.30 + 0.20 weight budget) rather than rescaled to 0-100, so it never
    reads as more complete than it is. This is an internal gating value only -- it is not
    the published Multi-Axis Scorer founder_score contract shape."""
    track_record = _track_record_subscore(public_signals.github)
    traction = _traction_subscore(public_signals.devpost_hn, public_signals.arxiv)
    return {
        "value": round(0.30 * track_record + 0.20 * traction, 1),
        "max_possible": 50,
        "trend": "new",
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


def draft_activation_email(candidate: dict, to_email: str) -> dict:
    """Template-based, no LLM call -- keeps this step at zero marginal API cost so it can
    run on every activated candidate without adding to the money/token budget."""
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

    subject = f"Came across your work on {sources} — quick intro?"
    body = (
        f"Hi {identity},\n\n"
        f"I came across your work via {sources} and wanted to reach out directly — "
        f"{'; '.join(highlights) if highlights else 'your public activity caught our attention'}.\n\n"
        "We're an early-stage fund and would love a short intro call if you're building "
        "something you'd want investor eyes on.\n\n"
        "Best,\nFounderScore"
    )
    return {"to": to_email, "subject": subject, "body": body}


def send_activation_email(email: dict) -> dict:
    """No email-provider credentials exist yet -- the contract's env vars are only
    OPENAI_API_KEY / TAVILY_API_KEY. Sending a real cold email to a real person needs that
    decision made explicitly, not assumed here. Until EMAIL_SMTP_HOST is set, this logs a
    dry run to activation_outbox.jsonl instead of dispatching anything."""
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

def run_outbound_pass(thesis_filter_fn=None) -> list[dict]:
    """End-to-end scaffold: fetch (bounded) -> dedup/tag -> Thesis filter -> partial
    score -> Activate above threshold -> draft + (dry-run) send. Returns one summary dict
    per candidate in the post-filter pool."""
    github_repos = fetch_github_trending()
    hn_posts = fetch_show_hn()
    arxiv_papers = fetch_arxiv_recent()

    candidates = build_candidate_pool(github_repos, hn_posts, arxiv_papers)
    candidates = apply_thesis_filter(candidates, thesis_filter_fn)

    results = []
    for candidate in candidates:
        partial_score = compute_partial_founder_score(candidate["public_signals"])
        activated = should_activate(partial_score)
        outreach = None

        if activated:
            contact = resolve_contact_email(candidate["identity"])
            if contact["channel"] == "email":
                email = draft_activation_email(candidate, contact["value"])
                outreach = send_activation_email(email)
                outreach["contact_source"] = contact["source"]
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
                "identity": candidate["identity"],
                "sources": candidate["sources"],
                "public_signals": candidate["public_signals"],
                "partial_score": partial_score,
                "activated": activated,
                "outreach": outreach,
            }
        )
    return results


if __name__ == "__main__":
    for result in run_outbound_pass():
        print(json.dumps({**result, "public_signals": result["public_signals"].model_dump()}, indent=2))
