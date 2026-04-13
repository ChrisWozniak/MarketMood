from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class SocialSnapshot(SQLModel, table=True):
    """Hourly snapshot of sentiment scores, trending topics, and AI-generated signals."""
    id: Optional[int] = Field(default=None, primary_key=True)
    captured_at: datetime = Field(default_factory=datetime.utcnow)
    platform_data: str = Field(default="{}")     # JSON: source stats + investment_signals + tech_momentum
    trending_topics: str = Field(default="[]")   # JSON: ranked topic list with sub_topics
    mood_scores: str = Field(default="{}")       # JSON: {category: {score, label, emotions, ...}}
    trend_history: str = Field(default="{}")     # JSON: {category: latest_volume}


class MarketSnapshot(SQLModel, table=True):
    """Kalshi + Polymarket prediction market data."""
    id: Optional[int] = Field(default=None, primary_key=True)
    captured_at: datetime = Field(default_factory=datetime.utcnow)
    markets_json: str = Field(default="[]")      # JSON array of market dicts
