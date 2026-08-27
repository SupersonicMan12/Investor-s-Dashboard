# Investor's Dashboard

A Python-first web app that surfaces weekly investment opportunities. FastAPI +
server-rendered Jinja templates, live market data from Yahoo Finance, and a
built-in signal engine tuned for a 1-week investment horizon.

## Features

- **Weekly signals** — every symbol in the universe (11 sector ETFs + 15
  large caps) is scored 0-100 for the week ahead by blending short-term
  momentum, trend alignment (price vs. 20/50-day SMAs), RSI positioning, and a
  volatility penalty. The top ideas are ranked on the dashboard with a
  plain-English thesis.
- **Market pulse** — S&P 500, Nasdaq 100, Dow, and Russell 2000 at a glance.
- **Sector momentum** — all 11 SPDR sector ETFs ranked by weekly strength.
- **Symbol pages** — 6-month SVG price chart, key indicators (1W/1M returns,
  RSI, annualized volatility, trend), and the full signal breakdown for any
  ticker Yahoo Finance knows about.
- **Watchlist** — track any tickers; they appear scored on the dashboard.
- **Portfolio** — record positions (shares + avg cost) and see live market
  value and unrealized P&L.
- **Resilient data layer** — quotes are cached in SQLite for 15 minutes; if
  Yahoo is unreachable the app falls back to the last cached data, then to
  bundled sample data, and shows a staleness banner instead of breaking.

## Run locally (one command)

```bash
./scripts/run-dev.sh
```

Open <http://127.0.0.1:8000> in your browser.

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt

# Run the test suite
.venv/bin/python -m pytest

# Lint
.venv/bin/ruff check .

# Refresh the bundled offline fallback data
.venv/bin/python scripts/update-sample-data.py
```

## Architecture

```
app/
  main.py                 # FastAPI routes (dashboard, symbol, watchlist, portfolio)
  config.py               # Symbol universe and tunables
  db.py                   # SQLite: quote cache, watchlist, holdings
  services/
    market_data.py        # Yahoo Finance client + cache + offline fallback
    analysis.py           # Indicators, 1-week scoring, thesis generation
    charts.py             # Server-rendered SVG sparklines and price charts
  templates/              # Jinja templates (base, dashboard, symbol, watchlist, portfolio)
  static/css/styles.css   # Design tokens + styling
  data/                   # SQLite DB (runtime) + bundled sample quotes
scripts/
  run-dev.sh              # One-command bootstrap + dev server
  update-sample-data.py   # Regenerate offline fallback data
tests/                    # pytest suite (analysis, routes, data layer)
```

## Disclaimer

Signals are heuristics for research and education only — not investment advice.
