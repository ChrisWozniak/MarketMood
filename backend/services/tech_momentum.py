"""
Technology momentum analyzer for MoodMarket.
Uses Claude to identify which technologies are gaining vs losing
public confidence based on trending topics and discussion patterns.
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


async def generate_tech_momentum(trending_topics: list) -> list[dict]:
    """
    Analyze trending topics to surface technology momentum signals.
    Answers: which technologies/companies are gaining or losing public confidence?

    Returns a list of momentum dicts:
    [
      {
        "technology": "AI Agents",
        "direction": "rising" | "declining" | "stable",
        "momentum_score": 0-100,
        "insight": "...",
        "key_companies": ["Anthropic", "OpenAI", "Microsoft"],
        "proxy_tickers": ["MSFT", "NVDA", "GOOGL"]
      },
      ...
    ]
    """
    tech_topics = [
        t for t in trending_topics
        if t.get("category") in ("Technology & AI", "Blockchain & Crypto")
    ]

    if not tech_topics:
        return []

    topics_summary = json.dumps(
        [{"category": t.get("category"),
          "trend": t.get("trend"),
          "volume_score": t.get("volume_score"),
          "sub_topics": t.get("sub_topics", [])}
         for t in tech_topics],
        indent=2
    )

    prompt = f"""You are a technology trend analyst. Based on the following social discussion data
from Reddit, Hacker News, and other platforms, identify which specific technologies and AI developments
are gaining or losing public confidence and developer mindshare.

TRENDING TECH TOPICS:
{topics_summary}

Produce a JSON array of momentum objects. Focus on specific technologies (e.g. "AI Agents",
"Ethereum L2", "Open Source LLMs") not just broad categories.

Each object must have exactly these fields:
- technology: specific technology or trend name
- direction: "rising", "declining", or "stable"
- momentum_score: 0-100 (100 = maximum positive momentum)
- insight: 2-3 sentences explaining what the discussion signals about this technology's trajectory
- key_companies: array of 2-3 companies leading or losing in this technology
- proxy_tickers: array of 1-3 stock symbols that serve as investment proxies

Respond with ONLY valid JSON array, no other text."""

    try:
        client = _get_client()
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = message.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as e:
        print(f"[tech_momentum] Claude error: {e}")
        return []
