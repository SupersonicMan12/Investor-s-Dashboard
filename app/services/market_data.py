"""Market data access: Yahoo Finance chart API with SQLite caching and an
offline sample-data fallback so the app always renders."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field

import httpx

from app import config
from app.db import get_connection

logger = logging.getLogger(__name__)

YAHOO_HOSTS = ("query1.finance.yahoo.com", "query2.finance.yahoo.com")
YAHOO_CHART_URL = "https://{host}/v8/finance/chart/{symbol}"
MAX_RETRIES = 3
BACKOFF_SECONDS = 2.0
FETCH_CONCURRENCY = 2
FETCH_STAGGER_SECONDS = 0.4
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


@dataclass
class Quote:
    """Daily price history plus latest quote for one symbol."""

    symbol: str
    name: str
    currency: str = "USD"
    timestamps: list[int] = field(default_factory=list)
    closes: list[float] = field(default_factory=list)
    volumes: list[int] = field(default_factory=list)
    price: float = 0.0
    previous_close: float = 0.0
    is_stale: bool = False

    @property
    def change(self) -> float:
        return self.price - self.previous_close

    @property
    def change_pct(self) -> float:
        if not self.previous_close:
            return 0.0
        return (self.price - self.previous_close) / self.previous_close * 100

    def to_json(self) -> str:
        return json.dumps(
            {
                "symbol": self.symbol,
                "name": self.name,
                "currency": self.currency,
                "timestamps": self.timestamps,
                "closes": self.closes,
                "volumes": self.volumes,
                "price": self.price,
                "previous_close": self.previous_close,
            }
        )

    @classmethod
    def from_json(cls, payload: str) -> "Quote":
        data = json.loads(payload)
        return cls(**data)


def _parse_chart_response(symbol: str, payload: dict) -> Quote:
    result = payload["chart"]["result"][0]
    meta = result["meta"]
    quote_data = result["indicators"]["quote"][0]
    timestamps = result.get("timestamp") or []

    closes: list[float] = []
    volumes: list[int] = []
    kept_timestamps: list[int] = []
    for i, ts in enumerate(timestamps):
        close = quote_data["close"][i]
        if close is None:
            continue
        kept_timestamps.append(ts)
        closes.append(round(float(close), 4))
        volume = quote_data["volume"][i]
        volumes.append(int(volume) if volume is not None else 0)

    price = float(meta.get("regularMarketPrice") or (closes[-1] if closes else 0.0))
    previous_close = float(
        meta.get("chartPreviousClose")
        or meta.get("previousClose")
        or (closes[-2] if len(closes) > 1 else price)
    )
    if len(closes) > 1 and abs(closes[-1] - price) < 1e-9:
        previous_close = closes[-2]

    return Quote(
        symbol=symbol,
        name=config.NAME_LOOKUP.get(symbol, meta.get("shortName", symbol)),
        currency=meta.get("currency", "USD"),
        timestamps=kept_timestamps,
        closes=closes,
        volumes=volumes,
        price=price,
        previous_close=previous_close,
    )


def _cache_get(symbol: str, max_age: int | None = None) -> Quote | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT payload, fetched_at FROM quote_cache WHERE symbol = ?",
            (symbol,),
        ).fetchone()
    if row is None:
        return None
    if max_age is not None and time.time() - row["fetched_at"] > max_age:
        return None
    quote = Quote.from_json(row["payload"])
    quote.is_stale = time.time() - row["fetched_at"] > config.CACHE_TTL_SECONDS
    return quote


def _cache_put(quote: Quote) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO quote_cache (symbol, payload, fetched_at) VALUES (?, ?, ?) "
            "ON CONFLICT(symbol) DO UPDATE SET payload = excluded.payload, "
            "fetched_at = excluded.fetched_at",
            (quote.symbol, quote.to_json(), int(time.time())),
        )
        conn.commit()


def _sample_quote(symbol: str) -> Quote | None:
    try:
        with open(config.SAMPLE_DATA_PATH) as fh:
            samples = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None
    if symbol not in samples:
        return None
    quote = Quote(**samples[symbol])
    quote.is_stale = True
    return quote


async def _fetch_from_yahoo(
    client: httpx.AsyncClient, symbol: str, range_: str = "6mo"
) -> Quote:
    """Fetch daily history, retrying with backoff across hosts on rate limits."""
    last_error: Exception = RuntimeError("no fetch attempted")
    for attempt in range(MAX_RETRIES):
        host = YAHOO_HOSTS[attempt % len(YAHOO_HOSTS)]
        try:
            response = await client.get(
                YAHOO_CHART_URL.format(host=host, symbol=symbol),
                params={"range": range_, "interval": "1d"},
                headers=REQUEST_HEADERS,
                timeout=15.0,
            )
            response.raise_for_status()
            return _parse_chart_response(symbol, response.json())
        except httpx.HTTPStatusError as exc:
            last_error = exc
            if exc.response.status_code != 429:
                raise
        except httpx.HTTPError as exc:
            last_error = exc
        if attempt < MAX_RETRIES - 1:
            await asyncio.sleep(BACKOFF_SECONDS * (attempt + 1))
    raise last_error


async def get_quote(client: httpx.AsyncClient, symbol: str) -> Quote | None:
    """Return a quote for ``symbol``: fresh cache, then network, then any
    cached copy, then bundled sample data."""
    cached = _cache_get(symbol, max_age=config.CACHE_TTL_SECONDS)
    if cached is not None:
        return cached
    try:
        quote = await _fetch_from_yahoo(client, symbol)
        _cache_put(quote)
        return quote
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
        logger.warning("fetch failed for %s: %s", symbol, exc)
    stale = _cache_get(symbol)
    if stale is not None:
        return stale
    return _sample_quote(symbol)


async def get_quotes(symbols: list[str]) -> dict[str, Quote]:
    """Fetch quotes for many symbols concurrently."""
    async with httpx.AsyncClient() as client:
        semaphore = asyncio.Semaphore(FETCH_CONCURRENCY)

        async def bounded(symbol: str) -> Quote | None:
            async with semaphore:
                quote = await get_quote(client, symbol)
                await asyncio.sleep(FETCH_STAGGER_SECONDS)
                return quote

        results = await asyncio.gather(*(bounded(s) for s in symbols))
    return {q.symbol: q for q in results if q is not None}
