"""
Shared fixtures for all Market Mood backend tests.

Uses an in-memory SQLite engine (StaticPool) so every test run is fully
isolated from the real moodmarket.db file and from each other.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy import text
from sqlalchemy.pool import StaticPool

from database import get_session
from models import SocialSnapshot, MarketSnapshot

# ── Shared in-memory DB ───────────────────────────────────────────────────────

TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,   # single connection — all sessions share same in-memory DB
)


def _override_session():
    with Session(TEST_ENGINE) as s:
        yield s


def _wipe():
    with TEST_ENGINE.connect() as conn:
        conn.execute(text("DELETE FROM socialsnapshot"))
        conn.execute(text("DELETE FROM marketsnapshot"))
        conn.commit()


# ── Session-scoped: create tables once ───────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def create_test_tables():
    SQLModel.metadata.create_all(TEST_ENGINE)
    yield


# ── Session-scoped: one TestClient for all tests (lifespan runs once) ────────

@pytest.fixture(scope="session")
def client(create_test_tables):
    from main import app
    app.dependency_overrides[get_session] = _override_session
    mock_sched = MagicMock()
    with patch("main.start_social_schedule"), \
         patch("main.create_db_and_tables"), \
         patch("main.scheduler", mock_sched):
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c
    app.dependency_overrides.clear()


# ── Per-test: wipe rows before every test for full isolation ─────────────────

@pytest.fixture(autouse=True)
def clean_tables():
    _wipe()
    yield
    _wipe()


# ── DB session for data fixtures ──────────────────────────────────────────────

@pytest.fixture
def db_session():
    with Session(TEST_ENGINE) as s:
        yield s


# ── Reusable fixture data ─────────────────────────────────────────────────────

SAMPLE_MOOD = {
    "Economy": {
        "score": 15, "label": "Slightly Positive",
        "dominant_emotions": ["optimism"], "category": "Economy",
    },
    "Technology & AI": {
        "score": 60, "label": "Positive",
        "dominant_emotions": ["enthusiasm"], "category": "Technology & AI",
    },
}

SAMPLE_SIGNALS = [
    {
        "category": "Economy", "signal": "bullish",
        "insight": "Strong economic indicators support equity exposure.",
        "tickers": ["SPY", "DIA"], "confidence": "medium",
    },
    {
        "category": "Technology & AI", "signal": "bullish",
        "insight": "AI momentum is driving semiconductor demand.",
        "tickers": ["QQQ", "NVDA", "SMH"], "confidence": "high",
    },
]

SAMPLE_TOPICS = [
    {
        "category": "Economy", "trend": "rising", "volume": 500,
        "sub_topics": ["Fed holds rates steady at 4.25%", "Jobs growth beats forecast"],
    },
]

SAMPLE_MARKETS = [
    {
        "source": "Kalshi", "question": "Will Fed cut rates in June?",
        "yes_pct": 63.0, "no_pct": 37.0, "volume_usd": 50000,
        "category": "Economy",
    },
]


@pytest.fixture
def snapshot(clean_tables, db_session):
    """Pre-populated SocialSnapshot. Depends on clean_tables to guarantee ordering."""
    s = SocialSnapshot(
        captured_at=datetime(2026, 5, 1, 12, 0, 0),
        mood_scores=json.dumps(SAMPLE_MOOD),
        trending_topics=json.dumps(SAMPLE_TOPICS),
        platform_data=json.dumps({
            "investment_signals": SAMPLE_SIGNALS,
            "tech_momentum": [],
        }),
        trend_history=json.dumps({"Economy": 500}),
    )
    db_session.add(s)
    db_session.commit()
    db_session.refresh(s)
    return s


@pytest.fixture
def market_snapshot(clean_tables, db_session):
    """Pre-populated MarketSnapshot. Depends on clean_tables to guarantee ordering."""
    ms = MarketSnapshot(
        captured_at=datetime(2026, 5, 1, 12, 0, 0),
        markets_json=json.dumps(SAMPLE_MARKETS),
    )
    db_session.add(ms)
    db_session.commit()
    db_session.refresh(ms)
    return ms
