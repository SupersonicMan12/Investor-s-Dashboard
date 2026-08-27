from app.services import market_data
from app.services.market_data import Quote


def make_payload():
    return {
        "chart": {
            "result": [
                {
                    "meta": {
                        "currency": "USD",
                        "regularMarketPrice": 105.0,
                        "chartPreviousClose": 100.0,
                        "shortName": "Test Asset",
                    },
                    "timestamp": [1, 2, 3, 4],
                    "indicators": {
                        "quote": [
                            {
                                "close": [100.0, None, 103.0, 105.0],
                                "volume": [10, 20, None, 40],
                            }
                        ]
                    },
                }
            ]
        }
    }


def test_parse_chart_response_skips_null_closes():
    quote = market_data._parse_chart_response("TEST", make_payload())
    assert quote.symbol == "TEST"
    assert quote.closes == [100.0, 103.0, 105.0]
    assert quote.volumes == [10, 0, 40]
    assert quote.timestamps == [1, 3, 4]
    assert quote.price == 105.0
    # Latest close equals live price, so previous close falls back to prior bar.
    assert quote.previous_close == 103.0


def test_quote_change_pct():
    quote = Quote(symbol="T", name="T", price=110.0, previous_close=100.0)
    assert quote.change == 10.0
    assert round(quote.change_pct, 2) == 10.0


def test_quote_json_roundtrip():
    quote = Quote(
        symbol="T",
        name="Test",
        timestamps=[1, 2],
        closes=[1.0, 2.0],
        volumes=[5, 6],
        price=2.0,
        previous_close=1.0,
    )
    restored = Quote.from_json(quote.to_json())
    assert restored == quote


def test_cache_roundtrip():
    quote = Quote(
        symbol="CACHE",
        name="Cached",
        timestamps=[1],
        closes=[1.0],
        volumes=[1],
        price=1.0,
        previous_close=1.0,
    )
    market_data._cache_put(quote)
    fetched = market_data._cache_get("CACHE", max_age=60)
    assert fetched is not None
    assert fetched.symbol == "CACHE"
    assert market_data._cache_get("MISSING") is None
