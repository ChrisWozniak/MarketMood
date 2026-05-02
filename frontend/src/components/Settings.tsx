import { useState, useEffect, useRef } from 'react'
import { getHealth, updateSchedule, getEmailConfig, saveEmailConfig, sendTestEmail, type EmailConfigPayload } from '../api'
import { useStore } from '../store'
import { searchLocal } from '../tickerList'
import type { Ticker } from '../tickerList'
import Card from './Card'
import Spinner from './Spinner'
import InfoTooltip from './InfoTooltip'

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
  title, open, onToggle, accent, controlsId, tooltip,
}: { title: string; open: boolean; onToggle: () => void; accent?: string; controlsId: string; tooltip?: string }) {
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onToggle}
      onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onToggle() } }}
      className="w-full flex items-center justify-between gap-2 group cursor-pointer text-left hover:opacity-80 transition-opacity"
      aria-expanded={open}
      aria-controls={controlsId}
    >
      <h3
        className="text-slate-200 font-semibold text-sm md:group-hover:text-base transition-all duration-200 flex items-center gap-1"
        style={accent ? { color: accent } : undefined}
      >
        {title}
        {tooltip && (
          <span onClick={e => e.stopPropagation()}>
            <InfoTooltip text={tooltip} />
          </span>
        )}
      </h3>
      <span
        aria-hidden="true"
        className="text-slate-500 text-xs transition-transform duration-200 shrink-0"
        style={{ display: 'inline-block', transform: open ? 'rotate(180deg)' : 'rotate(0deg)' }}
      >
        ▼
      </span>
    </div>
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
            <p className="text-slate-400 text-xs leading-tight md:group-hover/row:text-xs transition-all duration-200 truncate">
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
  const [sourcesOpen,   setSourcesOpen]   = useState(false)
  const [scheduleOpen,  setScheduleOpen]  = useState(false)
  const [watchlistOpen, setWatchlistOpen] = useState(false)

  useEffect(() => {
    if (panelCollapse === null) return
    setSourcesOpen(!panelCollapse)
    setScheduleOpen(!panelCollapse)
    setWatchlistOpen(!panelCollapse)
  }, [panelCollapse])

  // Custom Watchlist state
  const [watchlistTickers, setWatchlistTickers] = useState<string[]>(() => {
    try {
      const saved = JSON.parse(localStorage.getItem('mm_watchlist_tickers') || '[]')
      return Array.isArray(saved) ? saved.slice(0, 5) : []
    } catch { return [] }
  })
  const [watchlistQuery, setWatchlistQuery] = useState('')
  const [activeIdx, setActiveIdx] = useState(-1)
  const watchlistInputRef = useRef<HTMLInputElement>(null)

  const watchlistSuggestions = searchLocal(watchlistQuery)
  const dropdownOpen = watchlistSuggestions.length > 0 && watchlistQuery.length > 0

  useEffect(() => {
    localStorage.setItem('mm_watchlist_tickers', JSON.stringify(watchlistTickers))
  }, [watchlistTickers])

  const addWatchlistTicker = (t: Ticker) => {
    if (watchlistTickers.includes(t.symbol) || watchlistTickers.length >= 5) return
    setWatchlistTickers(prev => [...prev, t.symbol])
    setWatchlistQuery('')
    setActiveIdx(-1)
    watchlistInputRef.current?.focus()
  }

  const removeWatchlistTicker = (symbol: string) =>
    setWatchlistTickers(prev => prev.filter(s => s !== symbol))

  const handleWatchlistKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!dropdownOpen) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActiveIdx(i => Math.min(i + 1, watchlistSuggestions.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveIdx(i => Math.max(i - 1, 0))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      const target = activeIdx >= 0 ? watchlistSuggestions[activeIdx] : watchlistSuggestions[0]
      if (target) addWatchlistTicker(target)
    } else if (e.key === 'Escape') {
      setWatchlistQuery('')
      setActiveIdx(-1)
    }
  }

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

  // Email distribution
  const [emailEnabled,      setEmailEnabled]      = useState(false)
  const [emailSender,       setEmailSender]       = useState('')
  const [emailPassword,     setEmailPassword]     = useState('')
  const [emailPasswordSet,  setEmailPasswordSet]  = useState(false)
  const [emailRecipients,   setEmailRecipients]   = useState<string[]>([])
  const [emailInput,        setEmailInput]        = useState('')
  const [emailTheme,        setEmailTheme]        = useState<'dark' | 'light'>('dark')
  const [emailSaveStatus,   setEmailSaveStatus]   = useState<'idle' | 'saving' | 'ok' | 'error'>('idle')
  const [emailTestStatus,   setEmailTestStatus]   = useState<'idle' | 'sending' | 'ok' | 'error'>('idle')
  const [emailTestMessage,  setEmailTestMessage]  = useState('')

  useEffect(() => {
    getEmailConfig()
      .then((cfg: EmailConfigPayload & { smtp_password_set?: boolean; email_theme?: string }) => {
        setEmailEnabled(cfg.enabled ?? false)
        setEmailSender(cfg.smtp_sender ?? '')
        setEmailPasswordSet(cfg.smtp_password_set ?? false)
        setEmailPassword(cfg.smtp_password_set ? '••••••••' : '')
        setEmailRecipients(cfg.recipients ?? [])
        setEmailTheme((cfg.email_theme as 'dark' | 'light') ?? 'dark')
      })
      .catch(() => {})
  }, [])

  const addRecipient = () => {
    const email = emailInput.trim().toLowerCase()
    if (!email || emailRecipients.includes(email)) return
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return
    setEmailRecipients(prev => [...prev, email])
    setEmailInput('')
  }

  const removeRecipient = (email: string) =>
    setEmailRecipients(prev => prev.filter(e => e !== email))

  const saveEmail = async () => {
    setEmailSaveStatus('saving')
    try {
      await saveEmailConfig({
        enabled: emailEnabled,
        smtp_sender: emailSender,
        smtp_password: emailPassword,
        recipients: emailRecipients,
        email_theme: emailTheme,
      })
      setEmailSaveStatus('ok')
      setTimeout(() => setEmailSaveStatus('idle'), 2500)
    } catch {
      setEmailSaveStatus('error')
      setTimeout(() => setEmailSaveStatus('idle'), 3000)
    }
  }

  const handleTestEmail = async () => {
    setEmailTestStatus('sending')
    setEmailTestMessage('')
    try {
      // Always save current UI state to backend before testing
      await saveEmailConfig({
        enabled: emailEnabled,
        smtp_sender: emailSender,
        smtp_password: emailPassword,
        recipients: emailRecipients,
        email_theme: emailTheme,
      })
      const result = await sendTestEmail()
      setEmailTestStatus('ok')
      setEmailTestMessage(result.message || 'Test email sent!')
      setTimeout(() => { setEmailTestStatus('idle'); setEmailTestMessage('') }, 5000)
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setEmailTestStatus('error')
      setEmailTestMessage(detail || 'Failed to send test email.')
      setTimeout(() => { setEmailTestStatus('idle'); setEmailTestMessage('') }, 5000)
    }
  }

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
          controlsId="sources-content"
          tooltip="Choose which platforms and topic categories Market Mood monitors. Checked sources are fetched on every run; checked categories determine which topics receive a sentiment score and signal card."
        />
        {sourcesOpen && (
          <div id="sources-content" className="mt-4 space-y-5">
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

      {/* ── Custom Watchlist ── */}
      <Card accent="#f59e0b">
        <CollapseHeader
          title="Custom Watchlist"
          open={watchlistOpen}
          onToggle={() => setWatchlistOpen(o => !o)}
          controlsId="watchlist-content"
          tooltip="Add up to 5 tickers, ETFs, or crypto symbols. On the next run Gemini scores sentiment specifically for those assets and generates a dedicated investment signal card in the dashboard."
        />
        {watchlistOpen && (
          <div id="watchlist-content" className="mt-4 space-y-3">
            <p className="text-slate-500 text-xs">
              Type a ticker or company name. On the next run, your watchlist appears as its own mood indicator in Social Mood and gets a dedicated Investment Signal card. Max 5 tickers to keep analysis fast.
            </p>
            <p className="text-amber-600 text-xs mt-1">
              ⚡ Limited to 5 tickers to keep Gemini analysis fast and accurate.
            </p>

            {/* Combobox input */}
            <div className="relative">
              <input
                ref={watchlistInputRef}
                type="text"
                role="combobox"
                aria-expanded={dropdownOpen}
                aria-autocomplete="list"
                aria-controls="watchlist-listbox"
                aria-activedescendant={activeIdx >= 0 ? `watchlist-opt-${watchlistSuggestions[activeIdx]?.symbol}` : undefined}
                value={watchlistQuery}
                onChange={e => { setWatchlistQuery(e.target.value); setActiveIdx(-1) }}
                onKeyDown={handleWatchlistKeyDown}
                placeholder={watchlistTickers.length >= 5 ? 'Maximum 5 tickers reached' : 'Search ticker or company…'}
                disabled={watchlistTickers.length >= 5}
                className="w-full bg-slate-800 border border-slate-700 text-slate-200 text-sm px-3 py-2 rounded-lg placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-amber-500 disabled:opacity-40"
              />

              {dropdownOpen && (
                <ul
                  id="watchlist-listbox"
                  role="listbox"
                  aria-label="Ticker suggestions"
                  className="absolute z-50 top-full left-0 right-0 mt-1 bg-slate-800 border border-slate-700 rounded-lg overflow-hidden shadow-xl"
                >
                  {watchlistSuggestions.map((t, i) => (
                    <li
                      key={t.symbol}
                      id={`watchlist-opt-${t.symbol}`}
                      role="option"
                      aria-selected={i === activeIdx}
                      onMouseDown={e => { e.preventDefault(); addWatchlistTicker(t) }}
                      className={`flex items-center justify-between gap-2 px-3 py-2 cursor-pointer text-sm transition-colors ${
                        i === activeIdx ? 'bg-amber-600 text-white' : 'text-slate-200 hover:bg-slate-700'
                      }`}
                    >
                      <span className="flex items-center gap-2 min-w-0">
                        <span className="font-mono font-bold shrink-0">{t.symbol}</span>
                        <span className={`truncate text-xs ${i === activeIdx ? 'text-amber-100' : 'text-slate-400'}`}>{t.name}</span>
                      </span>
                      <span className={`text-xs px-1.5 py-0.5 rounded shrink-0 ${
                        i === activeIdx ? 'bg-amber-500 text-white' : 'bg-slate-700 text-slate-400'
                      }`}>{t.type}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Selected ticker chips */}
            {watchlistTickers.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {watchlistTickers.map(sym => (
                  <span
                    key={sym}
                    className="inline-flex items-center gap-1 bg-amber-950/50 border border-amber-700/50 text-amber-300 text-xs font-mono px-2 py-1 rounded-lg"
                  >
                    <a
                      href={`https://finance.yahoo.com/quote/${sym}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label={`Open ${sym} on Yahoo Finance`}
                      className="hover:text-white transition-colors duration-150"
                    >
                      {sym}
                    </a>
                    <button
                      type="button"
                      onClick={() => removeWatchlistTicker(sym)}
                      aria-label={`Remove ${sym} from watchlist`}
                      className="text-amber-500 hover:text-white ml-0.5 focus:outline-none focus:ring-1 focus:ring-amber-400 rounded leading-none"
                    >
                      ×
                    </button>
                  </span>
                ))}
                {watchlistTickers.length >= 2 && (
                  <button
                    type="button"
                    onClick={() => setWatchlistTickers([])}
                    className="text-xs text-slate-500 hover:text-red-400 px-1 transition-colors"
                  >
                    Clear all
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </Card>

      {/* ── Analysis Schedule & Distribution (collapsible) ── */}
      <Card accent="#0ea5e9">
        <CollapseHeader
          title="Analysis Schedule & Distribution"
          open={scheduleOpen}
          onToggle={() => setScheduleOpen(o => !o)}
          controlsId="schedule-content"
          tooltip="Set how often the backend auto-refreshes data and signals. Enable email distribution to receive a formatted HTML report in your inbox after each scheduled or manual run."
        />
        {scheduleOpen && (
          <div id="schedule-content" className="mt-4 space-y-4">
            <p className="text-slate-500 text-xs">
              The backend runs a full analysis automatically at the selected interval via APScheduler.
              Use the ⚡ Run Now button at the top for an immediate run.
            </p>

            {/* Interval selector */}
            <div>
              <p className="text-slate-400 text-xs font-medium mb-2">Auto-refresh interval</p>
              <div className="flex flex-wrap gap-2">
                {SCHEDULE_OPTIONS.map(opt => (
                  <button
                    key={opt.minutes}
                    type="button"
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
              <div className="mt-2 h-4" aria-live="polite" aria-atomic="true">
                {scheduleStatus === 'saving' && (
                  <p className="text-slate-500 text-xs flex items-center gap-1"><Spinner size={10} hidden /> Updating…</p>
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
                type="button"
                onClick={checkHealth}
                disabled={healthStatus === 'checking'}
                className="flex items-center gap-1.5 text-xs bg-slate-700 hover:bg-slate-600 disabled:opacity-50 text-slate-300 px-3 py-1.5 rounded-lg transition-colors"
              >
                {healthStatus === 'checking' && <Spinner size={10} hidden />}
                {healthStatus === 'idle'     && 'Ping'}
                {healthStatus === 'checking' && 'Checking…'}
                {healthStatus === 'ok'       && <span className="text-emerald-400">● OK</span>}
                {healthStatus === 'error'    && <span className="text-red-400">● Unreachable</span>}
              </button>
            </div>

            {/* ── Email Distribution ── */}
            <div className="border-t border-slate-700 pt-5">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="text-slate-300 text-sm font-medium">Email Distribution</p>
                  <p className="text-slate-500 text-xs mt-0.5">Send HTML report to recipients on every run</p>
                </div>
                <button
                  type="button"
                  role="switch"
                  aria-checked={emailEnabled}
                  onClick={() => setEmailEnabled(e => !e)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-sky-500 ${emailEnabled ? 'bg-sky-600' : 'bg-slate-700'}`}
                >
                  <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${emailEnabled ? 'translate-x-6' : 'translate-x-1'}`} />
                </button>
              </div>

              {emailEnabled && (
                <div className="space-y-3">
                  {/* Gmail sender */}
                  <div>
                    <label className="text-slate-400 text-xs mb-1 block">Gmail sender address</label>
                    <input
                      type="email"
                      value={emailSender}
                      onChange={e => setEmailSender(e.target.value)}
                      placeholder="yourname@gmail.com"
                      className="w-full bg-slate-800 border border-slate-700 text-slate-200 text-sm px-3 py-2 rounded-lg placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500"
                    />
                  </div>

                  {/* App password */}
                  <div>
                    <label className="text-slate-400 text-xs mb-1 block">
                      Gmail App Password
                      <span className="text-slate-600 ml-1">(not your regular password)</span>
                    </label>
                    <input
                      type="password"
                      value={emailPassword}
                      onChange={e => setEmailPassword(e.target.value)}
                      placeholder={emailPasswordSet ? 'Saved — enter new value to change' : 'xxxx xxxx xxxx xxxx'}
                      className="w-full bg-slate-800 border border-slate-700 text-slate-200 text-sm px-3 py-2 rounded-lg placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500"
                    />
                    <p className="text-slate-600 text-xs mt-1">
                      Generate at: Google Account → Security → 2-Step Verification → App passwords
                    </p>
                  </div>

                  {/* Recipients */}
                  <div>
                    <label className="text-slate-400 text-xs mb-1 block">Recipients</label>
                    <div className="flex gap-2">
                      <input
                        type="email"
                        value={emailInput}
                        onChange={e => setEmailInput(e.target.value)}
                        onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addRecipient() } }}
                        placeholder="recipient@email.com"
                        className="flex-1 bg-slate-800 border border-slate-700 text-slate-200 text-sm px-3 py-2 rounded-lg placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500"
                      />
                      <button
                        type="button"
                        onClick={addRecipient}
                        className="bg-slate-700 hover:bg-slate-600 text-slate-200 text-sm px-3 py-2 rounded-lg transition-colors shrink-0"
                      >
                        + Add
                      </button>
                    </div>
                    {emailRecipients.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {emailRecipients.map(email => (
                          <span
                            key={email}
                            className="inline-flex items-center gap-1 bg-sky-950/50 border border-sky-700/50 text-sky-300 text-xs px-2 py-1 rounded-lg"
                          >
                            {email}
                            <button
                              type="button"
                              onClick={() => removeRecipient(email)}
                              aria-label={`Remove ${email}`}
                              className="text-sky-500 hover:text-white ml-0.5 focus:outline-none focus:ring-1 focus:ring-sky-400 rounded leading-none"
                            >
                              ×
                            </button>
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Scheduled email theme */}
                  <div>
                    <label className="text-slate-400 text-xs mb-1 block">Scheduled report theme</label>
                    <div className="flex gap-2">
                      {(['dark', 'light'] as const).map(t => (
                        <button
                          key={t}
                          type="button"
                          onClick={() => setEmailTheme(t)}
                          className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
                            emailTheme === t
                              ? 'bg-sky-700 border-sky-500 text-white font-semibold'
                              : 'bg-slate-800 border-slate-700 text-slate-400 hover:border-sky-500 hover:text-slate-200'
                          }`}
                        >
                          {t === 'dark' ? '🌙 Dark' : '☀️ Light'}
                        </button>
                      ))}
                    </div>
                    <p className="text-slate-600 text-xs mt-1">Manual runs use your current app mode. This sets the theme for scheduled runs.</p>
                  </div>

                  {/* Action buttons */}
                  <div className="flex items-center gap-2 pt-1">
                    <button
                      type="button"
                      onClick={saveEmail}
                      disabled={emailSaveStatus === 'saving'}
                      className="flex items-center gap-1.5 bg-sky-700 hover:bg-sky-600 disabled:opacity-50 text-white text-xs font-medium px-4 py-2 rounded-lg transition-colors"
                    >
                      {emailSaveStatus === 'saving' && <Spinner size={10} hidden />}
                      {emailSaveStatus === 'saving' ? 'Saving…' : 'Save Settings'}
                    </button>
                    <button
                      type="button"
                      onClick={handleTestEmail}
                      disabled={emailTestStatus === 'sending' || !emailSender}
                      className="flex items-center gap-1.5 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 text-slate-200 text-xs px-4 py-2 rounded-lg transition-colors"
                    >
                      {emailTestStatus === 'sending' && <Spinner size={10} hidden />}
                      {emailTestStatus === 'sending' ? 'Sending…' : '✉ Test Email'}
                    </button>
                  </div>

                  {/* Status feedback */}
                  <div className="min-h-[1rem]" aria-live="polite">
                    {emailSaveStatus === 'ok'    && <p className="text-emerald-400 text-xs">● Settings saved</p>}
                    {emailSaveStatus === 'error'  && <p className="text-red-400 text-xs">● Failed to save — is the backend running?</p>}
                    {emailTestStatus === 'ok'    && <p className="text-emerald-400 text-xs">● {emailTestMessage}</p>}
                    {emailTestStatus === 'error'  && <p className="text-red-400 text-xs">● {emailTestMessage}</p>}
                  </div>
                </div>
              )}
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
          <p className="text-slate-500 text-xs md:group-hover/disclaimer:text-sm md:group-hover/disclaimer:text-red-500 transition-all duration-200">
            Aggregate data only — no individual user profiles stored.
          </p>
        </div>
      </Card>

    </div>
  )
}
