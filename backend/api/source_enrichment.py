"""Public-source enrichment for an application.

We deliberately keep this bounded: submitted URLs, one GitHub profile request, one
company-site metadata request, and at most five Tavily results.  The stored record is
structured metadata and a short excerpt, never raw publisher HTML.
"""
from __future__ import annotations

import ipaddress
import os
import re
from datetime import datetime, timezone
from html import unescape
from typing import Any
from urllib.parse import urljoin, urlparse

import requests

from backend.diligence_memo.clients import ExternalServiceError, TavilySearchClient


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def valid_public_url(value: str | None) -> str | None:
    if not value:
        return None
    url = value.strip()
    if not url:
        return None
    if not url.startswith(("https://", "http://")):
        url = f"https://{url}"
    parsed = urlparse(url)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname:
        return None
    hostname = parsed.hostname.lower()
    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".local"):
        return None
    try:
        if ipaddress.ip_address(hostname).is_private or ipaddress.ip_address(hostname).is_loopback:
            return None
    except ValueError:
        pass
    return url


def source_record(*, kind: str, title: str, url: str, excerpt: str = "", image_url: str | None = None, favicon_url: str | None = None, source: str | None = None, page: int | None = None) -> dict[str, Any]:
    return {
        "type": kind,
        "title": title[:300],
        "url": url,
        "excerpt": re.sub(r"\s+", " ", excerpt).strip()[:1200],
        "image_url": image_url,
        "favicon_url": favicon_url,
        "source": source or urlparse(url).hostname or "Submitted source",
        "page": page,
        "retrieved_at": _now(),
    }


def submitted_link_sources(profile: dict[str, Any]) -> list[dict[str, Any]]:
    labels = {
        "website": ("company_website", "Company website"),
        "github": ("github", "GitHub profile"),
        "linkedin": ("linkedin", "LinkedIn profile"),
        "x": ("x", "X profile"),
        "devpost": ("devpost", "Devpost profile"),
        "product_hunt": ("product_hunt", "Product Hunt"),
        "arxiv": ("paper", "arXiv profile"),
    }
    sources = []
    for key, (kind, label) in labels.items():
        url = valid_public_url(profile.get(key))
        if url:
            sources.append(source_record(kind=kind, title=label, url=url, source="Founder-submitted"))
    return sources


def fetch_site_metadata(website: str | None) -> dict[str, Any] | None:
    url = valid_public_url(website)
    if not url:
        return None
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "FounderScore/1.0 (+application source verification)"},
            timeout=8,
            allow_redirects=True,
            stream=True,
        )
        if response.status_code >= 400:
            return None
        body = response.raw.read(750_000, decode_content=True).decode(response.encoding or "utf-8", errors="replace")
    except requests.RequestException:
        return None
    title = _meta_value(body, "og:title") or _tag_text(body, "title") or urlparse(url).hostname
    description = _meta_value(body, "og:description") or _meta_value(body, "description") or ""
    image_url = _meta_value(body, "og:image")
    final_url = response.url
    return source_record(
        kind="company_website",
        title=title,
        url=final_url,
        excerpt=description,
        image_url=valid_public_url(image_url),
        favicon_url=_favicon_url(body, final_url),
        source=urlparse(final_url).hostname,
    )


