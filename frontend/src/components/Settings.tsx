import { useState, useEffect, useRef } from 'react'
import toast from 'react-hot-toast'
import { getSettings, saveSettings, testEmail } from '../api'
import { searchLocal } from '../tickerList'
import { searchLocations, searchCountries, toTitleCase } from '../locationList'
import type { Location } from '../locationList'
import { useStore } from '../store'
import Card from './Card'
import InfoTooltip from './InfoTooltip'
import Spinner from './Spinner'

const DEFAULT_CATEGORIES = [
  'Business & Economy', 'World News', 'Local News', 'Technology/AI',
  'Space/Cosmos', 'Entertainment & Culture', 'Sport',
  'Environment & Climate', 'Blockchain/Crypto', 'Science & Health',
]

const DAYS = [
  { label: 'M', value: 'mon' }, { label: 'T', value: 'tue' },
  { label: 'W', value: 'wed' }, { label: 'T', value: 'thu' },
  { label: 'F', value: 'fri' }, { label: 'S', value: 'sat' },
  { label: 'S', value: 'sun' },
]

function isValidEmail(e: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e.trim())
}

export default function Settings() {
  const { setSettingsDirty } = useStore()

  // ── Form state ──────────────────────────────────────────────────────────────
  const [form, setForm] = useState<Record<string, unknown>>({
    schedule_type: 'custom', schedule_value: '0 9 * * mon,tue,wed,thu,fri',
    timezone: 'America/New_York', social_refresh_hours: 24, articles_per_category: 5,
  })
  const [scheduleEnabled, setScheduleEnabled] = useState(true)
  const [selectedDays, setSelectedDays] = useState(['mon','tue','wed','thu','fri'])
  const [scheduleTime, setScheduleTime] = useState('09:00')
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)

  // ── Emails ──────────────────────────────────────────────────────────────────
  const [emails, setEmails] = useState<string[]>([])
  const [emailInput, setEmailInput] = useState('')

  // ── Categories ──────────────────────────────────────────────────────────────
  const [categories, setCategories] = useState<string[]>([])
  const [customCatInput, setCustomCatInput] = useState('')
  const [addingCat, setAddingCat] = useState(false)

  // ── Market Tickers ──────────────────────────────────────────────────────────
  const [tickers, setTickers] = useState<{name: string; symbol: string}[]>([])
  const [tickerInput, setTickerInput] = useState('')
  const [tickerSuggestions, setTickerSuggestions] = useState<{name: string; symbol: string; type: string}[]>([])
  const [tickerLoading, setTickerLoading] = useState(false)
  const [showTickerSug, setShowTickerSug] = useState(false)
  const tickerDebounce = useRef<ReturnType<typeof setTimeout> | null>(null)
  const tickerRef = useRef<HTMLDivElement>(null)

  // ── Local News ──────────────────────────────────────────────────────────────
  const [localLocations, setLocalLocations] = useState<{city: string; state: string; country: string}[]>([])
  const [locCity, setLocCity] = useState('')
  const [locState, setLocState] = useState('')
  const [locCountry, setLocCountry] = useState('')
  const [locSuggestions, setLocSuggestions] = useState<Location[]>([])
  const [showLocSug, setShowLocSug] = useState(false)
  const locRef = useRef<HTMLDivElement>(null)

  // ── World News ──────────────────────────────────────────────────────────────
  const [worldCountries, setWorldCountries] = useState<string[]>([])
  const [worldInput, setWorldInput] = useState('')
  const [worldSuggestions, setWorldSuggestions] = useState<string[]>([])
  const [showWorldSug, setShowWorldSug] = useState(false)
  const worldRef = useRef<HTMLDivElement>(null)

  // ── Dirty tracking ──────────────────────────────────────────────────────────
  const loaded = useRef(false)
  const markDirty = () => { if (loaded.current) setSettingsDirty(true) }

  // ── Load ────────────────────────────────────────────────────────────────────
  useEffect(() => {
    getSettings().then(d => {
      setForm(d)
      const rawEmails = (d.email as string) || ''
      setEmails(rawEmails ? rawEmails.split(',').map((e: string) => e.trim()).filter(Boolean) : [])
      setCategories(Array.isArray(d.categories) ? d.categories : [])
      setTickers(Array.isArray(d.market_tickers) ? d.market_tickers : [])
      setLocalLocations(Array.isArray(d.local_locations) ? d.local_locations : [])
      setWorldCountries(Array.isArray(d.world_countries) ? d.world_countries : [])
      if (d.schedule_type === 'disabled') {
        setScheduleEnabled(false)
      } else if (d.schedule_type === 'custom' && d.schedule_value) {
        const parts = (d.schedule_value as string).split(' ')
        if (parts.length === 5) {
          const [min, hour, , , days] = parts
          setScheduleTime(`${parseInt(hour).toString().padStart(2,'0')}:${parseInt(min).toString().padStart(2,'0')}`)
          setSelectedDays(days === '*' ? DAYS.map(d => d.value) : days.split(','))
        }
      } else if (d.schedule_type === 'daily' && d.schedule_value) {
        setScheduleTime(d.schedule_value as string)
        setSelectedDays(DAYS.map(d => d.value))
      }
      loaded.current = true
    }).catch(() => toast.error('Could not load settings.'))
  }, [])

  // ── Close dropdowns on outside click ───────────────────────────────────────
  useEffect(() => {
    const h = (e: MouseEvent) => {
      if (tickerRef.current && !tickerRef.current.contains(e.target as Node)) setShowTickerSug(false)
      if (locRef.current   && !locRef.current.contains(e.target as Node))    setShowLocSug(false)
      if (worldRef.current && !worldRef.current.contains(e.target as Node))  setShowWorldSug(false)
    }
    document.addEventListener('mousedown', h)
    return () => document.removeEventListener('mousedown', h)
  }, [])

  const set = (key: string, val: unknown) => { setForm(f => ({ ...f, [key]: val })); markDirty() }

  // ── Save ────────────────────────────────────────────────────────────────────
  const handleSave = async () => {
    setSaving(true)
    try {
      let schedule_type = 'disabled', schedule_value = ''
      if (scheduleEnabled && selectedDays.length > 0) {
        const [h, m] = scheduleTime.split(':')
        const dayStr = selectedDays.length === 7 ? '*' : selectedDays.join(',')
        schedule_type = 'custom'
        schedule_value = `${parseInt(m||'0')} ${parseInt(h||'9')} * * ${dayStr}`
      }
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone
      await saveSettings({
        ...form,
        email: emails.join(','),
        categories, schedule_type, schedule_value, timezone,
        market_tickers: tickers,
        local_locations: localLocations,
        world_countries: worldCountries,
      })
      setSettingsDirty(false)
      toast.success('Settings saved!')
    } catch {
      toast.error('Failed to save settings.')
    } finally {
      setSaving(false)
    }
  }

  // ── Email logic ─────────────────────────────────────────────────────────────
  const addEmail = () => {
    const e = emailInput.trim()
    if (!e) return
    if (!isValidEmail(e)) { toast.error('Invalid email address.'); return }
    if (emails.includes(e)) return
    setEmails(prev => [...prev, e])
    setEmailInput('')
    markDirty()
  }

  // ── Category logic ──────────────────────────────────────────────────────────
  const toggleCategory = (cat: string) => {
    setCategories(prev => prev.includes(cat) ? prev.filter(c => c !== cat) : [...prev, cat])
    markDirty()
  }

  const addCustomCategory = async () => {
    const cat = customCatInput.trim()
    if (!cat || cat.length < 2) return
    if (categories.includes(cat)) { toast.error('Category already exists.'); return }
    setAddingCat(true)
    // Spell-check via browser dictionary (best-effort via textarea approach)
    // We trust the browser spellcheck attribute on the input; just add the category
    setCategories(prev => [...prev, cat])
    setCustomCatInput('')
    markDirty()
    setAddingCat(false)
  }

  // ── Market Ticker logic ─────────────────────────────────────────────────────
  const onTickerInput = (val: string) => {
    setTickerInput(val); setShowTickerSug(true)
    if (tickerDebounce.current) clearTimeout(tickerDebounce.current)
    if (val.length < 1) { setTickerSuggestions([]); return }
    const local = searchLocal(val)
    setTickerSuggestions(local)
    if (local.length < 3) {
      setTickerLoading(true)
      tickerDebounce.current = setTimeout(async () => {
        try {
          const { searchTickers: apiSearch } = await import('../api')
          const results = await apiSearch(val)
          const merged = [...results, ...local.filter(l => !results.find((r: {symbol:string}) => r.symbol === l.symbol))].slice(0,7)
          setTickerSuggestions(merged)
        } catch { /* keep local */ } finally { setTickerLoading(false) }
      }, 400)
    }
    markDirty()
  }

  const addTickerFromSuggestion = (t: {name: string; symbol: string}) => {
    if (tickers.find(x => x.symbol === t.symbol)) return
    setTickers(prev => [...prev, { name: t.name, symbol: t.symbol }])
    setTickerInput(''); setTickerSuggestions([]); setShowTickerSug(false); markDirty()
  }

  const addTicker = () => {
    const raw = tickerInput.trim().toUpperCase()
    if (!raw) return
    if (tickerSuggestions.length > 0) { addTickerFromSuggestion(tickerSuggestions[0]); return }
    const parts = raw.split(/\s+/)
    const symbol = parts[parts.length - 1]
    const name = parts.length > 1 ? parts.slice(0,-1).join(' ') : symbol
    if (tickers.find(t => t.symbol === symbol)) return
    setTickers(prev => [...prev, { name, symbol }]); setTickerInput(''); markDirty()
  }

  // ── Local News logic ────────────────────────────────────────────────────────
  const onLocCityChange = (val: string) => {
    const v = toTitleCase(val); setLocCity(v)
    if (val.trim()) { setLocSuggestions(searchLocations(val.trim())); setShowLocSug(true) }
    else { setLocSuggestions([]); setShowLocSug(false) }
    markDirty()
  }
  const onLocCountryChange = (val: string) => {
    const v = toTitleCase(val); setLocCountry(v)
    if (val.trim()) {
      setLocSuggestions(searchLocations(val.trim()).filter(l => l.country.toLowerCase().includes(val.trim().toLowerCase())))
      setShowLocSug(true)
    } else { setLocSuggestions([]); setShowLocSug(false) }
    markDirty()
  }
  const applyLocSuggestion = (loc: Location) => {
    setLocCity(loc.city); setLocCountry(loc.country); setLocSuggestions([]); setShowLocSug(false)
  }
  const addLocation = () => {
    const city = locCity.trim(), state = locState.trim().toUpperCase(), country = locCountry.trim()
    if (!city && !country) return
    setLocalLocations(prev => [...prev, { city, state, country }])
    setLocCity(''); setLocState(''); setLocCountry(''); setLocSuggestions([]); setShowLocSug(false); markDirty()
  }

  // ── World News logic ────────────────────────────────────────────────────────
  const onWorldInput = (val: string) => {
    const v = toTitleCase(val); setWorldInput(v)
    if (val.trim()) { setWorldSuggestions(searchCountries(val.trim())); setShowWorldSug(true) }
    else { setWorldSuggestions([]); setShowWorldSug(false) }
    markDirty()
  }
  const addWorldCountry = (country?: string) => {
    const c = (country ?? worldInput).trim()
    if (!c) return
    if (worldCountries.find(x => x.toLowerCase() === c.toLowerCase())) return
    setWorldCountries(prev => [...prev, toTitleCase(c)])
    setWorldInput(''); setWorldSuggestions([]); setShowWorldSug(false); markDirty()
  }

  const typeLabel = (type: string) => {
    if (type === 'CRYPTOCURRENCY' || type === 'Crypto') return 'Crypto'
    if (type === 'Commodity') return 'Commodity'
    if (type === 'Forex') return 'Forex'
    if (type === 'Index') return 'Index'
    if (type === 'ETF') return 'ETF'
    return 'Stock'
  }

  // ── Section collapse state ───────────────────────────────────────────────────
  const [openEmail,    setOpenEmail]    = useState(true)
  const [openSchedule, setOpenSchedule] = useState(true)
  const [openTickers,  setOpenTickers]  = useState(true)
  const [openSocial,   setOpenSocial]   = useState(false)
  const [openCats,     setOpenCats]     = useState(true)

  const { panelCollapse } = useStore()
  useEffect(() => {
    if (panelCollapse === null) return
    setOpenEmail(!panelCollapse)
    setOpenSchedule(!panelCollapse)
    setOpenTickers(!panelCollapse)
    setOpenSocial(!panelCollapse)
    setOpenCats(!panelCollapse)
  }, [panelCollapse])

  const CollapseBtn = ({ open, toggle }: { open: boolean; toggle: () => void }) => (
    <button onClick={toggle}
      className="ml-auto text-slate-400 hover:text-slate-200 transition-colors p-1 rounded-lg hover:bg-slate-700">
      <span style={{ display:'inline-block', transform: open ? 'rotate(180deg)' : 'rotate(0deg)', transition:'transform 0.2s' }}>▼</span>
    </button>
  )

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6">

      {/* ── Email ── */}
      <Card accent="#6366f1">
        <div className="flex items-center mb-4">
          <h2 className="text-slate-200 font-semibold text-lg">
            Email Settings
            <InfoTooltip text="Add one or more recipient addresses. The digest is sent to all of them." />
          </h2>
          <CollapseBtn open={openEmail} toggle={() => setOpenEmail(o => !o)} />
        </div>

        {openEmail && (<>
          {emails.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-3">
              {emails.map(e => (
                <span key={e} className="flex items-center gap-1.5 bg-slate-700 border border-slate-600 text-slate-200 text-sm px-3 py-1.5 rounded-full">
                  <span className="text-xs">✉</span>
                  <span>{e}</span>
                  <button onClick={() => { setEmails(prev => prev.filter(x => x !== e)); markDirty() }}
                    className="text-slate-500 hover:text-red-400 transition-colors ml-1 text-xs">✕</button>
                </span>
              ))}
            </div>
          )}
          <div className="flex gap-2 mb-4">
            <input type="email" value={emailInput}
              onChange={e => setEmailInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addEmail() } }}
              placeholder="you@example.com"
              className="flex-1 bg-slate-700 border border-slate-600 text-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-indigo-500 transition-colors"
            />
            <button onClick={addEmail}
              className="bg-indigo-700 hover:bg-indigo-600 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-colors whitespace-nowrap">
              + Add Email
            </button>
          </div>
          <button
            onClick={async () => {
              setTesting(true)
              try { await testEmail(); toast.success('Test email sent!') }
              catch { toast.error('Test email failed.') }
              finally { setTesting(false) }
            }}
            disabled={testing || emails.length === 0}
            className="flex items-center gap-2 bg-slate-700 hover:bg-slate-600 disabled:opacity-40 text-slate-200 text-sm font-medium px-4 py-2.5 rounded-xl transition-colors border border-slate-600"
          >
            {testing && <Spinner size={14} />}
            {testing ? 'Sending…' : '✉ Send Test Email'}
          </button>
        </>)}
      </Card>

      {/* ── Schedule ── */}
      <Card accent="#8b5cf6">
        <div className="flex items-center mb-4">
          <h2 className="text-slate-200 font-semibold text-lg">
            ⏰ Schedule
            <InfoTooltip text="Choose which days and time to automatically receive your digest email." />
          </h2>
          <CollapseBtn open={openSchedule} toggle={() => setOpenSchedule(o => !o)} />
        </div>
        {openSchedule && <div className="space-y-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-200 text-sm font-medium">Enable automatic runs</p>
              <p className="text-slate-500 text-xs mt-0.5">Send digest on a fixed schedule</p>
            </div>
            <button onClick={() => { setScheduleEnabled(e => !e); markDirty() }}
              className={`relative w-12 h-6 rounded-full transition-colors ${scheduleEnabled ? 'bg-indigo-600' : 'bg-slate-600'}`}>
              <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${scheduleEnabled ? 'translate-x-6' : 'translate-x-0'}`} />
            </button>
          </div>

          {scheduleEnabled && (<>
            <div>
              <label className="block text-slate-400 text-xs font-semibold uppercase tracking-wider mb-3">Days</label>
              <div className="flex gap-2">
                {DAYS.map((d, i) => (
                  <button key={i}
                    onClick={() => { setSelectedDays(prev => prev.includes(d.value) ? prev.filter(x => x !== d.value) : [...prev, d.value]); markDirty() }}
                    className={`w-9 h-9 rounded-full text-sm font-semibold transition-all ${selectedDays.includes(d.value) ? 'bg-indigo-600 text-white shadow-md' : 'bg-slate-700 text-slate-400 hover:bg-slate-600'}`}>
                    {d.label}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-slate-400 text-xs font-semibold uppercase tracking-wider mb-2">
                Time (local)
                <InfoTooltip text="Uses your computer's timezone automatically." />
              </label>
              <input type="time" value={scheduleTime} onChange={e => { setScheduleTime(e.target.value); markDirty() }}
                className="bg-slate-700 border border-slate-600 text-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-indigo-500 transition-colors" />
            </div>
          </>)}

          <div>
            <label className="block text-slate-400 text-xs font-semibold uppercase tracking-wider mb-2">
              Articles per category
              <InfoTooltip text="How many article links appear per topic in each email. Max 10." />
            </label>
            <input type="number" min={1} max={10} value={(form.articles_per_category as number) || 5}
              onChange={e => set('articles_per_category', parseInt(e.target.value))}
              className="w-32 bg-slate-700 border border-slate-600 text-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-indigo-500 transition-colors" />
          </div>
        </div>}
      </Card>

      {/* ── Market Tickers ── */}
      <Card accent="#22c55e">
        <div className="flex items-center mb-1">
          <h2 className="text-slate-200 font-semibold text-lg">
            📈 Market Tickers
            <InfoTooltip text="Add stock, crypto, ETF, commodity or forex symbols. Each gets its own news section in your digest." />
          </h2>
          <CollapseBtn open={openTickers} toggle={() => setOpenTickers(o => !o)} />
        </div>
        {openTickers && <>
        <p className="text-slate-500 text-sm mb-4">News about these assets will appear in your digest.</p>
        <div className="flex flex-wrap gap-2 mb-3">
          {tickers.map(t => (
            <span key={t.symbol} className="flex items-center gap-1.5 bg-slate-700 border border-slate-600 text-slate-200 text-sm px-3 py-1.5 rounded-full">
              {t.name !== t.symbol && <span className="font-medium">{t.name}</span>}
              <span className="text-slate-400 text-xs font-mono">{t.symbol}</span>
              <button onClick={() => { setTickers(prev => prev.filter(x => x.symbol !== t.symbol)); markDirty() }}
                className="text-slate-500 hover:text-red-400 transition-colors ml-1 text-xs">✕</button>
            </span>
          ))}
        </div>
        <div className="relative" ref={tickerRef}>
          <div className="flex gap-2">
            <input type="text" value={tickerInput}
              onChange={e => onTickerInput(e.target.value)}
              onFocus={() => tickerInput && setShowTickerSug(true)}
              onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addTicker() } if (e.key === 'Escape') setShowTickerSug(false) }}
              placeholder="Type a company name or ticker symbol…"
              className="flex-1 bg-slate-700 border border-slate-600 text-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-green-500 transition-colors placeholder-slate-500"
            />
            <button onClick={addTicker}
              className="bg-green-700 hover:bg-green-600 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-colors whitespace-nowrap">
              + Add
            </button>
          </div>
          <p className="text-slate-600 text-xs mt-1.5">Suggestions appear instantly from local list; rare symbols search online.</p>
          {showTickerSug && (tickerLoading || tickerSuggestions.length > 0) && (
            <div className="absolute z-50 left-0 right-12 mt-1 bg-slate-800 border border-slate-600 rounded-xl shadow-xl overflow-hidden">
              {tickerLoading
                ? <div className="px-4 py-3 text-slate-400 text-sm">Searching…</div>
                : tickerSuggestions.map(s => (
                  <button key={s.symbol} onMouseDown={e => { e.preventDefault(); addTickerFromSuggestion(s) }}
                    className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-slate-700 transition-colors text-left">
                    <span className="text-slate-200 text-sm font-medium">{s.name}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-green-400 text-xs font-mono font-bold">{s.symbol}</span>
                      <span className="text-slate-600 text-xs">{typeLabel(s.type)}</span>
                    </div>
                  </button>
                ))
              }
            </div>
          )}
        </div>
        </>}
      </Card>

      {/* ── Social Refresh ── */}
      <Card accent="#0ea5e9">
        <div className="flex items-center mb-4">
          <h2 className="text-slate-200 font-semibold text-lg">
            Social & Market Data
            <InfoTooltip text="How often Reddit, YouTube, and Prediction Market data is refreshed. Separate from your email schedule." />
          </h2>
          <CollapseBtn open={openSocial} toggle={() => setOpenSocial(o => !o)} />
        </div>
        {openSocial && <div>
          <label className="block text-slate-400 text-sm mb-1.5">
            Refresh every (hours)
            <InfoTooltip text="How often social and market data is re-analyzed. Does not affect your email schedule." />
          </label>
          <input type="number" min={1} max={48} value={(form.social_refresh_hours as number) || 24}
            onChange={e => set('social_refresh_hours', parseInt(e.target.value))}
            className="w-32 bg-slate-700 border border-slate-600 text-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-indigo-500 transition-colors" />
        </div>}
      </Card>

      {/* ── Categories ── */}
      <Card accent="#f59e0b">
        <div className="flex items-center mb-2">
          <h2 className="text-slate-200 font-semibold text-lg">
            News Categories
            <InfoTooltip text="Topics included in your digest. Toggle to enable/disable. You can also add custom categories." />
          </h2>
          <CollapseBtn open={openCats} toggle={() => setOpenCats(o => !o)} />
        </div>
        {openCats && <>
        <p className="text-slate-400 text-sm mb-4">Select which topics to include in your digest.</p>

        {/* Default + custom category toggles */}
        <div className="flex flex-wrap gap-2 mb-4">
          {Array.from(new Set([...DEFAULT_CATEGORIES, ...categories.filter(c => !DEFAULT_CATEGORIES.includes(c))])).map(cat => (
            <button key={cat} onClick={() => toggleCategory(cat)}
              className={`px-4 py-2 rounded-xl text-sm font-medium transition-all border ${categories.includes(cat) ? 'bg-indigo-600 border-indigo-500 text-white' : 'bg-slate-700 border-slate-600 text-slate-400 hover:border-slate-500 hover:text-slate-300'}`}>
              {cat}
            </button>
          ))}
        </div>

        {/* Add custom category */}
        <div className="flex gap-2 mb-6">
          <input
            type="text"
            spellCheck={true}
            value={customCatInput}
            onChange={e => setCustomCatInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addCustomCategory() } }}
            placeholder="Add custom category (e.g. Real Estate, Fashion…)"
            className="flex-1 bg-slate-700 border border-slate-600 text-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-amber-500 transition-colors placeholder-slate-500"
          />
          <button onClick={addCustomCategory} disabled={addingCat || customCatInput.trim().length < 2}
            className="bg-amber-600 hover:bg-amber-500 disabled:opacity-40 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-colors whitespace-nowrap">
            {addingCat ? <Spinner size={14} /> : '+ Add Category'}
          </button>
        </div>
        <p className="text-slate-600 text-xs -mt-4 mb-4">Browser spell-check is active — underlined words may be misspelled.</p>

        {/* ── World News countries ── */}
        {openCats && categories.includes('World News') && (
          <div className="border-t border-slate-700 pt-4 mb-4">
            <p className="text-slate-400 text-sm mb-3">
              🌍 Focus countries for World News
              <InfoTooltip text="Add specific countries to get dedicated sections alongside general world news. Leave empty for general world news only." />
            </p>
            {worldCountries.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-3">
                {worldCountries.map((c, i) => (
                  <span key={i} className="flex items-center gap-1.5 bg-slate-700 border border-slate-600 text-slate-200 text-sm px-3 py-1.5 rounded-full">
                    <span className="text-xs">🌍</span><span>{c}</span>
                    <button onClick={() => { setWorldCountries(prev => prev.filter((_,j) => j !== i)); markDirty() }}
                      className="text-slate-500 hover:text-red-400 transition-colors ml-1 text-xs">✕</button>
                  </span>
                ))}
              </div>
            )}
            <div className="relative" ref={worldRef}>
              <div className="flex gap-2">
                <input type="text" value={worldInput} onChange={e => onWorldInput(e.target.value)}
                  onFocus={() => worldInput.trim() && setShowWorldSug(true)}
                  onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addWorldCountry() } if (e.key === 'Escape') setShowWorldSug(false) }}
                  placeholder="Type a country name…"
                  className="flex-1 bg-slate-700 border border-slate-600 text-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-sky-500 transition-colors placeholder-slate-500"
                />
                <button onClick={() => addWorldCountry()}
                  className="bg-sky-700 hover:bg-sky-600 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-colors whitespace-nowrap">
                  + Add Country
                </button>
              </div>
              {showWorldSug && worldSuggestions.length > 0 && (
                <div className="absolute z-50 left-0 right-36 mt-1 bg-slate-800 border border-slate-600 rounded-xl shadow-xl overflow-hidden">
                  {worldSuggestions.map(c => (
                    <button key={c} onMouseDown={e => { e.preventDefault(); addWorldCountry(c) }}
                      className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-slate-700 transition-colors text-left">
                      <span className="text-xs">🌍</span>
                      <span className="text-slate-200 text-sm">{c}</span>
                    </button>
                  ))}
                </div>
              )}
              <p className="text-slate-600 text-xs mt-1.5">General world news always runs. Each added country gets its own additional section.</p>
            </div>
          </div>
        )}

        {/* ── Local News locations ── */}
        {openCats && categories.includes('Local News') && (
          <div className="border-t border-slate-700 pt-4">
            <p className="text-slate-400 text-sm mb-3">
              📍 Local News locations
              <InfoTooltip text="Each location gets its own section. International: City + Country. US: City + State." />
            </p>
            {localLocations.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-3">
                {localLocations.map((loc, i) => {
                  const label = [loc.city, loc.state, loc.country].filter(Boolean).join(', ')
                  return (
                    <span key={i} className="flex items-center gap-1.5 bg-slate-700 border border-slate-600 text-slate-200 text-sm px-3 py-1.5 rounded-full">
                      <span className="text-xs">📍</span><span>{label}</span>
                      <button onClick={() => { setLocalLocations(prev => prev.filter((_,j) => j !== i)); markDirty() }}
                        className="text-slate-500 hover:text-red-400 transition-colors ml-1 text-xs">✕</button>
                    </span>
                  )
                })}
              </div>
            )}
            <div className="relative" ref={locRef}>
              <div className="flex gap-2 flex-wrap items-end">
                <div className="flex-1 min-w-[110px]">
                  <label className="block text-slate-500 text-xs mb-1.5">City</label>
                  <input type="text" value={locCity} onChange={e => onLocCityChange(e.target.value)}
                    onFocus={() => locCity.trim() && setShowLocSug(true)}
                    onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addLocation() } if (e.key === 'Escape') setShowLocSug(false) }}
                    placeholder="e.g. Warsaw"
                    className="w-full bg-slate-700 border border-slate-600 text-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-amber-500 transition-colors"
                  />
                </div>
                <div className="w-20">
                  <label className="block text-slate-500 text-xs mb-1.5">US State</label>
                  <input type="text" value={locState} onChange={e => { setLocState(e.target.value.toUpperCase()); markDirty() }}
                    placeholder="NY" maxLength={2}
                    className="w-full bg-slate-700 border border-slate-600 text-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-amber-500 transition-colors uppercase"
                  />
                </div>
                <div className="flex-1 min-w-[110px]">
                  <label className="block text-slate-500 text-xs mb-1.5">Country</label>
                  <input type="text" value={locCountry} onChange={e => onLocCountryChange(e.target.value)}
                    onFocus={() => locCountry.trim() && setShowLocSug(true)}
                    onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addLocation() } if (e.key === 'Escape') setShowLocSug(false) }}
                    placeholder="e.g. Poland"
                    className="w-full bg-slate-700 border border-slate-600 text-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-amber-500 transition-colors"
                  />
                </div>
                <button onClick={addLocation}
                  className="bg-amber-600 hover:bg-amber-500 text-white text-sm font-medium px-4 py-2 rounded-xl transition-colors whitespace-nowrap">
                  + Add Location
                </button>
              </div>
              {showLocSug && locSuggestions.length > 0 && (
                <div className="absolute z-50 left-0 right-36 mt-1 bg-slate-800 border border-slate-600 rounded-xl shadow-xl overflow-hidden">
                  {locSuggestions.map((s, i) => (
                    <button key={i} onMouseDown={e => { e.preventDefault(); applyLocSuggestion(s) }}
                      className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-slate-700 transition-colors text-left">
                      <span className="text-xs">📍</span>
                      <span className="text-slate-200 text-sm font-medium">{s.city}</span>
                      <span className="text-slate-500 text-xs">{s.country}</span>
                    </button>
                  ))}
                </div>
              )}
              <p className="text-slate-600 text-xs mt-2">Each location runs concurrently and gets its own section in the digest.</p>
            </div>
          </div>
        )}
        </>}
      </Card>

      {/* ── Save ── */}
      <div className="flex justify-end">
        <button onClick={handleSave} disabled={saving}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold px-6 py-3 rounded-xl transition-colors shadow-md">
          {saving && <Spinner size={16} />}
          {saving ? 'Saving…' : '💾 Save Settings'}
        </button>
      </div>
    </div>
  )
}
