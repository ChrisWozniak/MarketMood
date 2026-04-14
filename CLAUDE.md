# MoodMarket — Project Context for Claude Code

## What This Project Is
MoodMarket is a Social Sentiment Barometer with Investment Signals. It collects real-time social data
across multiple platforms, uses Gemini AI to analyze sentiment by topic category, and displays a live
barometer showing whether public mood is positive, negative, or neutral — then connects that mood
signal to investment implications and technology momentum trends.

Started April 2026. Based on code copied from News Digest (`C:\Users\k8woz\OneDrive\Documents\Home PC news digest\`).
News Digest remains intact and runs independently.

---

## Current State (as of April 2026, Session 3)

### Backend — COMPLETE
All backend files adapted for MoodMarket. All AI services migrated from Anthropic Claude to Google
Gemini (free tier). Real estate data sources (FRED + Redfin) added. Prediction markets fixed and
wired into investment signal prompts.

### Frontend — COMPLETE (core)
All 5 target files replaced (News Digest → MoodMarket). All "Claude" UI text updated to "Gemini".
`Dashboard.tsx` is still orphaned/unused — can delete or repurpose in a future session.

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

---

## Backend Architecture (COMPLETE)

### Files — complete, no further changes needed
- `backend/main.py` — FastAPI app, 3 routers; added `sys.stdout.reconfigure(encoding='utf-8')` for Windows Unicode safety
- `backend/models.py` — 2 tables: `SocialSnapshot`, `MarketSnapshot`
- `backend/services/scheduler.py` — hourly APScheduler job
- `backend/services/social/reddit_client.py` — subreddits per category; Real Estate category added: `["realestate", "FirstTimeHomeBuyer", "REBubble", "Renters", "Landlord", "airbnb", "RealEstateInvesting"]`
- `backend/services/social/hackernews_client.py` — category keywords; Real Estate keywords added
- `backend/services/social/youtube_client.py` — YouTube Data API v3 search
- `backend/services/social/trend_analyzer.py` — trend history + momentum scoring
- `backend/services/social/markets_client.py` — Kalshi + Polymarket; short-term price-range series removed (always near 0/100%); filter relaxed to 2–98%; Polymarket `liquidity` field added as volume fallback; all Unicode arrows replaced with ASCII `->` for Windows safety
- `backend/services/social/aggregator.py` — orchestrates all sources; injects FRED+Redfin posts into Real Estate; passes `housing_data` to `generate_investment_signals()`
- `backend/services/social/mood_scorer.py` — Gemini `models/gemini-2.0-flash-lite`; migrated from Anthropic; `_claude_call()` renamed to `_gemini_call()`
- `backend/services/investment_signals.py` — Gemini `models/gemini-2.5-flash`; takes `mood_scores` + `trending_topics` + `prediction_markets` + `housing_data`; prompt weights prediction market probabilities heavily
- `backend/services/tech_momentum.py` — Gemini `models/gemini-2.5-flash`; tracks tech direction week-over-week
- `backend/services/social/fred_client.py` — **NEW**: fetches FRED indicators (MORTGAGE30US, MSPUS, MSACSR, HOUST, USSTHPI, RRVRUSQ156N); converts to synthetic posts for mood_scorer; skips gracefully if FRED_API_KEY not set
- `backend/services/social/redfin_client.py` — **NEW**: downloads Redfin national housing tracker TSV.GZ from public S3; columns are UPPERCASE (MEDIAN_SALE_PRICE, HOMES_SOLD, etc.); uses MOM columns for trend; converts to synthetic posts
- `backend/routers/sentiment.py` — `/api/sentiment/analyze`, `/api/sentiment/latest`, `/api/sentiment/history`
- `backend/routers/signals.py` — `/api/signals/latest`, `/api/signals/generate`; fetches latest MarketSnapshot and passes prediction_markets + housing_data (from platform_data) to signal generator
- `backend/routers/social.py` — `/api/social/markets`, `/api/social/markets/refresh`

### Files — removed (News Digest only)
- `backend/services/email_sender.py`
- `backend/services/news_fetcher.py`
- `backend/services/summarizer.py`
- `backend/routers/digest.py`
- `backend/routers/config.py`

### API Endpoints
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/sentiment/analyze` | Trigger full social analysis + Gemini scoring |
| GET | `/api/sentiment/latest` | All barometer scores + trending topics |
| GET | `/api/sentiment/history` | Recent snapshots for momentum tracking |
| GET | `/api/signals/latest` | Gemini investment signals + tech momentum |
| POST | `/api/signals/generate` | Re-run Gemini analysis on latest snapshot |
| GET | `/api/social/markets` | Kalshi + Polymarket prediction markets |
| POST | `/api/social/markets/refresh` | Refresh market data only |
| GET | `/api/health` | Health check |

---

## Frontend Architecture (COMPLETE — core)

### Keep as-is (no changes needed)
- `frontend/src/components/social/MoodGauge.tsx` — radial gauge barometer widget
- `frontend/src/components/social/MarketPulse.tsx` — prediction markets panel
- `frontend/src/components/social/TrendingTopics.tsx` — topic list with engagement bars
- `frontend/src/components/Card.tsx` — universal card wrapper
- `frontend/src/components/Spinner.tsx`
- `frontend/src/components/InfoTooltip.tsx`
- `frontend/src/tickerList.ts` — investment signal ticker mapping
- `frontend/src/index.css` — full Tailwind dark/light mode system

### Orphaned / can delete
- `frontend/src/components/Dashboard.tsx` — unused leftover from News Digest; delete or repurpose

### Completed files
- `frontend/src/App.tsx` — MoodMarket header, single-page scroll, no Digest section
- `frontend/src/store.ts` — trimmed to darkMode + panelCollapse + loading
- `frontend/src/api.ts` — all MoodMarket endpoints; all comments updated to reference Gemini
- `frontend/src/components/Settings.tsx` — data sources, categories, schedule, health ping, disclaimer; "Gemini Flash" used throughout
- `frontend/src/components/social/SocialDashboard.tsx` — full MoodMarket dashboard: Social Mood gauges, Investment Signals, Tech Momentum, Trending Topics, MarketPulse; all UI text references Gemini not Claude

### Possible future components (not yet built)
- `frontend/src/components/CategoryBarometer.tsx` — full-width barometer per category
- `frontend/src/components/InvestmentSignal.tsx` — insight cards per category
- `frontend/src/components/TechMomentum.tsx` — week-over-week momentum for technologies
- `frontend/src/components/CategoryDetail.tsx` — drill-down per category with platform breakdown

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

---

## How to Run (development)

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

### Windows-specific notes
- Backend runs on port **8001** (8000 was used by a stale process and moved)
- `sys.stdout.reconfigure(encoding='utf-8', errors='replace')` added to `main.py` to prevent Unicode charmap crashes on Windows
- All Python print statements use ASCII-safe characters (no `→`, `–` etc.)

---

## Investment Signal Logic (3-layer synthesis)
Investment signals are generated by Gemini using three layers of data simultaneously:
1. **Social mood scores** — per-category sentiment from Reddit, HN, YouTube (-100 to +100)
2. **Prediction market probabilities** — Kalshi and Polymarket YES%/NO%/Volume; high-volume markets anchor signal direction
3. **Housing indicators** — FRED macro data (mortgage rates, home prices, housing starts) + Redfin current market stats (median sale price, inventory, days on market)

This multi-layer approach means signals reflect crowd wisdom + hard economic data, not just social chatter.

---

## What Makes MoodMarket Unique
Every competitor tracks either brand sentiment OR market signals OR technology trends separately.
MoodMarket connects everyday social conversation across all categories through a single Gemini AI
reasoning layer that links mood → investment signals AND technology momentum in one dashboard.

The Technology & AI category has a unique momentum layer: not just current sentiment but directional
confidence — is enthusiasm growing or fading after each model release, which companies are winning
the narrative, which blockchain platforms are gaining developer mindshare.

Ethical guardrails: aggregate scores only, no individual user profiles stored, all insights include
disclaimer that they are informational not financial advice.
