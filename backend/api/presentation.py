"""Grounded investor presentation fields derived from persisted deck claims.

These fields are intentionally separate from the locked agent outputs.  They select
representative, source-backed claims for a concise UI rather than letting the final
claim on a long deck overwrite the company summary.
"""
from __future__ import annotations

import re
from typing import Any


_PROJECTED = re.compile(r"\b(plan|planned|project|target|estimate|recommend|will|future|roadmap)\w*\b", re.I)
_ACTIVE = re.compile(r"\b(live|launched|app store|won|winner|beta|pilot|revenue|paying|grant|accepted)\b", re.I)


def build_enrichment(
    profile: dict[str, Any], signal: dict[str, Any], sources: list[dict[str, Any]], trace: list[dict[str, Any]]
) -> dict[str, Any]:
    claims = list(signal.get("deck_claims") or [])
    company = str(profile.get("company_name") or "Company")
    product_claims = _claims_for(claims, "problem_product")
    market_claims = _claims_for(claims, "market_size")
    traction_claims = _claims_for(claims, "traction")
    team_claims = _claims_for(claims, "team")

    solution = _choose_solution(product_claims, company)
    problem = _choose_problem(product_claims)
    traction_note = _traction_note(traction_claims)
    team = _team_members(profile, team_claims, sources)
    market = _market_from_claims(market_claims)
    return {
        "one_liner": solution,
        "problem": problem,
        "solution": solution,
        "sector": profile.get("sector") or "Not disclosed",
        "stage": profile.get("stage") or "Not disclosed",
        "geography": profile.get("geography") or "Not disclosed",
        "website": profile.get("website") or _website_from_sources(sources),
        "founders": team,
        "market": market,
        "pmf": {"signal": "early", "note": traction_note},
        "agent_trace": trace,
    }


def relevant_sources(company_name: str, sources: list[dict[str, Any]], website: str | None = None) -> list[dict[str, Any]]:
    """Keep submitted/deck sources and discard generic search noise from the investor UI."""
    company = company_name.casefold().strip()
    domain = re.sub(r"^www\.", "", re.sub(r"^https?://", "", website or "")).split("/", 1)[0]
    filtered = []
    for source in sources:
        if source.get("type") != "news":
            filtered.append(source)
            continue
        haystack = f"{source.get('title', '')} {source.get('excerpt', '')} {source.get('url', '')}".casefold()
        if company in haystack or (domain and domain in haystack):
            filtered.append(source)
    return filtered


def concise_memo(
    company_name: str, enrichment: dict[str, Any], analysis: dict[str, Any]
) -> dict[str, Any]:
    """Present a short decision memo while retaining detailed evidence separately."""
    existing = analysis["diligence_memo"]["memo"]
    flags = analysis["diligence_memo"]["diligence"].get("flagged_claims", [])
    unique_flags = list(dict.fromkeys(item.get("claim", "claim") for item in flags))
    strengths = []
    if re.search(r"\b(live|app store|won|winner|beta|grant)\b", enrichment["pmf"]["note"], re.I):
        strengths.append("Founder-reported product launch or execution milestone")
    if enrichment["founders"]:
        strengths.append("Named founding team is disclosed in the deck")
    weaknesses = [f"Unresolved {name.replace('_', ' ')} evidence gap" for name in unique_flags]
    if "No reported active-user" in enrichment["pmf"]["note"]:
        weaknesses.append("No active-user, retention, or paid-revenue evidence disclosed")
    market_basis = (enrichment.get("market") or {}).get("basis") or "Market sizing was not clearly disclosed."
    hypotheses = [
        f"{company_name} may solve the stated patient problem if its predictive workflow produces measurable outcomes.",
        "The investment case depends on independently validating usage, clinical workflow adoption, and the stated commercial model.",
    ]
    if unique_flags:
        hypotheses.append("Resolve the flagged quantitative assumptions before underwriting a check.")
    return {
        "required": {
            "company_snapshot": f"{company_name}: {enrichment['one_liner']}",
            "investment_hypotheses": hypotheses,
            "swot": {
                "strengths": strengths or ["Founder-submitted product thesis"],
                "weaknesses": weaknesses or ["Independent evidence remains limited"],
                "opportunities": [market_basis],
                "threats": ["Execution, adoption, and reimbursement assumptions require validation"],
            },
            "problem_and_product": f"Problem: {enrichment['problem']} Solution: {enrichment['solution']}",
            "traction_kpis": enrichment["pmf"]["note"],
        },
        "optional_or_flagged": {
            "team_and_history": _team_history(enrichment["founders"]),
            "cap_table": existing["optional_or_flagged"].get("cap_table", "Not disclosed"),
        },
    }


