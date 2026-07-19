"""Deck parsing: LLM extraction of structured deck_claims from a pitch deck.

Scope (see /backend/signal_intake/CLAUDE.md item 1): take an uploaded pitch deck
(text or PDF for now) and produce deck_claims exactly matching the contract shape,
each claim tagged with field, value, and source_slide.

This module only produces deck_claims. public_signals is populated by the outbound
scanning module (item 2 in CLAUDE.md); assemble_signal_intake_output() below fills it
with the contract's zeroed default until that module writes real values.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from openai import OpenAI
from pydantic import ValidationError

from .schemas import DeckClaim, PublicSignals, SignalIntakeOutput

MODEL = "gpt-5.5-2026-04-23"

_SLIDE_MARKER_RE = re.compile(r"^===\s*SLIDE\s+(\d+)\s*:?[^=]*===\s*$", re.IGNORECASE | re.MULTILINE)

_CLAIMS_JSON_SCHEMA = {
    "name": "deck_claims",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "deck_claims": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "field": {
                            "type": "string",
                            "enum": ["market_size", "traction", "team", "ask", "problem_product"],
                        },
                        "value": {"type": "string"},
                        "source_slide": {"type": "integer"},
                    },
                    "required": ["field", "value", "source_slide"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["deck_claims"],
        "additionalProperties": False,
    },
}

_EXTRACTION_INSTRUCTIONS = """You are extracting structured claims from a startup pitch deck for an investor \
screening pipeline. Each slide's text below is labeled with its slide number.

For every claim you find that fits one of these five fields, emit one entry:
- market_size: TAM/SAM/SOM figures, market growth rate, market sizing methodology
- traction: revenue, users, growth rate, pilots, signed customers, usage metrics
- team: founder backgrounds, prior companies, relevant experience, team composition
- ask: round size, valuation, use of funds, runway extension
- problem_product: the problem being solved and what the product does

Rules:
- Tag every claim with the exact slide number it came from (source_slide).
- A single slide may yield multiple claims, and may yield claims of different fields.
- Keep "value" concise and faithful to the source text — do not fabricate numbers or \
facts not present in the deck.
- Skip boilerplate (logos, taglines, contact info) that isn't a substantive claim.
- If a field has no supporting content anywhere in the deck, simply omit it — do not \
invent a claim to fill it."""


def load_deck_text(file_path: str | Path) -> str:
    """Load raw deck text. .txt fixtures are read as-is; .pdf files are extracted
    page-by-page via pypdf and re-joined with slide markers (one PDF page == one slide,
    the standard shape for an exported pitch deck)."""
    path = Path(file_path)
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        pages = []
        for i, page in enumerate(reader.pages, start=1):
            pages.append(f"=== SLIDE {i} ===\n{page.extract_text() or ''}")
        return "\n\n".join(pages)

    return path.read_text(encoding="utf-8")


def split_into_slides(raw_text: str) -> list[tuple[int, str]]:
    """Split raw deck text into (slide_number, slide_text) pairs using '=== SLIDE N ==='
    markers. Falls back to treating the whole document as slide 1 if no markers are found,
    which is the expected shape for a real PDF export before markers are inserted upstream."""
    matches = list(_SLIDE_MARKER_RE.finditer(raw_text))
    if not matches:
        return [(1, raw_text.strip())]

    slides = []
    for idx, match in enumerate(matches):
        slide_num = int(match.group(1))
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(raw_text)
        slides.append((slide_num, raw_text[start:end].strip()))
    return slides


def _build_prompt(slides: list[tuple[int, str]]) -> str:
    labeled = "\n\n".join(f"[Slide {num}]\n{text}" for num, text in slides)
    return f"{_EXTRACTION_INSTRUCTIONS}\n\n---DECK---\n\n{labeled}"


def extract_deck_claims(file_path: str | Path, client: OpenAI | None = None) -> list[DeckClaim]:
    """Main entry point: parse a deck file and return validated DeckClaim objects."""
    raw_text = load_deck_text(file_path)
    slides = split_into_slides(raw_text)
    if not any(text.strip() for _, text in slides):
        return []

    client = client or OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": _build_prompt(slides)}],
        response_format={"type": "json_schema", "json_schema": _CLAIMS_JSON_SCHEMA},
    )
    payload = json.loads(response.choices[0].message.content)

    try:
        return [DeckClaim(**c) for c in payload["deck_claims"]]
    except ValidationError as exc:
        raise ValueError(f"OpenAI returned deck_claims that don't match the contract shape: {exc}") from exc


def assemble_signal_intake_output(
    *,
    founder_id: str,
    company_id: str,
    deck_claims: list[DeckClaim],
    cold_start_flag: bool = False,
) -> SignalIntakeOutput:
    """Wrap deck_claims into the full contract envelope. public_signals is left at its
    zeroed default here — the outbound scanning module owns populating it."""
    return SignalIntakeOutput(
        founder_id=founder_id,
        company_id=company_id,
        deck_claims=deck_claims,
        public_signals=PublicSignals(),
        sourcing_channel="inbound",
        cold_start_flag=cold_start_flag,
    )


def record_deck_claims_in_memory(output: SignalIntakeOutput) -> None:
    """Persist this deck-parse result via B's shared Memory layer (backend/api/db.py):
    save_signal() for the raw evidence, then recompute_founder_score() since new evidence
    just arrived -- per that module's documented contract. Deliberately a separate call,
    not folded into assemble_signal_intake_output(), so building the output stays a pure
    function and callers choose when the persistence side-effect happens.

    Lazy-imported: backend.api.db is B's module and may not exist yet on every branch --
    this keeps deck_parser importable (and its own tests runnable) either way. Only fails
    at call time, once someone actually tries to persist a result."""
    from backend.api.db import recompute_founder_score, save_signal

    save_signal(output.founder_id, "deck", output.model_dump())
    recompute_founder_score(output.founder_id)


if __name__ == "__main__":
    import sys

    deck_path = sys.argv[1] if len(sys.argv) > 1 else "../../shared/fixtures/decks/sample_deck_01.txt"
    claims = extract_deck_claims(deck_path)
    output = assemble_signal_intake_output(
        founder_id="founder_demo_001",
        company_id="company_demo_001",
        deck_claims=claims,
    )
    print(output.model_dump_json(indent=2))
