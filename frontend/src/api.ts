import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export const getSettings = () => api.get('/settings').then(r => r.data)
export const saveSettings = (data: Record<string, unknown>) => api.put('/settings', data).then(r => r.data)
export const testEmail = () => api.post('/settings/test-email').then(r => r.data)
export const searchTickers = (q: string) => api.get(`/settings/ticker-search?q=${encodeURIComponent(q)}`).then(r => r.data)
export const getNextRun = () => api.get('/digest/next-run').then(r => r.data)

export const runNow = () => api.post('/digest/run-now').then(r => r.data)
export const getHistory = (limit = 20) => api.get(`/digest/history?limit=${limit}`).then(r => r.data)
export const getDigestRun = (id: number) => api.get(`/digest/history/${id}`).then(r => r.data)

export const analyzeSocial = () => api.post('/social/analyze').then(r => r.data)
export const getLatestSocial = () => api.get('/social/latest').then(r => r.data)
export const getMood = () => api.get('/social/mood').then(r => r.data)
export const getMarkets = () => api.get('/social/markets').then(r => r.data)
export const refreshMarkets = () => api.post('/social/markets/refresh').then(r => r.data)
export const getSocialHistory = () => api.get('/social/history').then(r => r.data)
