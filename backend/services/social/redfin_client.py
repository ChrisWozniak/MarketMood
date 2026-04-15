"""
Redfin Data Center client for Market Mood.
Pulls publicly available weekly housing market CSVs — no API key needed.
Data center: redfin.com/news/data-center

Metrics fetched (national weekly):
  - Median sale price
  - Homes sold
  - New listings
  - Median days on market
  - Sale-to-list price ratio
  - Price drop percentage
"""
import io
import httpx

# Redfin public data download URLs (national, weekly)
REDFIN_URLS = {
    "median_sale_price": (
        "https://redfin-public-data.s3.us-west-2.amazonaws.com/redfin_market_tracker/us_national_market_tracker.tsv000.gz",
        "tsv.gz",
    ),
}

# Simpler single endpoint that Redfin exposes for national stats
REDFIN_NATIONAL = "https://www.redfin.com/stingray/api/gis-csv?al=1&market=national&min_stories=1&num_homes=1&page_number=1&sold_within_days=90&status=9&uipt=1,2,3,4,5,6,7,8&v=8"

# Fallback: Redfin's data API (used by their website)
REDFIN_DATA_API = "https://www.redfin.com/stingray/do/query-unified-stats?al=1&region_id=1&region_type=1&tz=false&sf=1,2,3,4,5,6,11&num_homes=1&status=9&soldwithin=90"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.redfin.com/",
}


async def fetch_redfin_stats() -> dict:
    """
    Fetch national housing market stats from Redfin public data.
    Returns dict with metric name -> {value, unit, trend, title_snippet}
    Also returns synthetic posts for mood scoring.
    Falls back gracefully if Redfin blocks the request.
    """
    stats = {}
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(
                "https://redfin-public-data.s3.us-west-2.amazonaws.com"
                "/redfin_market_tracker/us_national_market_tracker.tsv000.gz",
                headers=HEADERS,
            )
            if resp.status_code == 200:
                import gzip
                import csv
                content = gzip.decompress(resp.content).decode("utf-8", errors="replace")
                reader = csv.DictReader(io.StringIO(content), delimiter="\t")
                # Filter to national + All Residential rows, sort by date
                rows = [
                    r for r in reader
                    if r.get("REGION_TYPE", "").lower() == "national"
                    and r.get("PROPERTY_TYPE", "") == "All Residential"
                ]
                rows.sort(key=lambda r: r.get("PERIOD_END", ""))
                if rows:
                    latest = rows[-1]
                    prev   = rows[-2] if len(rows) > 1 else {}
                    stats  = _parse_redfin_row(latest, prev)
                    print(f"[redfin] Got {len(stats)} metrics, period: {latest.get('PERIOD_END')}")
            else:
                print(f"[redfin] S3 download HTTP {resp.status_code} — using fallback")
                stats = await _fetch_fallback(client)
    except Exception as e:
        print(f"[redfin] Fetch error: {e}")
        stats = _hardcoded_fallback()

    posts = _stats_to_posts(stats)
    return {"stats": stats, "posts": posts}


async def _fetch_fallback(client: httpx.AsyncClient) -> dict:
    """Try Redfin's website data endpoint as fallback."""
    try:
        resp = await client.get(REDFIN_DATA_API, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            # Response is like: {}&&{"payload": {...}}
            text = resp.text
            if "&&" in text:
                text = text.split("&&", 1)[1]
            import json
            data = json.loads(text)
            payload = data.get("payload", {})
            return _parse_redfin_payload(payload)
    except Exception as e:
        print(f"[redfin] Fallback also failed: {e}")
    return _hardcoded_fallback()


def _parse_redfin_row(latest: dict, prev: dict) -> dict:
    """Parse a row from the Redfin national TSV tracker."""
    stats = {}

    def _safe_float(d: dict, key: str) -> float | None:
        try:
            v = d.get(key, "")
            return float(v) if v not in ("", None) else None
        except (ValueError, TypeError):
            return None

    def _trend(cur: float | None, prv: float | None) -> str:
        if cur is None or prv is None:
            return "stable"
        diff = cur - prv
        if diff > 0.5:
            return "rising"
        if diff < -0.5:
            return "falling"
        return "stable"

    # Map TSV column names (UPPERCASE) to friendly labels
    mappings = [
        ("MEDIAN_SALE_PRICE",   "Median Sale Price",    "USD",   "MEDIAN_SALE_PRICE_MOM"),
        ("HOMES_SOLD",          "Homes Sold",           "units", "HOMES_SOLD_MOM"),
        ("NEW_LISTINGS",        "New Listings",         "units", "NEW_LISTINGS_MOM"),
        ("MEDIAN_DOM",          "Days on Market",       "days",  "MEDIAN_DOM_MOM"),
        ("AVG_SALE_TO_LIST",    "Sale-to-List Ratio",   "",      "AVG_SALE_TO_LIST_MOM"),
        ("PRICE_DROPS",         "Price Drop %",         "%",     "PRICE_DROPS_MOM"),
        ("MONTHS_OF_SUPPLY",    "Months of Supply",     "mo",    "MONTHS_OF_SUPPLY_MOM"),
        ("INVENTORY",           "Active Inventory",     "homes", "INVENTORY_MOM"),
    ]

    for col, label, unit, mom_col in mappings:
        cur = _safe_float(latest, col)
        if cur is None:
            continue
        mom = _safe_float(latest, mom_col)  # month-over-month rate (0.01 = 1%)
        if mom is not None:
            trend = "rising" if mom > 0.005 else "falling" if mom < -0.005 else "stable"
            change_pct = round(mom * 100, 2)
        else:
            prv   = _safe_float(prev, col)
            trend = _trend(cur, prv)
            change_pct = None

        # Format value nicely
        if unit == "USD":
            display = f"${cur:,.0f}"
        elif unit == "":
            display = f"{cur:.3f}"
        elif unit == "%":
            display = f"{cur*100:.1f}%"
        else:
            display = f"{cur:.1f}"

        stats[label] = {
            "value":      cur,
            "display":    display,
            "unit":       unit,
            "trend":      trend,
            "change_pct": change_pct,
            "date":       latest.get("PERIOD_END", ""),
        }

    return stats


def _parse_redfin_payload(payload: dict) -> dict:
    """Parse Redfin website API payload (fallback)."""
    stats = {}
    try:
        if "median_sale_price" in payload:
            stats["Median Sale Price"] = {
                "value": payload["median_sale_price"],
                "unit": "USD", "trend": "stable", "change": None, "date": "",
            }
        if "median_dom" in payload:
            stats["Days on Market"] = {
                "value": payload["median_dom"],
                "unit": "days", "trend": "stable", "change": None, "date": "",
            }
    except Exception:
        pass
    return stats


def _hardcoded_fallback() -> dict:
    """Return empty dict if all Redfin fetches fail — degrade gracefully."""
    print("[redfin] All fetch methods failed — returning empty stats")
    return {}


def _stats_to_posts(stats: dict) -> list[dict]:
    """Convert Redfin stats into headline-style text for mood scoring."""
    from datetime import datetime
    posts = []
    for label, data in stats.items():
        display = data.get("display", str(data["value"]))
        trend   = data["trend"]
        chg     = data.get("change_pct")
        chg_str = f" ({'+' if chg and chg > 0 else ''}{chg}% MoM)" if chg else ""
        title   = f"Redfin housing data: {label} at {display}{chg_str} - {trend}"
        posts.append({
            "title":        title,
            "platform":     "Redfin",
            "score":        80,
            "num_comments": 0,
            "created_utc":  datetime.utcnow().timestamp(),
        })
    return posts
