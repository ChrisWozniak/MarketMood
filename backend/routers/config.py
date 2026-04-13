import json
import httpx
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session
from database import get_session
from models import Settings
from services.scheduler import update_schedule
from services.email_sender import send_test_email

router = APIRouter()


class SettingsUpdate(BaseModel):
    email: str | None = None
    schedule_type: str | None = None
    schedule_value: str | None = None
    timezone: str | None = None
    categories: list[str] | None = None
    social_refresh_hours: int | None = None
    articles_per_category: int | None = None
    language: str | None = None
    market_tickers: list[dict] | None = None
    local_locations: list[dict] | None = None
    world_countries: list[str] | None = None


@router.get("")
def get_settings(session: Session = Depends(get_session)):
    settings = session.get(Settings, 1)
    if not settings:
        settings = Settings()
        session.add(settings)
        session.commit()
        session.refresh(settings)
    return {
        "email": settings.email,
        "schedule_type": settings.schedule_type,
        "schedule_value": settings.schedule_value,
        "timezone": settings.timezone,
        "categories": json.loads(settings.categories),
        "social_refresh_hours": settings.social_refresh_hours,
        "articles_per_category": settings.articles_per_category,
        "language": settings.language,
        "market_tickers": json.loads(settings.market_tickers or "[]"),
        "local_locations": json.loads(settings.local_locations or "[]"),
        "world_countries": json.loads(settings.world_countries or "[]"),
    }


@router.put("")
def update_settings(
    body: SettingsUpdate,
    session: Session = Depends(get_session),
):
    settings = session.get(Settings, 1)
    if not settings:
        settings = Settings()
        session.add(settings)

    if body.email is not None:
        settings.email = body.email
    if body.schedule_type is not None:
        settings.schedule_type = body.schedule_type
    if body.schedule_value is not None:
        settings.schedule_value = body.schedule_value
    if body.timezone is not None:
        settings.timezone = body.timezone
    if body.categories is not None:
        settings.categories = json.dumps(body.categories)
    if body.social_refresh_hours is not None:
        settings.social_refresh_hours = body.social_refresh_hours
    if body.articles_per_category is not None:
        settings.articles_per_category = body.articles_per_category
    if body.language is not None:
        settings.language = body.language
    if body.market_tickers is not None:
        settings.market_tickers = json.dumps(body.market_tickers)
    if body.local_locations is not None:
        settings.local_locations = json.dumps(body.local_locations)
    if body.world_countries is not None:
        settings.world_countries = json.dumps(body.world_countries)

    session.commit()
    session.refresh(settings)

    # Update the running scheduler
    update_schedule(settings)

    return {"status": "updated"}


@router.get("/ticker-search")
async def ticker_search(q: str = Query(default="")):
    """Search for stock/crypto tickers via Yahoo Finance."""
    if not q or len(q) < 1:
        return []
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                "https://query1.finance.yahoo.com/v1/finance/search",
                params={"q": q, "quotesCount": 7, "newsCount": 0, "listsCount": 0},
                headers={"User-Agent": "Mozilla/5.0"},
            )
            data = resp.json()
            quotes = data.get("quotes", [])
            results = []
            for qt in quotes:
                symbol = qt.get("symbol", "")
                name = qt.get("longname") or qt.get("shortname") or symbol
                qtype = qt.get("quoteType", "")
                if symbol and qtype in ("EQUITY", "CRYPTOCURRENCY", "ETF", "INDEX"):
                    results.append({"symbol": symbol, "name": name, "type": qtype})
            return results
    except Exception:
        return []


@router.post("/test-email")
def test_email(session: Session = Depends(get_session)):
    settings = session.get(Settings, 1)
    if not settings or not settings.email:
        return {"status": "error", "message": "No email configured"}
    success = send_test_email(settings.email)
    return {"status": "sent" if success else "error"}
