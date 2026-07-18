"""Small HTTP clients for C's external services, with no SDK dependency."""

from __future__ import annotations

import json
import os
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .models import Evidence


class ExternalServiceError(RuntimeError):
    """Raised when an external provider cannot return a usable response."""


class SearchClient(Protocol):
    def search(self, query: str, max_results: int = 3) -> list[Evidence]: ...


class ReasoningClient(Protocol):
    def json_completion(self, system: str, user: str) -> dict[str, Any]: ...


def _post_json(url: str, headers: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ExternalServiceError(str(exc)) from exc


class TavilySearchClient:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("TAVILY_API_KEY", "")

    def search(self, query: str, max_results: int = 3) -> list[Evidence]:
        if not self.api_key:
            raise ExternalServiceError("TAVILY_API_KEY is not configured")
        data = _post_json(
            "https://api.tavily.com/search",
            {},
            {
                "api_key": self.api_key,
                "query": query,
                "search_depth": "advanced",
                "max_results": max_results,
                "include_answer": False,
            },
        )
        return [
            Evidence(
                title=str(item.get("title") or "Untitled source"),
                url=str(item.get("url") or ""),
                content=str(item.get("content") or ""),
                score=float(item.get("score") or 0.0),
            )
            for item in data.get("results", [])
            if item.get("url")
        ]


class OpenAIReasoningClient:
    def __init__(self, api_key: str | None = None, model: str = "gpt-5.5-2026-04-23") -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model

    def json_completion(self, system: str, user: str) -> dict[str, Any]:
        if not self.api_key:
            raise ExternalServiceError("OPENAI_API_KEY is not configured")
        data = _post_json(
            "https://api.openai.com/v1/responses",
            {"Authorization": f"Bearer {self.api_key}"},
            {
                "model": self.model,
                "instructions": system,
                "input": user,
                "text": {"format": {"type": "json_object"}},
            },
        )
        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    return json.loads(content.get("text", "{}"))
        raise ExternalServiceError("OpenAI returned no JSON output")
