import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

// ── Sentiment / Barometer ──────────────────────────────────────────────────
// Trigger full social analysis + Gemini scoring (slow — 30–90s)
export const analyzeSentiment = () => api.post('/sentiment/analyze').then(r => r.data)
// Latest barometer scores + trending topics for all categories
export const getLatestSentiment = () => api.get('/sentiment/latest').then(r => r.data)
// Recent snapshots for momentum tracking (default last 24)
export const getSentimentHistory = (limit = 24) =>
  api.get(`/sentiment/history?limit=${limit}`).then(r => r.data)

// ── Investment Signals ─────────────────────────────────────────────────────
// Gemini-generated signals + tech momentum based on latest snapshot
export const getLatestSignals = () => api.get('/signals/latest').then(r => r.data)
// Re-run Gemini signal analysis on latest snapshot
export const generateSignals = () => api.post('/signals/generate').then(r => r.data)

// ── Prediction Markets ─────────────────────────────────────────────────────
// Kalshi + Polymarket live markets
export const getMarkets = () => api.get('/social/markets').then(r => r.data)
// Refresh market data only (fast)
export const refreshMarkets = () => api.post('/social/markets/refresh').then(r => r.data)

// ── Settings ───────────────────────────────────────────────────────────────
export const updateSchedule = (minutes: number) =>
  api.post('/settings/schedule', { minutes }).then(r => r.data)

// ── Health ─────────────────────────────────────────────────────────────────
export const getHealth = () => api.get('/health').then(r => r.data)
