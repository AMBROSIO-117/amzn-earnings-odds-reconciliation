# AMZN Earnings Odds Reconciliation

A small, reproducible research sample comparing an options-implied earnings move with a Polymarket probability. It demonstrates data acquisition, normalization, a documented probability approximation, semantic reconciliation, and a static report. It is an independent portfolio project, not evidence of paid client work or a client engagement.

## Run

Python 3.10+ is required.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python run.py --demo
```

Demo mode uses the clearly labeled synthetic options fixture and attempts the public Polymarket search. To use live Cboe data, add a Cboe One API key to `.env` and run `python run.py`. Live requests time out, Cboe retries once, and failures include the URL. To select another market, use `python run.py --slug <market-slug>`. `--date YYYY-MM-DD` sets the as-of date used in the calculations.

Outputs are written to `output/dashboard.html`, `output/report.md`, and `output/snapshot.json`. The HTML opens locally; Chart.js is loaded from its CDN, so the chart requires internet access.

## Data and method

| Source | Endpoint | Use |
| --- | --- | --- |
| Cboe One | `https://cdn.cboedis.com/api/global/us/eod/histdata/snap.json` | End-of-day option quotes and underlying close; API key passed as `cboe_api_key` query parameter. Start with Cboe's [DataShop All Access API](https://datashop.cboe.com/cboe-all-access-api) and its [authentication/account API guidance](https://datashop.cboe.com/authentication); data access and licensed fields depend on the account and subscription. |
| Polymarket Gamma | `https://gamma-api.polymarket.com/markets` | Public market search and outcome prices; no authentication. |

The target expiration is the first expiration on or after the configured earnings date. The at-the-money (ATM) strike minimizes distance to spot. Implied move is the ATM call-plus-put midpoint divided by spot. `P(up)` is approximated with the ATM implied volatility and Black-Scholes `N(d2)` at the ATM strike; it is a model-based approximation, not a risk-neutral probability extracted directly from an option surface. Only a market whose wording maps to a higher-close outcome is reconciled. An EPS-beat market is retained as an unaligned raw probability and is not compared as if it meant a higher stock close.

The demo fixture is synthetic, internally consistent example data, not a historical Cboe snapshot. Its dates and values should not be represented as observed market data. Live market availability, market wording, and vendor schemas can change.

## Interpretation

The fixed signal threshold is five percentage points. Positive divergence means options imply a higher probability of an up close than the aligned Polymarket contract; negative divergence means the reverse. A disagreement is descriptive, not a trading recommendation. The note reports the size and direction of the measured gap and calls out the approximation and matching limits.

## Disclaimer

Research sample. Not financial advice. Odds are probabilities, not guarantees. Data may be delayed, incomplete, mismatched, or unavailable. No output is a recommendation to buy or sell securities or event contracts.
