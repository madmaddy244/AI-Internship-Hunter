from __future__ import annotations

import logging
import os
from typing import Any

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    OpenAIError,
    RateLimitError,
)

from backend.config import DEFAULT_NEBIUS_MODEL, ai_enabled, ai_model, nebius_base_url

logger = logging.getLogger(__name__)


class NebiusError(RuntimeError):
    def __init__(self, status_code: int, public_message: str) -> None:
        super().__init__(public_message)
        self.status_code = status_code
        self.public_message = public_message


def model_name() -> str:
    return ai_model()


def model_client() -> OpenAI:
    if not ai_enabled():
        raise NebiusError(
            503,
            "Nemotron is not configured. Add NEBIUS_API_KEY in Replit Secrets to enable AI features.",
        )
    return OpenAI(
        api_key=os.environ["NEBIUS_API_KEY"],
        base_url=nebius_base_url(),
        timeout=45.0,
        max_retries=0,
    )


def complete(
    *,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    tool_choice: Any = None,
    max_tokens: int = 1200,
    temperature: float = 0.2,
) -> Any:
    client = model_client()
    request: dict[str, Any] = {
        "model": ai_model() or DEFAULT_NEBIUS_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if tools:
        request["tools"] = tools
    if tool_choice is not None:
        request["tool_choice"] = tool_choice
    try:
        return client.chat.completions.create(**request)
    except RateLimitError as error:
        logger.warning("Nebius request rate limited (HTTP %s)", error.status_code)
        raise NebiusError(
            503, "Nebius rate limit reached. Wait briefly, then retry."
        ) from None
    except APITimeoutError:
        logger.warning("Nebius request timed out")
        raise NebiusError(
            504, "Nebius did not respond before the request timed out."
        ) from None
    except AuthenticationError:
        logger.error("Nebius rejected the configured credential")
        raise NebiusError(
            502, "Nebius rejected the configured API key. Check NEBIUS_API_KEY."
        ) from None
    except APIConnectionError:
        logger.warning("Nebius connection failed")
        raise NebiusError(
            502, "Could not connect to Nebius Token Factory."
        ) from None
    except APIStatusError as error:
        status_code = int(getattr(error, "status_code", 502) or 502)
        logger.error("Nebius returned HTTP %s", status_code)
        if status_code == 429:
            raise NebiusError(
                503, "Nebius rate limit reached. Wait briefly, then retry."
            ) from None
        if status_code in (401, 403):
            raise NebiusError(
                502, "Nebius rejected the configured API key. Check NEBIUS_API_KEY."
            ) from None
        raise NebiusError(
            502, f"Nebius Token Factory returned an error (HTTP {status_code})."
        ) from None
    except OpenAIError as error:
        logger.error("OpenAI-compatible Nebius client failed (%s)", type(error).__name__)
        raise NebiusError(
            502, "The Nebius request failed. Check the endpoint and model configuration."
        ) from None
