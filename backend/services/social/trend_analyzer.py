from collections import defaultdict
from datetime import datetime, timedelta
import math


def compute_trend_direction(volumes: list[float]) -> str:
    """Determine if a trend is rising, declining, stable, or cyclical."""
    if len(volumes) < 3:
        return "stable"

    recent = volumes[-7:] if len(volumes) >= 7 else volumes
    earlier = volumes[:-7] if len(volumes) >= 14 else volumes[:len(volumes)//2]

    if not earlier:
        return "stable"

    avg_recent = sum(recent) / len(recent)
    avg_earlier = sum(earlier) / len(earlier)

    if avg_earlier == 0:
        return "rising" if avg_recent > 0 else "stable"

    change_pct = (avg_recent - avg_earlier) / avg_earlier

    if change_pct > 0.25:
        return "rising"
    elif change_pct < -0.25:
        return "declining"
    else:
        # Check for cyclical pattern (alternating highs/lows)
        diffs = [volumes[i+1] - volumes[i] for i in range(len(volumes)-1)]
        sign_changes = sum(1 for i in range(len(diffs)-1) if diffs[i] * diffs[i+1] < 0)
        if sign_changes > len(diffs) * 0.5:
            return "cyclical"
        return "stable"


def detect_spikes(volumes: list[float], dates: list[str]) -> list[dict]:
    """Find dates where volume > 2x rolling average."""
    spikes = []
    window = 7
    for i in range(window, len(volumes)):
        rolling_avg = sum(volumes[max(0, i-window):i]) / window
        if rolling_avg > 0 and volumes[i] > rolling_avg * 2.0:
            spikes.append({"date": dates[i], "volume": volumes[i], "avg": rolling_avg})
    return spikes


def build_trend_history(
    category_posts: dict[str, list[dict]],
    days: int = 30,
) -> dict[str, dict]:
    """
    Build daily volume history per category from raw post data.
    Returns {category: {dates: [...], volumes: [...], direction: str, spikes: [...]}}
    """
    today = datetime.utcnow()
    date_range = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days-1, -1, -1)]
    date_set = set(date_range)

    history = {}
    for category, posts in category_posts.items():
        daily_counts: dict[str, float] = defaultdict(float)

        for post in posts:
            ts = post.get("created_utc")
            if ts:
                try:
                    post_date = datetime.utcfromtimestamp(float(ts)).strftime("%Y-%m-%d")
                    if post_date in date_set:
                        # Weight by engagement
                        score = post.get("score", 1)
                        comments = post.get("num_comments", 0)
                        engagement = math.log1p(score + comments)
                        daily_counts[post_date] += engagement
                except Exception:
                    pass

        volumes = [round(daily_counts.get(d, 0), 2) for d in date_range]
        history[category] = {
            "dates": date_range,
            "volumes": volumes,
            "direction": compute_trend_direction(volumes),
            "spikes": detect_spikes(volumes, date_range),
        }

    return history


def rank_trending_topics(
    category_posts: dict[str, list[dict]],
) -> list[dict]:
    """
    Rank categories by total engagement score.
    Returns sorted list with rank, volume_score, trend direction.
    """
    scores = []
    for category, posts in category_posts.items():
        total = sum(
            math.log1p(p.get("score", 0) + p.get("num_comments", 0))
            for p in posts
        )
        platforms = list({p.get("platform", "Unknown") for p in posts})
        scores.append({
            "category": category,
            "raw_score": total,
            "platforms": platforms,
            "post_count": len(posts),
        })

    scores.sort(key=lambda x: x["raw_score"], reverse=True)

    max_score = scores[0]["raw_score"] if scores else 1
    ranked = []
    for i, item in enumerate(scores[:15]):
        volume_score = round((item["raw_score"] / max_score) * 100) if max_score else 0
        ranked.append({
            "rank": i + 1,
            "subject": item["category"],
            "category": item["category"],
            "volume_score": volume_score,
            "platforms": item["platforms"],
            "post_count": item["post_count"],
            "trend": "stable",  # updated by aggregator after trend history is built
            "sub_topics": [],   # filled in by mood_scorer
        })

    return ranked
