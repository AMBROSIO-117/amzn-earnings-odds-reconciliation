"""Write an auditable Markdown report, JSON snapshot, and standalone dashboard."""

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _fmt(value: Any, style: str = "number") -> str:
    """Format a value without emitting NaN or implementation-specific nulls."""
    if value is None:
        return "—"
    if style == "pct":
        return f"{float(value):.1%}"
    if style == "move":
        return f"{float(value):.2f}%"
    if style == "money":
        return f"${float(value):,.2f}"
    if style == "signed_pct":
        return f"{float(value):+.1%}"
    return str(value)


def write_reports(as_of: str, event: str, indicators: dict[str, Any], polymarket: dict[str, Any] | None,
                  result: dict[str, Any], snaps: list[dict[str, Any]]) -> Path:
    """Write all output artifacts and return the dashboard path."""
    if polymarket is None:
        print("no matching Polymarket market found; showing options view only")
    elif result["pred_p_aligned"] is None:
        print("Polymarket market found, but its outcome does not map to higher-close semantics")
    generated = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out = Path("output")
    out.mkdir(parents=True, exist_ok=True)
    rows = [
        ("Spot", _fmt(indicators["spot"], "money"), "—"),
        ("Target expiry", indicators["target_expiry"], polymarket.get("end_date_iso", "—") if polymarket else "—"),
        ("Days to expiry", str(indicators["dte"]), "—"),
        ("ATM strike", _fmt(indicators["atm_strike"], "money"), "—"),
        ("Implied move", _fmt(indicators["implied_move_pct"], "move"), "—"),
        ("Implied P(close > prior close)", _fmt(result["implied_p_up"], "pct"), _fmt(result["pred_p_aligned"], "pct")),
        ("Raw Polymarket Yes", "—", _fmt(result["pred_p"], "pct")),
        ("Matched market", "—", polymarket.get("question", "—") if polymarket else "—"),
        ("Divergence (options − prediction)", "—", _fmt(result["divergence"], "signed_pct")),
        ("ATM IV / window volatility", _fmt(indicators["atm_iv"], "pct") + " / " + _fmt(indicators["vol_z"], "pct"), "—"),
        ("24h volume", "—", _fmt(polymarket["volume_24h"]) if polymarket else "—"),
    ]
    md = [f"# AMZN earnings odds — {as_of}", "", f"**Event:** {event}", "",
          "| Metric | Options (Cboe) | Polymarket |", "| --- | ---: | ---: |"]
    md.extend(f"| {name} | {left} | {right} |" for name, left, right in rows)
    md += ["", f"**Signal:** {result['signal']}", "", "## Analyst note", "", result["analyst_note"], "",
           "Options P(up) uses ATM implied volatility and Black-Scholes N(d2) as an approximation. "
           "The sample fixture is synthetic. Research sample. Not financial advice. Odds are probabilities, not guarantees.", "",
           f"Generated: {generated} UTC", ""]
    (out / "report.md").write_text("\n".join(md), encoding="utf-8")
    snapshot = {"as_of": as_of, "event": event, "cboe_normalized": snaps,
                "indicators": indicators, "polymarket_normalized": polymarket, "reconciliation": result,
                "generated_at_utc": generated}
    (out / "snapshot.json").write_text(json.dumps(snapshot, indent=2, allow_nan=False), encoding="utf-8")
    badge = "positive" if result["divergence"] is not None and result["divergence"] >= 0.05 else "negative" if result["divergence"] is not None and result["divergence"] <= -0.05 else "neutral"
    labels = json.dumps(["Implied P(up)", "Polymarket P(up)"])
    values = json.dumps([round(result["implied_p_up"] * 100, 2), round(result["pred_p_aligned"] * 100, 2) if result["pred_p_aligned"] is not None else None])
    table = "\n".join(f"<tr><th>{html.escape(name)}</th><td>{html.escape(left)}</td><td>{html.escape(right)}</td></tr>" for name, left, right in rows)
    page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AMZN Earnings Odds</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script><style>
body{{margin:0;background:#10151c;color:#e8edf4;font:16px/1.5 system-ui,sans-serif}}main{{max-width:1000px;margin:40px auto;padding:0 22px}}.eyebrow{{color:#74d4bd;text-transform:uppercase;letter-spacing:.12em;font-size:.78rem}}h1{{margin:.3em 0}}.muted,footer{{color:#aab5c2}}.card{{background:#19212b;border:1px solid #2b3744;border-radius:14px;padding:22px;margin:18px 0}}table{{width:100%;border-collapse:collapse}}td,th{{padding:11px;border-bottom:1px solid #2b3744;text-align:right}}th:first-child{{text-align:left}}.badge{{display:inline-block;padding:6px 12px;border-radius:99px;background:#334155}}.positive{{background:#14532d}}.negative{{background:#7f1d1d}}.neutral{{background:#334155}}canvas{{max-height:300px}}footer{{font-size:.88rem;padding:20px 0}}</style></head><body><main>
<div class="eyebrow">Independent research sample · Cboe One × Polymarket</div><h1>AMZN Earnings Odds</h1><p>{html.escape(event)}</p><p class="muted">As of {html.escape(as_of)} · target expiry {html.escape(indicators['target_expiry'])}</p>
<section class="card"><h2>Side-by-side metrics</h2><table><thead><tr><th>Metric</th><th>Options</th><th>Polymarket</th></tr></thead><tbody>{table}</tbody></table></section>
<section class="card"><h2>Implied P(up)</h2><canvas id="odds"></canvas></section><section class="card"><h2>SIGNAL</h2><span class="badge {badge}">{html.escape(result['signal'])}</span><p>{html.escape(result['analyst_note'])}</p></section>
<footer>Sources: Cboe One EOD options snapshot and Polymarket Gamma API. Generated {html.escape(generated)} UTC.<br>Options P(up) is an ATM Black-Scholes N(d2) approximation. Demo fixture is synthetic. Research sample. Not financial advice. Odds are probabilities, not guarantees.</footer>
<script>if(window.Chart){{new Chart(document.getElementById('odds'),{{type:'bar',data:{{labels:{labels},datasets:[{{label:'Probability (%)',data:{values},backgroundColor:['#55c3aa','#ec9b5e']}}]}},options:{{responsive:true,scales:{{y:{{beginAtZero:true,max:100,ticks:{{callback:v=>v+'%'}}}}}}}}}});}}</script></main></body></html>'''
    dashboard = out / "dashboard.html"
    dashboard.write_text(page, encoding="utf-8")
    return dashboard
