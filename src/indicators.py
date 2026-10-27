"""Calculate an ATM straddle move and a documented model-based P(up)."""

import math
from datetime import date
from typing import Any

import numpy as np


def _normal_cdf(value: float) -> float:
    """Standard normal cumulative distribution using the error function."""
    return 0.5 * (1 + math.erf(value / math.sqrt(2)))


def compute_indicators(snaps: list[dict[str, Any]], target_expiry: date, as_of: date) -> dict[str, Any]:
    """Compute ATM metrics from the closest call-put pair at target expiry."""
    expiry_rows = [row for row in snaps if date.fromisoformat(row["expiration"]) == target_expiry]
    if not expiry_rows:
        raise ValueError(f"No options rows available for target expiry {target_expiry}")
    spot_values = [row["underlying_close"] for row in expiry_rows if row["underlying_close"] > 0]
    if not spot_values:
        raise ValueError("No positive underlying_close values for target expiry")
    spot = float(np.median(spot_values))
    strikes = sorted({row["strike"] for row in expiry_rows})
    paired = []
    for strike in strikes:
        legs = {row["cp"]: row for row in expiry_rows if row["strike"] == strike}
        if "C" in legs and "P" in legs:
            paired.append((abs(strike - spot), strike, legs["C"], legs["P"]))
    if not paired:
        raise ValueError(f"No paired call and put at expiry {target_expiry}")
    _, strike, call, put = min(paired, key=lambda item: (item[0], item[1]))
    dte = (target_expiry - as_of).days
    iv = (float(call["iv"]) + float(put["iv"])) / 2
    sigma_window = iv * math.sqrt(max(dte, 0) / 365)
    if sigma_window <= 0 or spot <= 0:
        raise ValueError("ATM implied volatility and spot must be positive")
    d2 = (math.log(spot / strike) - 0.5 * sigma_window**2) / sigma_window
    return {
        "spot": spot, "dte": dte, "target_expiry": target_expiry.isoformat(),
        "atm_strike": strike, "atm_call_mid": float(call["mid"]), "atm_put_mid": float(put["mid"]),
        "implied_move_pct": (float(call["mid"]) + float(put["mid"])) / spot * 100,
        "implied_p_up": _normal_cdf(d2), "atm_iv": iv, "vol_z": sigma_window,
    }
