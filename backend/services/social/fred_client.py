"""
FRED (Federal Reserve Economic Data) client for MoodMarket.
Fetches key real estate and housing market indicators.
Free API — get a key at fred.stlouisfed.org/docs/api/api_key.html

Series used:
  MORTGAGE30US  - 30-year fixed mortgage rate (weekly)
  MSPUS         - Median sales price of houses sold (quarterly)
  MSACSR        - Monthly supply of houses (months of inventory)
  HOUST         - Housing starts (monthly)
  USSTHPI       - House price index (quarterly)
  RRVRUSQ156N   - Rental vacancy rate (quarterly)
"""
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"
FRED_API_KEY = os.getenv("FRED_API_KEY", "")

# Series to fetch: (series_id, label, unit)
HOUSING_SERIES = [
    ("MORTGAGE30US", "30-Year Mortgage Rate",    "%"),
    ("MSPUS",        "Median Home Sale Price",   "USD"),
    ("MSACSR",       "Housing Inventory",        "months"),
    ("HOUST",        "Housing Starts",           "thousands"),
    ("USSTHPI",      "House Price Index",        "index"),
    ("RRVRUSQ156N",  "Rental Vacancy Rate",      "%"),
]


def _is_configured() -> bool:
    return bool(FRED_API_KEY and FRED_API_KEY not in ("", "your_fred_api_key"))


def _pct_change(current: float, previous: float) -> float | None:
    if previous and previous != 0:
        return round((current - previous) / abs(previous) * 100, 2)
    return None


async def fetch_fred_housing() -> dict:
    """
    Fetch latest values for key housing indicators from FRED.
    Returns a dict with indicator name -> {value, unit, change_pct, label}
    Also returns a list of 'posts' (synthetic) for mood scoring.
    """
    if not _is_configured():
        print("[fred] FRED_API_KEY not set — skipping.")
        return {"indicators": {}, "posts": []}

    indicators = {}
    async with httpx.AsyncClient(timeout=15) as client:
        for series_id, label, unit in HOUSING_SERIES:
            try:
                resp = await client.get(
                    FRED_BASE,
                    params={
                        "series_id": series_id,
                        "api_key": FRED_API_KEY,
                        "file_type": "json",
                        "sort_order": "desc",
                        "limit": 4,          # last 4 observations for trend
                    },
                )
                if resp.status_code != 200:
                    print(f"[fred] {series_id} HTTP {resp.status_code}")
                    continue

                obs = [
                    o for o in resp.json().get("observations", [])
                    if o.get("value") not in (".", "", None)
                ]
                if not obs:
                    continue

                latest_val  = float(obs[0]["value"])
                prev_val    = float(obs[1]["value"]) if len(obs) > 1 else None
                change_pct  = _pct_change(latest_val, prev_val) if prev_val else None
                date        = obs[0]["date"]

                # Human-readable trend label
                if change_pct is None:
                    trend = "stable"
                elif change_pct > 1:
                    trend = "rising"
                elif change_pct < -1:
                    trend = "falling"
                else:
                    trend = "stable"

                indicators[label] = {
                    "series_id":  series_id,
                    "value":      latest_val,
                    "unit":       unit,
                    "date":       date,
                    "change_pct": change_pct,
                    "trend":      trend,
                }
                print(f"[fred] {label}: {latest_val}{unit} ({trend})")

            except Exception as e:
                print(f"[fred] {series_id} error: {e}")

    # Build synthetic "posts" so mood_scorer can include FRED in sentiment scoring
    posts = _indicators_to_posts(indicators)
    return {"indicators": indicators, "posts": posts}


def _indicators_to_posts(indicators: dict) -> list[dict]:
    """
    Convert FRED indicators into text snippets that Claude can score for sentiment.
    Each snippet reads like a headline so mood_scorer treats it like social posts.
    """
    from datetime import datetime
    posts = []
    for label, data in indicators.items():
        val   = data["value"]
        unit  = data["unit"]
        trend = data["trend"]
        chg   = data["change_pct"]

        chg_str = f" ({'+' if chg and chg > 0 else ''}{chg}% vs prior period)" if chg else ""
        title = f"{label}: {val}{unit}{chg_str} — trend is {trend}"

        posts.append({
            "title":       title,
            "platform":    "FRED",
            "score":       100,          # high weight — authoritative data
            "num_comments": 0,
            "created_utc": datetime.utcnow().timestamp(),
        })
    return posts
