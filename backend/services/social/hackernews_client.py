"""
Hacker News social signal client.
Uses the Algolia HN Search API — free, no auth, reliable.

Endpoint:
  https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=N
"""
import httpx

HN_ALGOLIA = "https://hn.algolia.com/api/v1/search"

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Technology & AI": [
        "ai", "gpt", "llm", "openai", "anthropic", "claude", "gemini",
        "machine learning", "deep learning", "nvidia", "chip", "semiconductor",
        "agent", "multimodal", "open source", "developer", "github", "model",
        "inference", "fine-tune", "transformer", "benchmark", "rag",
    ],
    "Blockchain & Crypto": [
        "bitcoin", "ethereum", "solana", "crypto", "blockchain", "defi",
        "nft", "web3", "token", "wallet", "stablecoin", "dao", "layer 2",
        "smart contract", "coinbase", "binance", "sec crypto", "etf bitcoin",
    ],
    "Economy": [
        "inflation", "fed", "interest rate", "recession", "gdp", "tariff",
        "trade war", "layoff", "unemployment", "housing market", "mortgage",
        "consumer spending", "cpi", "debt", "dollar", "treasury", "bank",
    ],
    "Politics": [
        "trump", "election", "congress", "senate", "president", "policy",
        "government", "war", "ukraine", "russia", "china", "iran", "nato",
        "regulation", "sanction", "geopolitics", "supreme court", "parliament",
    ],
    "Sector Sentiment": [
        "stock", "market", "ipo", "earnings", "revenue", "acquisition",
        "merger", "energy", "oil", "healthcare", "pharma", "real estate",
        "semiconductor", "ev", "tesla", "apple", "google", "microsoft",
    ],
    "Health & Science": [
        "health", "longevity", "cancer", "vaccine", "clinical trial", "fda",
        "drug", "medicine", "biology", "genetics", "aging", "nutrition",
        "mental health", "obesity", "alzheimer", "study finds", "researchers",
    ],
    "Real Estate": [
        "housing", "mortgage", "rent", "rental", "home price", "home sales",
        "real estate", "zillow", "redfin", "airbnb", "homebuyer", "eviction",
        "landlord", "tenant", "property", "foreclosure", "housing market",
    ],
    "Daily Hot Topics": [],  # catch-all for unmatched stories
}


def _categorize(title: str) -> str:
    lower = title.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if keywords and any(kw in lower for kw in keywords):
            return cat
    return "Daily Hot Topics"


async def fetch_hackernews_posts(top_n: int = 60) -> dict[str, list[dict]]:
    """
    Fetch top HN front page stories via Algolia API and classify into categories.
    Returns {category: [post_dict, ...]}
    """
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                HN_ALGOLIA,
                params={"tags": "front_page", "hitsPerPage": top_n},
                timeout=10,
            )
            if resp.status_code != 200:
                print(f"[hackernews] Algolia HTTP {resp.status_code}")
                return {}
            data = resp.json()
            hits = data.get("hits", [])
    except Exception as e:
        print(f"[hackernews] Fetch failed: {e}")
        return {}

    result: dict[str, list[dict]] = {}
    for item in hits:
        title = item.get("title", "").strip()
        if not title:
            continue
        cat = _categorize(title)
        post = {
            "title": title,
            "url": item.get("url") or f"https://news.ycombinator.com/item?id={item.get('objectID')}",
            "platform": "Hacker News",
            "score": item.get("points", 0) or 0,
            "num_comments": item.get("num_comments", 0) or 0,
            "created_utc": item.get("created_at_i", 0) or 0,
            "subreddit": None,
        }
        result.setdefault(cat, []).append(post)

    for cat, posts in result.items():
        print(f"[hackernews] {cat}: {len(posts)} stories")

    return result
