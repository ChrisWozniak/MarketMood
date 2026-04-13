"""
Mood scorer for MoodMarket.
Uses Claude (claude-haiku-4-5 for speed/cost) to score sentiment per category
and extract sub-topics from post titles.
"""
import asyncio
import json
import re
import os
from collections import Counter
import anthropic

_client: anthropic.Anthropic | None = None

MOOD_CATEGORY_LIMIT = 7  # Score all MoodMarket categories

STOP_WORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'can', 'as', 'it', 'its', 'this', 'that',
    'these', 'those', 'he', 'she', 'they', 'we', 'you', 'i', 'his', 'her',
    'their', 'our', 'your', 'my', 'not', 'no', 'new', 'how', 'why', 'what',
    'when', 'where', 'who', 'which', 'after', 'before', 'about', 'up', 'down',
    'out', 'into', 'over', 'than', 'more', 'most', 'also', 'just', 'now',
    'all', 'back', 'first', 'last', 'next', 'other', 'says', 'said', 'amid',
    'us', 'uk', 'report', 'reports', 'get', 'gets', 'got', 'make', 'makes',
}


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


async def _claude_call(prompt: str, max_tokens: int = 300) -> str | None:
    """Synchronous Claude call run in executor to avoid blocking the event loop."""
    loop = asyncio.get_running_loop()
    try:
        def _call():
            return get_client().messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
        resp = await asyncio.wait_for(loop.run_in_executor(None, _call), timeout=30.0)
        return resp.content[0].text.strip()
    except asyncio.TimeoutError:
        print("[mood_scorer] Claude timed out")
        return None
    except Exception as e:
        print(f"[mood_scorer] Claude error: {e}")
        return None


def _extract_subtopics_fallback(posts: list[dict], n: int = 5) -> list[str]:
    titles = [p.get("title", "") for p in posts[:40] if p.get("title")]
    if not titles:
        return []

    def tokenize(text: str) -> list[str]:
        return [t for t in re.findall(r"[A-Za-z][a-zA-Z']{2,}", text)
                if t.lower() not in STOP_WORDS and len(t) > 3]

    bigrams: list[str] = []
    all_words: list[str] = []
    for title in titles:
        tokens = tokenize(title)
        all_words.extend(tokens)
        for i in range(len(tokens) - 1):
            bigrams.append(f"{tokens[i]} {tokens[i+1]}")

    bigram_counts = Counter(bigrams)
    word_counts = Counter(all_words)
    min_bigram_count = 2 if len(titles) >= 8 else 1
    top_bigrams = [term for term, cnt in bigram_counts.most_common(n * 2)
                   if cnt >= min_bigram_count]
    top_words = []
    for word, _ in word_counts.most_common(n * 3):
        covered = any(word.lower() in bg.lower() for bg in top_bigrams)
        if not covered:
            top_words.append(word)

    return (top_bigrams + top_words)[:n]


async def score_mood(category: str, posts: list[dict]) -> dict:
    """Score the social mood for a category using Claude Haiku."""
    if not posts:
        return _empty_mood(category)

    sample_titles = [p.get("title", "") for p in posts[:25] if p.get("title")]
    if not sample_titles:
        return _empty_mood(category)

    titles_text = "\n".join(f"- {t}" for t in sample_titles)
    prompt = f"""Analyze the sentiment of these {category} social media post titles.

Posts:
{titles_text}

Return a JSON object with exactly these fields:
{{
  "score": <integer from -100 (very negative) to +100 (very positive)>,
  "label": "<2-3 word sentiment label>",
  "dominant_emotions": ["<emotion1>", "<emotion2>", "<emotion3>"],
  "key_narratives": ["<narrative1>", "<narrative2>"],
  "polarization_level": <1-10 or null>,
  "trust_level": <1-10 or null>
}}

Return only valid JSON."""

    raw = await _claude_call(prompt, max_tokens=300)
    if not raw:
        return _score_mood_fallback(category, posts)

    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        data = json.loads(cleaned.strip())
        data["category"] = category
        return data
    except Exception as e:
        print(f"[mood_scorer] JSON parse error for {category}: {e}")
        return _score_mood_fallback(category, posts)


