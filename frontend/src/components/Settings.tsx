import { useState, useEffect } from 'react'
import { getHealth, updateSchedule } from '../api'
import { useStore } from '../store'
import Card from './Card'
import Spinner from './Spinner'

// ── Constants ──────────────────────────────────────────────────────────────

const DATA_SOURCES = [
  { name: 'Reddit',      icon: '🟠', desc: 'Subreddits per category' },
  { name: 'Hacker News', icon: '🟡', desc: 'Algolia search API' },
  { name: 'YouTube',     icon: '🔴', desc: 'YouTube Data API v3' },
  { name: 'Kalshi',      icon: '🔵', desc: 'Prediction market contracts' },
  { name: 'Polymarket',  icon: '🟣', desc: 'Decentralised market odds' },
  { name: 'FRED',        icon: '🟢', desc: 'Federal Reserve macro data' },
  { name: 'Redfin',      icon: '🏠', desc: 'Housing market stats' },
]

const CATEGORIES = [
  { name: 'Economy',            desc: 'Inflation, rates, tariffs' },
  { name: 'Politics',           desc: 'Elections, policy, regulation' },
  { name: 'Daily Hot Topics',   desc: 'Reddit & HN trending' },
  { name: 'Sector Sentiment',   desc: 'Energy, healthcare, finance' },
  { name: 'Technology & AI',    desc: 'Models, dev sentiment, chips' },
  { name: 'Blockchain & Crypto',desc: 'BTC, ETH, DeFi, Web3' },
  { name: 'Real Estate',        desc: 'Housing, mortgage, REITs' },
  { name: 'Health & Science',   desc: 'Research, longevity, medicine' },
]

const SCHEDULE_OPTIONS = [
  { label: '30 min',  minutes: 30 },
  { label: '1 hour',  minutes: 60 },
  { label: '2 hours', minutes: 120 },
  { label: '4 hours', minutes: 240 },
  { label: '6 hours', minutes: 360 },
  { label: '12 hours',minutes: 720 },
  { label: '24 hours',minutes: 1440 },
]

// ── Helpers ────────────────────────────────────────────────────────────────

function loadBoolMap(key: string, names: string[]): Record<string, boolean> {
  try {
    const stored = localStorage.getItem(key)
    if (stored) return JSON.parse(stored)
  } catch { /* ignore */ }
  return Object.fromEntries(names.map(n => [n, true]))
}

function CollapseHeader({
  title, open, onToggle, accent,
}: { title: string; open: boolean; onToggle: () => void; accent?: string }) {
  return (
    <button
      onClick={onToggle}
      className="w-full flex items-center justify-between gap-2 group"
    >
      <h3
        className="text-slate-200 font-semibold text-sm md:group-hover:text-base transition-all duration-200"
        style={accent ? { color: accent } : undefined}
      >
        {title}
      </h3>
      <span
        className="text-slate-500 text-xs transition-transform duration-200 shrink-0"
        style={{ display: 'inline-block', transform: open ? 'rotate(180deg)' : 'rotate(0deg)' }}
      >
        ▼
      </span>
    </button>
  )
}

// ── Checkbox grid shared by sources and categories ─────────────────────────

function CheckboxGrid({
  items, enabled, onToggle,
}: {
  items: { name: string; desc: string; icon?: string }[]
  enabled: Record<string, boolean>
  onToggle: (name: string) => void
}) {
  return (
    <div className="grid grid-cols-2 gap-x-4 gap-y-1">
      {items.map(item => (
        <label
          key={item.name}
          className="flex items-start gap-2 py-2 cursor-pointer group/row border-b border-slate-800/50 last:border-0"
        >
          <input
            type="checkbox"
            checked={enabled[item.name] ?? true}
            onChange={() => onToggle(item.name)}
            className="mt-0.5 accent-indigo-500 shrink-0 cursor-pointer"
          />
          <div className="min-w-0">
            <p className="text-slate-200 text-xs font-medium leading-tight md:group-hover/row:text-sm transition-all duration-200 flex items-center gap-1">
              {item.icon && <span>{item.icon}</span>}
              {item.name}
            </p>
            <p className="text-slate-500 text-xs leading-tight md:group-hover/row:text-xs transition-all duration-200 truncate">
              {item.desc}
            </p>
          </div>
        </label>
      ))}
    </div>
  )
}

// ── Main Component ─────────────────────────────────────────────────────────

type HealthStatus = 'idle' | 'checking' | 'ok' | 'error'

