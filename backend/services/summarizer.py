import asyncio
import io
import json
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from groq import AsyncGroq, RateLimitError
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
MODEL = "llama-3.3-70b-versatile"

_client: AsyncGroq | None = None


def get_client() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=GROQ_API_KEY)
    return _client


def _fallback_summary(category: str, articles: list[dict]) -> str:
    """Build a plain summary from headlines when Groq is unavailable."""
    if not articles:
        return "No articles found for this category."
    titles = [f"{a['title']} ({a.get('source', '')})" for a in articles[:5]]
    return (
        f"Top {category} stories: " + " | ".join(titles) + "."
    )


async def summarize_category(category: str, articles: list[dict]) -> dict:
    """Summarize a single category's articles using Groq, with headline fallback."""
    if not articles:
        return {"category": category, "summary": "No articles found for this category.", "articles": []}

    headlines = "\n".join(
        f"- {a['title']} ({a.get('source', '')})" for a in articles
    )

    prompt = (
        f"You are a professional news editor creating a daily digest. "
        f"Summarize the following {category} news headlines into a concise 3-5 sentence paragraph. "
        f"Focus on the most important developments. Be clear, factual, and professional.\n\n"
        f"Headlines:\n{headlines}"
    )

    for attempt in range(2):
        try:
            response = await asyncio.wait_for(
                get_client().chat.completions.create(
                    model=MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=300,
                    temperature=0.3,
                ),
                timeout=30.0,
            )
            summary = response.choices[0].message.content.strip()
            return {"category": category, "summary": summary, "articles": articles}
        except RateLimitError:
            print(f"[summarizer] Rate limit hit for {category} — using headline fallback")
            break
        except asyncio.TimeoutError:
            print(f"[summarizer] Timeout for {category} — using headline fallback")
            break
        except Exception as e:
            print(f"[summarizer] Groq error for {category}: {e}")
            break

    # Fallback: list headlines directly — always produces readable output
    summary = _fallback_summary(category, articles)
    return {"category": category, "summary": summary, "articles": articles}


async def summarize_all(category_data: list[dict]) -> list[dict]:
    """Summarize all categories sequentially to avoid hitting TPD rate limits."""
    results = []
    for cd in category_data:
        result = await summarize_category(cd["category"], cd["articles"])
        results.append(result)
        await asyncio.sleep(1)  # small gap to stay within TPD
    return results


def _build_market_pulse_block(markets: list[dict]) -> str:
    """Generate the Prediction Market Pulse HTML block."""
    if not markets:
        return ""

    rows = ""
    for m in markets:
        yes = m["yes_pct"]
        no = m["no_pct"]
        vol = m["volume_usd"]
        vol_str = f"${vol/1_000_000:.1f}M" if vol >= 1_000_000 else f"${vol/1_000:.0f}K" if vol >= 1_000 else f"${vol:.0f}"
        source = m["source"]
        question = m["question"]

        rows += f"""
        <div style="margin-bottom:16px;padding:14px 16px;background:#0f172a;border-radius:10px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <span style="color:#94a3b8;font-size:11px;font-weight:600;letter-spacing:0.05em;text-transform:uppercase;">{source}</span>
            <span style="color:#64748b;font-size:11px;">{vol_str} traded</span>
          </div>
          <p style="color:#e2e8f0;font-size:13px;margin:0 0 10px 0;line-height:1.5;">{question}</p>
          <div style="display:flex;gap:8px;align-items:center;">
            <span style="color:#4ade80;font-size:12px;font-weight:700;min-width:44px;">YES {yes:.0f}%</span>
            <div style="flex:1;background:#1e293b;border-radius:4px;height:8px;overflow:hidden;">
              <div style="width:{yes:.0f}%;background:linear-gradient(90deg,#22c55e,#4ade80);height:100%;border-radius:4px;"></div>
            </div>
            <span style="color:#f87171;font-size:12px;font-weight:700;min-width:44px;text-align:right;">NO {no:.0f}%</span>
          </div>
        </div>"""

    return f"""
    <div style="background:#1e293b;border-radius:12px;padding:24px;margin-bottom:20px;border-left:4px solid #8b5cf6;">
      <h2 style="color:#f1f5f9;font-size:18px;margin:0 0 6px 0;">📊 Prediction Market Pulse</h2>
      <p style="color:#64748b;font-size:12px;margin:0 0 18px 0;">What people are financially betting on right now — via Kalshi &amp; Polymarket</p>
      {rows}
    </div>"""


