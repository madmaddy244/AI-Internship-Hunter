from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from backend.config import search_enabled

logger = logging.getLogger(__name__)
TAVILY_SEARCH_URL = "https://api.tavily.com/search"


class SearchError(RuntimeError):
    def __init__(self, public_message: str, status_code: int = 502) -> None:
        super().__init__(public_message)
        self.public_message = public_message
        self.status_code = status_code


def search_internships(query: str, max_results: int = 12) -> list[dict[str, Any]]:
    if not search_enabled():
        raise SearchError(
            "Live search is not configured. Add TAVILY_API_KEY, or turn on clearly labeled Demo Mode.",
            503,
        )
    payload = {
        "api_key": os.environ["TAVILY_API_KEY"],
        "query": query,
        "topic": "general",
        "search_depth": "advanced",
        "max_results": max(1, min(max_results, 20)),
        "include_answer": False,
        "include_raw_content": False,
    }
    try:
        response = httpx.post(TAVILY_SEARCH_URL, json=payload, timeout=25.0)
        if response.status_code == 401 or response.status_code == 403:
            logger.error("Tavily rejected its configured credential (HTTP %s)", response.status_code)
            raise SearchError("Tavily rejected the configured key. Check TAVILY_API_KEY.", 502)
        if response.status_code == 429:
            logger.warning("Tavily rate limited a search request")
            raise SearchError("Tavily rate limit reached. Wait briefly, then retry.", 503)
        response.raise_for_status()
        data = response.json()
        results = data.get("results")
        if not isinstance(results, list):
            raise SearchError("Tavily returned an invalid search response.", 502)
        return [item for item in results if isinstance(item, dict)]
    except SearchError:
        raise
    except httpx.TimeoutException:
        logger.warning("Tavily search timed out")
        raise SearchError("Tavily search timed out. Try again in a moment.", 504) from None
    except httpx.HTTPStatusError as error:
        status_code = error.response.status_code
        logger.error("Tavily returned HTTP %s", status_code)
        raise SearchError(f"Tavily returned an error (HTTP {status_code}).", 502) from None
    except (httpx.HTTPError, ValueError):
        logger.warning("Tavily search could not be completed")
        raise SearchError("Could not connect to Tavily search. Try again later.", 502) from None
