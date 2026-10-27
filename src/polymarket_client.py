"""Search public Polymarket markets and normalize binary outcome prices."""

import json
from typing import Any

import requests

from src.config import POLYMARKET_BASE_URL, REQUEST_TIMEOUT_SECONDS


def _get(url: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Request one Gamma API endpoint and report its exact URL and status on failure."""
    exact_url = requests.Request("GET", url, params=params).prepare().url
    try:
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        print(f"Polymarket request status: {response.status_code} ({response.url})")
        if not response.ok:
            raise requests.HTTPError(f"HTTP {response.status_code}", response=response)
        data = response.json()
        return data if isinstance(data, list) else data.get("markets", [])
    except (requests.RequestException, ValueError, TypeError) as exc:
        status = getattr(getattr(exc, "response", None), "status_code", "unavailable")
        print(f"Polymarket request failed at {getattr(exc, 'url', None) or exact_url} (status {status}): {exc}")
        raise


def _contains_match(market: dict[str, Any]) -> bool:
    """Keep likely AMZN/Amazon earnings rows from the server-side page."""
    text = f"{market.get('question', '')} {market.get('slug', '')}".lower()
    issuer = "amzn" in text or "amazon" in text
    topic = any(term in text for term in ("earn", "eps", "beat"))
    return issuer and topic


def _normalize(market: dict[str, Any]) -> dict[str, Any] | None:
    """Decode Gamma's JSON-encoded strings and map Yes/No by outcome label."""
    try:
        outcomes = market.get("outcomes", [])
        prices = market.get("outcomePrices", [])
        tokens = market.get("clobTokenIds", [])
        if isinstance(outcomes, str):
            outcomes = json.loads(outcomes)
        if isinstance(prices, str):
            prices = json.loads(prices)
        if isinstance(tokens, str):
            tokens = json.loads(tokens)
        labels = [str(item).lower() for item in outcomes]
        yes_index, no_index = labels.index("yes"), labels.index("no")
        return {
            "question": str(market.get("question", "")), "slug": str(market.get("slug", "")),
            "yes_price": float(prices[yes_index]), "no_price": float(prices[no_index]),
            "volume_24h": float(market.get("volume24hr", market.get("volume24h", 0)) or 0),
            "end_date_iso": market.get("endDate") or market.get("endDateIso"),
            "clob_token_id_yes": str(tokens[yes_index]),
        }
    except (ValueError, TypeError, IndexError, KeyError, json.JSONDecodeError):
        return None


def find_market(slug: str = "") -> dict[str, Any] | None:
    """Try an explicit slug before one open-market search, in that order."""
    base = f"{POLYMARKET_BASE_URL}/markets"
    if slug:
        try:
            for market in _get(base, {"slug": slug}):
                normalized = _normalize(market)
                if normalized:
                    return normalized
        except requests.RequestException:
            pass
    for market in _get(base, {"closed": "false", "limit": 100}):
        if _contains_match(market):
            normalized = _normalize(market)
            if normalized:
                return normalized
    return None