def get_logo_bytes() -> bytes | None:
    """Load and resize logo.png to 160x160. Returns raw PNG bytes, or None if unavailable."""
    logo_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "public", "logo.png")
    )
    try:
        from PIL import Image
        img = Image.open(logo_path).resize((160, 160), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()
    except Exception as e:
        print(f"[summarizer] Logo load failed: {e}")
        return None


def build_html_report(summaries: list[dict], run_at: datetime, trigger: str, markets: list[dict] | None = None, timezone: str = "America/New_York") -> str:
    """Generate a full HTML email report.

    The logo is embedded as a base64 data URI so the HTML renders correctly in
    browser iframes (Recent Digests preview).  The email sender replaces the
    data URI src with ``cid:newsdigest_logo`` before attaching the image inline,
    which is what email clients (Gmail, Outlook) require.
    """
    import base64

    try:
        tz = ZoneInfo(timezone)
        local_dt = run_at.replace(tzinfo=ZoneInfo("UTC")).astimezone(tz)
        tz_abbr = local_dt.strftime("%Z")
        timestamp = local_dt.strftime(f"%B %d, %Y at %I:%M %p {tz_abbr}")
    except Exception:
        timestamp = run_at.strftime("%B %d, %Y at %I:%M %p UTC")
    trigger_label = "Scheduled" if trigger == "scheduled" else "Manual Run"

    # Build logo img tag — prefer base64 data URI (works in browsers and email)
    logo_bytes = get_logo_bytes()
    if logo_bytes:
        b64 = base64.b64encode(logo_bytes).decode("ascii")
        logo_src = f"data:image/png;base64,{b64}"
    else:
        logo_src = ""

    logo_html = (
        f'<img src="{logo_src}" alt="News Digest" width="160" height="160" '
        'style="width:160px;height:160px;border-radius:28px;object-fit:cover;display:block;margin:0 auto 16px auto;">'
        if logo_src else ""
    )

    category_blocks = ""
    for item in summaries:
        cat = item["category"]
        summary = item["summary"]
        articles = item.get("articles", [])

        # Skip sections with no articles and no real summary
        if not articles and summary in ("No articles found for this category.", ""):
            continue

        article_links = "".join(
            f'<li><a href="{a["url"]}" style="color:#60a5fa;text-decoration:none;">'
            f'{a["title"]}</a>'
            f'<span style="color:#94a3b8;font-size:12px;"> — {a.get("source","")}</span></li>'
            for a in articles[:5]
        )

        category_blocks += f"""
        <div style="background:#1e293b;border-radius:12px;padding:24px;margin-bottom:20px;border-left:4px solid #3b82f6;">
          <h2 style="color:#f1f5f9;font-size:18px;margin:0 0 12px 0;">{cat}</h2>
          <p style="color:#cbd5e1;font-size:14px;line-height:1.7;margin:0 0 16px 0;">{summary}</p>
          <ul style="margin:0;padding-left:20px;color:#94a3b8;font-size:13px;">
            {article_links}
          </ul>
        </div>
        """

    market_pulse_block = _build_market_pulse_block(markets or [])

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#0f172a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <div style="max-width:680px;margin:0 auto;padding:32px 16px;">

    <!-- Header -->
    <div style="text-align:center;margin-bottom:32px;">
      {logo_html}
      <h1 style="color:#f8fafc;font-size:30px;font-weight:700;margin:0 0 4px 0;letter-spacing:-0.5px;">
        News Digest
      </h1>
      <p style="color:#94a3b8;font-size:13px;margin:0 0 10px 0;">Personal Brain Feed</p>
      <p style="color:#64748b;font-size:13px;margin:0;">
        {timestamp} &nbsp;·&nbsp; {trigger_label}
      </p>
    </div>

    <!-- Category Summaries -->
    {category_blocks}

    <!-- Prediction Market Pulse -->
    {market_pulse_block}

    <!-- Footer -->
    <div style="text-align:center;padding-top:24px;border-top:1px solid #1e293b;margin-top:8px;">
      <p style="color:#475569;font-size:12px;margin:0;">
        Generated by your personal News Digest · Powered by Groq AI
      </p>
    </div>

  </div>
</body>
</html>"""
    return html


def build_json_report(summaries: list[dict], run_at: datetime, trigger: str) -> dict:
    """Generate a JSON-serializable report for the frontend."""
    return {
        "run_at": run_at.isoformat(),
        "trigger": trigger,
        "categories": summaries,
    }
