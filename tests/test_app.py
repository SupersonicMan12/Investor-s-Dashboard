from fastapi.testclient import TestClient

from app import db, main
from app.services.market_data import Quote

client = TestClient(main.app)


def make_quote(symbol: str, name: str = "Test Asset") -> Quote:
    closes = [100 + i * 0.5 for i in range(120)]
    return Quote(
        symbol=symbol,
        name=name,
        timestamps=list(range(120)),
        closes=closes,
        volumes=[1000] * 120,
        price=closes[-1],
        previous_close=closes[-2],
    )


def fake_get_quotes(symbols):
    return {s: make_quote(s) for s in symbols}


async def fake_get_quotes_async(symbols):
    return fake_get_quotes(symbols)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_dashboard_renders(monkeypatch):
    monkeypatch.setattr(main.market_data, "get_quotes", fake_get_quotes_async)
    response = client.get("/")
    assert response.status_code == 200
    assert "This week's signals" in response.text
    assert "Market pulse" in response.text
    assert "Sector momentum" in response.text


def test_symbol_detail(monkeypatch):
    monkeypatch.setattr(main.market_data, "get_quotes", fake_get_quotes_async)
    response = client.get("/symbol/aapl")
    assert response.status_code == 200
    assert "AAPL" in response.text
    assert "1-week signal" in response.text


def test_symbol_not_found(monkeypatch):
    async def empty(symbols):
        return {}

    monkeypatch.setattr(main.market_data, "get_quotes", empty)
    response = client.get("/symbol/NOPE")
    assert response.status_code == 404
    assert "not found" in response.text


def test_watchlist_add_and_remove(monkeypatch):
    monkeypatch.setattr(main.market_data, "get_quotes", fake_get_quotes_async)

    response = client.post(
        "/watchlist/add", data={"symbol": "nvda", "next_url": "/watchlist"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert db.get_watchlist_symbols() == ["NVDA"]

    response = client.get("/watchlist")
    assert response.status_code == 200
    assert "NVDA" in response.text

    response = client.post(
        "/watchlist/remove", data={"symbol": "NVDA", "next_url": "/watchlist"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert db.get_watchlist_symbols() == []


def test_watchlist_redirect_rejects_external_url():
    response = client.post(
        "/watchlist/add",
        data={"symbol": "NVDA", "next_url": "https://evil.example"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/watchlist"


def test_portfolio_add_and_remove(monkeypatch):
    monkeypatch.setattr(main.market_data, "get_quotes", fake_get_quotes_async)

    response = client.post(
        "/portfolio/add",
        data={"symbol": "aapl", "shares": "10", "cost_basis": "150"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    holdings = db.get_holdings()
    assert len(holdings) == 1
    assert holdings[0]["symbol"] == "AAPL"

    response = client.get("/portfolio")
    assert response.status_code == 200
    assert "AAPL" in response.text
    assert "Unrealized P&amp;L" in response.text

    response = client.post(
        "/portfolio/remove",
        data={"holding_id": str(holdings[0]["id"])},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert db.get_holdings() == []


def test_portfolio_rejects_nonpositive_shares():
    client.post(
        "/portfolio/add",
        data={"symbol": "AAPL", "shares": "0", "cost_basis": "150"},
        follow_redirects=False,
    )
    assert db.get_holdings() == []
