"""
Investment signal generator for MoodMarket.
Uses Claude to map category mood scores -> sector/ticker implications.
"""
import os
import json
from google import genai as google_genai

_client = None

def _get_client() -> google_genai.Client:
    global _client
    if _client is None:
        _client = google_genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return _client


async def generate_investment_signals(
    mood_scores: dict,
    trending_topics: list,
    prediction_markets: list | None = None,
    housing_data: dict | None = None,
) -> list[dict]:
    """
    Ask Claude to analyze mood scores, trending topics, prediction market
    probabilities, and housing indicators to produce investment signal insights.

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

    # Build prediction markets section — most valuable signal layer
    markets_section = ""
    if prediction_markets:
        markets_lines = []
        for m in prediction_markets[:15]:
            src   = m.get("source", "")
            q     = m.get("question", "")
            yes   = m.get("yes_pct", 0)
            no    = m.get("no_pct", 0)
            vol   = m.get("volume_usd", 0)
            cat   = m.get("category", "")
            markets_lines.append(
                f"  [{src}] {q}\n"
                f"    YES {yes}% / NO {no}% | Volume ${vol:,.0f} | Category: {cat}"
            )
        markets_section = (
            "\n\nPREDICTION MARKET PROBABILITIES (crowd-sourced, highly calibrated):\n"
            + "\n".join(markets_lines)
            + "\n  Use these probabilities to adjust signal confidence — "
            "a high-volume market near 50/50 signals genuine uncertainty; "
            "a market at 80%+ signals strong crowd conviction."
        )

    # Build housing/FRED section
    housing_section = ""
    if housing_data:
        fred = housing_data.get("fred", {})
        redfin = housing_data.get("redfin", {})
        lines = []
        for label, data in fred.items():
            val   = data.get("value", "")
            unit  = data.get("unit", "")
            trend = data.get("trend", "")
            lines.append(f"  {label}: {val}{unit} ({trend})")
        for label, data in redfin.items():
            display = data.get("display", data.get("value", ""))
            trend   = data.get("trend", "")
            chg     = data.get("change_pct")
            chg_str = f" {'+' if chg and chg > 0 else ''}{chg}% MoM" if chg else ""
            lines.append(f"  {label}: {display}{chg_str} ({trend})")
        if lines:
            housing_section = (
                "\n\nHOUSING & REAL ESTATE INDICATORS (FRED + Redfin):\n"
                + "\n".join(lines)
                + "\n  Use these to inform signals for Real Estate, homebuilders (ITB, XHB), "
                "REITs (VNQ), and mortgage-sensitive sectors."
            )

    prompt = f"""You are a senior financial analyst. Synthesize ALL of the following data layers \
to generate investment signal insights. Weight prediction market probabilities heavily — \
they represent the most calibrated crowd forecasts available.

SOCIAL MOOD SCORES (scale -100 to +100, scored by AI from Reddit/HN/YouTube):
{mood_summary}

TRENDING TOPICS (by discussion volume):
{topics_summary}{markets_section}{housing_section}

For each category that has meaningful data, produce a JSON array of signal objects.
Each object must have exactly these fields:
- category: the category name
- signal: "bullish", "bearish", or "neutral"
- insight: 2-3 sentences synthesizing social mood + prediction market odds + any hard data
- tickers: array of 2-4 relevant stock/ETF symbols (e.g. ["NVDA", "QQQ"])
- confidence: "high" (multiple indicators agree), "medium" (mixed signals), or "low" (limited data)

Rules:
- If a prediction market directly addresses a category outcome, let it anchor the signal direction
- If sentiment and prediction markets disagree, flag this tension in the insight
- Include a Real Estate signal using the housing indicators if present
- This is informational analysis only, not financial advice
Respond with ONLY valid JSON array, no other text."""

    try:
        resp = _get_client().models.generate_content(model="models/gemini-2.5-flash", contents=prompt)
        raw  = resp.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as e:
        print(f"[investment_signals] Gemini error: {e}")
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
