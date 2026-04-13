# MoodMarket — Project Context for Claude Code

## What This Project Is
MoodMarket is a Social Sentiment Barometer with Investment Signals. It collects real-time social data
across multiple platforms, uses Claude AI to analyze sentiment by topic category, and displays a live
barometer showing whether public mood is positive, negative, or neutral — then connects that mood
signal to investment implications and technology momentum trends.

Started April 2026. Based on code copied from News Digest (`C:\Users\k8woz\OneDrive\Documents\Home PC news digest\`).
News Digest remains intact and runs independently.

---

## Current State (as of April 2026)

### Backend — COMPLETE
All backend files have been adapted for MoodMarket. The backend is ready to run.

### Frontend — NOT STARTED YET
Frontend still contains News Digest components. Next work session starts here.
New components to build: `CategoryBarometer`, `InvestmentSignal`, `TechMomentum`, `CategoryDetail`.
Files to replace: `App.tsx`, `store.ts`, `api.ts`, `Dashboard.tsx`, `Settings.tsx`, `SocialDashboard.tsx`.

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
4. Claude will replace `database.py` and `models.py` with Motor (async MongoDB driver)

---

## Core Categories
- Economy (inflation, interest rates, housing, tariffs, unemployment)
- Politics (elections, policy, regulation, geopolitical events, sanctions)
- Prediction Markets (Kalshi, Polymarket — probability shifts, crowd wisdom)
- Daily Hot Topics (Reddit, HN — catch-all for trending discussions)
- Sector Sentiment (energy, tech, healthcare, real estate → stocks/ETFs)
- Technology & AI (model releases, developer sentiment, enterprise adoption, AI regulation)
- Blockchain & Crypto (Ethereum, Solana, Bitcoin, DeFi, NFT, Web3 vs TradFi)

---

## Backend Architecture (DONE)

### Files — keep as-is (no further changes needed)
- `backend/services/social/reddit_client.py` — MoodMarket subreddits already set per category
- `backend/services/social/hackernews_client.py` — MoodMarket category keywords already set
- `backend/services/social/markets_client.py` — Kalshi + Polymarket, unchanged
- `backend/services/social/trend_analyzer.py` — trend history + momentum, unchanged
- `backend/services/social/aggregator.py` — orchestrates all sources, calls Claude signals
- `backend/services/social/youtube_client.py` — YouTube video search, unchanged

### Files — already adapted for MoodMarket
- `backend/main.py` — FastAPI app, 3 routers: sentiment, signals, social
- `backend/models.py` — Only 2 tables: `SocialSnapshot`, `MarketSnapshot` (DigestRun/Settings removed)
- `backend/services/scheduler.py` — Hourly social analysis auto-scheduler (APScheduler)
- `backend/services/social/mood_scorer.py` — Uses Claude Haiku for sentiment scoring (was Groq)
- `backend/services/investment_signals.py` — NEW: Claude Sonnet maps mood → sector/ticker signals
- `backend/services/tech_momentum.py` — NEW: Claude Sonnet tracks tech direction week-over-week
- `backend/routers/sentiment.py` — NEW: `/api/sentiment/analyze`, `/api/sentiment/latest`
- `backend/routers/signals.py` — NEW: `/api/signals/latest`, `/api/signals/generate`
- `backend/routers/social.py` — kept from News Digest for markets endpoints

### Files — removed (News Digest only)
- `backend/services/email_sender.py` — deleted
- `backend/services/news_fetcher.py` — deleted
- `backend/services/summarizer.py` — deleted
- `backend/routers/digest.py` — deleted
- `backend/routers/config.py` — deleted

### API Endpoints
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/sentiment/analyze` | Trigger full social analysis + Claude scoring |
| GET | `/api/sentiment/latest` | All barometer scores + trending topics |
| GET | `/api/sentiment/history` | Recent snapshots for momentum tracking |
| GET | `/api/signals/latest` | Claude investment signals + tech momentum |
| POST | `/api/signals/generate` | Re-run Claude analysis on latest snapshot |
| GET | `/api/social/markets` | Kalshi + Polymarket prediction markets |
| POST | `/api/social/markets/refresh` | Refresh market data only |
| GET | `/api/health` | Health check |

---

## Frontend Architecture (TODO — next session)

### Keep as-is (no changes needed)
- `frontend/src/components/social/MoodGauge.tsx` — radial gauge, IS the barometer widget
- `frontend/src/components/social/MarketPulse.tsx` — prediction markets panel
- `frontend/src/components/social/TrendingTopics.tsx` — topic list (add momentum column)
- `frontend/src/components/Card.tsx` — universal card wrapper
- `frontend/src/components/Spinner.tsx`
- `frontend/src/components/InfoTooltip.tsx`
- `frontend/src/tickerList.ts` — investment signal ticker mapping
- `frontend/src/index.css` — full Tailwind dark/light mode system

### Replace (still contain News Digest code)
- `frontend/src/App.tsx` — keep sticky header/dark mode/collapse pattern, update nav sections
- `frontend/src/store.ts` — keep Zustand pattern, replace state slices for MoodMarket
- `frontend/src/api.ts` — keep Axios pattern, point to new MoodMarket endpoints
- `frontend/src/components/Dashboard.tsx` — replace with CategoryBarometer view
- `frontend/src/components/Settings.tsx` — replace with lightweight source preferences panel
- `frontend/src/components/social/SocialDashboard.tsx` — replace with MoodMarket main dashboard

### New components to build
- `frontend/src/components/CategoryBarometer.tsx` — full-width barometer per category (main view)
- `frontend/src/components/InvestmentSignal.tsx` — Claude-generated insight cards per category
- `frontend/src/components/TechMomentum.tsx` — week-over-week momentum for technologies/companies
- `frontend/src/components/CategoryDetail.tsx` — drill-down per category with platform breakdown

---

## Tech Stack

| Component | Value |
|-----------|-------|
| Backend | FastAPI + SQLite (SQLModel) |
| AI — sentiment scoring | Claude Haiku (`claude-haiku-4-5-20251001`) |
| AI — investment signals | Claude Sonnet (`claude-sonnet-4-6`) |
| AI — tech momentum | Claude Sonnet (`claude-sonnet-4-6`) |
| Social data | Reddit (public JSON), HackerNews (Algolia), YouTube (Data API v3) |
| Market data | Kalshi API, Polymarket API |
| Scheduler | APScheduler — hourly social analysis |
| Frontend | React 19 + Zustand + Recharts + Tailwind CSS v4 |
| Build | Vite + TypeScript |

Note: MongoDB Atlas was originally planned but SQLite kept for simplicity —
can migrate later if data volume requires it.

---

## Environment Variables (create `backend/.env`)
```
ANTHROPIC_API_KEY=        # claude.ai -> Settings -> API Keys
YOUTUBE_API_KEY=          # console.cloud.google.com -> YouTube Data API v3
FRONTEND_URL=http://localhost:8000
DATABASE_URL=sqlite:///./moodmarket.db
```

---

## How to Run (development)
```powershell
cd backend
.\venv\Scripts\Activate.ps1    # or: python -m venv venv first
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
Frontend dev server (separate terminal):
```powershell
cd frontend
npm install
npm run dev
```

---

## What Makes MoodMarket Unique
Every competitor tracks either brand sentiment OR market signals OR technology trends separately.
MoodMarket connects everyday social conversation across all categories through a single Claude AI
reasoning layer that links mood → investment signals AND technology momentum in one dashboard.

The Technology & AI category has a unique momentum layer: not just current sentiment but directional
confidence — is enthusiasm growing or fading after each model release, which companies are winning
the narrative, which blockchain platforms are gaining developer mindshare.

Ethical guardrails: aggregate scores only, no individual user profiles stored, all insights include
disclaimer that they are informational not financial advice.
