"""
Mood scorer for Market Mood.
Uses Claude (claude-haiku-4-5 for speed/cost) to score sentiment per category
and extract sub-topics from post titles.
"""
import asyncio
import json
import re
import os
from collections import Counter
from google import genai as google_genai

_client = None

MOOD_CATEGORY_LIMIT = 7  # Score all Market Mood categories

STOP_WORDS = {
    # Articles, conjunctions, prepositions
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'as', 'into', 'over', 'than', 'out', 'up',
    'down', 'about', 'after', 'before', 'between', 'through', 'during',
    'without', 'against', 'within', 'per', 'across', 'behind', 'beyond',
    'plus', 'except', 'around', 'along', 'among', 'since', 'while',
    'although', 'because', 'unless', 'until', 'whether', 'though',
    # Pronouns
    'it', 'its', 'this', 'that', 'these', 'those', 'he', 'she', 'they',
    'we', 'you', 'i', 'his', 'her', 'their', 'our', 'your', 'my',
    'both', 'either', 'neither', 'another', 'each', 'own', 'same',
    # Auxiliary verbs
    'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did',
    'will', 'would', 'could', 'should', 'may', 'might', 'can',
    # Common verbs (too generic to be topics)
    'get', 'gets', 'got', 'getting', 'make', 'makes', 'made', 'making',
    'say', 'says', 'said', 'saying', 'know', 'think', 'want', 'need',
    'use', 'used', 'using', 'take', 'takes', 'took', 'taking',
    'go', 'going', 'goes', 'went', 'come', 'comes', 'came', 'coming',
    'look', 'looks', 'looking', 'seem', 'seems', 'seemed', 'show', 'shows',
    'tell', 'told', 'find', 'found', 'give', 'gave', 'given',
    'become', 'became', 'becomes', 'keep', 'kept', 'try', 'tried',
    'call', 'let', 'run', 'move', 'turn', 'start', 'end', 'open',
    'help', 'talk', 'read', 'write', 'lead', 'live', 'stand',
    'bring', 'happen', 'include', 'continue', 'feel', 'believe',
    'allow', 'add', 'change', 'expect', 'remain', 'appear',
    'send', 'build', 'stay', 'provide', 'raise', 'offer', 'consider',
    'increase', 'face', 'lose', 'pass', 'stop', 'ask', 'put', 'set',
    'mean', 'means', 'meant', 'leave', 'left', 'hold', 'pay',
    # Negations and conjunctions
    'not', 'no', 'nor', 'never', 'always', 'still', 'already', 'yet',
    'however', 'therefore', 'instead', 'rather', 'indeed', 'actually',
    # Quantifiers / generic descriptors
    'all', 'more', 'most', 'many', 'much', 'some', 'any', 'few', 'less',
    'least', 'every', 'each', 'only', 'also', 'even', 'very', 'really',
    'quite', 'too', 'such', 'different', 'other', 'new', 'old',
    'big', 'large', 'small', 'high', 'low', 'long', 'short',
    'good', 'bad', 'right', 'wrong', 'better', 'worse', 'best', 'worst',
    'full', 'half', 'both', 'next', 'last', 'first',
    # Generic nouns (not specific enough to be topics)
    'thing', 'things', 'something', 'anything', 'everything', 'nothing',
    'someone', 'anyone', 'everyone', 'nobody', 'people', 'person',
    'time', 'times', 'year', 'years', 'day', 'days', 'week', 'weeks',
    'month', 'months', 'today', 'tomorrow', 'yesterday',
    'way', 'ways', 'case', 'part', 'parts', 'place', 'places',
    'point', 'points', 'kind', 'type', 'side', 'world', 'line',
    'number', 'lot', 'lots', 'bit', 'back', 'here', 'there', 'where',
    # Common adverbs
    'how', 'why', 'what', 'when', 'who', 'which',
    'just', 'now', 'then', 'soon', 'often', 'ever', 'else',
    'well', 'away', 'maybe', 'perhaps', 'probably', 'likely',
    # Question word contractions / common short words
    'whats', 'thats', 'dont', 'cant', 'wont', 'isnt', 'arent',
    'wasnt', 'werent', 'hasnt', 'havent', 'wouldnt', 'couldnt',
    'shouldnt', 'didnt', 'doesnt', 'its', 'theres', 'theyre',
    # Common source/meta words
    'said', 'says', 'amid', 'via', 'per',
    'report', 'reports', 'reported', 'update', 'updates', 'updated',
    'news', 'post', 'posts', 'comment', 'comments', 'question',
    'week', 'month', 'year', 'daily', 'weekly', 'monthly', 'annual',
    # Common country/region abbreviations too short to be useful
    'us', 'uk',
}


