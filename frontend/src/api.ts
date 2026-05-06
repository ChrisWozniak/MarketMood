import axios from 'axios'

const ADMIN_KEY = import.meta.env.VITE_ADMIN_KEY ?? ''

const api = axios.create({ baseURL: '/api' })

// Attach admin key to all mutating requests (POST/PUT/PATCH/DELETE)
api.interceptors.request.use(config => {
  if (ADMIN_KEY && config.method !== 'get') {
    config.headers['X-API-Key'] = ADMIN_KEY
  }
  return config
})

// ── Sentiment / Barometer ──────────────────────────────────────────────────
// Trigger full social analysis + Gemini scoring (slow — 30–90s)
export const analyzeSentiment = (customTickers?: string[], theme?: string) =>
  api.post('/sentiment/analyze', {
    ...(customTickers?.length ? { custom_tickers: customTickers } : {}),
    ...(theme ? { theme } : {}),
  }).then(r => r.data)
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

// ── Settings — Schedule ────────────────────────────────────────────────────
export const updateSchedule = (minutes: number) =>
  api.post('/settings/schedule', { minutes }).then(r => r.data)

// ── Settings — Email Distribution ──────────────────────────────────────────
export interface EmailConfigPayload {
  enabled: boolean
  smtp_sender: string
  smtp_password: string
  recipients: string[]
  email_theme?: string
}
export const getEmailConfig = () => api.get('/settings/email').then(r => r.data)
export const saveEmailConfig = (config: EmailConfigPayload) =>
  api.post('/settings/email', config).then(r => r.data)
export const sendTestEmail = () => api.post('/settings/email/test').then(r => r.data)

// ── Health ─────────────────────────────────────────────────────────────────
export const getHealth = () => api.get('/health').then(r => r.data)
