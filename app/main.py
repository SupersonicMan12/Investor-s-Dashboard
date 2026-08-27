"""Investor's Dashboard: FastAPI app with server-rendered pages."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import config, db
from app.services import analysis, charts, market_data

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Investor's Dashboard")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.filters["money"] = lambda v: f"{v:,.2f}"
templates.env.filters["signed_pct"] = lambda v: f"{v:+.2f}%"


def _now_label() -> str:
    return datetime.now(timezone.utc).strftime("%b %d, %Y %H:%M UTC")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    index_symbols = [entry["symbol"] for entry in config.MARKET_INDICES]
    opportunity_symbols = [entry["symbol"] for entry in config.OPPORTUNITY_UNIVERSE]
    watchlist_symbols = db.get_watchlist_symbols()
    symbols = list(dict.fromkeys(index_symbols + opportunity_symbols + watchlist_symbols))

    quotes = await market_data.get_quotes(symbols)

    indices = [quotes[s] for s in index_symbols if s in quotes]
    sector_symbols = {entry["symbol"] for entry in config.SECTOR_ETFS}
    sectors = analysis.rank_signals(
        {s: q for s, q in quotes.items() if s in sector_symbols}
    )
    opportunities = analysis.rank_signals(
        {s: q for s, q in quotes.items() if s in opportunity_symbols}
    )[:8]
    watchlist = [
        analysis.score_quote(quotes[s]) for s in watchlist_symbols if s in quotes
    ]
    any_stale = any(q.is_stale for q in quotes.values())

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "active_page": "dashboard",
            "indices": indices,
            "sectors": sectors,
            "opportunities": opportunities,
            "watchlist": watchlist,
            "sparkline": charts.sparkline,
            "updated_at": _now_label(),
            "any_stale": any_stale,
        },
    )


@app.get("/symbol/{symbol}", response_class=HTMLResponse)
async def symbol_detail(request: Request, symbol: str) -> HTMLResponse:
    symbol = symbol.upper()
    quotes = await market_data.get_quotes([symbol])
    quote = quotes.get(symbol)
    if quote is None:
        return templates.TemplateResponse(
            request,
            "symbol.html",
            {"active_page": None, "symbol": symbol, "signal": None,
             "chart_svg": None, "in_watchlist": False, "updated_at": _now_label()},
            status_code=404,
        )
    signal = analysis.score_quote(quote)
    return templates.TemplateResponse(
        request,
        "symbol.html",
        {
            "active_page": None,
            "symbol": symbol,
            "signal": signal,
            "chart_svg": charts.price_chart(quote.timestamps, quote.closes),
            "in_watchlist": symbol in db.get_watchlist_symbols(),
            "updated_at": _now_label(),
        },
    )


@app.get("/watchlist", response_class=HTMLResponse)
async def watchlist_page(request: Request) -> HTMLResponse:
    symbols = db.get_watchlist_symbols()
    quotes = await market_data.get_quotes(symbols) if symbols else {}
    signals = [analysis.score_quote(quotes[s]) for s in symbols if s in quotes]
    missing = [s for s in symbols if s not in quotes]
    return templates.TemplateResponse(
        request,
        "watchlist.html",
        {
            "active_page": "watchlist",
            "signals": signals,
            "missing": missing,
            "sparkline": charts.sparkline,
            "updated_at": _now_label(),
        },
    )


@app.post("/watchlist/add")
async def watchlist_add(
    symbol: str = Form(...), next_url: str = Form("/watchlist")
) -> RedirectResponse:
    cleaned = symbol.strip().upper()
    if cleaned:
        db.add_to_watchlist(cleaned)
    return RedirectResponse(url=next_url if next_url.startswith("/") else "/watchlist",
                            status_code=303)


@app.post("/watchlist/remove")
async def watchlist_remove(
    symbol: str = Form(...), next_url: str = Form("/watchlist")
) -> RedirectResponse:
    db.remove_from_watchlist(symbol)
    return RedirectResponse(url=next_url if next_url.startswith("/") else "/watchlist",
                            status_code=303)


@app.get("/portfolio", response_class=HTMLResponse)
async def portfolio_page(request: Request) -> HTMLResponse:
    holdings = db.get_holdings()
    symbols = list({row["symbol"] for row in holdings})
    quotes = await market_data.get_quotes(symbols) if symbols else {}

    rows = []
    total_value = 0.0
    total_cost = 0.0
    for holding in holdings:
        quote = quotes.get(holding["symbol"])
        price = quote.price if quote else 0.0
        value = price * holding["shares"]
        cost = holding["cost_basis"] * holding["shares"]
        gain = value - cost
        rows.append(
            {
                "id": holding["id"],
                "symbol": holding["symbol"],
                "name": quote.name if quote else holding["symbol"],
                "shares": holding["shares"],
                "cost_basis": holding["cost_basis"],
                "price": price,
                "value": value,
                "gain": gain,
                "gain_pct": (gain / cost * 100) if cost else 0.0,
                "has_quote": quote is not None,
            }
        )
        total_value += value
        total_cost += cost

    total_gain = total_value - total_cost
    return templates.TemplateResponse(
        request,
        "portfolio.html",
        {
            "active_page": "portfolio",
            "rows": rows,
            "total_value": total_value,
            "total_cost": total_cost,
            "total_gain": total_gain,
            "total_gain_pct": (total_gain / total_cost * 100) if total_cost else 0.0,
            "updated_at": _now_label(),
        },
    )


@app.post("/portfolio/add")
async def portfolio_add(
    symbol: str = Form(...),
    shares: float = Form(...),
    cost_basis: float = Form(...),
) -> RedirectResponse:
    cleaned = symbol.strip().upper()
    if cleaned and shares > 0 and cost_basis >= 0:
        db.add_holding(cleaned, shares, cost_basis)
    return RedirectResponse(url="/portfolio", status_code=303)


@app.post("/portfolio/remove")
async def portfolio_remove(holding_id: int = Form(...)) -> RedirectResponse:
    db.remove_holding(holding_id)
    return RedirectResponse(url="/portfolio", status_code=303)