def get_client() -> google_genai.Client:
    global _client
    if _client is None:
        _client = google_genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return _client


async def _gemini_call(prompt: str, max_tokens: int = 300) -> str | None:
    """Gemini call run in executor to avoid blocking the event loop."""
    loop = asyncio.get_running_loop()
    try:
        def _call():
            return get_client().models.generate_content(
                model="models/gemini-2.0-flash-lite",
                contents=prompt,
            )
        resp = await asyncio.wait_for(loop.run_in_executor(None, _call), timeout=30.0)
        return resp.text.strip()
    except asyncio.TimeoutError:
        print("[mood_scorer] Gemini timed out")
        return None
    except Exception as e:
        print(f"[mood_scorer] Gemini error: {e}")
        return None


def _extract_subtopics_fallback(posts: list[dict], n: int = 5) -> list[str]:
    titles = [p.get("title", "") for p in posts[:40] if p.get("title")]
    if not titles:
        return []

    def tokenize(text: str) -> list[str]:
        raw_tokens = re.findall(r"[A-Za-z][a-zA-Z']{2,}", text)
        result = []
        for t in raw_tokens:
            # Strip apostrophe suffixes ('s, 't, 're, 've, 'll, etc.) before checking
            clean = re.sub(r"'[a-z]{1,3}$", '', t.lower())
            if clean not in STOP_WORDS and len(clean) > 3:
                result.append(t)
        return result

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

    raw = await _gemini_call(prompt, max_tokens=300)
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


MAX_SUBTOPICS = 3  # Maximum subtopics shown per category


def _clean_titles(posts: list[dict], limit: int = 20) -> list[str]:
    """Extract and clean post titles, stripping Reddit/HN meta-prefixes."""
    STRIP_PREFIXES = ("TIL ", "TIL: ", "TIL that ", "Ask HN: ", "Show HN: ", "Tell HN: ")
    titles = []
    for p in posts[:limit]:
        t = p.get("title", "").strip()
        if not t:
            continue
        for prefix in STRIP_PREFIXES:
            if t.startswith(prefix):
                t = t[len(prefix):]
        if t:
            titles.append(t)
    return titles


def _parse_gemini_list(raw: str) -> list[str]:
    """Parse a JSON array from a Gemini response, stripping markdown fences."""
    cleaned = raw.strip()
    for fence in ["```json", "```"]:
        if cleaned.startswith(fence):
            cleaned = cleaned[len(fence):]
        if cleaned.endswith(fence):
            cleaned = cleaned[:-len(fence)]
    cleaned = cleaned.strip()
    result = json.loads(cleaned)
    if isinstance(result, list):
        return [str(s).strip() for s in result if s and str(s).strip()]
    return []


def _top_posts_by_engagement(posts: list[dict], n: int) -> list[dict]:
    return sorted(
        [p for p in posts if p.get("title")],
        key=lambda p: p.get("score", 0) + p.get("num_comments", 0),
        reverse=True,
    )[:n]


