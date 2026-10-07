from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

DEFAULT_NEBIUS_BASE_URL = "https://api.tokenfactory.nebius.com/v1/"
DEFAULT_NEBIUS_MODEL = "nvidia/Nemotron-3_5-Lightning"


def ai_enabled() -> bool:
    enabled = os.getenv("NEBIUS_ENABLED", "true").strip().lower() not in {
        "0",
        "false",
        "off",
        "no",
    }
    return enabled and bool(os.getenv("NEBIUS_API_KEY", "").strip())


def ai_model() -> str:
    return os.getenv("NEBIUS_MODEL", DEFAULT_NEBIUS_MODEL).strip() or DEFAULT_NEBIUS_MODEL


def nebius_base_url() -> str:
    configured = os.getenv("NEBIUS_BASE_URL", "").strip()
    return configured or DEFAULT_NEBIUS_BASE_URL


def search_enabled() -> bool:
    enabled = os.getenv("TAVILY_ENABLED", "true").strip().lower() not in {
        "0",
        "false",
        "off",
        "no",
    }
    return enabled and bool(os.getenv("TAVILY_API_KEY", "").strip())
