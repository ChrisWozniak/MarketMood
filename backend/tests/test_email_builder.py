"""
Unit tests for email_sender.py helper functions and build_html_report().

No SMTP connection is made — only the HTML/text builder and pure helpers
are exercised. Safe to run without any email credentials.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime
from services.email_sender import (
    build_html_report,
    _score_bar,
    _vol_str,
    _find_best_url,
    _signal_emoji,
    _confidence_color,
    _ticker_badge_html,
    _THEMES,
)

# ── Shared fixture data ───────────────────────────────────────────────────────

MOOD = {
    "Economy":         {"score":  20, "label": "Slightly Positive"},
    "Technology & AI": {"score": -40, "label": "Slightly Negative"},
}
TOPICS = [
    {
        "category": "Economy", "trend": "rising",
        "sub_topics": ["Fed holds rates steady at 4.25%", "Jobs growth beats forecast"],
    },
]
SIGNALS = [
    {
        "category": "Economy", "signal": "bullish",
        "insight": "Strong economic indicators support equity exposure.",
        "tickers": ["SPY", "DIA"], "confidence": "high",
    },
    {
        "category": "Technology & AI", "signal": "bearish",
        "insight": "Sentiment turning cautious after sector rotation.",
        "tickers": ["QQQ"], "confidence": "medium",
    },
]
MARKETS = [
    {
        "source": "Kalshi", "question": "Will Fed cut rates in June?",
        "yes_pct": 63.0, "no_pct": 37.0, "volume_usd": 50_000,
        "category": "Economy",
    },
    {
        "source": "Polymarket", "question": "Will S&P 500 hit 6000 by end of 2025?",
        "yes_pct": 45.0, "no_pct": 55.0, "volume_usd": 1_200_000,
        "category": "Economy",
    },
]
TS = datetime(2026, 5, 1, 14, 0, 0)


# ── build_html_report: return type ───────────────────────────────────────────

def test_returns_tuple_of_two_strings():
    result = build_html_report(MOOD, TOPICS, SIGNALS, MARKETS, TS)
    assert isinstance(result, tuple) and len(result) == 2
    html, text = result
    assert isinstance(html, str) and isinstance(text, str)

def test_html_starts_with_doctype():
    html, _ = build_html_report(MOOD, TOPICS, SIGNALS, MARKETS, TS)
    assert html.strip().startswith("<!DOCTYPE html>")

def test_html_ends_with_closing_tag():
    html, _ = build_html_report(MOOD, TOPICS, SIGNALS, MARKETS, TS)
    assert "</html>" in html


# ── build_html_report: content presence ──────────────────────────────────────

def test_html_contains_category_names():
    html, _ = build_html_report(MOOD, TOPICS, SIGNALS, MARKETS, TS)
    assert "Economy" in html

def test_html_contains_bullish_signal():
    html, _ = build_html_report(MOOD, TOPICS, SIGNALS, MARKETS, TS)
    assert "bullish" in html.lower()

def test_html_contains_bearish_signal():
    html, _ = build_html_report(MOOD, TOPICS, SIGNALS, MARKETS, TS)
    assert "bearish" in html.lower()

def test_html_contains_ticker_with_yahoo_link():
    html, _ = build_html_report(MOOD, TOPICS, SIGNALS, MARKETS, TS)
    assert "SPY" in html
    assert "yahoo.com/quote/SPY" in html

def test_html_contains_market_question():
    html, _ = build_html_report(MOOD, TOPICS, SIGNALS, MARKETS, TS)
    assert "Will Fed cut rates in June?" in html

def test_html_contains_subtopic():
    html, _ = build_html_report(MOOD, TOPICS, SIGNALS, MARKETS, TS)
    assert "Fed holds rates steady at 4.25%" in html

def test_html_contains_timestamp():
    html, _ = build_html_report(MOOD, TOPICS, SIGNALS, MARKETS, TS)
    assert "2026" in html

def test_html_contains_run_type_scheduled():
    html, _ = build_html_report(MOOD, TOPICS, SIGNALS, MARKETS, TS, run_type="Scheduled")
    assert "Scheduled" in html

def test_html_contains_run_type_test():
    html, _ = build_html_report(MOOD, TOPICS, SIGNALS, MARKETS, TS, run_type="Test")
    assert "Test" in html

def test_html_contains_market_mood_title():
    html, _ = build_html_report(MOOD, TOPICS, SIGNALS, MARKETS, TS)
    assert "Market Mood" in html


# ── build_html_report: plain text ────────────────────────────────────────────

def test_plain_text_contains_disclaimer():
    _, text = build_html_report(MOOD, TOPICS, SIGNALS, MARKETS, TS)
    assert "DISCLAIMER" in text or "Not financial advice" in text

def test_plain_text_contains_signal_category():
    _, text = build_html_report(MOOD, TOPICS, SIGNALS, MARKETS, TS)
    assert "Economy" in text

def test_plain_text_contains_signal_direction():
    _, text = build_html_report(MOOD, TOPICS, SIGNALS, MARKETS, TS)
    assert "BULLISH" in text

def test_plain_text_contains_market_mood_header():
    _, text = build_html_report(MOOD, TOPICS, SIGNALS, MARKETS, TS)
    assert "Market Mood" in text

def test_plain_text_contains_score_bar():
    _, text = build_html_report(MOOD, TOPICS, SIGNALS, MARKETS, TS)
    assert "█" in text or "░" in text


# ── Theme differences ─────────────────────────────────────────────────────────

def test_dark_theme_uses_dark_page_color():
    html, _ = build_html_report(MOOD, TOPICS, SIGNALS, MARKETS, TS, theme="dark")
    assert _THEMES["dark"]["page"] in html

def test_light_theme_uses_light_page_color():
    html, _ = build_html_report(MOOD, TOPICS, SIGNALS, MARKETS, TS, theme="light")
    assert _THEMES["light"]["page"] in html

def test_dark_and_light_html_differ():
    html_dark,  _ = build_html_report(MOOD, TOPICS, SIGNALS, MARKETS, TS, theme="dark")
    html_light, _ = build_html_report(MOOD, TOPICS, SIGNALS, MARKETS, TS, theme="light")
    assert html_dark != html_light

def test_invalid_theme_falls_back_to_dark():
    html, _ = build_html_report(MOOD, TOPICS, SIGNALS, MARKETS, TS, theme="neon_purple")
    assert _THEMES["dark"]["page"] in html


# ── build_html_report: empty inputs don't crash ───────────────────────────────

def test_empty_mood_does_not_raise():
    html, text = build_html_report({}, [], [], [], TS)
    assert isinstance(html, str)

def test_empty_signals_omits_signals_section():
    html, _ = build_html_report(MOOD, TOPICS, [], MARKETS, TS)
    assert "Investment Signals" not in html

def test_empty_markets_omits_markets_section():
    html, _ = build_html_report(MOOD, TOPICS, SIGNALS, [], TS)
    assert "Prediction Market" not in html

def test_empty_topics_omits_topics_section():
    html, _ = build_html_report(MOOD, [], SIGNALS, MARKETS, TS)
    assert "Trending Topics" not in html


# ── _score_bar ────────────────────────────────────────────────────────────────

def test_score_bar_always_20_chars():
    for score in [-100, -50, -1, 0, 1, 50, 100]:
        assert len(_score_bar(score)) == 20

def test_score_bar_minimum_all_empty():
    assert _score_bar(-100) == "░" * 20

def test_score_bar_maximum_all_filled():
    assert _score_bar(100) == "█" * 20

def test_score_bar_zero_is_half_filled():
    bar = _score_bar(0)
    assert bar.count("█") == 10
    assert bar.count("░") == 10

def test_score_bar_positive_more_filled_than_zero():
    assert _score_bar(50).count("█") > _score_bar(0).count("█")

def test_score_bar_negative_less_filled_than_zero():
    assert _score_bar(-50).count("█") < _score_bar(0).count("█")


# ── _vol_str ──────────────────────────────────────────────────────────────────

def test_vol_str_millions():
    assert _vol_str(1_500_000) == "$1.5M"

def test_vol_str_exact_million():
    assert _vol_str(1_000_000) == "$1.0M"

def test_vol_str_thousands():
    assert _vol_str(25_000) == "$25K"

def test_vol_str_exact_thousand():
    assert _vol_str(1_000) == "$1K"

def test_vol_str_small():
    assert _vol_str(500) == "$500"

def test_vol_str_zero():
    assert _vol_str(0) == "$0"


# ── _find_best_url ────────────────────────────────────────────────────────────

def test_find_best_url_exact_match():
    posts = [{"title": "Fed holds rates steady at 4.25%", "url": "https://example.com/fed"}]
    assert _find_best_url("Fed holds rates steady at 4.25%", posts) == "https://example.com/fed"

def test_find_best_url_partial_overlap():
    posts = [{"title": "Federal Reserve holds interest rates steady", "url": "https://example.com/fed"}]
    url = _find_best_url("Fed holds rates steady", posts)
    assert url != ""

def test_find_best_url_no_overlap():
    posts = [{"title": "Lakers win championship", "url": "https://example.com/lakers"}]
    assert _find_best_url("Fed holds rates steady at 4.25%", posts) == ""

def test_find_best_url_empty_posts():
    assert _find_best_url("Fed holds rates steady", []) == ""

def test_find_best_url_empty_headline():
    posts = [{"title": "Fed holds rates steady", "url": "https://example.com/fed"}]
    assert _find_best_url("", posts) == ""

def test_find_best_url_picks_best_of_multiple():
    posts = [
        {"title": "Basketball game recap", "url": "https://example.com/sports"},
        {"title": "Fed holds interest rates steady at 4.25%", "url": "https://example.com/fed"},
    ]
    url = _find_best_url("Fed holds rates steady at 4.25%", posts)
    assert url == "https://example.com/fed"


# ── _signal_emoji ─────────────────────────────────────────────────────────────

def test_signal_emoji_bullish():
    assert _signal_emoji("bullish") == "📈"

def test_signal_emoji_bearish():
    assert _signal_emoji("bearish") == "📉"

def test_signal_emoji_neutral():
    assert _signal_emoji("neutral") == "⚖️"

def test_signal_emoji_unknown_falls_back_to_neutral():
    assert _signal_emoji("unknown") == "⚖️"


# ── _confidence_color ─────────────────────────────────────────────────────────

def test_confidence_color_high_is_green():
    assert _confidence_color("high") == "#22c55e"

def test_confidence_color_medium_is_amber():
    assert _confidence_color("medium") == "#f59e0b"

def test_confidence_color_low_is_slate():
    assert _confidence_color("low") == "#94a3b8"

def test_confidence_color_unknown_falls_back():
    assert _confidence_color("unknown") == "#94a3b8"


# ── _ticker_badge_html ────────────────────────────────────────────────────────

def test_ticker_badge_contains_ticker_symbol():
    C = _THEMES["dark"]
    html = _ticker_badge_html("NVDA", C)
    assert "NVDA" in html

def test_ticker_badge_links_to_yahoo():
    C = _THEMES["dark"]
    html = _ticker_badge_html("NVDA", C)
    assert "yahoo.com/quote/NVDA" in html

def test_ticker_badge_is_anchor_tag():
    C = _THEMES["dark"]
    html = _ticker_badge_html("SPY", C)
    assert html.startswith("<a ")
    assert "</a>" in html