export default function Settings() {
  // Collapse state — also wired to global Collapse All / Expand All
  const { panelCollapse } = useStore()
  const [sourcesOpen,  setSourcesOpen]  = useState(false)
  const [scheduleOpen, setScheduleOpen] = useState(false)

  useEffect(() => {
    if (panelCollapse === null) return
    setSourcesOpen(!panelCollapse)
    setScheduleOpen(!panelCollapse)
  }, [panelCollapse])

  // Enabled toggles (persisted in localStorage)
  const [sourcesEnabled, setSourcesEnabled] = useState<Record<string, boolean>>(() =>
    loadBoolMap('mm_sources', DATA_SOURCES.map(s => s.name))
  )
  const [catsEnabled, setCatsEnabled] = useState<Record<string, boolean>>(() =>
    loadBoolMap('mm_categories', CATEGORIES.map(c => c.name))
  )

  // Schedule
  const [intervalMinutes, setIntervalMinutes] = useState<number>(() => {
    const stored = localStorage.getItem('mm_interval')
    return stored ? parseInt(stored, 10) : 60
  })
  const [scheduleStatus, setScheduleStatus] = useState<'idle' | 'saving' | 'ok' | 'error'>('idle')

  // Health
  const [healthStatus, setHealthStatus] = useState<HealthStatus>('idle')

  // Persist toggles
  useEffect(() => {
    localStorage.setItem('mm_sources', JSON.stringify(sourcesEnabled))
  }, [sourcesEnabled])
  useEffect(() => {
    localStorage.setItem('mm_categories', JSON.stringify(catsEnabled))
  }, [catsEnabled])

  const toggleSource = (name: string) =>
    setSourcesEnabled(prev => ({ ...prev, [name]: !prev[name] }))
  const toggleCat = (name: string) =>
    setCatsEnabled(prev => ({ ...prev, [name]: !prev[name] }))

  const applySchedule = async (minutes: number) => {
    setIntervalMinutes(minutes)
    localStorage.setItem('mm_interval', String(minutes))
    setScheduleStatus('saving')
    try {
      await updateSchedule(minutes)
      setScheduleStatus('ok')
      setTimeout(() => setScheduleStatus('idle'), 2000)
    } catch {
      setScheduleStatus('error')
      setTimeout(() => setScheduleStatus('idle'), 3000)
    }
  }

  const checkHealth = async () => {
    setHealthStatus('checking')
    try {
      await getHealth()
      setHealthStatus('ok')
    } catch {
      setHealthStatus('error')
    }
  }

  const currentLabel = SCHEDULE_OPTIONS.find(o => o.minutes === intervalMinutes)?.label ?? `${intervalMinutes}m`

  return (
    <div className="space-y-6">

      {/* ── Data Sources & Categories (single collapsible panel) ── */}
      <Card accent="#6366f1">
        <CollapseHeader
          title="Data Sources & Monitored Categories"
          open={sourcesOpen}
          onToggle={() => setSourcesOpen(o => !o)}
        />
        {sourcesOpen && (
          <div className="mt-4 space-y-5">
            <div>
              <p className="text-slate-500 text-xs mb-3 font-medium uppercase tracking-wider">
                Data Sources
              </p>
              <CheckboxGrid
                items={DATA_SOURCES}
                enabled={sourcesEnabled}
                onToggle={toggleSource}
              />
            </div>
            <div className="border-t border-slate-700 pt-4">
              <p className="text-slate-500 text-xs mb-3 font-medium uppercase tracking-wider">
                Categories
              </p>
              <CheckboxGrid
                items={CATEGORIES}
                enabled={catsEnabled}
                onToggle={toggleCat}
              />
            </div>
          </div>
        )}
      </Card>

      {/* ── Analysis Schedule (collapsible) ── */}
      <Card accent="#0ea5e9">
        <CollapseHeader
          title="Analysis Schedule"
          open={scheduleOpen}
          onToggle={() => setScheduleOpen(o => !o)}
        />
        {scheduleOpen && (
          <div className="mt-4 space-y-4">
            <p className="text-slate-500 text-xs">
              The backend runs a full analysis automatically at the selected interval via APScheduler.
              Use the ⚡ Refresh Now button at the top for an immediate run.
            </p>

            {/* Interval selector */}
            <div>
              <p className="text-slate-400 text-xs font-medium mb-2">Auto-refresh interval</p>
              <div className="flex flex-wrap gap-2">
                {SCHEDULE_OPTIONS.map(opt => (
                  <button
                    key={opt.minutes}
                    onClick={() => applySchedule(opt.minutes)}
                    className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
                      intervalMinutes === opt.minutes
                        ? 'bg-indigo-600 border-indigo-500 text-white font-semibold'
                        : 'bg-slate-800 border-slate-700 text-slate-400 hover:border-indigo-500 hover:text-slate-200'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
              <div className="mt-2 h-4">
                {scheduleStatus === 'saving' && (
                  <p className="text-slate-500 text-xs flex items-center gap-1"><Spinner size={10} /> Updating…</p>
                )}
                {scheduleStatus === 'ok' && (
                  <p className="text-emerald-400 text-xs">● Schedule updated to {currentLabel}</p>
                )}
                {scheduleStatus === 'error' && (
                  <p className="text-red-400 text-xs">● Failed to update — is the backend running?</p>
                )}
              </div>
            </div>

            {/* Status + health */}
            <div className="flex items-center justify-between py-3 border-t border-slate-800">
              <div>
                <p className="text-slate-300 text-sm">Automatic refresh</p>
                <p className="text-slate-500 text-xs">Every {currentLabel}</p>
              </div>
              <span className="text-xs text-emerald-400 font-medium">● Running</span>
            </div>
            <div className="flex items-center justify-between py-3 border-t border-slate-800">
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
          </div>
        )}
      </Card>

      {/* ── Disclaimer (not collapsible, hover text scale) ── */}
      <Card>
        <h3 className="text-slate-200 font-semibold mb-3">Disclaimer</h3>
        <div className="group/disclaimer disclaimer-group space-y-2">
          <p className="text-slate-500 text-xs md:group-hover/disclaimer:text-sm md:group-hover/disclaimer:text-red-400 leading-relaxed transition-all duration-200">
            Market Mood provides social sentiment analysis and AI-generated market observations for
            informational purposes only. Nothing on this platform constitutes financial advice,
            investment recommendations, or an offer to buy or sell any security. Always conduct
            your own research and consult a qualified financial advisor before making investment
            decisions. Sentiment signals are derived from public social media and may not reflect
            actual market conditions.
          </p>
          <p className="text-slate-600 text-xs md:group-hover/disclaimer:text-sm md:group-hover/disclaimer:text-red-500 transition-all duration-200">
            Aggregate data only — no individual user profiles stored.
          </p>
        </div>
      </Card>

    </div>
  )
}
