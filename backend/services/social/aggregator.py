import asyncio
import json
from datetime import datetime
from sqlmodel import Session

from database import engine
from models import SocialSnapshot, MarketSnapshot
from services.social.reddit_client import fetch_reddit_posts
from services.social.hackernews_client import fetch_hackernews_posts
from services.social.youtube_client import fetch_youtube_videos
from services.social.markets_client import fetch_top_markets
from services.social.trend_analyzer import build_trend_history, rank_trending_topics
from services.social.mood_scorer import score_all_moods, extract_all_sub_topics


def _merge_platforms(*platform_dicts: dict[str, list[dict]]) -> dict[str, list[dict]]:
    """Merge post lists from multiple platforms per category."""
    merged: dict[str, list[dict]] = {}
    for platform_data in platform_dicts:
        for cat, posts in platform_data.items():
            for p in posts:
                # Ensure all posts have required fields
                p.setdefault("created_utc", datetime.utcnow().timestamp())
                p.setdefault("score", 0)
                p.setdefault("num_comments", 0)
                p.setdefault("platform", "Unknown")
            merged.setdefault(cat, []).extend(posts)
    return merged


async def run_social_analysis() -> SocialSnapshot:
    """Full pipeline: collect → analyze → save → return snapshot."""
    print("[aggregator] Starting social analysis...")

    # 1. Fetch from all sources concurrently
    # Reddit is now async; YouTube runs in executor (sync); HN is async
    loop = asyncio.get_running_loop()

    reddit_task  = fetch_reddit_posts(25)
    hn_task      = fetch_hackernews_posts(60)
    youtube_task = asyncio.wait_for(
        loop.run_in_executor(None, fetch_youtube_videos, 5),
        timeout=30.0,
    )
    markets_task = fetch_top_markets(10)

    results = await asyncio.gather(
        reddit_task, hn_task, youtube_task, markets_task,
        return_exceptions=True,
    )

    def _safe(val, default):
        return default if isinstance(val, BaseException) else val

    reddit_data  = _safe(results[0], {})
    hn_data      = _safe(results[1], {})
    youtube_data = _safe(results[2], {})
    market_data  = _safe(results[3], [])

    if isinstance(results[2], BaseException):
        print(f"[aggregator] YouTube fetch failed/timed out: {results[2]}")
    if isinstance(results[3], BaseException):
        print(f"[aggregator] Markets fetch failed: {results[3]}")

    print(f"[aggregator] Sources: Reddit={sum(len(v) for v in reddit_data.values())} posts, "
          f"HN={sum(len(v) for v in hn_data.values())} stories, "
          f"YouTube={sum(len(v) for v in youtube_data.values())} videos, "
          f"Markets={len(market_data)}")

    # 2. Merge all platforms
    merged = _merge_platforms(reddit_data, hn_data, youtube_data)

    # 3. Build trend history and rank topics
    trend_history_raw = build_trend_history(merged, days=30)
    ranked_topics = rank_trending_topics(merged)

    # 4. Score mood for top categories by post volume (dynamic, not hardcoded)
    top_categories = [item["category"] for item in ranked_topics[:4]]
    mood_scores = await score_all_moods(merged, scored_categories=top_categories)

    # 5. Extract sub-topics sequentially (small model, avoids rate limit burst)
    sub_topic_map = await extract_all_sub_topics(ranked_topics, merged)

    for item in ranked_topics:
        cat = item["category"]
        item["sub_topics"] = sub_topic_map.get(cat, [])
        if cat in trend_history_raw:
            item["trend"] = trend_history_raw[cat]["direction"]
        if cat in mood_scores:
            item["mood_score"] = mood_scores[cat].get("score", 0)

    # 6. Build flat trend history
    flat_history = {cat: data["volumes"][-1] if data["volumes"] else 0
                   for cat, data in trend_history_raw.items()}

    # 7. Generate investment signals and tech momentum via Claude
    from services.investment_signals import generate_investment_signals
    from services.tech_momentum import generate_tech_momentum
    investment_signals = await generate_investment_signals(mood_scores, ranked_topics)
    tech_momentum = await generate_tech_momentum(ranked_topics)

    # 8. Save snapshot
    snapshot = SocialSnapshot(
        captured_at=datetime.utcnow(),
        platform_data=json.dumps({
            "reddit_categories": list(reddit_data.keys()),
            "hn_categories": list(hn_data.keys()),
            "youtube_categories": list(youtube_data.keys()),
            "investment_signals": investment_signals,
            "tech_momentum": tech_momentum,
        }),
        trending_topics=json.dumps(ranked_topics),
        mood_scores=json.dumps(mood_scores),
        trend_history=json.dumps(flat_history),
    )

    with Session(engine) as session:
        session.add(snapshot)
        market_snapshot = MarketSnapshot(
            captured_at=datetime.utcnow(),
            markets_json=json.dumps(market_data),
        )
        session.add(market_snapshot)
        session.commit()
        session.refresh(snapshot)

    print(f"[aggregator] Done: {len(ranked_topics)} topics, "
          f"{len(mood_scores)} mood scores, {len(market_data)} markets")
    return snapshot