POSITIVE_WORDS = {
    'win', 'wins', 'winning', 'won', 'record', 'best', 'top', 'great', 'good',
    'success', 'successful', 'breakthrough', 'growth', 'rise', 'rises', 'gain',
    'gains', 'profit', 'rally', 'soars', 'boost', 'approve', 'approval',
    'launch', 'launches', 'amazing', 'incredible', 'improve', 'improved',
    'positive', 'hope', 'optimism', 'agree', 'deal', 'progress', 'advance',
}
NEGATIVE_WORDS = {
    'fail', 'fails', 'failed', 'failure', 'lose', 'loses', 'loss', 'losses',
    'crash', 'crashes', 'crisis', 'collapse', 'collapses', 'fear', 'fears',
    'warn', 'warning', 'threat', 'danger', 'dangerous', 'attack', 'attacks',
    'kill', 'killed', 'death', 'deaths', 'disaster', 'scandal', 'fraud',
    'arrest', 'ban', 'banned', 'block', 'blocked', 'reject', 'rejected',
    'fall', 'falls', 'drop', 'drops', 'decline', 'declines', 'negative',
    'bad', 'worse', 'worst', 'terrible', 'awful', 'problem', 'issue',
    'layoff', 'layoffs', 'fired', 'bankrupt', 'recession', 'war', 'conflict',
}


def _score_mood_fallback(category: str, posts: list[dict]) -> dict:
    titles = [p.get("title", "").lower() for p in posts if p.get("title")]
    if not titles:
        return _empty_mood(category)

    pos = sum(1 for t in titles for w in t.split() if w.strip('.,!?') in POSITIVE_WORDS)
    neg = sum(1 for t in titles for w in t.split() if w.strip('.,!?') in NEGATIVE_WORDS)
    total = pos + neg

    if total == 0:
        score, label, emotions = 0, "Neutral", ["mixed"]
    else:
        ratio = (pos - neg) / total
        score = int(ratio * 60)
        if score >= 30:
            label, emotions = "Positive", ["optimism", "enthusiasm"]
        elif score >= 10:
            label, emotions = "Slightly Positive", ["interest", "hope"]
        elif score >= -10:
            label, emotions = "Mixed", ["uncertainty", "curiosity"]
        elif score >= -30:
            label, emotions = "Slightly Negative", ["concern", "anxiety"]
        else:
            label, emotions = "Negative", ["frustration", "worry"]

    return {
        "category": category, "score": score, "label": label,
        "dominant_emotions": emotions, "key_narratives": [],
        "polarization_level": None, "trust_level": None,
    }


def _empty_mood(category: str) -> dict:
    return {
        "category": category, "score": 0, "label": "Neutral",
        "dominant_emotions": [], "key_narratives": [],
        "polarization_level": None, "trust_level": None,
    }


async def score_all_moods(
    category_posts: dict[str, list[dict]],
    scored_categories: list[str] | None = None,
) -> dict[str, dict]:
    if scored_categories is None:
        ranked = sorted(category_posts.keys(),
                        key=lambda c: len(category_posts[c]), reverse=True)
        scored_categories = ranked[:MOOD_CATEGORY_LIMIT]

    print(f"[mood_scorer] Scoring mood for: {scored_categories}")
    results = {}
    for cat in scored_categories:
        posts = category_posts.get(cat, [])
        results[cat] = await score_mood(cat, posts)
        print(f"[mood_scorer] {cat}: score={results[cat].get('score')}, label={results[cat].get('label')}")
        await asyncio.sleep(1)
    return results


async def extract_sub_topics(category: str, posts: list[dict]) -> list[str]:
    if not posts:
        return []

    titles = [p.get("title", "") for p in posts[:15] if p.get("title")]
    if not titles:
        return []

    prompt = (
        f"From these {category} social media post titles, list the 3-5 most discussed "
        f"specific sub-topics. Be specific, not generic.\n"
        f"Titles:\n" + "\n".join(f"- {t}" for t in titles) +
        "\n\nReturn ONLY a JSON array of short strings. Example: [\"topic1\", \"topic2\"]"
    )

    raw = await _claude_call(prompt, max_tokens=120)
    if raw:
        cleaned = raw.strip()
        for fence in ["```json", "```"]:
            if cleaned.startswith(fence):
                cleaned = cleaned[len(fence):]
            if cleaned.endswith(fence):
                cleaned = cleaned[:-len(fence)]
        cleaned = cleaned.strip()
        try:
            result = json.loads(cleaned)
            if isinstance(result, list) and result:
                subtopics = [str(s) for s in result if s]
                if subtopics:
                    return subtopics
        except Exception:
            pass

    return _extract_subtopics_fallback(posts, n=5)


async def extract_all_sub_topics(
    ranked_topics: list[dict],
    merged_posts: dict[str, list[dict]],
) -> dict[str, list[str]]:
    results = {}
    for item in ranked_topics:
        cat = item["category"]
        posts = merged_posts.get(cat, [])
        subtopics = await extract_sub_topics(cat, posts)
        results[cat] = subtopics
        print(f"[mood_scorer] Subtopics for {cat}: {subtopics}")
        await asyncio.sleep(0.5)
    return results
