"""Fetch and normalize a Cboe One EOD options snapshot."""

import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests

from src.config import CBOE_ENDPOINT, REQUEST_TIMEOUT_SECONDS, SAMPLE_PATH, SYMBOL


def _url(as_of: str) -> str:
    """Build a redacted diagnostic URL; never expose the key in logs."""
    return f"{CBOE_ENDPOINT}?{urlencode({'symbol': SYMBOL, 'date': as_of, 'cboe_api_key': '[REDACTED]'})}"


def _normalize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert vendor fields to the stable internal contract shape."""
    normalized = []
    for row in rows:
        bid, ask = float(row.get("bid") or 0), float(row.get("ask") or 0)
        normalized.append({
            "cp": str(row.get("c", "")).upper(), "strike": float(row["strike"]),
            "expiration": str(row["expiration"])[:10], "bid": bid, "ask": ask,
            "mid": (bid + ask) / 2, "iv": float(row.get("implied_volatility") or 0),
            "oi": int(row.get("open_interest") or 0), "volume": int(row.get("volume") or 0),
            "underlying_close": float(row.get("underlying_close") or row.get("unadjusted_close") or 0),
        })
    return normalized


def load_sample() -> list[dict[str, Any]]:
    """Load the included synthetic fixture."""
    with Path(SAMPLE_PATH).open(encoding="utf-8") as file:
        return _normalize(json.load(file))


def fetch_snapshot(as_of: str, api_key: str, demo_fallback: bool = False) -> list[dict[str, Any]]:
    """Fetch once per attempt, retry one HTTP failure, then optionally demo-fallback."""
    params = {"symbol": SYMBOL, "date": as_of, "cboe_api_key": api_key}
    diagnostic_url = _url(as_of)
    last_error_message = "unknown error"
    for attempt in range(2):
        try:
            response = requests.get(CBOE_ENDPOINT, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
            print(f"Cboe request status: {response.status_code} ({diagnostic_url})")
            if not response.ok:
                raise requests.HTTPError(f"HTTP {response.status_code}", response=response)
            payload = response.json()
            rows = payload if isinstance(payload, list) else payload.get("data", [])
            return _normalize(rows)
        except (requests.RequestException, ValueError, TypeError, KeyError) as exc:
            status = getattr(getattr(exc, "response", None), "status_code", "unavailable")
            message = str(exc).replace(api_key, "[REDACTED]") if api_key else str(exc)
            last_error_message = message
            print(f"Cboe request failed at {diagnostic_url} (status {status}): {message}")
            if attempt == 0:
                time.sleep(1.05)
    if demo_fallback:
        print("Using the synthetic Cboe fixture after the live request failed.")
        return load_sample()
    raise RuntimeError(f"Cboe request failed after one retry: {last_error_message}")
