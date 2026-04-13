from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class Settings(SQLModel, table=True):
    id: int = Field(default=1, primary_key=True)
    email: str = Field(default="")
    schedule_type: str = Field(default="daily")   # "daily" | "hourly" | "custom"
    schedule_value: str = Field(default="09:00")  # "09:00" | "2" | cron string
    timezone: str = Field(default="America/New_York")
    categories: str = Field(default='["Business & Economy","World News","Technology/AI","Science & Health","Environment & Climate"]')
    social_refresh_hours: int = Field(default=24)
    language: str = Field(default="en")
    articles_per_category: int = Field(default=5)
    market_tickers: str = Field(default="[]")    # JSON: [{name, symbol}]
    local_locations: str = Field(default="[]")   # JSON: [{city, state, country}]
    world_countries: str = Field(default="[]")   # JSON: ["France", "India", ...]


class DigestRun(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    run_at: datetime = Field(default_factory=datetime.utcnow)
    trigger: str = Field(default="manual")   # "scheduled" | "manual"
    status: str = Field(default="success")   # "success" | "failed"
    summary_html: str = Field(default="")
    summary_json: str = Field(default="")
    error_message: Optional[str] = Field(default=None)


class SocialSnapshot(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    captured_at: datetime = Field(default_factory=datetime.utcnow)
    platform_data: str = Field(default="{}")
    trending_topics: str = Field(default="[]")
    mood_scores: str = Field(default="{}")
    trend_history: str = Field(default="{}")


class MarketSnapshot(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    captured_at: datetime = Field(default_factory=datetime.utcnow)
    markets_json: str = Field(default="[]")  # JSON array of normalized market dicts
