import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.social.mood_scorer import _score_mood_fallback

# ── Helpers ───────────────────────────────────────────────────────────────────

def score_to_label(score: int) -> str:
    if score > 10:
        return "positive"
    if score < -10:
        return "negative"
    return "neutral"

def make_posts(titles: list, platform: str) -> list:
    return [{"title": t, "score": 10, "num_comments": 5, "platform": platform}
            for t in titles]

# ── Fixtures ──────────────────────────────────────────────────────────────────

POSITIVE_TITLES = [
    "Markets rally on strong earnings growth",
    "Tech stocks soar to record highs",
    "Fed signals rate cuts — rally expected",
    "Jobs growth beats forecast for third month",
    "Investor confidence reaches multi-year high",
]

NEGATIVE_TITLES = [
    "Recession fears grow as GDP contracts",
    "Layoffs surge across tech sector",
    "Bank failure sparks financial crisis fears",
    "Markets crash on inflation shock",
    "Consumer confidence collapses amid uncertainty",
]

MIXED_TITLES = [
    "Markets show uncertainty ahead of Fed decision",
    "Mixed signals from jobs report",
    "Tech gains offset by energy sector losses",
]

# ── Consistency tests ─────────────────────────────────────────────────────────

def test_positive_sentiment_consistency():
    """Reddit and HN posts with clearly positive language should both score positive."""
    reddit_result = _score_mood_fallback("Economy", make_posts(POSITIVE_TITLES, "Reddit"))
    hn_result     = _score_mood_fallback("Economy", make_posts(POSITIVE_TITLES, "Hacker News"))

    reddit_label = score_to_label(reddit_result["score"])
    hn_label     = score_to_label(hn_result["score"])

    assert reddit_label == hn_label, (
        f"Direction mismatch: reddit={reddit_label} ({reddit_result['score']}), "
        f"hn={hn_label} ({hn_result['score']})"
    )

def test_negative_sentiment_consistency():
    """Reddit and HN posts with clearly negative language should both score negative."""
    reddit_result = _score_mood_fallback("Economy", make_posts(NEGATIVE_TITLES, "Reddit"))
    hn_result     = _score_mood_fallback("Economy", make_posts(NEGATIVE_TITLES, "Hacker News"))

    reddit_label = score_to_label(reddit_result["score"])
    hn_label     = score_to_label(hn_result["score"])

    assert reddit_label == hn_label, (
        f"Direction mismatch: reddit={reddit_label} ({reddit_result['score']}), "
        f"hn={hn_label} ({hn_result['score']})"
    )

# ── Confidence tests ──────────────────────────────────────────────────────────

def test_sentiment_confidence_positive():
    """Same positive content from both sources should produce scores within 30 points."""
    reddit_score = _score_mood_fallback("Economy", make_posts(POSITIVE_TITLES, "Reddit"))["score"]
    hn_score     = _score_mood_fallback("Economy", make_posts(POSITIVE_TITLES, "Hacker News"))["score"]

    variance = abs(reddit_score - hn_score)
    assert variance <= 30, (
        f"Low confidence — variance={variance} points "
        f"(reddit={reddit_score}, hn={hn_score})"
    )

def test_sentiment_confidence_negative():
    """Same negative content from both sources should produce scores within 30 points."""
    reddit_score = _score_mood_fallback("Economy", make_posts(NEGATIVE_TITLES, "Reddit"))["score"]
    hn_score     = _score_mood_fallback("Economy", make_posts(NEGATIVE_TITLES, "Hacker News"))["score"]

    variance = abs(reddit_score - hn_score)
    assert variance <= 30, (
        f"Low confidence — variance={variance} points "
        f"(reddit={reddit_score}, hn={hn_score})"
    )

# ── Edge case tests ───────────────────────────────────────────────────────────

def test_empty_posts_returns_neutral():
    """Empty post list should return a neutral score of 0."""
    result = _score_mood_fallback("Economy", [])
    assert result["score"] == 0
    assert result["label"] == "Neutral"

def test_score_in_valid_range():
    """Score must always fall within the -100..+100 range."""
    for titles in [POSITIVE_TITLES, NEGATIVE_TITLES, MIXED_TITLES]:
        result = _score_mood_fallback("Economy", make_posts(titles, "Reddit"))
        assert -100 <= result["score"] <= 100, f"Score out of range: {result['score']}"

def test_result_has_required_fields():
    """Result dict must contain every field the frontend expects."""
    result = _score_mood_fallback("Economy", make_posts(POSITIVE_TITLES, "Reddit"))
    for field in ["score", "label", "dominant_emotions", "category"]:
        assert field in result, f"Missing required field: {field}"
