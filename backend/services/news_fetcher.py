import asyncio
import feedparser
import httpx
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
NEWSAPI_BASE = "https://newsapi.org/v2/everything"

# Default RSS feeds per category
CATEGORY_FEEDS: dict[str, list[str]] = {
    "Business & Economy": [
        "https://feeds.finance.yahoo.com/rss/2.0/headline",
        "https://www.investing.com/rss/news.rss",
        "https://feeds.bloomberg.com/markets/news.rss",
    ],
    "World News": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://feeds.reuters.com/Reuters/worldNews",
    ],
    "Local News": [
        "https://www.govtrack.us/events/events.rss?feeds=bill-status",
        "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml",
    ],
    "Technology/AI": [
        "https://techcrunch.com/feed/",
        "https://feeds.arstechnica.com/arstechnica/technology-lab",
        "https://www.technologyreview.com/feed/",
    ],
    "Space/Cosmos": [
        "https://www.nasa.gov/rss/dyn/breaking_news.rss",
        "https://www.space.com/feeds/all",
        "https://feeds.arstechnica.com/arstechnica/science",
    ],
    "Entertainment & Culture": [
        "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/Arts.xml",
        "https://variety.com/feed/",
    ],
    "Sport": [
        "https://feeds.bbci.co.uk/sport/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/Sports.xml",
        "https://www.espn.com/espn/rss/news",
    ],
    "Environment & Climate": [
        "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
        "https://feeds.reuters.com/reuters/environment",
        "https://rss.nytimes.com/services/xml/rss/nyt/Climate.xml",
    ],
    "Blockchain/Crypto": [
        "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "https://decrypt.co/feed",
        "https://cointelegraph.com/rss",
    ],
    "Science & Health": [
        "https://feeds.bbci.co.uk/news/health/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/Health.xml",
        "https://www.sciencedaily.com/rss/all.xml",
        "https://feeds.newscientist.com/full-feed",
    ],
}

# Maps old/renamed category names → current names so saved settings still work
CATEGORY_ALIASES: dict[str, str] = {
    "Financial":              "Business & Economy",
    "Finance":                "Business & Economy",
    "Business":               "Business & Economy",
    "Economy":                "Business & Economy",
    "Economy & Finance":      "Business & Economy",
    "World Politics":         "World News",
    "World":                  "World News",
    "Politics":               "World News",
    "Technology":             "Technology/AI",
    "Technology & AI":        "Technology/AI",
    "AI":                     "Technology/AI",
    "Tech":                   "Technology/AI",
    "Space":                  "Space/Cosmos",
    "Cosmos":                 "Space/Cosmos",
    "Entertainment":          "Entertainment & Culture",
    "Culture":                "Entertainment & Culture",
    "Sports":                 "Sport",
    "Climate":                "Environment & Climate",
    "Environment":            "Environment & Climate",
    "Blockchain":             "Blockchain/Crypto",
    "Crypto":                 "Blockchain/Crypto",
    "Cryptocurrency":         "Blockchain/Crypto",
    "Science":                "Science & Health",
    "Health":                 "Science & Health",
    "Science & Health":       "Science & Health",
    "Health & Wellness":      "Science & Health",
    "Local":                  "Local News",
}

# NewsAPI keyword mapping
CATEGORY_KEYWORDS: dict[str, str] = {
    "Business & Economy": "finance OR stock market OR economy OR Fed OR inflation OR trade OR GDP",
    "World News": "world news OR international affairs OR foreign policy",
    "Local News": "US politics OR congress OR senate OR legislation",
    "Technology/AI": "artificial intelligence OR machine learning OR technology OR quantum computing OR semiconductor",
    "Space/Cosmos": "space OR NASA OR SpaceX OR asteroid OR rocket OR Mars OR telescope OR cosmos",
    "Entertainment & Culture": "entertainment OR movies OR music OR culture OR celebrity OR awards OR TV",
    "Sport": "sport OR football OR basketball OR soccer OR tennis OR Olympics OR baseball OR NHL",
    "Environment & Climate": "climate change OR environment OR global warming OR emissions OR renewable energy OR sustainability",
    "Blockchain/Crypto": "blockchain OR cryptocurrency OR bitcoin OR ethereum OR DeFi OR NFT OR Web3",
    "Science & Health": "science OR health OR medicine OR research OR biology OR physics OR disease OR vaccine",
}


def _parse_feed_entries(feed_url: str, max_items: int = 10) -> list[dict]:
    try:
        parsed = feedparser.parse(feed_url)
        articles = []
        for entry in parsed.entries[:max_items]:
            articles.append({
                "title": entry.get("title", "").strip(),
                "url": entry.get("link", ""),
                "source": parsed.feed.get("title", feed_url),
                "published": entry.get("published", ""),
                "summary": entry.get("summary", "")[:300],
            })
        return articles
    except Exception:
        return []


