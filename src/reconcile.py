"""Align comparable binary semantics and produce a bounded signal."""

from typing import Any

from src.config import SIGNAL_THRESHOLD


def _higher_close_semantics(question: str) -> bool:
    """Only treat explicitly directional close/stock wording as price semantics."""
    text = question.lower()
    return ("higher" in text or "above" in text or "up" in text) and any(
        term in text for term in ("close", "stock", "share price")
    )


def reconcile(indicators: dict[str, Any], polymarket: dict[str, Any] | None) -> dict[str, Any]:
    """Compare options P(up) only with a price-close-aligned market."""
    raw = float(polymarket["yes_price"]) if polymarket else None
    aligned = raw if polymarket and _higher_close_semantics(polymarket["question"]) else None
    divergence = float(indicators["implied_p_up"]) - aligned if aligned is not None else None
    if divergence is None:
        signal = "Options-only (no matching market)" if polymarket is None else "Options-only (no aligned price market)"
        note = ("No matching Polymarket contract with higher-close semantics was found. "
                "Options imply an approximate up-close probability of "
                f"{indicators['implied_p_up']:.1%}; no cross-market gap is calculated.")
    elif abs(divergence) < SIGNAL_THRESHOLD:
        signal = "Neutral"
        note = (f"Options imply {indicators['implied_p_up']:.1%} for a higher close versus "
                f"{aligned:.1%} in Polymarket, a {divergence:+.1%} gap. The gap is below the "
                "fixed five-point threshold; the options estimate remains model-based.")
    elif divergence > 0:
        signal = "Prediction market UNDERpricing up"
        note = (f"Options imply {indicators['implied_p_up']:.1%} for a higher close versus "
                f"{aligned:.1%} in Polymarket, a {divergence:+.1%} gap. By the fixed threshold, "
                "the prediction-market probability is lower; this comparison is descriptive and "
                "sensitive to market matching and the options approximation.")
    else:
        signal = "Prediction market OVERpricing up"
        note = (f"Options imply {indicators['implied_p_up']:.1%} for a higher close versus "
                f"{aligned:.1%} in Polymarket, a {divergence:+.1%} gap. By the fixed threshold, "
                "the prediction-market probability is higher; this comparison is descriptive and "
                "sensitive to market matching and the options approximation.")
    return {"implied_p_up": indicators["implied_p_up"], "pred_p": raw,
            "pred_p_aligned": aligned, "divergence": divergence, "signal": signal,
            "analyst_note": note}
