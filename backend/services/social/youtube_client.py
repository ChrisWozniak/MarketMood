from googleapiclient.discovery import build
from dotenv import load_dotenv
import os

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

CATEGORY_KEYWORDS: dict[str, str] = {
    "Politics": "politics news today",
    "Economy & Finance": "economy finance stock market today",
    "Technology & AI": "artificial intelligence technology 2024",
    "Entertainment": "entertainment celebrity news",
    "Health & Wellness": "health wellness science",
    "Environment & Climate": "climate change environment",
    "Sports": "sports highlights today",
    "Science": "science discovery news",
    "Memes & Viral": "viral trends today",
}


def _is_configured() -> bool:
    return bool(YOUTUBE_API_KEY and YOUTUBE_API_KEY != "your_youtube_data_api_v3_key")


def fetch_youtube_videos(max_results_per_category: int = 5) -> dict[str, list[dict]]:
    """
    Returns {category: [video_dict, ...]}
    Returns empty dict if YouTube API is not configured.
    """
    if not _is_configured():
        print("[youtube] Not configured — skipping.")
        return {}

    try:
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    except Exception as e:
        print(f"[youtube] Build failed: {e}")
        return {}

    result: dict[str, list[dict]] = {}
    for category, keyword in CATEGORY_KEYWORDS.items():
        try:
            search_resp = youtube.search().list(
                q=keyword,
                part="id,snippet",
                type="video",
                order="viewCount",
                publishedAfter="2024-01-01T00:00:00Z",
                maxResults=max_results_per_category,
            ).execute()

            videos = []
            for item in search_resp.get("items", []):
                video_id = item["id"].get("videoId", "")
                snippet = item.get("snippet", {})
                videos.append({
                    "title": snippet.get("title", ""),
                    "channel": snippet.get("channelTitle", ""),
                    "published_at": snippet.get("publishedAt", ""),
                    "url": f"https://youtube.com/watch?v={video_id}",
                    "platform": "YouTube",
                })
            result[category] = videos
        except Exception as e:
            print(f"[youtube] {category} error: {e}")
            result[category] = []

    return result
