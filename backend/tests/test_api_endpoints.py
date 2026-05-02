"""
Endpoint tests for all read-path API routes.

Uses the `client` fixture from conftest.py which wires a FastAPI TestClient
to an in-memory SQLite DB — no real DB file, no network, no Gemini calls.
POST /analyze and POST /generate are NOT tested here because they call Gemini;
those belong in integration tests with a mocked Gemini client.
"""

# ── Health ────────────────────────────────────────────────────────────────────

def test_health_ok(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ── GET /api/sentiment/latest ─────────────────────────────────────────────────

def test_sentiment_latest_empty_returns_404(client):
    r = client.get("/api/sentiment/latest")
    assert r.status_code == 404

def test_sentiment_latest_returns_snapshot(client, snapshot):
    r = client.get("/api/sentiment/latest")
    assert r.status_code == 200
    body = r.json()
    assert "mood_scores" in body
    assert "trending_topics" in body
    assert "captured_at" in body

def test_sentiment_latest_mood_scores_schema(client, snapshot):
    body = client.get("/api/sentiment/latest").json()
    economy = body["mood_scores"]["Economy"]
    assert economy["score"] == 15
    assert economy["label"] == "Slightly Positive"
    assert "dominant_emotions" in economy

def test_sentiment_latest_trending_topics_present(client, snapshot):
    body = client.get("/api/sentiment/latest").json()
    topics = body["trending_topics"]
    assert isinstance(topics, list)
    assert len(topics) >= 1
    assert topics[0]["category"] == "Economy"


# ── GET /api/sentiment/history ────────────────────────────────────────────────

def test_sentiment_history_empty_returns_empty_list(client):
    r = client.get("/api/sentiment/history")
    assert r.status_code == 200
    assert r.json() == []

def test_sentiment_history_returns_list(client, snapshot):
    r = client.get("/api/sentiment/history")
    assert r.status_code == 200
    history = r.json()
    assert len(history) >= 1

def test_sentiment_history_entry_schema(client, snapshot):
    history = client.get("/api/sentiment/history").json()
    entry = history[0]
    assert "id" in entry
    assert "captured_at" in entry
    assert "mood_scores" in entry

def test_sentiment_history_limit_param(client, snapshot):
    r = client.get("/api/sentiment/history?limit=1")
    assert r.status_code == 200
    assert len(r.json()) <= 1


# ── GET /api/signals/latest ───────────────────────────────────────────────────

def test_signals_latest_empty_returns_404(client):
    r = client.get("/api/signals/latest")
    assert r.status_code == 404

def test_signals_latest_returns_signals(client, snapshot):
    r = client.get("/api/signals/latest")
    assert r.status_code == 200
    body = r.json()
    assert "investment_signals" in body
    assert "tech_momentum" in body
    assert "captured_at" in body

def test_signals_latest_signal_count(client, snapshot):
    body = client.get("/api/signals/latest").json()
    assert len(body["investment_signals"]) == 2

def test_signals_latest_signal_schema(client, snapshot):
    signals = client.get("/api/signals/latest").json()["investment_signals"]
    for sig in signals:
        assert "category" in sig
        assert "signal" in sig
        assert sig["signal"] in ("bullish", "bearish", "neutral")
        assert "insight" in sig
        assert "tickers" in sig
        assert "confidence" in sig
        assert sig["confidence"] in ("high", "medium", "low")

def test_signals_latest_economy_is_bullish(client, snapshot):
    signals = client.get("/api/signals/latest").json()["investment_signals"]
    by_cat = {s["category"]: s for s in signals}
    assert by_cat["Economy"]["signal"] == "bullish"

def test_signals_latest_tech_is_high_confidence(client, snapshot):
    signals = client.get("/api/signals/latest").json()["investment_signals"]
    by_cat = {s["category"]: s for s in signals}
    assert by_cat["Technology & AI"]["confidence"] == "high"


# ── GET /api/social/markets ───────────────────────────────────────────────────

def test_social_markets_empty_returns_empty_list(client):
    r = client.get("/api/social/markets")
    assert r.status_code == 200
    body = r.json()
    assert body["markets"] == []
    assert body["captured_at"] is None

def test_social_markets_returns_snapshot(client, market_snapshot):
    r = client.get("/api/social/markets")
    assert r.status_code == 200
    body = r.json()
    assert len(body["markets"]) == 1
    assert body["captured_at"] is not None

def test_social_markets_entry_schema(client, market_snapshot):
    market = client.get("/api/social/markets").json()["markets"][0]
    assert market["source"] == "Kalshi"
    assert market["question"] == "Will Fed cut rates in June?"
    assert market["yes_pct"] == 63.0
    assert market["volume_usd"] == 50000


# ── GET /api/social/latest ────────────────────────────────────────────────────

def test_social_latest_empty_returns_404(client):
    r = client.get("/api/social/latest")
    assert r.status_code == 404

def test_social_latest_returns_snapshot(client, snapshot):
    r = client.get("/api/social/latest")
    assert r.status_code == 200
    body = r.json()
    assert "mood_scores" in body
    assert "trending_topics" in body
    assert "captured_at" in body


# ── GET /api/social/history ───────────────────────────────────────────────────

def test_social_history_empty_returns_empty_list(client):
    r = client.get("/api/social/history")
    assert r.status_code == 200
    assert r.json() == []

def test_social_history_entry_schema(client, snapshot):
    history = client.get("/api/social/history").json()
    assert len(history) >= 1
    entry = history[0]
    assert "id" in entry
    assert "captured_at" in entry
    assert "topic_count" in entry

def test_social_history_topic_count_correct(client, snapshot):
    entry = client.get("/api/social/history").json()[0]
    assert entry["topic_count"] == 1   # SAMPLE_TOPICS has 1 topic


# ── GET /api/social/trends/{topic} ───────────────────────────────────────────

def test_social_trends_empty_returns_404(client):
    r = client.get("/api/social/trends/Economy")
    assert r.status_code == 404

def test_social_trends_returns_trend_array(client, snapshot):
    r = client.get("/api/social/trends/Economy")
    assert r.status_code == 200
    body = r.json()
    assert body["topic"] == "Economy"
    assert isinstance(body["trend"], list)
    assert len(body["trend"]) >= 1

def test_social_trends_entry_has_date_and_volume(client, snapshot):
    trend = client.get("/api/social/trends/Economy").json()["trend"]
    assert "date" in trend[0]
    assert "volume" in trend[0]
    assert trend[0]["volume"] == 500   # from SAMPLE trend_history
