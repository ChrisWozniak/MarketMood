"""
Investment signal generator for MoodMarket.
Uses Claude to map category mood scores → sector/ticker implications.
"""
import os
import json
import anthropic

_client = None

def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


async def generate_investment_signals(
    mood_scores: dict,
    trending_topics: list,
) -> list[dict]:
    """
    Ask Claude to analyze mood scores and trending topics and produce
    investment signal insights per category.

    Returns a list of signal dicts:
    [
      {
        "category": "Technology & AI",
        "signal": "bullish" | "bearish" | "neutral",
        "insight": "...",
        "tickers": ["NVDA", "MSFT", "GOOGL"],
        "confidence": "high" | "medium" | "low"
      },
      ...
    ]
    """
    mood_summary = json.dumps(mood_scores, indent=2)
    topics_summary = json.dumps(
        [{"category": t.get("category"), "trend": t.get("trend"), "sub_topics": t.get("sub_topics", [])}
         for t in trending_topics[:10]],
        indent=2
    )

    prompt = f"""You are a financial analyst assistant. Based on the following social sentiment data,
generate investment signal insights for each category. Connect public mood to potential market implications.

MOOD SCORES (scale -100 to +100):
{mood_summary}

TRENDING TOPICS:
{topics_summary}

For each category that has meaningful data, produce a JSON array of signal objects.
Each object must have exactly these fields:
- category: the category name
- signal: "bullish", "bearish", or "neutral"
- insight: 2-3 sentence explanation connecting mood to investment implication
- tickers: array of 2-4 relevant stock/ETF symbols (e.g. ["NVDA", "QQQ"])
- confidence: "high", "medium", or "low"

Important: This is informational analysis only, not financial advice.
Respond with ONLY valid JSON array, no other text."""

    try:
        client = _get_client()
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = message.content[0].text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as e:
        print(f"[investment_signals] Claude error: {e}")
        return _fallback_signals(mood_scores)


def _fallback_signals(mood_scores: dict) -> list[dict]:
    """Simple rule-based fallback if Claude is unavailable."""
    CATEGORY_TICKERS = {
        "Economy": ["SPY", "TLT", "DXY", "GLD"],
        "Technology & AI": ["QQQ", "NVDA", "MSFT", "GOOGL"],
        "Blockchain & Crypto": ["BTC-USD", "ETH-USD", "COIN"],
        "Sector Sentiment": ["XLE", "XLK", "XLV", "XLF"],
        "Politics": ["VIX", "TLT", "GLD"],
        "Prediction Markets": ["SPY", "VIX"],
    }
    results = []
    for cat, score_data in mood_scores.items():
        score = score_data.get("score", 0) if isinstance(score_data, dict) else 0
        signal = "bullish" if score > 20 else "bearish" if score < -20 else "neutral"
        results.append({
            "category": cat,
            "signal": signal,
            "insight": f"Sentiment score of {score} suggests {signal} outlook for this category.",
            "tickers": CATEGORY_TICKERS.get(cat, ["SPY"]),
            "confidence": "low",
        })
    return results