async def _fetch_newsapi(keyword: str, max_items: int = 5) -> list[dict]:
    if not NEWSAPI_KEY or NEWSAPI_KEY == "your_newsapi_key_here":
        return []
    params = {
        "q": keyword,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": max_items,
        "apiKey": NEWSAPI_KEY,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(NEWSAPI_BASE, params=params)
            if resp.status_code == 200:
                data = resp.json()
                return [
                    {
                        "title": a.get("title", "").strip(),
                        "url": a.get("url", ""),
                        "source": a.get("source", {}).get("name", "NewsAPI"),
                        "published": a.get("publishedAt", ""),
                        "summary": (a.get("description") or "")[:300],
                    }
                    for a in data.get("articles", [])
                    if a.get("title") and "[Removed]" not in a.get("title", "")
                ]
    except Exception:
        pass
    return []


def _deduplicate(articles: list[dict]) -> list[dict]:
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    result = []
    for a in articles:
        url = a.get("url", "")
        title = a.get("title", "").lower()[:60]
        if url and url not in seen_urls and title not in seen_titles:
            seen_urls.add(url)
            seen_titles.add(title)
            result.append(a)
    return result


async def fetch_category(
    category: str,
    custom_feeds: list[str] | None = None,
    max_per_category: int = 5,
) -> dict:
    """Fetch and return articles for a single category."""
    # Resolve aliases so renamed/old category names still get feeds
    resolved = CATEGORY_ALIASES.get(category, category)
    feeds = custom_feeds or CATEGORY_FEEDS.get(resolved) or CATEGORY_FEEDS.get(category, [])
    keyword = CATEGORY_KEYWORDS.get(resolved) or CATEGORY_KEYWORDS.get(category, category)

    loop = asyncio.get_event_loop()
    rss_tasks = [
        loop.run_in_executor(None, _parse_feed_entries, url, 8)
        for url in feeds
    ]
    newsapi_task = _fetch_newsapi(keyword, max_items=5)

    rss_results = await asyncio.gather(*rss_tasks)
    newsapi_results = await newsapi_task

    all_articles: list[dict] = []
    for batch in rss_results:
        all_articles.extend(batch)
    all_articles.extend(newsapi_results)

    deduped = _deduplicate(all_articles)
    return {"category": category, "articles": deduped[:max_per_category]}


async def fetch_tickers_category(tickers: list[dict], max_per_category: int = 5) -> dict:
    """Fetch news for market tickers as a virtual category."""
    if not tickers:
        return {"category": "Market Tickers", "articles": []}

    # Build a combined NewsAPI query from ticker names/symbols
    terms = [f'"{t.get("name", t.get("symbol", ""))}"' for t in tickers[:5]]
    keyword = " OR ".join(terms)
    articles = await _fetch_newsapi(keyword, max_items=max_per_category * 2)
    return {"category": "Market Tickers", "articles": _deduplicate(articles)[:max_per_category]}


async def fetch_world_country_category(country: str, max_per_category: int = 5) -> dict:
    """Fetch world news focused on a specific country."""
    country = country.strip()
    if not country:
        return {"category": "World News", "articles": []}
    keyword = f'"{country}" news politics economy'
    articles = await _fetch_newsapi(keyword, max_items=max_per_category * 2)
    return {"category": f"World News — {country}", "articles": _deduplicate(articles)[:max_per_category]}


async def fetch_local_news_category(city: str, state: str, country: str, max_per_category: int = 5) -> dict:
    """Fetch local news for a city + state (US) or city + country (international)."""
    city = city.strip()
    state = state.strip()
    country = country.strip()

    if not city and not country:
        return {"category": "Local News", "articles": []}

    # Build location label and search query
    if country and country.lower() not in ("us", "usa", "united states"):
        # International: use city + country, ignore state
        location_label = f"{city}, {country}".strip(", ") if city else country
        parts = [f'"{p}"' for p in [city, country] if p]
        keyword = " ".join(parts) + " news"
    else:
        # US: use city + state
        location_label = ", ".join(p for p in [city, state] if p) or "US"
        parts = [f'"{p}"' for p in [city, state] if p]
        keyword = " ".join(parts) + " local news"

    articles = await _fetch_newsapi(keyword, max_items=max_per_category * 2)
    return {"category": f"Local News — {location_label}", "articles": _deduplicate(articles)[:max_per_category]}


async def fetch_all_categories(
    categories: list[str],
    custom_category_feeds: dict[str, list[str]] | None = None,
    max_per_category: int = 5,
    market_tickers: list[dict] | None = None,
    local_locations: list[dict] | None = None,
    world_countries: list[str] | None = None,
) -> list[dict]:
    """Fetch articles for all enabled categories concurrently."""
    tasks = []
    for cat in categories:
        custom = (custom_category_feeds or {}).get(cat)
        tasks.append(fetch_category(cat, custom_feeds=custom, max_per_category=max_per_category))

    # Per-country World News fetches — each country gets its own additional section
    if "World News" in categories and world_countries:
        for country in world_countries:
            if country.strip():
                tasks.append(fetch_world_country_category(country.strip(), max_per_category))

    # Add Market Tickers as extra category if tickers configured
    if market_tickers:
        tasks.append(fetch_tickers_category(market_tickers, max_per_category))

    # Add one Local News fetch per location, all concurrent
    if "Local News" in categories and local_locations:
        for loc in local_locations:
            city = loc.get("city", "").strip()
            state = loc.get("state", "").strip()
            country = loc.get("country", "").strip()
            if city or country:
                tasks.append(fetch_local_news_category(city, state, country, max_per_category))

    return await asyncio.gather(*tasks)
