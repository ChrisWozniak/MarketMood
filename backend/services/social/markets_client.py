"""
Prediction Market Pulse — Kalshi + Polymarket client.

Kalshi:  Query known active series tickers (generic /markets returns untraded stubs)
         Prices in 0-1 dollar range -> multiply by 100 for %
Polymarket: gamma-api, no auth required, returns outcomePrices as ["0.73","0.27"]
"""

import asyncio
import json
import httpx


def _print(msg: str) -> None:
    """Print safely — replaces any characters that can't be encoded on this platform."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", errors="replace").decode("ascii"))

POLYMARKET_URL = "https://gamma-api.polymarket.com/markets"
KALSHI_BASE    = "https://api.elections.kalshi.com/trade-api/v2/markets"
TIMEOUT        = 10.0

# Known active Kalshi series that have real prices and trading volume
KALSHI_SERIES = [
    "KXFED",          # Federal funds rate
    "KXGDP",          # US GDP growth
    "KXINFLATION",    # CPI / inflation
    "KXUNEMPLOYMENT", # Unemployment rate
    "KXTRUMP",        # Trump approval / actions
    "KXECON",         # Economy topics
    "KXWARMING",      # Climate / temperature
    "KXAI",           # AI topics
    # Excluded: KXBTC, KXETH, KXSP500, KXNASDAQ — short-term daily price ranges
    # always resolve near 0% or 100% (too specific), filtered out by the price filter
]

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Economy & Finance": [
        "fed", "federal reserve", "rate", "rates", "inflation", "gdp", "recession",
        "unemployment", "jobs", "market", "s&p", "dow", "nasdaq", "stock", "oil",
        "gold", "dollar", "debt", "deficit", "tariff", "trade", "cpi", "pce",
    ],
    "Politics": [
        "election", "president", "trump", "biden", "harris", "congress", "senate",
        "house", "republican", "democrat", "vote", "ballot", "impeach", "white house",
        "governor", "primary", "poll", "approval",
    ],
    "Technology & AI": [
        "ai", "artificial intelligence", "openai", "gpt", "llm", "tech", "apple",
        "google", "microsoft", "meta", "amazon", "nvidia", "chip", "crypto", "bitcoin",
        "ethereum", "blockchain", "spacex", "elon",
    ],
    "World Affairs": [
        "war", "ukraine", "russia", "china", "nato", "israel", "iran", "korea",
        "taiwan", "conflict", "sanction", "nuclear", "ceasefire", "summit", "india",
        "pakistan", "pope", "eu", "europe",
    ],
    "Health & Science": [
        "fda", "drug", "vaccine", "health", "covid", "cancer", "disease", "climate",
        "hurricane", "earthquake", "nasa", "space", "temperature", "celsius",
    ],
}


def _infer_category(text: str) -> str:
    lower = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return category
    return "General"


def _clean_title(title: str) -> str:
    """Remove markdown bold markers and sanitize Unicode for cross-platform safety."""
    return title.replace("**", "").encode("ascii", errors="replace").decode("ascii").strip()


async def _fetch_kalshi_series(client: httpx.AsyncClient, series: str) -> list[dict]:
    """Fetch markets for one Kalshi series ticker."""
    try:
        resp = await client.get(
            KALSHI_BASE,
            params={"status": "open", "series_ticker": series, "limit": 20},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=TIMEOUT,
        )
        if resp.status_code != 200:
            return []
        markets = resp.json().get("markets", [])
    except Exception as e:
        _print(f"[markets_client] Kalshi series {series} error: {e}")
        return []

    results = []
    for m in markets:
        try:
            title = _clean_title(m.get("title") or m.get("yes_sub_title") or "")
            if not title:
                continue

            # yes_ask_dollars is 0-1 (dollar per contract, face value $1)
            yes_ask = m.get("yes_ask_dollars")
            yes_bid = m.get("yes_bid_dollars")
            if yes_ask is None and yes_bid is None:
                continue

            ya = float(yes_ask or 0)
            yb = float(yes_bid or 0)
            if ya > 0 and yb > 0:
                yes_pct = ((ya + yb) / 2) * 100
            elif ya > 0:
                yes_pct = ya * 100
            elif yb > 0:
                yes_pct = yb * 100
            else:
                continue

            # Skip fully resolved outcomes only
            if yes_pct < 2 or yes_pct > 98:
                continue

            no_pct = 100.0 - yes_pct

            # Prefer liquidity_dollars (real USD locked), fall back to volume_fp
            volume = float(m.get("liquidity_dollars") or 0)
            if volume == 0:
                volume = float(m.get("volume_fp") or 0)
            if volume == 0:
                volume = float(m.get("open_interest_fp") or 0)

            # Skip markets with negligible activity (< 50 contracts / dollars)
            if volume < 50:
                continue

            results.append({
                "source": "Kalshi",
                "question": title,
                "yes_pct": round(yes_pct, 1),
                "no_pct": round(no_pct, 1),
                "volume_usd": round(volume, 0),
                "category": _infer_category(title),
            })
        except (TypeError, ValueError):
            continue

    return results


async def _fetch_kalshi(client: httpx.AsyncClient) -> list[dict]:
    """Fetch from all known Kalshi series concurrently."""
    tasks = [_fetch_kalshi_series(client, s) for s in KALSHI_SERIES]
    results_per_series = await asyncio.gather(*tasks)
    all_markets: list[dict] = [m for batch in results_per_series for m in batch]

    # Deduplicate by question text (some series overlap)
    seen: set[str] = set()
    unique = []
    for m in all_markets:
        key = m["question"].lower()[:60]
        if key not in seen:
            seen.add(key)
            unique.append(m)

    _print(f"[markets_client] Kalshi: {len(unique)} unique markets from {len(KALSHI_SERIES)} series")
    return unique


async def _fetch_polymarket(client: httpx.AsyncClient) -> list[dict]:
    """Fetch top active markets from Polymarket sorted by 24h volume."""
    try:
        resp = await client.get(
            POLYMARKET_URL,
            params={"closed": "false", "limit": 30, "order": "volume24hr", "ascending": "false"},
            timeout=TIMEOUT,
        )
        if resp.status_code != 200:
            _print(f"[markets_client] Polymarket HTTP {resp.status_code}")
            return []
        data = resp.json()
        markets = data if isinstance(data, list) else data.get("markets", [])
    except Exception as e:
        _print(f"[markets_client] Polymarket fetch failed: {e}")
        return []

    results = []
    for m in markets:
        try:
            question = (m.get("question") or m.get("title") or "").strip()
            question = question.encode("ascii", errors="replace").decode("ascii").strip()
            if not question:
                continue

            # outcomePrices: JSON string ["0.73","0.27"] or already a list
            outcome_raw = m.get("outcomePrices", "[]")
            prices = json.loads(outcome_raw) if isinstance(outcome_raw, str) else outcome_raw
            if len(prices) < 2:
                continue

            yes_pct = float(prices[0]) * 100
            no_pct  = float(prices[1]) * 100

            # Skip fully resolved outcomes only
            if yes_pct < 2 or yes_pct > 98:
                continue

            volume = float(m.get("volume24hr") or m.get("volume") or m.get("liquidity") or 0)
            if volume < 100:
                continue

            results.append({
                "source": "Polymarket",
                "question": question,
                "yes_pct": round(yes_pct, 1),
                "no_pct": round(no_pct, 1),
                "volume_usd": round(volume, 0),
                "category": _infer_category(question),
            })
        except (TypeError, ValueError, json.JSONDecodeError):
            continue

    _print(f"[markets_client] Polymarket: {len(results)} markets")
    return results


async def fetch_top_markets(top_n: int = 10) -> list[dict]:
    """
    Fetch and merge markets from Kalshi and Polymarket.
    Takes top N/2 from each source (sorted by their own volume) then interleaves,
    so both sources always appear regardless of volume scale differences.
    """
    async with httpx.AsyncClient() as client:
        kalshi_results, poly_results = await asyncio.gather(
            _fetch_kalshi(client),
            _fetch_polymarket(client),
        )

    # Sort each source by its own volume (volumes are not cross-comparable)
    kalshi_sorted = sorted(kalshi_results, key=lambda m: m["volume_usd"], reverse=True)
    poly_sorted   = sorted(poly_results,   key=lambda m: m["volume_usd"], reverse=True)

    # Take equal share from each, interleave so both sources appear in the list
    per_source = max(top_n // 2, 1)
    top_kalshi = kalshi_sorted[:per_source]
    top_poly   = poly_sorted[:per_source]

    # Interleave: Kalshi[0], Poly[0], Kalshi[1], Poly[1], ...
    merged = []
    for i in range(max(len(top_kalshi), len(top_poly))):
        if i < len(top_kalshi):
            merged.append(top_kalshi[i])
        if i < len(top_poly):
            merged.append(top_poly[i])

    top = merged[:top_n]
    _print(f"[markets_client] Total: {len(kalshi_results)} Kalshi + {len(poly_results)} Polymarket -> showing {len(top_kalshi)} + {len(top_poly)}")
    return top
