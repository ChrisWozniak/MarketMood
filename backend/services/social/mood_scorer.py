import asyncio
import json
import re
from collections import Counter
from groq import AsyncGroq, RateLimitError
from dotenv import load_dotenv
import os

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

MODEL_MOOD     = "llama-3.3-70b-versatile"
MODEL_SUBTOPIC = "llama-3.1-8b-instant"

_client: AsyncGroq | None = None

# How many categories to score mood for (picks top N by post volume)
MOOD_CATEGORY_LIMIT = 4

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
    'take', 'takes', 'give', 'gives', 'come', 'goes', 'show', 'shows', 'need',
    'use', 'used', 'using', 'want', 'look', 'seem', 'tell', 'try', 'ask',
    'call', 'keep', 'let', 'put', 'set', 'run', 'move', 'live', 'play',
    'year', 'years', 'day', 'days', 'week', 'weeks', 'time', 'times',
    'way', 'ways', 'part', 'parts', 'place', 'people', 'person', 'thing',
    'things', 'world', 'country', 'city', 'state', 'there', 'here',
}


def get_client() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=GROQ_API_KEY)
    return _client


async def _groq_call(model: str, messages: list, max_tokens: int, temperature: float,
                     response_format: dict | None = None, retries: int = 1) -> str | None:
    """Wrapper with rate-limit retry and 25s hard timeout per call."""
    for attempt in range(retries + 1):
        try:
            kwargs = dict(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            if response_format:
                kwargs["response_format"] = response_format
            resp = await asyncio.wait_for(
                get_client().chat.completions.create(**kwargs),
                timeout=25.0,
            )
            return resp.choices[0].message.content.strip()
        except asyncio.TimeoutError:
            print(f"[mood_scorer] Groq timed out (attempt {attempt+1})")
            return None
        except RateLimitError as e:
            if attempt < retries:
                print(f"[mood_scorer] Rate limit — waiting 10s before retry")
                await asyncio.sleep(10)
            else:
                print(f"[mood_scorer] Rate limit exhausted: {e}")
                return None
        except Exception as e:
            print(f"[mood_scorer] Groq error: {e}")
            return None


def _extract_subtopics_fallback(posts: list[dict], n: int = 5) -> list[str]:
    """
    Keyword-based subtopic extraction from post titles — no AI required.
    Works even with very few posts by relaxing bigram frequency requirements.
    """
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

    # With few posts, lower threshold to 1; with many posts prefer repeated bigrams
    min_bigram_count = 2 if len(titles) >= 8 else 1
    top_bigrams = [term for term, cnt in bigram_counts.most_common(n * 2)
                   if cnt >= min_bigram_count]

    # Fill with single words not already part of a selected bigram
    top_words = []
    for word, _ in word_counts.most_common(n * 3):
        covered = any(word.lower() in bg.lower() for bg in top_bigrams)
        if not covered:
            top_words.append(word)

    combined = (top_bigrams + top_words)[:n]
    return combined


async def score_mood(category: str, posts: list[dict]) -> dict:
    """Score the social mood for a category using Groq."""
    if not posts:
        return _empty_mood(category)

    sample_titles = [p.get("title", "") for p in posts[:25] if p.get("title")]
    if not sample_titles:
        return _empty_mood(category)

    titles_text = "\n".join(f"- {t}" for t in sample_titles)
    prompt = f"""You are a social media analyst. Analyze the sentiment of these {category} social media post titles.

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

    raw = await _groq_call(MODEL_MOOD, [{"role": "user", "content": prompt}],
                           max_tokens=300, temperature=0.2,
                           response_format={"type": "json_object"})
    if not raw:
        print(f"[mood_scorer] Groq unavailable for {category} — using keyword fallback")
        return _score_mood_fallback(category, posts)

    try:
        data = json.loads(raw)
        data["category"] = category
        return data
    except Exception as e:
        print(f"[mood_scorer] JSON parse error for {category}: {e}")
        return _score_mood_fallback(category, posts)


POSITIVE_WORDS = {
    'win', 'wins', 'winning', 'won', 'record', 'best', 'top', 'great', 'good',
    'success', 'successful', 'breakthrough', 'growth', 'rise', 'rises', 'gain',
    'gains', 'profit', 'rally', 'soars', 'boost', 'approve', 'approval',
    'launch', 'launches', 'new', 'first', 'love', 'amazing', 'incredible',
    'improve', 'improved', 'improvement', 'safe', 'safety', 'save', 'saved',
    'positive', 'hope', 'optimism', 'agree', 'deal', 'progress', 'advance',
}
NEGATIVE_WORDS = {
    'fail', 'fails', 'failed', 'failure', 'lose', 'loses', 'loss', 'losses',
    'crash', 'crashes', 'crisis', 'collapse', 'collapses', 'fear', 'fears',
    'warn', 'warning', 'warnings', 'threat', 'threatens', 'danger', 'dangerous',
    'attack', 'attacks', 'kill', 'killed', 'death', 'deaths', 'dead',
    'disaster', 'scandal', 'fraud', 'corrupt', 'arrest', 'arrested', 'ban',
    'banned', 'block', 'blocked', 'reject', 'rejected', 'cut', 'cuts',
    'fall', 'falls', 'falling', 'drop', 'drops', 'decline', 'declines',
    'negative', 'bad', 'worse', 'worst', 'terrible', 'awful', 'hate',
    'problem', 'problems', 'issue', 'issues', 'concern', 'concerns', 'risk',
    'layoff', 'layoffs', 'fired', 'bankrupt', 'recession', 'inflation',
    'protest', 'protests', 'riot', 'riots', 'war', 'conflict', 'violence',
}


def _score_mood_fallback(category: str, posts: list[dict]) -> dict:
    """Keyword-based mood scoring when Groq is unavailable."""
    titles = [p.get("title", "").lower() for p in posts if p.get("title")]
    if not titles:
        return _empty_mood(category)

    pos = sum(1 for t in titles for w in t.split() if w.strip('.,!?') in POSITIVE_WORDS)
    neg = sum(1 for t in titles for w in t.split() if w.strip('.,!?') in NEGATIVE_WORDS)
    total = pos + neg

    if total == 0:
        score = 0
        label = "Neutral"
        emotions = ["mixed"]
    else:
        ratio = (pos - neg) / total
        score = int(ratio * 60)  # scale to ±60 max for keyword method
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
        "category": category,
        "score": score,
        "label": label,
        "dominant_emotions": emotions,
        "key_narratives": [],
        "polarization_level": None,
        "trust_level": None,
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
    """
    Score mood for the given categories (or auto-pick top N by post count).
    Sequential calls to avoid Groq rate limits.
    """
    if scored_categories is None:
        # Pick categories with the most posts
        ranked = sorted(category_posts.keys(),
                        key=lambda c: len(category_posts[c]), reverse=True)
        scored_categories = ranked[:MOOD_CATEGORY_LIMIT]

    print(f"[mood_scorer] Scoring mood for: {scored_categories}")
    results = {}
    for cat in scored_categories:
        posts = category_posts.get(cat, [])
        results[cat] = await score_mood(cat, posts)
        print(f"[mood_scorer] {cat}: score={results[cat].get('score')}, label={results[cat].get('label')}")
        await asyncio.sleep(2)  # gap between calls
    return results


async def extract_sub_topics(category: str, posts: list[dict]) -> list[str]:
    """
    Extract top 3-5 sub-topics. Tries Groq first, falls back to keyword extraction.
    """
    if not posts:
        return []

    titles = [p.get("title", "") for p in posts[:15] if p.get("title")]
    if not titles:
        return []

    # Try Groq first
    prompt = (
        f"From these {category} social media post titles, list the 3-5 most discussed "
        f"specific sub-topics (be specific, not generic). "
        f"Titles:\n" + "\n".join(f"- {t}" for t in titles) +
        "\n\nReturn ONLY a JSON array of short strings. Example: [\"topic1\", \"topic2\"]"
    )

    raw = await _groq_call(MODEL_SUBTOPIC, [{"role": "user", "content": prompt}],
                           max_tokens=120, temperature=0.2)

    if raw:
        # Strip markdown fences
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

    # Fallback: keyword extraction from titles (always works)
    print(f"[mood_scorer] Using keyword fallback for {category} subtopics")
    return _extract_subtopics_fallback(posts, n=5)


async def extract_all_sub_topics(
    ranked_topics: list[dict],
    merged_posts: dict[str, list[dict]],
) -> dict[str, list[str]]:
    """Extract subtopics for all categories sequentially."""
    results = {}
    for item in ranked_topics:
        cat = item["category"]
        posts = merged_posts.get(cat, [])
        subtopics = await extract_sub_topics(cat, posts)
        results[cat] = subtopics
        print(f"[mood_scorer] Subtopics for {cat}: {subtopics}")
        await asyncio.sleep(0.5)
    return results
