# MoodMarket — Project Context for Claude Code

## What This Project Is
MoodMarket is a Social Sentiment Barometer with Investment Signals. It collects real-time social data
across multiple platforms, uses Claude AI to analyze sentiment by topic category, and displays a live
barometer showing whether public mood is positive, negative, or neutral — then connects that mood
signal to investment implications and technology momentum trends.

This project was started in April 2026 and is based on code copied from the "Home PC news digest"
project located at: `C:\Users\k8woz\OneDrive\Documents\Home PC news digest\`

---

## Current State
- Codebase is a direct copy of the News Digest project — no MoodMarket-specific changes made yet
- News Digest is kept intact and still runs independently
- Development on MoodMarket starts from this copy as a base

---

## Core Categories to Track
- Economy (gas prices, inflation, unemployment, interest rates, housing, tariffs)
- Politics (elections, policy, regulation, geopolitical events, sanctions)
- Prediction Markets (Kalshi, Polymarket — probability shifts, crowd wisdom)
- Daily Hot Topics (Reddit, Telegram, Bluesky, HackerNews — updated hourly)
- Sector Sentiment (energy, tech, healthcare, consumer goods, real estate → mapped to stocks/ETFs)
- Technology & AI (model releases, developer sentiment, enterprise adoption, AI regulation)
- Blockchain & Crypto (Ethereum, Solana, Bitcoin, DeFi, NFT, Web3 vs TradFi)

---

## What to Reuse from News Digest (already copied here)

### Backend — keep mostly as-is, adapt:
- `backend/services/social/reddit_client.py` — change subreddit lists for MoodMarket categories
- `backend/services/social/hackernews_client.py` — change category keywords
- `backend/services/social/markets_client.py` — Kalshi + Polymarket, use as-is
- `backend/services/social/trend_analyzer.py` — trend history + momentum, use as-is
- `backend/services/social/mood_scorer.py` — keep logic, upgrade prompts for investment signals
- `backend/services/social/aggregator.py` — orchestration pattern, extend for new sources
- `backend/services/scheduler.py` — keep APScheduler, tune to hourly refresh

### Backend — remove or repurpose (News Digest specific, not needed for MoodMarket):
- `backend/services/email_sender.py` — no email delivery in MoodMarket
- `backend/services/news_fetcher.py` — no RSS/NewsAPI digest in MoodMarket
- `backend/services/summarizer.py` — no email digest needed
- `backend/routers/digest.py` — replace with sentiment/signals routers
- `backend/routers/config.py` — replace with MoodMarket settings

### Frontend — keep as-is:
- `frontend/src/components/social/MoodGauge.tsx` — radial gauge IS the barometer widget
- `frontend/src/components/social/MarketPulse.tsx` — prediction markets panel
- `frontend/src/components/social/TrendingTopics.tsx` — add momentum column
- `frontend/src/components/Card.tsx` — universal wrapper
- `frontend/src/components/Spinner.tsx`
- `frontend/src/components/InfoTooltip.tsx`
- `frontend/src/tickerList.ts` — needed for investment signal sector/ticker mapping
- `frontend/src/index.css` — full Tailwind dark/light mode system

### Frontend — replace/rebuild:
- `frontend/src/components/Dashboard.tsx` — replace with CategoryBarometer view
- `frontend/src/components/Settings.tsx` — replace with source preferences + category toggles
- `frontend/src/components/social/SocialDashboard.tsx` — replace with MoodMarket main dashboard
- `frontend/src/store.ts` — keep Zustand pattern, replace state slices
- `frontend/src/api.ts` — keep Axios pattern, replace endpoints

---

## New Things to Build

### New Data Sources (backend)
- `services/social/stocktwits_client.py` — cashtag sentiment (REST, no auth)
- `services/social/bluesky_client.py` — AT Protocol public API
- `services/social/telegram_client.py` — Telethon library, public crypto/AI channels
- `services/social/pytrends_client.py` — Google Trends search volume
- YouTube comments on major tech announcements (different from current video search in youtube_client.py)
- Truth Social high-profile public accounts (optional, lower priority)

### New Backend Services
- `services/investment_signals.py` — Claude maps topic sentiment → sector/ticker implications
- `services/tech_momentum.py` — Claude tracks week-over-week technology enthusiasm (directional)
- New routers: `routers/sentiment.py`, `routers/signals.py`

### New Frontend Components
- `components/CategoryBarometer.tsx` — full-width barometer per category (main view)
- `components/InvestmentSignal.tsx` — Claude-generated insight cards
- `components/TechMomentum.tsx` — week-over-week momentum chart for technologies/companies
- `components/CategoryDetail.tsx` — drill-down per category with platform breakdown

---

## Tech Stack Changes vs News Digest

| Component | News Digest (source) | MoodMarket (target) |
|-----------|---------------------|----------------------|
| Database | SQLite | MongoDB Atlas |
| AI model | Groq llama-3.3-70b | Claude claude-sonnet-4-6 |
| Data sources | Reddit, HN, YouTube, Kalshi, Polymarket | All above + StockTwits, Bluesky, Telegram, Google Trends |
| Email delivery | Yes (Gmail SMTP) | No |
| Investment signals | No | Yes (new) |
| Tech momentum tracking | No | Yes (new, directional week-over-week) |

---

## Key Design Decisions Made
- MongoDB Atlas (not SQLite) for posts + mood_snapshots collections — better for time-series sentiment data at scale
- Claude API (not Groq) for the investment signal and momentum layers — deeper reasoning needed
- Frontend served from FastAPI static files in production (same pattern as News Digest)
- No email feature — MoodMarket is a live dashboard only
- Ethical guardrails: aggregate scores only, no individual user profiles, disclaimer on all insights

---

## Environment Variables Needed (create backend/.env)
```
# AI
ANTHROPIC_API_KEY=        # claude.ai -> API Keys

# Data Sources
REDDIT_CLIENT_ID=         # reddit.com/prefs/apps -> create app
REDDIT_CLIENT_SECRET=
YOUTUBE_API_KEY=          # console.cloud.google.com -> YouTube Data API v3
NEWSAPI_KEY=              # newsapi.org (optional)

# MongoDB
MONGODB_URI=              # MongoDB Atlas connection string

# Optional
TELEGRAM_API_ID=          # my.telegram.org -> App configuration
TELEGRAM_API_HASH=
FRONTEND_URL=http://localhost:8000
```

---

## What Makes MoodMarket Unique
Every competitor tracks either brand sentiment OR market signals OR technology trends separately.
MoodMarket connects everyday social conversation across all categories through a single AI reasoning
layer that links mood → investment signals AND technology momentum in one dashboard.

The Technology & AI category has a unique "momentum layer": not just current sentiment but
directional confidence — is enthusiasm growing or fading week-over-week after each major model
release, which companies are winning the narrative, which blockchain platforms are gaining developer
mindshare.
