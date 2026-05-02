"""
Email distribution for Market Mood — formatted HTML report via Gmail SMTP.
"""
import asyncio
import json
import re
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "email_config.json"

# ── Theme palettes ─────────────────────────────────────────────────────────────
_THEMES: dict[str, dict[str, str]] = {
    "dark": {
        "page":         "#0f172a",
        "card":         "#1e293b",
        "signal_card":  "#0f172a",
        "border":       "#334155",
        "text_main":    "#e2e8f0",
        "text_sub":     "#94a3b8",
        "text_muted":   "#475569",
        "text_footer":  "#334155",
        "link":         "#7dd3fc",
        "section_head": "#94a3b8",
        "bar_track":    "#334155",
        "tick_bg":      "#1e293b",
        "tick_border":  "#334155",
        "tick_color":   "#93c5fd",
        "header_grad":  "linear-gradient(135deg,#1e293b 0%,#0f172a 100%)",
        "header_border":"#334155",
        "header_title": "#f1f5f9",
        "header_sub":   "#64748b",
        "header_ts":    "#94a3b8",
        "market_div":   "#0f172a",
        "mkt_src_bg":   "22",   # alpha suffix for hex badge bg
    },
    "light": {
        "page":         "#f4ead8",
        "card":         "#fdf7ee",
        "signal_card":  "#f8f5ee",
        "border":       "#e2d9c5",
        "text_main":    "#1e293b",
        "text_sub":     "#64748b",
        "text_muted":   "#a8977e",
        "text_footer":  "#c4b49a",
        "link":         "#7c3aed",
        "section_head": "#78716c",
        "bar_track":    "#e2d9c5",
        "tick_bg":      "#fdf7ee",
        "tick_border":  "#e2d9c5",
        "tick_color":   "#7c3aed",
        "header_grad":  "linear-gradient(135deg,#fdf7ee 0%,#f4ead8 100%)",
        "header_border":"#e2d9c5",
        "header_title": "#1e293b",
        "header_sub":   "#78716c",
        "header_ts":    "#64748b",
        "market_div":   "#f4ead8",
        "mkt_src_bg":   "28",   # slightly more opaque on light bg
    },
}

# Run-type badge colors per theme
_RUN_BADGE: dict[str, dict[str, dict[str, str]]] = {
    "dark": {
        "Scheduled": {"bg": "#22c55e22", "border": "#22c55e66", "color": "#22c55e", "icon": "🕐"},
        "Manual":    {"bg": "#6366f122", "border": "#6366f166", "color": "#a5b4fc", "icon": "⚡"},
        "Test":      {"bg": "#f59e0b22", "border": "#f59e0b66", "color": "#f59e0b", "icon": "✉"},
    },
    "light": {
        "Scheduled": {"bg": "#dcfce7",   "border": "#86efac",   "color": "#16a34a", "icon": "🕐"},
        "Manual":    {"bg": "#e0e7ff",   "border": "#a5b4fc",   "color": "#4f46e5", "icon": "⚡"},
        "Test":      {"bg": "#fef3c7",   "border": "#fcd34d",   "color": "#d97706", "icon": "✉"},
    },
}

# Common words to ignore when fuzzy-matching headlines to post URLs
_MATCH_STOP = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "are", "was", "were", "be",
    "it", "its", "this", "that", "have", "has", "had", "will", "would",
    "could", "should", "not", "no", "so", "up", "out", "how", "why",
    "what", "when", "who", "which", "do", "does", "did", "into", "over",
}


def load_email_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"enabled": False, "smtp_sender": "", "smtp_password": "", "recipients": [], "email_theme": "dark"}