def _claims_for(claims: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    return [claim for claim in claims if claim.get("field") == field and claim.get("value")]


def _choose_solution(claims: list[dict[str, Any]], company: str) -> str:
    if not claims:
        return "Product description not disclosed."
    company_match = [claim for claim in claims if company.casefold() in claim["value"].casefold()]
    candidates = company_match or claims
    candidates.sort(key=lambda claim: (claim.get("source_slide", 0), len(claim["value"])))
    return candidates[0]["value"]


def _choose_problem(claims: list[dict[str, Any]]) -> str:
    if not claims:
        return "Customer problem not disclosed."
    ranked = sorted(
        claims,
        key=lambda claim: (
            0 if re.search(r"\b(reactive|struggle|unpredictable|problem|cannot|can.t)\b", claim["value"], re.I) else 1,
            claim.get("source_slide", 0),
        ),
    )
    return ranked[0]["value"]


def _traction_note(claims: list[dict[str, Any]]) -> str:
    observed = [claim["value"] for claim in claims if _ACTIVE.search(claim["value"]) and not _PROJECTED.search(claim["value"])]
    if observed:
        return f"Founder-reported: {observed[0]} Independent active-user, retention, and paid-revenue evidence is not yet disclosed."
    return "No independently verifiable active-user, retention, or paid-revenue evidence is disclosed; deck projections are not treated as traction."


def _team_members(profile: dict[str, Any], claims: list[dict[str, Any]], sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    team_text = claims[0]["value"] if claims else ""
    entries = re.findall(r"([^,:]+?)\s*\(([^)]+)\)", team_text)
    if not entries:
        entries = [(profile.get("founder_name") or "Founder", profile.get("founder_role") or "Founder")]
    avatar = next((source.get("image_url") for source in sources if source.get("type") == "github" and source.get("image_url")), profile.get("photo_url"))
    members = []
    for index, (name, role) in enumerate(entries):
        cleaned_name = re.sub(r"^Team:\s*", "", name).strip()
        is_submitter = cleaned_name.casefold() in str(profile.get("founder_name", "")).casefold() or index == 0
        members.append({
            "name": profile.get("founder_name") if is_submitter else cleaned_name,
            "role": profile.get("founder_role") if is_submitter else role.strip(),
            "avatar": avatar if is_submitter else None,
            "background": "Listed in the uploaded deck." if not is_submitter else (team_text or "Listed in the uploaded deck."),
            "linkedin": profile.get("linkedin") if is_submitter else None,
            "github": profile.get("github") if is_submitter else None,
            "x": profile.get("x") if is_submitter else None,
            "ai_read": "Founder-submitted profile link and deck identity." if is_submitter else "Deck-listed team member; no public profile was supplied for identity matching.",
        })
    return members


def _team_history(members: list[dict[str, Any]]) -> str:
    return "; ".join(f"{member['name']} ({member['role']})" for member in members) or "Not disclosed"


def _website_from_sources(sources: list[dict[str, Any]]) -> str | None:
    for source in sources:
        excerpt = str(source.get("excerpt") or "")
        match = re.search(r"\b(?:website (?:is|at) |visit )((?:https?://)?(?:www\.)?[a-z0-9-]+\.[a-z]{2,}(?:/[^\s.,)]*)?)", excerpt, re.I)
        if not match:
            continue
        url = match.group(1).rstrip(".")
        return url if url.startswith("http") else f"https://{url}"
    return None


def _market_from_claims(claims: list[dict[str, Any]]) -> dict[str, Any] | None:
    values: dict[str, tuple[float, str, str, int]] = {}
    for claim in claims:
        text = claim["value"]
        label_match = re.search(r"\b(TAM|SAM|SOM)\b", text, re.I)
        amount_match = re.search(r"\$\s*([\d.]+)\s*(B|M|K)\b", text, re.I)
        if not label_match or not amount_match:
            continue
        label = label_match.group(1).casefold()
        amount = float(amount_match.group(1))
        unit = amount_match.group(2).upper()
        millions = amount * {"B": 1000, "M": 1, "K": 0.001}[unit]
        values[label] = (millions, f"${amount:g}{unit}", text, int(claim.get("source_slide", 0)))
    if not {"tam", "sam", "som"}.issubset(values):
        basis = claims[-1]["value"] if claims else ""
        return {"basis": basis} if basis else None
    return {
        "tam": values["tam"][0], "sam": values["sam"][0], "som": values["som"][0],
        "unit": "$M", "display": {"tam": values["tam"][1], "sam": values["sam"][1], "som": values["som"][1]},
        "basis": f"Deck slide {values['tam'][3]}: {values['tam'][2]} Deck slide {values['sam'][3]}: {values['sam'][2]} Deck slide {values['som'][3]}: {values['som'][2]}",
    }