def _hot_topics_fallback(posts: list[dict]) -> list[str]:
    """Fallback: take top posts by engagement, truncate titles to 5 words."""
    results = []
    seen: set[str] = set()
    for p in _top_posts_by_engagement(posts, MAX_SUBTOPICS * 3):
        title = p["title"].strip()
        for prefix in ("TIL ", "TIL: ", "TIL that ", "Ask HN: ", "Show HN: ", "Tell HN: "):
            if title.startswith(prefix):
                title = title[len(prefix):]
        words = title.split()[:6]
        while words and words[-1].lower() in {'a', 'an', 'the', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or'}:
            words.pop()
        short = " ".join(words[:5])
        if short and short.lower() not in seen:
            seen.add(short.lower())
            results.append(short)
        if len(results) >= MAX_SUBTOPICS:
            break
    return results


# Shared prompt rules injected into every subtopic extraction call
_TOPIC_RULES = (
    "Rules for each topic:\n"
    "- 3-5 words maximum\n"
    "- Neutral, factual, journalistic language — no inflammatory, partisan, or sensationalist phrasing\n"
    "- Name specific events, policies, companies, people, or issues\n"
    "- Avoid generic filler words (time, people, things, world, situation)\n"
    f"Return ONLY a JSON array of exactly {MAX_SUBTOPICS} short strings.\n"
)


async def extract_sub_topics(category: str, posts: list[dict]) -> list[str]:
    if not posts:
        return []

    if category == "Daily Hot Topics":
        return await _extract_daily_hot_topics(posts)

    if category == "Sector Sentiment":
        return await _extract_sector_topics(posts)

    titles = _clean_titles(posts, limit=20)
    if not titles:
        return []

    prompt = (
        f"From these {category} social media post titles, identify the {MAX_SUBTOPICS} "
        f"most newsworthy specific topics being discussed right now.\n"
        f"Good examples: 'Fed rate decision', 'Gaza ceasefire talks', 'GPT-5 release', "
        f"'mortgage rate rise', 'tariff impact'.\n"
        f"{_TOPIC_RULES}"
        f"Titles:\n" + "\n".join(f"- {t}" for t in titles[:15])
    )

    raw = await _gemini_call(prompt, max_tokens=150)
    if raw:
        try:
            result = _parse_gemini_list(raw)
            if result:
                return result[:MAX_SUBTOPICS]
        except Exception:
            pass

    return _extract_subtopics_fallback(posts, n=MAX_SUBTOPICS)


async def _extract_daily_hot_topics(posts: list[dict]) -> list[str]:
    """
    For Daily Hot Topics: rank by engagement, compress each top story into
    a short neutral headline. Falls back to title truncation.
    """
    top = _top_posts_by_engagement(posts, MAX_SUBTOPICS * 2)
    titles = _clean_titles(top, limit=MAX_SUBTOPICS)
    if not titles:
        return []

    prompt = (
        f"Compress each of these trending news headlines into a 3-5 word neutral summary.\n"
        f"Good examples: 'Fluoride water safety review', 'Swalwell House resignation', "
        f"'Antarctic ice shelf collapse', 'Netflix password crackdown'.\n"
        f"{_TOPIC_RULES}"
        f"Headlines:\n" + "\n".join(f"- {t}" for t in titles)
    )

    raw = await _gemini_call(prompt, max_tokens=150)
    if raw:
        try:
            result = _parse_gemini_list(raw)
            if result:
                return result[:MAX_SUBTOPICS]
        except Exception:
            pass

    return _hot_topics_fallback(posts)


async def _extract_sector_topics(posts: list[dict]) -> list[str]:
    """
    For Sector Sentiment: each topic must be prefixed with its sector name
    so users immediately know which industry is being discussed.
    e.g. 'Energy: natural gas prices', 'Healthcare: drug pricing bill'
    """
    titles = _clean_titles(posts, limit=20)
    if not titles:
        return []

    prompt = (
        f"From these Sector Sentiment posts, identify the {MAX_SUBTOPICS} most discussed topics.\n"
        f"For each topic, identify its sector (Energy, Healthcare, Technology, Finance, "
        f"Consumer, Industrial, Materials) and format as 'Sector: topic'.\n"
        f"Good examples: 'Energy: natural gas prices', 'Healthcare: drug pricing bill', "
        f"'Tech: data center demand', 'Finance: bank earnings'.\n"
        f"{_TOPIC_RULES}"
        f"Titles:\n" + "\n".join(f"- {t}" for t in titles[:15])
    )

    raw = await _gemini_call(prompt, max_tokens=150)
    if raw:
        try:
            result = _parse_gemini_list(raw)
            if result:
                return result[:MAX_SUBTOPICS]
        except Exception:
            pass

    return _extract_subtopics_fallback(posts, n=MAX_SUBTOPICS)


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