def save_email_config(config: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")


def _icon_html() -> str:
    """Return an email-safe HTML icon (table cell with emoji) — works in Gmail and all clients."""
    return (
        '<table cellpadding="0" cellspacing="0" border="0" align="center"'
        ' style="margin:0 auto 12px;">'
        '<tr><td width="56" height="56"'
        ' style="background:linear-gradient(135deg,#863bff 0%,#6d28d9 100%);'
        'border-radius:14px;text-align:center;vertical-align:middle;'
        'font-size:30px;line-height:56px;mso-line-height-rule:exactly;">'
        '&#x26A1;'  # ⚡ lightning bolt — HTML entity so it works everywhere
        '</td></tr></table>'
    )


def _score_bar(score: int) -> str:
    """20-char ASCII bar for mood score -100..+100."""
    normalized = (score + 100) / 200
    filled = int(normalized * 20)
    return "█" * filled + "░" * (20 - filled)


def _signal_emoji(signal: str) -> str:
    return {"bullish": "📈", "bearish": "📉", "neutral": "⚖️"}.get(signal, "⚖️")


def _confidence_color(confidence: str) -> str:
    return {"high": "#22c55e", "medium": "#f59e0b", "low": "#94a3b8"}.get(confidence, "#94a3b8")


def _vol_str(vol: float) -> str:
    if vol >= 1_000_000:
        return f"${vol / 1_000_000:.1f}M"
    if vol >= 1_000:
        return f"${vol / 1_000:.0f}K"
    return f"${vol:.0f}"


def _words(text: str) -> set[str]:
    return {w for w in re.sub(r"[^\w\s]", "", text.lower()).split() if w not in _MATCH_STOP}


def _find_best_url(headline: str, posts: list[dict], threshold: float = 0.12) -> str:
    """Fuzzy-match a headline to the best-fitting post URL via Jaccard overlap."""
    h_words = _words(headline)
    if not h_words:
        return ""
    best_score, best_url = 0.0, ""
    for post in posts:
        title = post.get("title", "")
        url   = post.get("url", "")
        if not title or not url:
            continue
        t_words = _words(title)
        if not t_words:
            continue
        union = len(h_words | t_words)
        if union == 0:
            continue
        j = len(h_words & t_words) / union
        if j > best_score:
            best_score, best_url = j, url
    return best_url if best_score >= threshold else ""


def _ticker_badge_html(ticker: str, C: dict) -> str:
    url = f"https://finance.yahoo.com/quote/{ticker}"
    return (
        f'<a href="{url}" target="_blank" rel="noopener noreferrer" '
        f'style="display:inline-block;background:{C["tick_bg"]};border:1px solid {C["tick_border"]};'
        f'color:{C["tick_color"]};font-family:monospace;font-size:10px;font-weight:700;'
        f'padding:2px 6px;border-radius:4px;margin:1px;text-decoration:none;">'
        f'{ticker}</a>'
    )


def build_html_report(
    mood_scores: dict,
    trending_topics: list,
    investment_signals: list,
    prediction_markets: list,
    captured_at: datetime,
    run_type: str = "Scheduled",
    merged_posts: dict | None = None,
    theme: str = "dark",
) -> tuple[str, str]:
    """Return (html_body, plain_text_body) for the Market Mood report."""
    C    = _THEMES.get(theme, _THEMES["dark"])
    B    = _RUN_BADGE.get(theme, _RUN_BADGE["dark"]).get(run_type, _RUN_BADGE["dark"]["Scheduled"])
    ts   = captured_at.strftime("%A, %B %d, %Y at %I:%M %p UTC")
    # ── HTML ─────────────────────────────────────────────────────────────────
    hp: list[str] = []
    hp.append(f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Market Mood Report</title></head>
<body style="margin:0;padding:0;background:{C['page']};font-family:'Segoe UI',Arial,sans-serif;color:{C['text_main']};">
<table width="100%" cellpadding="0" cellspacing="0" style="background:{C['page']};padding:20px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

<!-- Header — centered -->
<tr><td style="background:{C['header_grad']};border:1px solid {C['header_border']};border-radius:12px 12px 0 0;padding:28px 28px 22px;text-align:center;">
  {_icon_html()}
  <h1 style="margin:0 0 3px;font-size:22px;font-weight:700;color:{C['header_title']};letter-spacing:-0.5px;">Market Mood</h1>
  <p style="margin:0 0 12px;font-size:12px;color:{C['header_sub']};">Social Sentiment Barometer</p>
  <span style="display:inline-block;background:{B['bg']};border:1px solid {B['border']};color:{B['color']};font-size:11px;font-weight:600;padding:3px 12px;border-radius:20px;">
    {B['icon']} {run_type}
  </span>
  <p style="margin:12px 0 0;font-size:12px;color:{C['header_ts']};">{ts}</p>
</td></tr>
""")

    # ── Mood Scores ──────────────────────────────────────────────────────────
    hp.append(f"""<tr><td style="background:{C['card']};border-left:1px solid {C['border']};border-right:1px solid {C['border']};padding:20px 28px;">
  <h2 style="margin:0 0 14px;font-size:13px;font-weight:600;color:{C['section_head']};text-transform:uppercase;letter-spacing:0.08em;">Market Mood Summary</h2>""")
    for cat, data in mood_scores.items():
        score = data.get("score", 0) if isinstance(data, dict) else 0
        label = data.get("label", "Neutral") if isinstance(data, dict) else "Neutral"
        color = "#22c55e" if score > 10 else "#ef4444" if score < -10 else C["text_sub"]
        bar_pct = max(2, min(98, (score + 100) / 2))
        sign = "+" if score > 0 else ""
        grad = "linear-gradient(90deg,#16a34a,#4ade80)" if score >= 0 else "linear-gradient(90deg,#dc2626,#f87171)"
        hp.append(f"""  <div style="margin-bottom:12px;">
    <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:4px;">
      <span style="font-size:13px;color:{C['text_main']};font-weight:500;">{cat}</span>
      <span style="font-size:12px;font-weight:700;color:{color};">{sign}{score} &nbsp;{label}</span>
    </div>
    <div style="background:{C['bar_track']};border-radius:4px;height:6px;overflow:hidden;">
      <div style="width:{bar_pct:.0f}%;height:6px;background:{grad};border-radius:4px;"></div>
    </div>
  </div>""")
    hp.append("</td></tr>")

    # ── Trending Topics (article links) ──────────────────────────────────────
    if trending_topics:
        hp.append(f"""<tr><td style="background:{C['card']};border-left:1px solid {C['border']};border-right:1px solid {C['border']};padding:0 28px 20px;">
  <div style="border-top:1px solid {C['border']};padding-top:20px;">
  <h2 style="margin:0 0 14px;font-size:13px;font-weight:600;color:{C['section_head']};text-transform:uppercase;letter-spacing:0.08em;">Trending Topics</h2>""")
        for topic in trending_topics[:6]:
            cat       = topic.get("category", "")
            trend     = topic.get("trend", "")
            icon_dir  = "↑" if trend == "rising" else "↓" if trend == "falling" else "→"
            subs      = topic.get("sub_topics", [])
            cat_posts = (merged_posts or {}).get(cat, [])
            hp.append(f"""  <div style="margin-bottom:14px;">
    <p style="margin:0 0 5px;font-size:13px;font-weight:600;color:{C['link']};">{icon_dir} {cat}</p>""")
            for st in subs[:4]:
                url = _find_best_url(st, cat_posts) if cat_posts else ""
                if url:
                    hp.append(
                        f'    <p style="margin:0 0 3px 12px;font-size:12px;">'
                        f'• <a href="{url}" target="_blank" rel="noopener noreferrer" '
                        f'style="color:{C["link"]};text-decoration:none;">{st}</a></p>'
                    )
                else:
                    hp.append(f'    <p style="margin:0 0 3px 12px;font-size:12px;color:{C["text_sub"]};">• {st}</p>')
            hp.append("  </div>")
        hp.append("</div></td></tr>")

    # ── Investment Signals (Yahoo Finance ticker links) ───────────────────────
    if investment_signals:
        hp.append(f"""<tr><td style="background:{C['card']};border-left:1px solid {C['border']};border-right:1px solid {C['border']};padding:0 28px 20px;">
  <div style="border-top:1px solid {C['border']};padding-top:20px;">
  <h2 style="margin:0 0 14px;font-size:13px;font-weight:600;color:{C['section_head']};text-transform:uppercase;letter-spacing:0.08em;">Investment Signals</h2>""")
        for sig in investment_signals:
            cat        = sig.get("category", "")
            signal     = sig.get("signal", "neutral")
            insight    = sig.get("insight", "")
            tickers    = sig.get("tickers", [])
            confidence = sig.get("confidence", "low")
            sig_color  = {"bullish": "#22c55e", "bearish": "#ef4444", "neutral": C["text_sub"]}.get(signal, C["text_sub"])
            conf_color = _confidence_color(confidence)
            emoji      = _signal_emoji(signal)
            badges     = " ".join(_ticker_badge_html(t, C) for t in tickers)
            hp.append(f"""  <div style="background:{C['signal_card']};border:1px solid {C['border']};border-radius:8px;padding:14px;margin-bottom:10px;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
      <span style="font-size:13px;font-weight:600;color:{C['text_main']};">{cat}</span>
      <div>
        <span style="font-size:11px;font-weight:700;color:{sig_color};text-transform:uppercase;">{emoji} {signal}</span>
        &nbsp;
        <span style="font-size:10px;color:{conf_color};border:1px solid {conf_color}44;padding:1px 6px;border-radius:10px;">{confidence}</span>
      </div>
    </div>
    <p style="margin:0 0 8px;font-size:12px;color:{C['text_sub']};line-height:1.5;">{insight}</p>
    <div>{badges}</div>
  </div>""")
        hp.append("</div></td></tr>")

    # ── Prediction Markets ───────────────────────────────────────────────────
    if prediction_markets:
        hp.append(f"""<tr><td style="background:{C['card']};border-left:1px solid {C['border']};border-right:1px solid {C['border']};padding:0 28px 20px;">
  <div style="border-top:1px solid {C['border']};padding-top:20px;">
  <h2 style="margin:0 0 14px;font-size:13px;font-weight:600;color:{C['section_head']};text-transform:uppercase;letter-spacing:0.08em;">Prediction Market Highlights</h2>""")
        for m in prediction_markets[:5]:
            src      = m.get("source", "")
            q        = m.get("question", "")
            yes      = m.get("yes_pct", 0)
            vol      = m.get("volume_usd", 0)
            src_color = "#8b5cf6" if src == "Kalshi" else "#0ea5e9"
            alpha    = C["mkt_src_bg"]
            bar_w    = min(98, max(2, yes))
            hp.append(f"""  <div style="margin-bottom:12px;padding-bottom:12px;border-bottom:1px solid {C['market_div']};">
    <div style="margin-bottom:4px;"><span style="font-size:10px;font-weight:600;color:{src_color};background:{src_color}{alpha};padding:1px 7px;border-radius:10px;">{src}</span></div>
    <p style="margin:4px 0;font-size:12px;color:{C['text_main']};line-height:1.4;">{q}</p>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-top:6px;">
      <span style="font-size:11px;color:#22c55e;font-weight:700;">YES {yes:.0f}%</span>
      <div style="flex:1;margin:0 8px;background:{C['bar_track']};border-radius:3px;height:4px;overflow:hidden;">
        <div style="width:{bar_w:.0f}%;height:4px;background:linear-gradient(90deg,#16a34a,#4ade80);"></div>
      </div>
      <span style="font-size:11px;color:{C['text_sub']};">💰 {_vol_str(vol)}</span>
    </div>
  </div>""")
        hp.append("</div></td></tr>")

    # ── Footer ───────────────────────────────────────────────────────────────
    hp.append(f"""<tr><td style="background:{C['signal_card']};border:1px solid {C['border']};border-top:none;border-radius:0 0 12px 12px;padding:16px 28px;">
  <p style="margin:0;font-size:11px;color:{C['text_muted']};line-height:1.5;">
    This report is generated automatically by Market Mood and is for informational purposes only.
    Nothing in this report constitutes financial advice or investment recommendations.
    Always conduct your own research before making investment decisions.
  </p>
  <p style="margin:8px 0 0;font-size:10px;color:{C['text_footer']};">Market Mood &bull; {ts}</p>
</td></tr>

</table></td></tr></table>
</body></html>""")

    html_body = "\n".join(hp)

    # ── Plain text ───────────────────────────────────────────────────────────
    tp: list[str] = [
        "Market Mood — Sentiment Report",
        f"{ts}  |  {run_type} run",
        "=" * 60,
        "",
        "MARKET MOOD SUMMARY",
        "-" * 30,
    ]
    for cat, data in mood_scores.items():
        score = data.get("score", 0) if isinstance(data, dict) else 0
        label = data.get("label", "Neutral") if isinstance(data, dict) else "Neutral"
        sign = "+" if score > 0 else ""
        tp.append(f"{cat:<26} {_score_bar(score)} {sign}{score:>4} ({label})")

    if trending_topics:
        tp += ["", "TRENDING TOPICS", "-" * 30]
        for topic in trending_topics[:6]:
            cat   = topic.get("category", "")
            trend = topic.get("trend", "")
            icon_dir = "^" if trend == "rising" else "v" if trend == "falling" else "-"
            tp.append(f"\n{icon_dir} {cat}")
            cat_posts = (merged_posts or {}).get(cat, [])
            for st in topic.get("sub_topics", [])[:4]:
                url  = _find_best_url(st, cat_posts) if cat_posts else ""
                line = f"  * {st}"
                if url:
                    line += f"\n    {url}"
                tp.append(line)

    if investment_signals:
        tp += ["", "INVESTMENT SIGNALS", "-" * 30]
        for sig in investment_signals:
            cat        = sig.get("category", "")
            signal_txt = sig.get("signal", "").upper()
            insight    = sig.get("insight", "")
            tickers    = sig.get("tickers", [])
            confidence = sig.get("confidence", "")
            tp.append(f"\n{cat} -- {signal_txt} ({confidence} confidence)")
            ticker_links = "  ".join(
                f"{t} <https://finance.yahoo.com/quote/{t}>" for t in tickers
            )
            tp.append(f"Tickers: {ticker_links}")
            tp.append(insight)

    if prediction_markets:
        tp += ["", "PREDICTION MARKET HIGHLIGHTS", "-" * 30]
        for m in prediction_markets[:5]:
            src = m.get("source", "")
            q   = m.get("question", "")
            yes = m.get("yes_pct", 0)
            vol = m.get("volume_usd", 0)
            tp.append(f"[{src}] {q}")
            tp.append(f"  YES {yes:.0f}% | {_vol_str(vol)} in bets")

    tp += [
        "",
        "=" * 60,
        "DISCLAIMER: Informational purposes only. Not financial advice.",
        f"Market Mood | {ts}",
    ]

    return html_body, "\n".join(tp)


def _smtp_send(sender: str, password: str, recipients: list[str], msg: MIMEMultipart) -> None:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, recipients, msg.as_string())
    print(f"[email_sender] Report sent to {len(recipients)} recipient(s)")


async def send_report_email(
    mood_scores: dict,
    trending_topics: list,
    investment_signals: list,
    prediction_markets: list,
    captured_at: datetime,
    run_type: str = "Scheduled",
    config: dict | None = None,
    merged_posts: dict | None = None,
    theme: str | None = None,
) -> bool:
    """Send Market Mood report email. Returns True on success, False if disabled/unconfigured."""
    cfg = config or load_email_config()
    if not cfg.get("enabled"):
        return False
    recipients = [r.strip() for r in cfg.get("recipients", []) if r.strip()]
    if not recipients:
        return False
    sender   = cfg.get("smtp_sender", "").strip()
    password = cfg.get("smtp_password", "")
    if not sender or not password:
        return False

    # Theme: explicit param wins; fall back to stored preference; then default dark
    resolved_theme = theme or cfg.get("email_theme", "dark")

    ts_label = captured_at.strftime("%a %b %d, %Y")
    subject  = f"Market Mood Report — {ts_label} ({run_type})"

    html_body, text_body = build_html_report(
        mood_scores=mood_scores,
        trending_topics=trending_topics,
        investment_signals=investment_signals,
        prediction_markets=prediction_markets,
        captured_at=captured_at,
        run_type=run_type,
        merged_posts=merged_posts,
        theme=resolved_theme,
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = sender
    msg["To"]      = ", ".join(recipients)
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _smtp_send, sender, password, recipients, msg)
    return True