def github_profile_signal(github_url: str | None) -> tuple[dict[str, Any], dict[str, Any] | None]:
    url = valid_public_url(github_url)
    defaults = {"repos": 0, "commit_consistency_score": 0.0, "longevity_months": 0}
    if not url or "github.com" not in (urlparse(url).hostname or ""):
        return defaults, None
    username = urlparse(url).path.strip("/").split("/", 1)[0]
    if not username:
        return defaults, None
    try:
        response = requests.get(f"https://api.github.com/users/{username}", timeout=8, headers={"Accept": "application/vnd.github+json"})
        if response.status_code >= 400:
            return defaults, None
        data = response.json()
        repos = int(data.get("public_repos") or 0)
        repo_response = requests.get(
            f"https://api.github.com/users/{username}/repos",
            params={"per_page": 100, "sort": "updated"},
            timeout=8,
            headers={"Accept": "application/vnd.github+json"},
        )
        repo_items = repo_response.json() if repo_response.status_code < 400 else []
        created = [_parse_github_time(item.get("created_at")) for item in repo_items]
        pushed = [_parse_github_time(item.get("pushed_at")) for item in repo_items]
        created = [item for item in created if item]
        pushed = [item for item in pushed if item]
        now = datetime.now(timezone.utc)
        longevity = max(((now - item).days // 30 for item in created), default=0)
        recently_active = sum((now - item).days <= 180 for item in pushed)
        consistency = round(recently_active / len(pushed), 2) if pushed else 0.0
        profile = source_record(
            kind="github",
            title=data.get("name") or f"GitHub: @{username}",
            url=url,
            excerpt=data.get("bio") or "Public GitHub profile submitted by founder.",
            image_url=valid_public_url(data.get("avatar_url")),
            source="GitHub",
        )
        return {"repos": repos, "commit_consistency_score": consistency, "longevity_months": longevity}, profile
    except (requests.RequestException, ValueError, TypeError):
        return defaults, None


def enrich_submitted_people(profile: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Enrich only exact LinkedIn URLs a founder explicitly supplied.

    This deliberately does not discover people by name.  A provider response is used
    only after its returned LinkedIn identity matches the submitted `/in/` profile.
    We persist a tiny provider-status marker so repeated analysis does not consume a
    new paid lookup for the same person.
    """
    if not os.getenv("PEOPLE_DATA_LABS_API_KEY"):
        return dict(profile), []

    updated = dict(profile)
    sources: list[dict[str, Any]] = []

    founder_state, founder_source = _pdl_person_enrichment(
        updated.get("linkedin"),
        updated.get("profile_enrichment"),
        updated.get("founder_name"),
    )
    if founder_state:
        updated["profile_enrichment"] = founder_state
        if founder_state.get("image_url"):
            updated["linkedin_avatar_url"] = founder_state["image_url"]
    if founder_source:
        sources.append(founder_source)

    members = []
    for member in updated.get("team_members") or []:
        if not isinstance(member, dict):
            continue
        item = dict(member)
        state, source = _pdl_person_enrichment(item.get("linkedin"), item.get("profile_enrichment"), item.get("name"))
        if state:
            item["profile_enrichment"] = state
            if state.get("image_url"):
                item["linkedin_avatar_url"] = state["image_url"]
        if source:
            sources.append(source)
        members.append(item)
    if members:
        updated["team_members"] = members
    return updated, sources


def _pdl_person_enrichment(
    linkedin_url: str | None, previous: Any, submitted_name: str | None
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Use People Data Labs as an optional, exact-profile provider.

    The provider's API accepts a LinkedIn profile URL.  It is intentionally optional:
    applications still process normally with no key, an unavailable provider, or no
    matching record.  We retain only presentation metadata, never PDL's full record.
    """
    submitted = _linkedin_identity(linkedin_url)
    if not submitted:
        return None, None
    if isinstance(previous, dict) and previous.get("provider") == "people_data_labs":
        return previous, None
    api_key = os.getenv("PEOPLE_DATA_LABS_API_KEY")
    if not api_key:
        return None, None
    try:
        response = requests.get(
            "https://api.peopledatalabs.com/v5/person/enrich",
            headers={"X-Api-Key": api_key},
            params={"profile": valid_public_url(linkedin_url), "min_likelihood": 10},
            timeout=10,
        )
        payload = response.json()
    except (requests.RequestException, ValueError, TypeError):
        return None, None

    if response.status_code != 200 or not isinstance(payload, dict) or payload.get("status") != 200:
        # Cache only a completed no-match; transient provider failures should be
        # eligible for a later retry.
        if response.status_code == 404:
            return {"provider": "people_data_labs", "status": "not_found", "checked_at": _now()}, None
        return None, None
    data = payload.get("data") or {}
    returned = _linkedin_identity(data.get("linkedin_url")) or _linkedin_profile_from_list(data.get("profiles"))
    if returned != submitted:
        return {"provider": "people_data_labs", "status": "identity_mismatch", "checked_at": _now()}, None
    image_url = valid_public_url(data.get("image"))
    state = {
        "provider": "people_data_labs",
        "status": "matched",
        "checked_at": _now(),
        "image_url": image_url,
        "headline": str(data.get("headline") or "")[:280],
        "job_title": str(data.get("job_title") or "")[:160],
        "job_company_name": str(data.get("job_company_name") or "")[:160],
    }
    display_name = str(data.get("full_name") or submitted_name or "Founder").strip()
    return state, source_record(
        kind="profile_enrichment",
        title=f"{display_name} · profile enrichment",
        url=valid_public_url(linkedin_url) or linkedin_url or "",
        excerpt="Exact founder-submitted LinkedIn URL matched through People Data Labs.",
        image_url=image_url,
        source="People Data Labs · exact submitted profile",
    )


def _linkedin_identity(value: Any) -> str | None:
    url = valid_public_url(value if isinstance(value, str) else None)
    if not url:
        return None
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    match = re.match(r"^/in/([^/?#]+)/?", parsed.path, re.I)
    if not (host == "linkedin.com" or host.endswith(".linkedin.com")) or not match:
        return None
    return match.group(1).casefold()


def _linkedin_profile_from_list(profiles: Any) -> str | None:
    if not isinstance(profiles, list):
        return None
    for item in profiles:
        if not isinstance(item, dict) or str(item.get("network") or "").casefold() != "linkedin":
            continue
        identity = _linkedin_identity(item.get("url"))
        if identity:
            return identity
    return None


def search_press(company_name: str, website: str | None = None, max_results: int = 5) -> list[dict[str, Any]]:
    """Return only company-specific coverage, never generic startup-news roundups."""
    company = company_name.strip().casefold()
    domain = (urlparse(valid_public_url(website) or "").hostname or "").casefold()
    try:
        query = f'"{company_name}" (health OR product OR launch OR app OR funding)'
        if domain:
            query = f'{query} OR site:{domain}'
        results = TavilySearchClient().search(query, max_results=max_results * 2)
    except ExternalServiceError:
        return []
    filtered = []
    for item in results:
        haystack = f"{item.title} {item.content} {item.url}".casefold()
        result_domain = (urlparse(item.url).hostname or "").casefold()
        if company not in haystack and (not domain or not result_domain.endswith(domain)):
            continue
        filtered.append(source_record(kind="news", title=item.title, url=item.url, excerpt=item.content, source=result_domain))
        if len(filtered) >= max_results:
            break
    return filtered


def _parse_github_time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _meta_value(html: str, name: str) -> str | None:
    match = re.search(rf'<meta[^>]+(?:property|name)=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)', html, re.IGNORECASE)
    if not match:
        match = re.search(rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']{re.escape(name)}["\']', html, re.IGNORECASE)
    return unescape(match.group(1)).strip() if match else None


def _tag_text(html: str, tag: str) -> str | None:
    match = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", html, re.IGNORECASE | re.DOTALL)
    return unescape(re.sub(r"<[^>]+>", "", match.group(1))).strip() if match else None


def _favicon_url(html: str, page_url: str) -> str | None:
    """Resolve the site's own icon for a compact, non-invented company mark."""
    match = re.search(
        r'<link[^>]+rel=["\'][^"\']*(?:icon|shortcut icon)[^"\']*["\'][^>]+href=["\']([^"\']+)',
        html,
        re.IGNORECASE,
    )
    if not match:
        match = re.search(
            r'<link[^>]+href=["\']([^"\']+)["\'][^>]+rel=["\'][^"\']*(?:icon|shortcut icon)[^"\']*["\']',
            html,
            re.IGNORECASE,
        )
    return valid_public_url(urljoin(page_url, match.group(1))) if match else valid_public_url(urljoin(page_url, "/favicon.ico"))
