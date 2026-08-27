"""Application configuration: symbol universe and tunables."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "dashboard.db"
SAMPLE_DATA_PATH = DATA_DIR / "sample_quotes.json"

# How long cached market data stays fresh, in seconds.
CACHE_TTL_SECONDS = 15 * 60

# Trading days assumed per week / month for horizon math.
WEEK_DAYS = 5
MONTH_DAYS = 21

MARKET_INDICES = [
    {"symbol": "SPY", "name": "S&P 500"},
    {"symbol": "QQQ", "name": "Nasdaq 100"},
    {"symbol": "DIA", "name": "Dow Jones"},
    {"symbol": "IWM", "name": "Russell 2000"},
]

SECTOR_ETFS = [
    {"symbol": "XLK", "name": "Technology"},
    {"symbol": "XLF", "name": "Financials"},
    {"symbol": "XLV", "name": "Health Care"},
    {"symbol": "XLE", "name": "Energy"},
    {"symbol": "XLI", "name": "Industrials"},
    {"symbol": "XLY", "name": "Consumer Discretionary"},
    {"symbol": "XLP", "name": "Consumer Staples"},
    {"symbol": "XLU", "name": "Utilities"},
    {"symbol": "XLB", "name": "Materials"},
    {"symbol": "XLRE", "name": "Real Estate"},
    {"symbol": "XLC", "name": "Communication Services"},
]

STOCK_UNIVERSE = [
    {"symbol": "AAPL", "name": "Apple Inc."},
    {"symbol": "MSFT", "name": "Microsoft Corporation"},
    {"symbol": "NVDA", "name": "NVIDIA Corporation"},
    {"symbol": "GOOGL", "name": "Alphabet Inc."},
    {"symbol": "AMZN", "name": "Amazon.com, Inc."},
    {"symbol": "META", "name": "Meta Platforms, Inc."},
    {"symbol": "TSLA", "name": "Tesla, Inc."},
    {"symbol": "AVGO", "name": "Broadcom Inc."},
    {"symbol": "JPM", "name": "JPMorgan Chase & Co."},
    {"symbol": "UNH", "name": "UnitedHealth Group"},
    {"symbol": "V", "name": "Visa Inc."},
    {"symbol": "XOM", "name": "Exxon Mobil Corporation"},
    {"symbol": "COST", "name": "Costco Wholesale"},
    {"symbol": "LLY", "name": "Eli Lilly and Company"},
    {"symbol": "HD", "name": "The Home Depot"},
]

# Symbols scored as weekly opportunity candidates.
OPPORTUNITY_UNIVERSE = SECTOR_ETFS + STOCK_UNIVERSE

NAME_LOOKUP = {
    entry["symbol"]: entry["name"]
    for entry in MARKET_INDICES + SECTOR_ETFS + STOCK_UNIVERSE
}

ALL_SYMBOLS = list(NAME_LOOKUP)
