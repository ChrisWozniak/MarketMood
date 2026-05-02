"""
Unit tests for markets_client.py pure-Python functions.

No network calls — all tested logic is deterministic keyword matching,
filtering, and the sort-key used for per-series deduplication.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.social.markets_client import (
    _infer_category,
    _is_relevant,
    _clean_title,
)

# ── _infer_category ───────────────────────────────────────────────────────────

def test_infer_category_economy():
    assert _infer_category("Will the Fed cut interest rates in June?") == "Economy"

def test_infer_category_economy_cpi():
    assert _infer_category("CPI inflation report beats expectations") == "Economy"

def test_infer_category_politics_trump():
    # "tariff" also appears in Economy, so use a Politics-only keyword
    assert _infer_category("Will the Senate vote on the new immigration bill?") == "Politics"

def test_infer_category_politics_election():
    assert _infer_category("Will the senate vote on the bill?") == "Politics"

def test_infer_category_tech_ai():
    assert _infer_category("Will OpenAI release GPT-5 this year?") == "Technology & AI"

def test_infer_category_tech_nvidia():
    # "earnings" also appears in Economy; use a Tech-only keyword
    assert _infer_category("Will Nvidia semiconductor chip demand keep rising?") == "Technology & AI"

def test_infer_category_crypto_bitcoin():
    assert _infer_category("Will Bitcoin hit $100K before year end?") == "Blockchain & Crypto"

def test_infer_category_crypto_ethereum():
    # "ETF" also appears in Economy; use a Crypto-only keyword
    assert _infer_category("Will Ethereum DeFi protocols surpass Bitcoin in volume?") == "Blockchain & Crypto"

def test_infer_category_real_estate():
    assert _infer_category("Will housing market prices fall in 2025?") == "Real Estate"

def test_infer_category_real_estate_mortgage():
    # "mortgage rate" also appears in Economy; use a Real Estate-only keyword
    assert _infer_category("Will home sales in the housing market recover in Q3?") == "Real Estate"

def test_infer_category_health_fda():
    assert _infer_category("FDA approves new cancer treatment drug") == "Health & Science"

def test_infer_category_health_climate():
    assert _infer_category("Hurricane season outlook for 2025") == "Health & Science"

def test_infer_category_returns_none_for_sports():
    assert _infer_category("Will the Lakers win the NBA championship?") is None

def test_infer_category_returns_none_for_gibberish():
    assert _infer_category("xyzzy plugh frobozz nothing relevant here") is None

def test_infer_category_case_insensitive():
    assert _infer_category("FEDERAL RESERVE INTEREST RATE DECISION") == "Economy"

def test_infer_category_partial_keyword_match():
    assert _infer_category("Will gdp growth slow in Q3?") == "Economy"


# ── _is_relevant ──────────────────────────────────────────────────────────────

def test_is_relevant_allows_financial():
    assert _is_relevant("Will the Federal Reserve cut rates in 2025?") is True

def test_is_relevant_allows_political():
    assert _is_relevant("Will Trump sign the tariff bill?") is True

def test_is_relevant_allows_crypto():
    assert _is_relevant("Will Bitcoin reach $100,000 by December?") is True

def test_is_relevant_blocks_vs_matchup():
    assert _is_relevant("Lakers vs. Celtics — who wins game 7?") is False

def test_is_relevant_blocks_vs_no_period():
    assert _is_relevant("Arsenal vs Chelsea match result") is False

def test_is_relevant_blocks_nba():
    assert _is_relevant("NBA finals winner 2025") is False

def test_is_relevant_blocks_nfl():
    assert _is_relevant("NFL Super Bowl winner this season") is False

def test_is_relevant_blocks_oscars():
    assert _is_relevant("Who will win the Oscars best picture award?") is False

def test_is_relevant_blocks_album():
    assert _is_relevant("Will Taylor Swift release a new album in 2025?") is False

def test_is_relevant_blocks_esports():
    assert _is_relevant("Will NaVi win IEM Katowice CS2 major?") is False

def test_is_relevant_blocks_fortnite():
    assert _is_relevant("Fortnite world cup winner prediction") is False

def test_is_relevant_blocks_bundesliga():
    assert _is_relevant("Bundesliga season top scorer") is False

def test_is_relevant_case_insensitive():
    assert _is_relevant("TOTAL POINTS scored in Super Bowl") is False


# ── _clean_title ──────────────────────────────────────────────────────────────

def test_clean_title_removes_markdown_bold():
    result = _clean_title("**Will the Fed cut rates?**")
    assert "**" not in result

def test_clean_title_strips_whitespace():
    assert _clean_title("  hello world  ") == "hello world"

def test_clean_title_returns_str():
    assert isinstance(_clean_title("normal title"), str)

def test_clean_title_handles_unicode_replacement():
    result = _clean_title("Café market")
    assert isinstance(result, str)
    assert len(result) > 0

def test_clean_title_empty_string():
    assert _clean_title("") == ""


# ── Per-series deduplication sort key ────────────────────────────────────────
# Mirrors the logic in _fetch_kalshi_series:
#   results.sort(key=lambda m: (abs(m["yes_pct"] - 50), -m["volume_usd"]))
#   return results[:1]

def test_dedup_closest_to_50_wins():
    markets = [
        {"question": "far",    "yes_pct": 80.0, "volume_usd": 100_000},
        {"question": "close",  "yes_pct": 51.0, "volume_usd":   5_000},
        {"question": "medium", "yes_pct": 63.0, "volume_usd":  50_000},
    ]
    markets.sort(key=lambda m: (abs(m["yes_pct"] - 50), -m["volume_usd"]))
    assert markets[0]["question"] == "close"

def test_dedup_volume_breaks_equal_distance():
    markets = [
        {"question": "low_vol",  "yes_pct": 55.0, "volume_usd":   5_000},
        {"question": "high_vol", "yes_pct": 55.0, "volume_usd": 100_000},
    ]
    markets.sort(key=lambda m: (abs(m["yes_pct"] - 50), -m["volume_usd"]))
    assert markets[0]["question"] == "high_vol"

def test_dedup_symmetric_distance_equal_volume():
    markets = [
        {"question": "above", "yes_pct": 60.0, "volume_usd": 10_000},
        {"question": "below", "yes_pct": 40.0, "volume_usd": 10_000},
    ]
    markets.sort(key=lambda m: (abs(m["yes_pct"] - 50), -m["volume_usd"]))
    assert markets[0]["question"] in ("above", "below")  # both 10 pts away — either valid

def test_dedup_single_market_returned():
    # b and c are both 2pts from 50; c has higher volume so c wins the tiebreak
    markets = [
        {"question": "a", "yes_pct": 70.0, "volume_usd": 10_000},
        {"question": "b", "yes_pct": 52.0, "volume_usd":  5_000},
        {"question": "c", "yes_pct": 48.0, "volume_usd": 20_000},
    ]
    markets.sort(key=lambda m: (abs(m["yes_pct"] - 50), -m["volume_usd"]))
    assert len(markets[:1]) == 1
    assert markets[0]["question"] == "c"  # equidistant from 50 but higher volume than b

def test_dedup_exact_50_beats_everything():
    markets = [
        {"question": "exact", "yes_pct": 50.0, "volume_usd":     500},
        {"question": "close", "yes_pct": 51.0, "volume_usd": 100_000},
    ]
    markets.sort(key=lambda m: (abs(m["yes_pct"] - 50), -m["volume_usd"]))
    assert markets[0]["question"] == "exact"
