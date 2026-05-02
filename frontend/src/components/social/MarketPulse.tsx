import { useState, useEffect } from 'react'
import toast from 'react-hot-toast'
import { getMarkets, refreshMarkets } from '../../api'
import Card from '../Card'
import Spinner from '../Spinner'
import InfoTooltip from '../InfoTooltip'

interface Market {
  source: string
  question: string
  yes_pct: number
  no_pct: number
  volume_usd: number
  category: string
}

const CATEGORY_COLORS: Record<string, string> = {
  'Economy':           '#22c55e',
  'Politics':          '#f59e0b',
  'Technology & AI':   '#6366f1',
  'Blockchain & Crypto': '#f97316',
  'World Affairs':     '#0ea5e9',
  'Real Estate':       '#10b981',
  'Health & Science':  '#ec4899',
  'Sector Sentiment':  '#a78bfa',
}

const SOURCE_COLORS: Record<string, string> = {
  'Kalshi':     '#8b5cf6',
  'Polymarket': '#0ea5e9',
}

function fmtVolume(v: number): string {
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1_000)     return `$${(v / 1_000).toFixed(0)}K`
  return `$${v.toFixed(0)}`
}

interface Props {
  collapsed?: boolean
  onToggleCollapse?: () => void
}

export default function MarketPulse({ collapsed = false, onToggleCollapse }: Props) {
  const [markets, setMarkets]       = useState<Market[]>([])
  const [capturedAt, setCapturedAt] = useState<string | null>(null)
  const [loading, setLoading]       = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const load = () => {
    setLoading(true)
    getMarkets()
      .then(d => {
        setMarkets(d.markets || [])
        setCapturedAt(d.captured_at || null)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      const d = await refreshMarkets()
      if (d.status === 'error') {
        toast.error(`Markets fetch failed: ${d.message}`)
      } else {
        setMarkets(d.markets || [])
        setCapturedAt(d.captured_at || null)
        toast.success(`Loaded ${(d.markets || []).length} markets`)
      }
    } catch (e) {
      toast.error('Could not reach market APIs.')
    } finally {
      setRefreshing(false)
    }
  }

  return (
    <Card accent="#8b5cf6">
      <div className="flex items-center justify-between mb-1 gap-2">
        <button
          type="button"
          className="flex-1 flex items-center justify-between cursor-pointer group text-left hover:opacity-80 transition-opacity"
          onClick={onToggleCollapse}
          aria-expanded={!collapsed}
          aria-controls="market-content"
        >
          <h3 className="text-slate-200 font-semibold md:group-hover:text-lg transition-all duration-200 flex items-center gap-1">
            📊 Prediction Market Pulse
            <span onClick={e => e.stopPropagation()}><InfoTooltip text="Live prediction market data from Kalshi and Polymarket — real money bets on real outcomes. Higher volume = stronger conviction." /></span>
          </h3>
          {onToggleCollapse && (
            <span
              aria-hidden="true"
              className="text-slate-400 p-1 shrink-0"
              style={{ display: 'inline-block', transform: collapsed ? 'rotate(0deg)' : 'rotate(180deg)', transition: 'transform 0.2s' }}
            >
              ▼
            </span>
          )}
        </button>
        {!collapsed && (
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            type="button"
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-colors shrink-0"
          >
            {refreshing ? <Spinner size={14} hidden /> : '⚡'}
            {refreshing ? 'Fetching…' : 'Refresh Now'}
          </button>
        )}
      </div>

      {!collapsed && (
        <div id="market-content">
          {capturedAt && (
            <p className="text-slate-300 text-xs mb-4">
              Top 5 Kalshi + top 5 Polymarket by trading volume — updated {new Date(capturedAt + 'Z').toLocaleString()}
            </p>
          )}
          {!capturedAt && !loading && (
            <p className="text-slate-300 text-xs mb-4">Real-money prediction markets from Kalshi and Polymarket</p>
          )}

          {loading ? (
            <div className="flex justify-center py-8"><Spinner size={28} label="Loading market data" /></div>
          ) : markets.length === 0 ? (
            <div className="text-center py-8 space-y-3" aria-live="polite">
              <p className="text-slate-400 text-sm">No market data yet.</p>
              <p className="text-slate-600 text-xs max-w-xs mx-auto">
                Click Refresh to fetch live data from Kalshi and Polymarket.
                If both APIs are unreachable, this section will remain empty.
              </p>
              <button
                onClick={handleRefresh}
                disabled={refreshing}
                type="button"
                className="flex items-center gap-2 mx-auto bg-violet-700 hover:bg-violet-600 disabled:opacity-50 text-white text-sm px-5 py-2.5 rounded-xl transition-colors"
              >
                {refreshing && <Spinner size={14} hidden />}
                {refreshing ? 'Fetching…' : '↻ Fetch Markets Now'}
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {markets.map((m, i) => {
                const color = CATEGORY_COLORS[m.category] || '#94a3b8'
                return (
                  <div key={i} className="bg-slate-700 border border-slate-600 rounded-xl p-4">
                    {/* Row 1: source + category badges */}
                    <div className="flex items-center gap-2 flex-wrap mb-2">
                      <span
                        className="text-xs font-semibold px-2 py-0.5 rounded-full"
                        style={{
                          background: (SOURCE_COLORS[m.source] || '#94a3b8') + '33',
                          color: SOURCE_COLORS[m.source] || '#94a3b8',
                        }}
                      >
                        {m.source}
                      </span>
                      <span
                        className="text-xs font-medium px-2 py-0.5 rounded-full"
                        style={{ background: color + '28', color }}
                      >
                        {m.category}
                      </span>
                    </div>

                    {/* Row 2: question */}
                    <p className="text-slate-200 text-sm leading-relaxed mb-3">{m.question}</p>

                    {/* Row 3: betting volume — prominent second metric */}
                    <div className="flex items-center gap-1.5 mb-3">
                      <span className="text-slate-400 text-xs">💰</span>
                      <span className="text-sm font-bold" style={{ color }}>{fmtVolume(m.volume_usd)}</span>
                      <span className="text-slate-400 text-xs">in active bets</span>
                    </div>

                    {/* Row 4: YES/NO probability bar */}
                    <div className="flex items-center gap-2">
                      <span className="text-green-400 text-xs font-bold w-14 shrink-0">YES {m.yes_pct.toFixed(0)}%</span>
                      <div className="flex-1 h-2 bg-slate-600 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all"
                          style={{
                            width: `${Math.min(Math.max(m.yes_pct, 2), 98)}%`,
                            background: 'linear-gradient(90deg,#16a34a,#4ade80)',
                          }}
                        />
                      </div>
                      <span className="text-red-400 text-xs font-bold w-14 shrink-0 text-right">NO {m.no_pct.toFixed(0)}%</span>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}
    </Card>
  )
}
