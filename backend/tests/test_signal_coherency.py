"""
Signal coherency regression tests — verify that investment signal logic
produces consistent, well-formed output. No API key required (uses _fallback_signals only).
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.investment_signals import _fallback_signals

# ── Fixtures ──────────────────────────────────────────────────────────────────

STRONGLY_POSITIVE_MOOD = {
    "Economy": {"score": 65, "label": "Very Positive"},
    "Technology & AI": {"score": 72, "label": "Very Positive"},
}

STRONGLY_NEGATIVE_MOOD = {
    "Economy": {"score": -58, "label": "Negative"},
    "Politics": {"score": -71, "label": "Very Negative"},
}

MIXED_MOOD = {
    "Economy": {"score": 15, "label": "Slightly Positive"},
    "Politics": {"score": -12, "label": "Slightly Negative"},
    "Technology & AI": {"score": 5, "label": "Neutral"},
}

BOUNDARY_MOOD = {
    "Economy": {"score": 25, "label": "Positive"},         # above bullish threshold (>20)
    "Politics": {"score": -25, "label": "Negative"},       # below bearish threshold (<-20)
    "Blockchain & Crypto": {"score": 0, "label": "Neutral"},
}

# ── Schema / structure tests ──────────────────────────────────────────────────

def test_required_fields_present():
    """Every signal object must have: category, signal, insight, tickers, confidence."""
    signals = _fallback_signals(STRONGLY_POSITIVE_MOOD)
    for sig in signals:
        for field in ("category", "signal", "insight", "tickers", "confidence"):
            assert field in sig, f"Signal missing '{field}': {sig}"


def test_signal_values_are_valid():
    """signal must be bullish/bearish/neutral; confidence must be high/medium/low."""
    signals = _fallback_signals(MIXED_MOOD)
    valid_signals = {"bullish", "bearish", "neutral"}
    valid_confidence = {"high", "medium", "low"}
    for sig in signals:
        assert sig["signal"] in valid_signals, f"Invalid signal value: {sig['signal']!r}"
        assert sig["confidence"] in valid_confidence, f"Invalid confidence: {sig['confidence']!r}"


def test_insight_is_nonempty_string():
    """insight must be a non-empty string for every signal."""
    for mood in (STRONGLY_POSITIVE_MOOD, STRONGLY_NEGATIVE_MOOD, MIXED_MOOD):
        for sig in _fallback_signals(mood):
            assert isinstance(sig["insight"], str) and sig["insight"].strip(), (
                f"Empty insight for {sig.get('category')}"
            )


def test_tickers_are_nonempty_strings():
    """tickers must be a non-empty list of non-empty strings."""
    signals = _fallback_signals(STRONGLY_POSITIVE_MOOD)
    for sig in signals:
        assert isinstance(sig["tickers"], list), f"tickers is not a list: {sig}"
        assert len(sig["tickers"]) > 0, f"Empty tickers list for {sig['category']}"
        for t in sig["tickers"]:
            assert isinstance(t, str) and t.strip(), f"Invalid ticker value: {t!r}"

# ── Directional coherency tests ───────────────────────────────────────────────

def test_strongly_positive_mood_not_bearish():
    """Mood scores of +65/+72 must NOT produce bearish signals."""
    signals = _fallback_signals(STRONGLY_POSITIVE_MOOD)
    for sig in signals:
        assert sig["signal"] != "bearish", (
            f"{sig['category']} with strongly positive mood incorrectly flagged as bearish"
        )


def test_strongly_negative_mood_not_bullish():
    """Mood scores of -58/-71 must NOT produce bullish signals."""
    signals = _fallback_signals(STRONGLY_NEGATIVE_MOOD)
    for sig in signals:
        assert sig["signal"] != "bullish", (
            f"{sig['category']} with strongly negative mood incorrectly flagged as bullish"
        )


def test_neutral_score_produces_neutral_signal():
    """A score of exactly 0 should produce a neutral signal."""
    signals = _fallback_signals({"Economy": {"score": 0, "label": "Neutral"}})
    assert len(signals) == 1
    assert signals[0]["signal"] == "neutral", (
        f"Score 0 should be neutral, got: {signals[0]['signal']}"
    )


def test_threshold_boundary_direction():
    """Scores at +25/-25/0 should be bullish, bearish, and neutral respectively.
    Fallback threshold is strictly > 20 for bullish, < -20 for bearish."""
    signals = _fallback_signals(BOUNDARY_MOOD)
    by_cat = {s["category"]: s["signal"] for s in signals}
    assert by_cat.get("Economy") == "bullish", f"Score +25 should be bullish, got {by_cat.get('Economy')}"
    assert by_cat.get("Politics") == "bearish", f"Score -25 should be bearish, got {by_cat.get('Politics')}"
    assert by_cat.get("Blockchain & Crypto") == "neutral", f"Score 0 should be neutral, got {by_cat.get('Blockchain & Crypto')}"

# ── Deduplication / structural integrity ─────────────────────────────────────

def test_no_duplicate_categories():
    """Each category must appear at most once in the signal list."""
    signals = _fallback_signals(MIXED_MOOD)
    categories = [s["category"] for s in signals]
    assert len(categories) == len(set(categories)), (
        f"Duplicate categories found: {[c for c in categories if categories.count(c) > 1]}"
    )


def test_signal_count_matches_mood_input():
    """Number of signals should equal number of mood categories provided."""
    for mood in (STRONGLY_POSITIVE_MOOD, STRONGLY_NEGATIVE_MOOD, MIXED_MOOD):
        signals = _fallback_signals(mood)
        assert len(signals) == len(mood), (
            f"Expected {len(mood)} signals, got {len(signals)}"
        )

# ── Edge cases ────────────────────────────────────────────────────────────────

def test_empty_mood_returns_empty_list():
    """Empty mood dict must return an empty signal list."""
    signals = _fallback_signals({})
    assert signals == [], f"Expected [], got {signals}"


def test_score_range_clamped():
    """Fallback should not crash on extreme scores outside -100..+100."""
    extreme_mood = {
        "Economy": {"score": 200, "label": "Extreme Positive"},
        "Politics": {"score": -200, "label": "Extreme Negative"},
    }
    signals = _fallback_signals(extreme_mood)
    assert len(signals) == 2
    for sig in signals:
        assert sig["signal"] in {"bullish", "bearish", "neutral"}
