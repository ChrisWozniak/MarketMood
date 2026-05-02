"""
Integration test for run_social_analysis().

All external calls (network, AI, SMTP) are mocked via ExitStack.
Uses its own isolated in-memory SQLite engine — does NOT depend on
conftest.TEST_ENGINE so there is no module-import ambiguity.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))  # backend/

import json
import pytest
from contextlib import ExitStack
from contextlib import contextmanager
from unittest.mock import MagicMock, AsyncMock, patch
from sqlalchemy import text
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, select, create_engine

from models import SocialSnapshot, MarketSnapshot


# ── Isolated in-memory DB for this module ────────────────────────────────────

_AGG_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest.fixture(scope="module", autouse=True)
def _create_agg_tables():
    SQLModel.metadata.create_all(_AGG_ENGINE)
    yield


def _wipe():
    with _AGG_ENGINE.connect() as conn:
        conn.execute(text("DELETE FROM socialsnapshot"))
        conn.execute(text("DELETE FROM marketsnapshot"))
        conn.commit()


@pytest.fixture(autouse=True)
def _wipe_agg_tables():
    _wipe()
    yield
    _wipe()


# ── Shared mock return values ─────────────────────────────────────────────────

MOCK_REDDIT = {
    "Economy": [
        {
            "title": "Fed holds rates", "score": 100, "num_comments": 50,
            "platform": "Reddit", "url": "https://reddit.com/r/a",
            "created_utc": 1700000000,
        },
    ]
}
MOCK_HN = {
    "Economy": [
        {
            "title": "Rates stable", "score": 200, "num_comments": 80,
            "platform": "Hacker News", "url": "https://news.ycombinator.com/1",
            "created_utc": 1700000001,
        },
    ]
}
MOCK_MARKETS = [
    {
        "source": "Kalshi", "question": "Will Fed cut?",
        "yes_pct": 55.0, "no_pct": 45.0, "volume_usd": 50_000,
        "category": "Economy",
    },
]
MOCK_MOOD = {
    "Economy": {
        "score": 30, "label": "Slightly Positive",
        "dominant_emotions": ["optimism"], "category": "Economy",
    }
}
MOCK_WATCHLIST_MOOD = {
    "score": 20, "label": "Slightly Positive",
    "dominant_emotions": ["curiosity"], "category": "Custom Watchlist",
}
MOCK_SIGNALS = [
    {
        "category": "Economy", "signal": "bullish",
        "insight": "Good.", "tickers": ["SPY"], "confidence": "medium",
    },
]
MOCK_MOMENTUM = [
    {
        "technology": "AI Agents", "direction": "rising", "momentum_score": 70,
        "insight": "Growing.", "key_companies": ["OpenAI"], "proxy_tickers": ["MSFT"],
    },
]
MOCK_SUBTOPICS     = {"Economy": ["Fed holds rates steady"]}
MOCK_TREND_HISTORY = {"Economy": {"direction": "rising", "volumes": [500]}}
MOCK_RANKED_TOPICS = [{"category": "Economy", "trend": "rising", "volume": 500}]
MOCK_FRED          = {"indicators": {}, "posts": []}
MOCK_REDFIN        = {"stats": {}, "posts": []}


# ── Helper: ExitStack with all 15 calls mocked ───────────────────────────────

def _make_patches(
    email_mock: AsyncMock | None = None,
    override_mood: AsyncMock | None = None,
) -> ExitStack:
    import services.social.aggregator as agg
    import services.investment_signals as inv_mod
    import services.tech_momentum as tech_mod
    import services.email_sender as email_mod

    mood_mock = override_mood or AsyncMock(return_value=MOCK_MOOD)
    if email_mock is None:
        email_mock = AsyncMock(return_value=True)

    stack = ExitStack()
    stack.enter_context(patch.object(agg,      "engine",                      _AGG_ENGINE))
    stack.enter_context(patch.object(agg,      "fetch_reddit_posts",          AsyncMock(return_value=MOCK_REDDIT)))
    stack.enter_context(patch.object(agg,      "fetch_hackernews_posts",      AsyncMock(return_value=MOCK_HN)))
    stack.enter_context(patch.object(agg,      "fetch_youtube_videos",        MagicMock(return_value={})))
    stack.enter_context(patch.object(agg,      "fetch_top_markets",           AsyncMock(return_value=MOCK_MARKETS)))
    stack.enter_context(patch.object(agg,      "fetch_fred_housing",          AsyncMock(return_value=MOCK_FRED)))
    stack.enter_context(patch.object(agg,      "fetch_redfin_stats",          AsyncMock(return_value=MOCK_REDFIN)))
    stack.enter_context(patch.object(agg,      "score_all_moods",             mood_mock))
    stack.enter_context(patch.object(agg,      "score_watchlist_mood",        AsyncMock(return_value=MOCK_WATCHLIST_MOOD)))
    stack.enter_context(patch.object(agg,      "extract_all_sub_topics",      AsyncMock(return_value=MOCK_SUBTOPICS)))
    stack.enter_context(patch.object(agg,      "build_trend_history",         MagicMock(return_value=MOCK_TREND_HISTORY)))
    stack.enter_context(patch.object(agg,      "rank_trending_topics",        MagicMock(return_value=MOCK_RANKED_TOPICS)))
    stack.enter_context(patch.object(inv_mod,  "generate_investment_signals", AsyncMock(return_value=MOCK_SIGNALS)))
    stack.enter_context(patch.object(tech_mod, "generate_tech_momentum",      AsyncMock(return_value=MOCK_MOMENTUM)))
    stack.enter_context(patch.object(email_mod,"send_report_email",           email_mock))
    return stack


# ── Shared fixture: run analysis once, return (snapshot, email_mock) ─────────

@pytest.fixture
async def analysis_result():
    email_mock = AsyncMock(return_value=True)
    with _make_patches(email_mock=email_mock):
        from services.social.aggregator import run_social_analysis
        snapshot = await run_social_analysis()
    return snapshot, email_mock


# ── Happy-path tests ──────────────────────────────────────────────────────────

async def test_run_social_analysis_returns_snapshot(analysis_result):
    snapshot, _ = analysis_result
    assert isinstance(snapshot, SocialSnapshot)
    assert snapshot.id is not None


async def test_snapshot_mood_scores_saved(analysis_result):
    snapshot, _ = analysis_result
    mood = json.loads(snapshot.mood_scores)
    assert "Economy" in mood
    assert mood["Economy"]["score"] == 30


async def test_snapshot_trending_topics_saved(analysis_result):
    snapshot, _ = analysis_result
    topics = json.loads(snapshot.trending_topics)
    assert isinstance(topics, list)
    assert len(topics) >= 1


async def test_snapshot_platform_data_has_signals(analysis_result):
    snapshot, _ = analysis_result
    pd = json.loads(snapshot.platform_data)
    assert "investment_signals" in pd
    assert len(pd["investment_signals"]) >= 1


async def test_snapshot_platform_data_has_momentum(analysis_result):
    snapshot, _ = analysis_result
    pd = json.loads(snapshot.platform_data)
    assert "tech_momentum" in pd
    assert len(pd["tech_momentum"]) >= 1


async def test_market_snapshot_saved(analysis_result):
    with Session(_AGG_ENGINE) as s:
        rows = s.exec(select(MarketSnapshot)).all()
    assert len(rows) == 1
    assert json.loads(rows[0].markets_json)[0]["source"] == "Kalshi"


async def test_custom_tickers_appended_to_mood():
    with _make_patches():
        from services.social.aggregator import run_social_analysis
        snapshot = await run_social_analysis(custom_tickers=["NVDA"])
    mood = json.loads(snapshot.mood_scores)
    assert "Custom Watchlist" in mood


async def test_email_called_once(analysis_result):
    _, email_mock = analysis_result
    assert email_mock.call_count == 1


# ── Error-path test ───────────────────────────────────────────────────────────

async def test_email_not_called_on_exception():
    """If score_all_moods raises, no snapshot is saved and email is never sent."""
    email_mock   = AsyncMock(return_value=True)
    failing_mood = AsyncMock(side_effect=RuntimeError("AI unavailable"))
    with _make_patches(email_mock=email_mock, override_mood=failing_mood):
        from services.social.aggregator import run_social_analysis
        with pytest.raises(RuntimeError):
            await run_social_analysis()

    with Session(_AGG_ENGINE) as s:
        rows = s.exec(select(SocialSnapshot)).all()
    assert len(rows) == 0
    assert email_mock.call_count == 0
