"""
Reddit social signal client for MoodMarket.
Uses the public JSON API (no auth required for public subreddits).
Endpoint: https://www.reddit.com/r/{sub}/hot.json?limit=25
"""
import asyncio
import httpx

CATEGORY_SUBREDDITS: dict[str, list[str]] = {
    "Economy": ["economics", "investing", "personalfinance", "stocks", "wallstreetbets", "economy", "inflation"],
    "Politics": ["politics", "worldnews", "PoliticalDiscussion", "geopolitics", "NeutralPolitics"],
    "Prediction Markets": ["predictionmarkets", "Kalshi", "polymarket", "futuresandoptions"],
    "Daily Hot Topics": ["AskReddit", "todayilearned", "news", "worldnews", "interestingasfuck"],
    "Sector Sentiment": ["energy", "healthcare", "dividends", "ETFs"],
    "Technology & AI": ["artificial", "MachineLearning", "ChatGPT", "singularity", "LocalLLaMA", "OpenAI", "Anthropic"],
    "Blockchain & Crypto": ["CryptoCurrency", "ethereum", "Bitcoin", "solana", "defi", "web3"],
    "Real Estate": ["realestate", "FirstTimeHomeBuyer", "REBubble",
                    "Renters", "Landlord", "airbnb", "RealEstateInvesting"],
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}


async def _fetch_subreddit(client: httpx.AsyncClient, subreddit: str, limit: int = 25) -> list[dict]:
    """Fetch hot posts from a subreddit via public JSON API."""
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
    try:
        resp = await client.get(url, headers=HEADERS, timeout=10, follow_redirects=True)
        if resp.status_code != 200:
            print(f"[reddit] r/{subreddit} HTTP {resp.status_code}")
            return []
        data = resp.json()
        children = data.get("data", {}).get("children", [])
        posts = []
        for child in children:
            p = child.get("data", {})
            if p.get("stickied") or not p.get("title"):
                continue
            posts.append({
                "title": p.get("title", ""),
                "url": p.get("url", ""),
                "platform": "Reddit",
                "subreddit": subreddit,
                "score": p.get("score", 0),
                "num_comments": p.get("num_comments", 0),
                "created_utc": p.get("created_utc", 0),
            })
        return posts
    except Exception as e:
        print(f"[reddit] r/{subreddit} error: {e}")
        return []


async def fetch_reddit_posts(max_posts_per_sub: int = 25) -> dict[str, list[dict]]:
    """
    Async: fetch posts for all categories concurrently.
    Returns {category: [post_dict, ...]}
    """
    async with httpx.AsyncClient(timeout=15) as client:
        tasks = {}
        for category, subs in CATEGORY_SUBREDDITS.items():
            tasks[category] = [_fetch_subreddit(client, sub, max_posts_per_sub) for sub in subs]

        result: dict[str, list[dict]] = {}
        for category, sub_tasks in tasks.items():
            sub_results = await asyncio.gather(*sub_tasks)
            posts = [p for batch in sub_results for p in batch]
            result[category] = posts
            print(f"[reddit] {category}: {len(posts)} posts")

    return result
