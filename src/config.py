"""Project constants and default event framing."""

from datetime import date

SYMBOL = "AMZN"
EVENT_LABEL = "Will AMZN close higher during/after its earnings release this week?"
EARNINGS_DATE = date(2026, 10, 29)
POLYMARKET_BASE_URL = "https://gamma-api.polymarket.com"
POLYMARKET_DEFAULT_SLUG = ""
CBOE_ENDPOINT = "https://cdn.cboedis.com/api/global/us/eod/histdata/snap.json"
SIGNAL_THRESHOLD = 0.05
REQUEST_TIMEOUT_SECONDS = 15
OUTPUT_DIR = "output"
SAMPLE_PATH = "sample_data/snaps.json"
