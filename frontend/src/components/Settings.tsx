import { useState } from 'react'
import { getHealth } from '../api'
import Card from './Card'
import Spinner from './Spinner'

const DATA_SOURCES = [
  { name: 'Reddit',            icon: '🟠', desc: 'Subreddits per category — public JSON API',        status: 'active' },
  { name: 'Hacker News',       icon: '🟡', desc: 'Algolia search API — tech & startup discussion',   status: 'active' },
  { name: 'YouTube',           icon: '🔴', desc: 'Video search via YouTube Data API v3',             status: 'active' },
  { name: 'Kalshi',            icon: '🔵', desc: 'Prediction market contracts & probabilities',      status: 'active' },
  { name: 'Polymarket',        icon: '🟣', desc: 'Decentralised prediction market odds',             status: 'active' },
]

const CATEGORIES = [
  { name: 'Economy',            desc: 'Inflation, interest rates, housing, tariffs, unemployment' },
  { name: 'Politics',           desc: 'Elections, policy, regulation, geopolitical events' },
  { name: 'Prediction Markets', desc: 'Kalshi & Polymarket — probability shifts, crowd wisdom' },
  { name: 'Daily Hot Topics',   desc: 'Reddit & HN catch-all for trending discussions' },
  { name: 'Sector Sentiment',   desc: 'Energy, tech, healthcare, real estate → stocks/ETFs' },
  { name: 'Technology & AI',    desc: 'Model releases, developer sentiment, enterprise adoption' },
  { name: 'Blockchain & Crypto',desc: 'Ethereum, Solana, Bitcoin, DeFi, NFT, Web3 vs TradFi' },
]

type HealthStatus = 'idle' | 'checking' | 'ok' | 'error'

export default function Settings() {
  const [healthStatus, setHealthStatus] = useState<HealthStatus>('idle')

  const checkHealth = async () => {
    setHealthStatus('checking')
    try {
      await getHealth()
      setHealthStatus('ok')
    } catch {
      setHealthStatus('error')
    }
  }

  return (
    <div className="space-y-6">

      {/* ── Data Sources ── */}
      <Card accent="#6366f1">
        <h3 className="text-slate-200 font-semibold mb-1">Data Sources</h3>
        <p className="text-slate-500 text-xs mb-4">Platforms monitored during each analysis run</p>
        <div className="space-y-2">
          {DATA_SOURCES.map(src => (
            <div key={src.name} className="flex items-center gap-3 py-2 border-b border-slate-800 last:border-0">
              <span className="text-lg">{src.icon}</span>
              <div className="flex-1 min-w-0">
                <p className="text-slate-200 text-sm font-medium">{src.name}</p>
                <p className="text-slate-500 text-xs">{src.desc}</p>
              </div>
              <span className="text-xs text-emerald-400 font-medium shrink-0">● Active</span>
            </div>
          ))}
        </div>
      </Card>

      {/* ── Categories ── */}
      <Card accent="#f59e0b">
        <h3 className="text-slate-200 font-semibold mb-1">Monitored Categories</h3>
        <p className="text-slate-500 text-xs mb-4">Each category is scored independently by Claude Haiku</p>
        <div className="space-y-2">
          {CATEGORIES.map(cat => (
            <div key={cat.name} className="flex items-start gap-3 py-2 border-b border-slate-800 last:border-0">
              <span className="text-slate-600 text-xs font-bold mt-0.5">▸</span>
              <div>
                <p className="text-slate-200 text-sm font-medium">{cat.name}</p>
                <p className="text-slate-500 text-xs">{cat.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* ── Schedule & Backend ── */}
      <Card>
        <h3 className="text-slate-200 font-semibold mb-1">Analysis Schedule</h3>
        <p className="text-slate-500 text-xs mb-4">The backend runs a full analysis automatically every hour via APScheduler. Use the ⚡ Refresh Now button at the top to trigger an immediate run.</p>
        <div className="flex items-center justify-between py-3 border-b border-slate-800">
          <div>
            <p className="text-slate-300 text-sm">Automatic refresh</p>
            <p className="text-slate-500 text-xs">Every 60 minutes</p>
          </div>
          <span className="text-xs text-emerald-400 font-medium">● Running</span>
        </div>
        <div className="flex items-center justify-between py-3">
          <div>
            <p className="text-slate-300 text-sm">Backend health</p>
            <p className="text-slate-500 text-xs">FastAPI + SQLite</p>
          </div>
          <button
            onClick={checkHealth}
            disabled={healthStatus === 'checking'}
            className="flex items-center gap-1.5 text-xs bg-slate-700 hover:bg-slate-600 disabled:opacity-50 text-slate-300 px-3 py-1.5 rounded-lg transition-colors"
          >
            {healthStatus === 'checking' && <Spinner size={10} />}
            {healthStatus === 'idle'     && 'Ping'}
            {healthStatus === 'checking' && 'Checking…'}
            {healthStatus === 'ok'       && <span className="text-emerald-400">● OK</span>}
            {healthStatus === 'error'    && <span className="text-red-400">● Unreachable</span>}
          </button>
        </div>
      </Card>

      {/* ── Disclaimer ── */}
      <Card>
        <h3 className="text-slate-200 font-semibold mb-2">Disclaimer</h3>
        <p className="text-slate-500 text-xs leading-relaxed">
          MoodMarket provides social sentiment analysis and AI-generated market observations for
          informational purposes only. Nothing on this platform constitutes financial advice,
          investment recommendations, or an offer to buy or sell any security. Always conduct
          your own research and consult a qualified financial advisor before making investment
          decisions. Sentiment signals are derived from public social media and may not reflect
          actual market conditions.
        </p>
        <p className="text-slate-600 text-xs mt-3">
          Aggregate data only — no individual user profiles stored.
        </p>
      </Card>

    </div>
  )
}
