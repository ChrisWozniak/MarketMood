# Market Mood — Project Context for Claude Code

## What This Project Is
Market Mood (root folder: `Market Mood`) is a Social Sentiment Barometer with Investment Signals.
It collects real-time social data across multiple platforms, uses Gemini AI to analyze sentiment by
topic category, and displays a live barometer showing whether public mood is positive, negative, or
neutral — then connects that mood signal to investment implications and technology momentum trends.

Started April 2026. Based on code copied from News Digest (`C:\Users\k8woz\OneDrive\Documents\Home PC news digest\`).
News Digest remains intact and runs independently.

---

## Current State (as of May 2026, Session 7)

### Backend — COMPLETE
All backend files adapted for Market Mood. All AI services migrated from Anthropic Claude to Google
Gemini (free tier). Real estate data sources (FRED + Redfin) added. Prediction markets fixed and
wired into investment signal prompts. Custom watchlist tickers accepted via POST body and injected
into Gemini investment signal prompt. Email distribution added (Session 6). Dark/light theme
wired end-to-end through the full request stack (Session 7).

### Frontend — COMPLETE
Full accessibility pass (WCAG 2.1 AA). Custom Watchlist feature added in Settings (max 5 tickers).
Light mode (Warm Paper theme) implemented. Hover blow-out effects on Investment Signals and Tech
Momentum panels. All ticker badges throughout app are clickable links to Yahoo Finance.
Custom Watchlist tickers shown as amber pills in the Social Mood barometer row.
Email distribution UI added in Settings (Session 6). Scheduled report theme toggle added (Session 7).

### Tests — ADDED (Sessions 5 & 6)
- `backend/tests/test_sentiment.py` — 7 unit tests for sentiment fallback logic. No API key needed.
- `backend/tests/test_signal_coherency.py` — 12 regression tests for investment signal coherency (schema, direction, deduplication, edge cases). Uses `_fallback_signals()` only — no API key needed.

Run with: `pytest tests/ -v` from the backend directory.

---

## Database Decision: SQLite now, MongoDB later

**Current:** SQLite (kept for simplicity during development — fast, local, no setup needed)

**Original plan was MongoDB Atlas** — still the right long-term choice. Switch when raw posts
collection is added (Reddit/HN/StockTwits raw data). At that point free tier fills in ~3 weeks.

### MongoDB Atlas tier guide (when ready to switch)
| Phase | Tier | Cost | Storage |
|-------|------|------|---------|
| Snapshots only (current) | Free M0 | $0 | 512 MB — lasts ~4 years |
| Raw posts added | M2 | $9/mo | 2 GB |
| At scale | M10 | $57/mo | 10 GB |

### To switch to MongoDB, provide:
1. Create free account at cloud.mongodb.com
2. Create M0 cluster → Connect → Drivers → copy connection string:
   `mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/`
3. Add to `backend/.env` as `MONGODB_URI=...`
4. Replace `database.py` and `models.py` with Motor (async MongoDB driver)

---

## Core Categories
- Economy (inflation, interest rates, housing, tariffs, unemployment)
- Politics (elections, policy, regulation, geopolitical events, sanctions)
- Prediction Markets (Kalshi, Polymarket — probability shifts, crowd wisdom)
- Daily Hot Topics (Reddit, HN — catch-all for trending discussions)
- Sector Sentiment (energy, tech, healthcare — stocks/ETFs; real estate moved to own category)
- Technology & AI (model releases, developer sentiment, enterprise adoption, AI regulation)
- Blockchain & Crypto (Ethereum, Solana, Bitcoin, DeFi, NFT, Web3 vs TradFi)
- Real Estate (Reddit subreddits + HN keywords + FRED indicators + Redfin housing data)
- Health & Science (FDA, vaccines, climate events, NASA, public health)

---

## Backend Architecture (COMPLETE)

### Files — complete, no further changes needed
- `backend/main.py` — FastAPI app, **4 routers** (sentiment, signals, social, settings); `sys.stdout.reconfigure(encoding='utf-8')` for Windows Unicode safety
- `backend/models.py` — 2 tables: `SocialSnapshot`, `MarketSnapshot`
- `backend/services/scheduler.py` — APScheduler job; calls `run_social_analysis(run_type="Scheduled")`
- `backend/services/social/reddit_client.py` — subreddits per category; Real Estate: `["realestate", "FirstTimeHomeBuyer", "REBubble", "Renters", "Landlord", "airbnb", "RealEstateInvesting"]`
- `backend/services/social/hackernews_client.py` — category keywords; Real Estate keywords added
- `backend/services/social/youtube_client.py` — YouTube Data API v3 search
- `backend/services/social/trend_analyzer.py` — trend history + momentum scoring
- `backend/services/social/fred_client.py` — fetches FRED indicators (MORTGAGE30US, MSPUS, MSACSR, HOUST, USSTHPI, RRVRUSQ156N); converts to synthetic posts for mood_scorer; skips gracefully if FRED_API_KEY not set
- `backend/services/social/redfin_client.py` — downloads Redfin national housing tracker TSV.GZ from public S3; columns are UPPERCASE (MEDIAN_SALE_PRICE, HOMES_SOLD, etc.); uses MOM columns for trend; converts to synthetic posts
- `backend/routers/sentiment.py` — `/api/sentiment/analyze` accepts `AnalyzeRequest` body: `custom_tickers: list[str] | None`, `theme: str = "dark"` (UI dark/light mode forwarded to email); `/api/sentiment/latest`; `/api/sentiment/history`
- `backend/routers/signals.py` — `/api/signals/latest`, `/api/signals/generate`; fetches latest MarketSnapshot and passes prediction_markets + housing_data to signal generator
- `backend/routers/social.py` — `/api/social/markets`, `/api/social/markets/refresh`

### Key backend files — added in Sessions 6 & 7

**`backend/services/email_sender.py`** — HTML email report sent on every run (scheduled + manual + test):
- `load_email_config()` / `save_email_config()` — reads/writes `backend/email_config.json` (not committed)
- `_THEMES` dict: `"dark"` and `"light"` palettes (~15 color keys each); `_RUN_BADGE` dict: per-theme badge styles for Scheduled / Manual / Test run types
- `_icon_html()` — email-safe icon: HTML table cell with purple gradient (`#863bff → #6d28d9`) + ⚡ emoji (SVG/data URI blocked by Gmail; this approach works everywhere)
- `build_html_report(..., theme, merged_posts)` — full HTML + plain-text email; Jaccard fuzzy-match (`_find_best_url`) maps AI-generated subtopic headlines to source post URLs for clickable links
- `send_report_email(..., theme, config)` — theme resolution: explicit param (manual run UI mode) → `cfg["email_theme"]` (scheduled default) → `"dark"`; SMTP send runs in executor (non-blocking async)
- Gmail SMTP via `smtplib.SMTP_SSL` port 465; requires Gmail App Password (not regular password)

**`backend/routers/settings.py`** — email distribution settings endpoints:
- `GET /api/settings/email` — returns config (password masked as `•` × 8, adds `smtp_password_set` bool)
- `POST /api/settings/email` — saves config (`EmailConfig` model with `enabled`, `smtp_sender`, `smtp_password`, `recipients`, `email_theme`); preserves existing password if placeholder `•••••••• ` sent
- `POST /api/settings/email/test` — sends test email using saved config; raises 400 if disabled/no recipients/missing credentials

**`backend/services/social/aggregator.py`** — updated:
- `run_social_analysis(custom_tickers, run_type, theme)` — `theme` param forwarded to `send_report_email()`
- Email send is non-blocking (wrapped in try/except); snapshot is always saved even if email fails

### Key backend files — updated in Session 5

**`backend/services/social/markets_client.py`** — Major overhaul:
- `KALSHI_SERIES` now includes `KXBTC` and `KXETH` (longer-horizon crypto markets pass 2–98% filter)
- `EXCLUDE_KEYWORDS` expanded with more sports patterns (Bundesliga, "win the", "total points", hat trick, etc.) and entertainment filters
- `CATEGORY_KEYWORDS` expanded: added `Health & Science` and `Sector Sentiment` entries; Economy, Politics, Tech, Crypto all have more keywords
- `_infer_category()` returns `None` (not `"General"`) for unmatched markets — unmatched markets are dropped entirely
- Per-series deduplication: each Kalshi series contributes exactly **1 market** — the one closest to 50% YES (most uncertain/informative), breaking ties by volume
- Polymarket: fetches 100 markets ordered by total `volume` (not `volume24hr` which is often 0); volume fallback chain: `volume → volumeNum → liquidity → volume24hr`
- Minimum volume threshold: **$1,000** for both sources (filters empty markets, keeps real liquidity)
- Total markets shown: **12** (6 Kalshi + 6 Polymarket, interleaved)

**`backend/services/social/mood_scorer.py`** — Subtopic quality improvements:
- `MAX_SUBTOPICS` increased from 3 to **4**
- `_TOPIC_RULES` changed from "3–5 words" to **newspaper headline style** (5–8 words with a verb) — e.g. "Fed holds rates steady at 4.25%" not "rate decision"
- All three subtopic prompts (general, Daily Hot Topics, Sector Sentiment) updated with headline-style examples
- `_extract_subtopics_fallback` rewritten: now returns full post titles from highest-engagement posts instead of word-frequency bigrams
- `_is_valid_topic` minimum word count raised from 3 to 4

### Files — removed (News Digest only, no longer present)
- `backend/services/news_fetcher.py`
- `backend/services/summarizer.py`
- `backend/routers/digest.py`
- `backend/routers/config.py`

### API Endpoints
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/sentiment/analyze` | Trigger full social analysis; body: `{"custom_tickers": [...], "theme": "dark"}` |
| GET | `/api/sentiment/latest` | All barometer scores + trending topics |
| GET | `/api/sentiment/history` | Recent snapshots for momentum tracking |
| GET | `/api/signals/latest` | Gemini investment signals + tech momentum |
| POST | `/api/signals/generate` | Re-run Gemini analysis on latest snapshot |
| GET | `/api/social/markets` | Kalshi + Polymarket prediction markets |
| POST | `/api/social/markets/refresh` | Refresh market data only |
| GET | `/api/settings/email` | Get email distribution config (password masked) |
| POST | `/api/settings/email` | Save email distribution config |
| POST | `/api/settings/email/test` | Send test email using saved config |
| GET | `/api/health` | Health check |

---

## Frontend Architecture (COMPLETE)

### Files updated in Session 5
- `frontend/src/store.ts` — dark mode preference persisted to `localStorage` (`mm_dark_mode`); correct theme applied on page load without flash
- `frontend/src/index.css` — full light mode (Warm Paper palette: page `#f4ead8`, cards `#fdf7ee`); explicit overrides for Tailwind opacity variants (`bg-slate-800/50` etc.); `prefers-reduced-motion` block; amber focus indicators in light mode
- `frontend/src/App.tsx` — Toaster style responds to `darkMode` state (warm cream in light mode)
- `frontend/src/components/social/CategoryBarometer.tsx` — `watchlistTickers?: string[]` prop; amber ticker pills with Yahoo Finance links; emotion pills scale 125% on hover
- `frontend/src/components/social/InvestmentSignal.tsx` — `group` hover: insight text grows xs→sm; ticker pills are Yahoo Finance links
- `frontend/src/components/social/TechMomentum.tsx` — `group` hover: name grows sm→base, insight grows xs→sm; tickers link to Yahoo Finance
- `frontend/src/components/social/CategoryDetail.tsx` — ticker pills link to Yahoo Finance; insight text grows on hover
- `frontend/src/components/social/MarketPulse.tsx` — betting volume as dedicated row (💰 + colored amount); `CATEGORY_COLORS` matches actual backend category names

### Files updated in Sessions 6 & 7
- `frontend/src/api.ts` — email config functions added (`getEmailConfig`, `saveEmailConfig`, `sendTestEmail`); `EmailConfigPayload` interface exported (includes `email_theme?: string`); `analyzeSentiment(customTickers?, theme?)` forwards UI dark/light mode to backend
- `frontend/src/components/Settings.tsx` — panel renamed "Analysis Schedule & Distribution"; Custom Watchlist limit 10→**5**; email distribution section: enable toggle, Gmail sender, App Password input, recipient list with add/remove/Enter, **scheduled report theme toggle** (🌙 Dark / ☀️ Light), Save Settings + Test Email buttons; loads config on mount; `handleTestEmail` always saves before testing
- `frontend/src/components/social/SocialDashboard.tsx` — `watchlistTickers` state reads from localStorage; `darkMode` destructured from `useStore()`; `analyzeSentiment(tickers, darkMode ? 'dark' : 'light')` forwards current UI theme to backend so manual-run emails match the app's visual mode

### Keep as-is
- `frontend/src/components/social/TrendingTopics.tsx` — topic list with engagement bars
- `frontend/src/components/Card.tsx` — universal card wrapper
- `frontend/src/components/Spinner.tsx` — supports `label` and `hidden` props for accessibility
- `frontend/src/components/InfoTooltip.tsx` — keyboard accessible (onFocus/onBlur/Escape), role="tooltip"
- `frontend/src/tickerList.ts` — 128 tickers with `searchLocal(query)` helper; used by Custom Watchlist

### Deleted (orphaned)
- `frontend/src/components/Dashboard.tsx` — removed (News Digest leftover)
- `frontend/src/components/social/MoodGauge.tsx` — removed (replaced by CategoryBarometer)

---

## Tech Stack

| Component | Value |
|-----------|-------|
| Backend | FastAPI + SQLite (SQLModel) |
| AI — sentiment scoring | Gemini Flash Lite (`models/gemini-2.0-flash-lite`) |
| AI — investment signals | Gemini Flash (`models/gemini-2.5-flash`) |
| AI — tech momentum | Gemini Flash (`models/gemini-2.5-flash`) |
| AI SDK | `google-genai >= 1.0.0` (NOT the deprecated `google-generativeai`) |
| Social data | Reddit (public JSON), HackerNews (Algolia), YouTube (Data API v3) |
| Real estate data | FRED API (free key), Redfin public S3 TSV.GZ (no key needed) |
| Market data | Kalshi API (no auth), Polymarket gamma-api (no auth) |
| Scheduler | APScheduler — hourly social analysis |
| Frontend | React 19 + Zustand + Recharts + Tailwind CSS v4 |
| Build | Vite + TypeScript |
| Testing | pytest (backend unit tests only; no API key needed) |

Note: Anthropic Claude was the original AI provider but switched to Google Gemini (free tier) after
credits ran out. MongoDB Atlas was originally planned but SQLite kept for simplicity — migrate later
if data volume requires it.

---

## Environment Variables (create `backend/.env`)
```
GEMINI_API_KEY=            # aistudio.google.com -> Get API key
YOUTUBE_API_KEY=           # console.cloud.google.com -> YouTube Data API v3
FRED_API_KEY=              # fred.stlouisfed.org -> My Account -> API Keys (free)
FRONTEND_URL=http://localhost:8001
DATABASE_URL=sqlite:///./moodmarket.db
```

**Note:** `ANTHROPIC_API_KEY` is no longer needed — all AI calls use Gemini.

## Email Distribution Config (`backend/email_config.json`)
Created automatically when settings are saved via UI. Not committed to git. Schema:
```json
{
  "enabled": true,
  "smtp_sender": "yourname@gmail.com",
  "smtp_password": "xxxx xxxx xxxx xxxx",
  "recipients": ["you@example.com"],
  "email_theme": "dark"
}
```
- `smtp_password` must be a **Gmail App Password** (Google Account → Security → 2-Step Verification → App passwords). Regular Gmail password will fail with SMTP 534 error.
- `email_theme` sets the theme for **scheduled** runs. Manual runs always use the current UI dark/light mode (forwarded via `theme` field in POST body).
- Email icon uses HTML table-cell with ⚡ emoji + purple gradient — SVG data URIs are blocked by Gmail.

---

## How to Run (development)

### One-click (recommended)
Double-click `start.bat` in the project root. On each run it:
1. Kills any previously opened "Market Mood Backend" and "Market Mood Frontend" terminal windows using `/T` (kills the window AND all child processes — uvicorn, node, vite)
2. Kills any process still holding ports 8001 or 5173 as a fallback
3. Starts both servers in fresh named terminal windows
4. Opens http://localhost:5173 in the browser automatically

**Important implementation detail:** `venv\Scripts\activate.bat` changes the terminal title, which would break the title-based kill on the next run. The batch file resets the title with an explicit `title Market Mood Backend/Frontend` command immediately after activation so the next run can always find and close the windows reliably.

### Manual
Backend (terminal 1):
```powershell
cd backend
.\venv\Scripts\Activate.ps1    # first time: python -m venv venv
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

Frontend (terminal 2):
```powershell
cd frontend
npm install
npm run dev
```

Frontend dev server proxies `/api` to `http://localhost:8001` (configured in `vite.config.ts`).

### Run tests
```powershell
cd backend
.\venv\Scripts\Activate.ps1
pytest tests/ -v
```

### Windows-specific notes
- Backend runs on port **8001** (8000 was used by a stale process and moved)
- `sys.stdout.reconfigure(encoding='utf-8', errors='replace')` added to `main.py` to prevent Unicode charmap crashes on Windows
- All Python print statements use ASCII-safe characters (no `→`, `–` etc.)

---

## Investment Signal Logic (4-layer synthesis)
Investment signals are generated by Gemini using four layers of data simultaneously:
1. **Social mood scores** — per-category sentiment from Reddit, HN, YouTube (-100 to +100)
2. **Prediction market probabilities** — Kalshi and Polymarket YES%/NO%/Volume; high-volume markets anchor signal direction
3. **Housing indicators** — FRED macro data (mortgage rates, home prices, housing starts) + Redfin current market stats (median sale price, inventory, days on market)
4. **Custom Watchlist** — user-selected tickers (up to **5**) from Settings; when present, Gemini appends a "Custom Watchlist" signal card synthesizing current mood vs. those specific stocks/ETFs/crypto

This multi-layer approach means signals reflect crowd wisdom + hard economic data + the user's personal holdings, not just social chatter.

### Custom Watchlist flow
- User adds up to **5** tickers in Settings → "Custom Watchlist" panel (autocomplete from `tickerList.ts`, persisted in `localStorage` key `mm_watchlist_tickers`)
- On "Run Now", `SocialDashboard` reads tickers from localStorage state and sends `{"custom_tickers": [...]}` in the POST body
- `routers/sentiment.py` deserializes via `AnalyzeRequest` Pydantic model and passes through aggregator → `score_watchlist_mood()` + `generate_investment_signals()`
- `mood_scorer.score_watchlist_mood(tickers, merged)` flattens all category posts, picks top 25 by engagement, and asks Gemini Flash Lite to score sentiment specifically for those assets → result inserted into `mood_scores` under key `"Custom Watchlist"` → appears as a `CategoryBarometer` row showing amber ticker pills
- `investment_signals.py` appends a `CUSTOM WATCHLIST REQUEST` section to the Gemini prompt; Gemini returns an extra `{"category": "Custom Watchlist", ...}` object
- `InvestmentSignal` component renders both the mood bar and the signal card identically to other categories

### Prediction Markets logic
- Kalshi series: KXFED, KXGDP, KXINFLATION, KXUNEMPLOYMENT, KXTRUMP, KXECON, KXWARMING, KXAI, KXBTC, KXETH
- Each series contributes **1 market** — the threshold closest to 50% YES (most uncertain = most informative)
- Markets below **$1,000** in active bets are excluded (both sources)
- Sports, entertainment, and celebrity markets are excluded by keyword filter
- Markets that don't match any app category are dropped — no "General" catch-all
- Polymarket: fetches top 100 by total lifetime volume (not 24h volume which is often 0)

---

## What Makes Market Mood Unique
Every competitor tracks either brand sentiment OR market signals OR technology trends separately.
Market Mood connects everyday social conversation across all categories through a single Gemini AI
reasoning layer that links mood → investment signals AND technology momentum in one dashboard.

The Technology & AI category has a unique momentum layer: not just current sentiment but directional
confidence — is enthusiasm growing or fading after each model release, which companies are winning
the narrative, which blockchain platforms are gaining developer mindshare.

Ethical guardrails: aggregate scores only, no individual user profiles stored, all insights include
disclaimer that they are informational not financial advice.
