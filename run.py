"""Command-line entrypoint for the AMZN earnings odds research sample."""

import argparse
import os
import sys
from datetime import date

from dotenv import load_dotenv

from src.cboe_client import fetch_snapshot, load_sample
from src.config import EARNINGS_DATE, EVENT_LABEL, POLYMARKET_DEFAULT_SLUG, SYMBOL
from src.indicators import compute_indicators
from src.polymarket_client import find_market
from src.reconcile import reconcile
from src.report import write_reports


def parse_args() -> argparse.Namespace:
    """Parse the small non-interactive command-line interface."""
    parser = argparse.ArgumentParser(description="Compare AMZN options odds with a Polymarket market.")
    parser.add_argument("--demo", action="store_true", help="Use the synthetic options fixture; skip Cboe.")
    parser.add_argument("--date", default=date.today().isoformat(), help="As-of date (YYYY-MM-DD).")
    parser.add_argument("--slug", default=POLYMARKET_DEFAULT_SLUG, help="Optional Polymarket market slug.")
    args = parser.parse_args()
    try:
        date.fromisoformat(args.date)
    except ValueError:
        parser.error("--date must use YYYY-MM-DD")
    return args


def main() -> int:
    """Run endpoint preflight, metrics, reconciliation, and artifact generation."""
    args = parse_args()
    load_dotenv()
    api_key = os.getenv("CBOE_API_KEY", "").strip()
    if args.demo:
        print("Cboe request status: SKIPPED (--demo; using synthetic fixture)")
        snaps = load_sample()
        cboe_failure = False
    elif not api_key:
        print("Cboe request status: NOT SENT (CBOE_API_KEY missing); see .env.example")
        snaps = []
        cboe_failure = True
    else:
        try:
            snaps = fetch_snapshot(args.date, api_key)
            cboe_failure = not bool(snaps)
        except RuntimeError as exc:
            print(f"Cboe unavailable: {exc}")
            snaps = []
            cboe_failure = True
    try:
        market = find_market(args.slug)
    except Exception as exc:
        print(f"Polymarket search unavailable; continuing options-only: {exc}")
        market = None
    if cboe_failure and not args.demo:
        return 2 if not api_key else 3
    if not snaps:
        print("No Cboe data available; cannot compute options indicators.")
        return 3
    expiries = sorted({date.fromisoformat(row["expiration"]) for row in snaps
                       if date.fromisoformat(row["expiration"]) >= EARNINGS_DATE})
    if not expiries:
        print(f"No options expiry on or after configured earnings date {EARNINGS_DATE}.")
        return 3
    try:
        indicators = compute_indicators(snaps, expiries[0], date.fromisoformat(args.date))
    except (ValueError, TypeError) as exc:
        print(f"Unable to compute options indicators: {exc}")
        return 3
    result = reconcile(indicators, market)
    path = write_reports(args.date, EVENT_LABEL, indicators, market, result, snaps)
    print(f"Event: {SYMBOL} earnings higher-close comparison")
    print(f"Options implied move: {indicators['implied_move_pct']:.2f}%")
    print(f"Options P(up): {result['implied_p_up']:.1%}")
    print(f"Polymarket P(up): {result['pred_p_aligned']:.1%}" if result["pred_p_aligned"] is not None else "Polymarket P(up): —")
    print(f"Signal: {result['signal']} | Dashboard: {path.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
