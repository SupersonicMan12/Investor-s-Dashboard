from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Investor Dashboard")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request) -> HTMLResponse:
    mock_opportunities = [
        {
            "symbol": "XLK",
            "name": "Technology Select Sector SPDR Fund",
            "confidence": "High",
            "thesis": "Tech sector relative strength remains positive over the past 5 sessions.",
        },
        {
            "symbol": "MSFT",
            "name": "Microsoft Corporation",
            "confidence": "Medium",
            "thesis": "Stable trend with supportive sentiment and moderate volatility.",
        },
    ]

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "title": "Investor Dashboard",
            "horizon": "1-week investment horizon",
            "opportunities": mock_opportunities,
        },
    )
