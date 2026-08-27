"""Regenerate the bundled offline fallback data at app/data/sample_quotes.json.

Usage: .venv/bin/python scripts/update-sample-data.py
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config  # noqa: E402
from app.services import market_data  # noqa: E402


async def main() -> None:
    quotes = await market_data.get_quotes(config.ALL_SYMBOLS)
    payload = {symbol: json.loads(quote.to_json()) for symbol, quote in quotes.items()}
    config.SAMPLE_DATA_PATH.write_text(json.dumps(payload))
    print(f"Wrote {len(payload)} symbols to {config.SAMPLE_DATA_PATH}")
    missing = set(config.ALL_SYMBOLS) - set(payload)
    if missing:
        print(f"Missing: {', '.join(sorted(missing))}")


if __name__ == "__main__":
    asyncio.run(main())
