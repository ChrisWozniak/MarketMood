import { useState, useEffect, useRef } from 'react'
import toast from 'react-hot-toast'
import { getLatestSentiment, analyzeSentiment, getLatestSignals } from '../../api'
import { useStore } from '../../store'
import Card from '../Card'
import Spinner from '../Spinner'
import InfoTooltip from '../InfoTooltip'
import TrendingTopics from './TrendingTopics'
import MoodGauge from './MoodGauge'
import MarketPulse from './MarketPulse'

// ── Types ──────────────────────────────────────────────────────────────────

interface MoodScore {
  score: number
  label: string
  dominant_emotions?: string[]
}

interface InvestmentSignal {
  category: string
  signal: 'bullish' | 'bearish' | 'neutral'
  insight: string
  tickers: string[]
  confidence: 'high' | 'medium' | 'low'
}

interface TechMomentumItem {
  technology: string
  direction: 'rising' | 'declining' | 'stable'
  momentum_score: number
  insight: string
  key_companies: string[]
  proxy_tickers: string[]
}


// ── Constants ──────────────────────────────────────────────────────────────

const ANALYSIS_STAGES = [
  { delay: 0,     msg: 'Connecting to Reddit & Hacker News…' },
  { delay: 6000,  msg: 'Fetching trending posts…' },
  { delay: 14000, msg: 'Scoring sentiment with Gemini…' },
  { delay: 28000, msg: 'Generating investment signals…' },
  { delay: 45000, msg: 'Calculating tech momentum…' },
  { delay: 70000, msg: 'Still working, please be patient…' },
]

const SIGNAL_STYLES = {
  bullish: { badge: 'bg-emerald-950 text-emerald-400 border border-emerald-800', dot: 'bg-emerald-400', label: '▲ Bullish' },
  bearish: { badge: 'bg-red-950 text-red-400 border border-red-800',           dot: 'bg-red-400',     label: '▼ Bearish' },
  neutral: { badge: 'bg-slate-800 text-slate-400 border border-slate-700',     dot: 'bg-slate-400',   label: '● Neutral' },
}

const CONFIDENCE_STYLES = {
  high:   'text-indigo-400',
  medium: 'text-amber-400',
  low:    'text-slate-300',
}

const DIRECTION_STYLES = {
  rising:   { icon: '↑', color: 'text-emerald-400' },
  declining:{ icon: '↓', color: 'text-red-400' },
  stable:   { icon: '→', color: 'text-slate-300' },
}

// ── Sub-components ─────────────────────────────────────────────────────────

function CollapseButton({ open, onClick }: { open: boolean; onClick: () => void }) {
  return (
    <button
      onClick={e => { e.stopPropagation(); onClick() }}
      className="text-slate-400 hover:text-slate-200 transition-colors p-1 rounded-lg hover:bg-slate-700 shrink-0"
      title={open ? 'Collapse' : 'Expand'}
    >
      <span style={{ display: 'inline-block', transform: open ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}>
        ▼
      </span>
    </button>
  )
}

function SignalCard({ signal }: { signal: InvestmentSignal }) {
  const style = SIGNAL_STYLES[signal.signal]
  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4 space-y-2">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <span className="text-slate-200 font-medium text-sm">{signal.category}</span>
        <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${style.badge}`}>
          {style.label}
        </span>
      </div>
      <p className="text-slate-300 text-xs leading-relaxed">{signal.insight}</p>
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex gap-1 flex-wrap">
          {signal.tickers.map(t => (
            <span key={t} className="text-xs font-mono bg-slate-700 text-slate-300 px-1.5 py-0.5 rounded">
              {t}
            </span>
          ))}
        </div>
        <span className={`text-xs font-medium ${CONFIDENCE_STYLES[signal.confidence]}`}>
          {signal.confidence} confidence
        </span>
      </div>
    </div>
  )
}


function MomentumRow({ item }: { item: TechMomentumItem }) {
  const dir = DIRECTION_STYLES[item.direction]
  return (
    <div className="space-y-1.5 py-3 border-b border-slate-800 last:border-0">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className={`text-base font-bold ${dir.color}`}>{dir.icon}</span>
          <span className="text-slate-200 font-medium text-sm">{item.technology}</span>
        </div>
        <span className="text-slate-400 text-xs">{item.momentum_score}/100</span>
      </div>
      {/* Momentum bar */}
      <div className="w-full h-1 bg-slate-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${
            item.direction === 'rising' ? 'bg-emerald-500' :
            item.direction === 'declining' ? 'bg-red-500' : 'bg-slate-500'
          }`}
          style={{ width: `${item.momentum_score}%` }}
        />
      </div>
      <p className="text-slate-400 text-xs leading-relaxed">{item.insight}</p>
      <div className="flex gap-1 flex-wrap">
        {item.proxy_tickers.map(t => (
          <span key={t} className="text-xs font-mono bg-slate-700 text-slate-300 px-1.5 py-0.5 rounded">
            {t}
          </span>
        ))}
        {item.key_companies.map(c => (
          <span key={c} className="text-xs bg-slate-800 text-slate-300 border border-slate-700 px-1.5 py-0.5 rounded">
            {c}
          </span>
        ))}
      </div>
    </div>
  )
}

// ── Main Component ─────────────────────────────────────────────────────────

export default function SocialDashboard() {
  const [data, setData]           = useState<Record<string, unknown> | null>(null)
  const [signals, setSignals]     = useState<{ investment_signals: InvestmentSignal[]; tech_momentum: TechMomentumItem[] } | null>(null)
  const [loading, setLoading]     = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [stageMsg, setStageMsg]   = useState('')

  const [moodOpen,     setMoodOpen]     = useState(true)   // open on fresh start
  const [signalsOpen,  setSignalsOpen]  = useState(false)
  const [momentumOpen, setMomentumOpen] = useState(false)
  const [topicsOpen,   setTopicsOpen]   = useState(false)
  const [marketsOpen,  setMarketsOpen]  = useState(false)

  const { panelCollapse } = useStore()
  useEffect(() => {
    if (panelCollapse === null) return
    setMoodOpen(!panelCollapse)
    setSignalsOpen(!panelCollapse)
    setMomentumOpen(!panelCollapse)
    setTopicsOpen(!panelCollapse)
    setMarketsOpen(!panelCollapse)
  }, [panelCollapse])

  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([])

  const clearStageTimers = () => {
    timersRef.current.forEach(t => clearTimeout(t))
    timersRef.current = []
  }

  const startStageMessages = () => {
    clearStageTimers()
    ANALYSIS_STAGES.forEach(({ delay, msg }) => {
      const t = setTimeout(() => setStageMsg(msg), delay)
      timersRef.current.push(t)
    })
  }

  const loadAll = () => {
    setLoading(true)
    Promise.all([
      getLatestSentiment().catch(() => null),
      getLatestSignals().catch(() => null),
    ]).then(([sentiment, sigs]) => {
      setData(sentiment)
      setSignals(sigs)
    }).finally(() => setLoading(false))
  }

  useEffect(() => { loadAll() }, [])

  const handleAnalyze = async () => {
    setAnalyzing(true)
    setStageMsg(ANALYSIS_STAGES[0].msg)
    startStageMessages()
    try {
      await analyzeSentiment()
      toast.success('Analysis complete!')
      loadAll()
    } catch {
      toast.error('Analysis failed.')
    } finally {
      clearStageTimers()
      setAnalyzing(false)
      setStageMsg('')
    }
  }

  const moodScores  = (data?.mood_scores as Record<string, MoodScore>) || {}
  const trendingTopics = (data?.trending_topics as unknown[]) || []
  const investmentSignals = signals?.investment_signals || []
  const techMomentum      = signals?.tech_momentum || []


  return (
    <div className="space-y-6">

      {/* ── Header ── */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-slate-200 font-semibold text-lg">Market Mood</h2>
          {data && !analyzing && (
            <p className="text-slate-300 text-xs mt-0.5">
              Last updated: {new Date((data.captured_at as string) + 'Z').toLocaleString()}
            </p>
          )}
          <div aria-live="assertive" aria-atomic="true">
            {analyzing && stageMsg && (
              <p className="text-indigo-400 text-xs mt-0.5 animate-pulse">{stageMsg}</p>
            )}
          </div>
        </div>
        <button
          onClick={handleAnalyze}
          disabled={analyzing}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-colors"
        >
          {analyzing ? <Spinner size={14} hidden /> : '⚡'}
          {analyzing ? 'Working…' : 'Refresh Now'}
        </button>
      </div>

      {analyzing && (
        <div className="w-full h-1 bg-slate-800 rounded-full overflow-hidden">
          <div className="h-full bg-indigo-500 rounded-full animate-pulse" style={{ width: '100%' }} />
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-16"><Spinner size={36} label="Loading dashboard data" /></div>
      ) : !data ? (
        <Card>
          <div className="text-center py-8">
            <p className="text-slate-400 mb-4">No data yet. Run your first analysis to see sentiment, signals, and momentum.</p>
            <button
              onClick={handleAnalyze}
              disabled={analyzing}
              className="flex items-center gap-2 mx-auto bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-xl transition-colors"
            >
              {analyzing && <Spinner size={14} hidden />}
              {analyzing ? 'Working…' : '⚡ Run Analysis'}
            </button>
          </div>
        </Card>
      ) : (
        <>
          {/* ── Social Mood Barometer ── */}
          {Object.keys(moodScores).length > 0 && (
            <Card accent="#6366f1">
              <button type="button" className="w-full flex items-center justify-between mb-1 cursor-pointer group text-left hover:opacity-80 transition-opacity" onClick={() => setMoodOpen(o => !o)} aria-expanded={moodOpen} aria-controls="mood-content">
                <h3 className="text-slate-200 font-semibold md:group-hover:text-lg transition-all duration-200 flex items-center gap-1">
                  Social Mood
                  <span onClick={e => e.stopPropagation()}><InfoTooltip text="Sentiment score from -100 (very negative) to +100 (very positive), scored by Gemini Flash from Reddit, Hacker News, YouTube, FRED, and Redfin." /></span>
                </h3>
                <CollapseButton open={moodOpen} onClick={() => {}} />
              </button>
              {moodOpen && (
                <div id="mood-content">
                  <p className="text-slate-300 text-xs mb-4">Crowd sentiment per category — scored by Gemini AI from live social posts</p>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {Object.entries(moodScores).map(([cat, mood]) => (
                      <MoodGauge key={cat} category={cat} data={mood} />
                    ))}
                  </div>
                </div>
              )}
            </Card>
          )}

          {/* ── Investment Signals ── */}
          {investmentSignals.length > 0 && (
            <Card accent="#22c55e">
              <button type="button" className="w-full flex items-center justify-between mb-1 cursor-pointer group text-left hover:opacity-80 transition-opacity" onClick={() => setSignalsOpen(o => !o)} aria-expanded={signalsOpen} aria-controls="signals-content">
                <h3 className="text-slate-200 font-semibold md:group-hover:text-lg transition-all duration-200 flex items-center gap-1">
                  Investment Signals
                  <span onClick={e => e.stopPropagation()}><InfoTooltip text="Gemini Pro synthesizes social mood, prediction market probabilities, and housing data into sector and ticker signals. Informational only — not financial advice." /></span>
                </h3>
                <CollapseButton open={signalsOpen} onClick={() => {}} />
              </button>
              {signalsOpen && (
                <div id="signals-content">
                  <p className="text-slate-300 text-xs mb-4">AI-generated market implications based on current social sentiment — not financial advice</p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {investmentSignals.map(sig => (
                      <SignalCard key={sig.category} signal={sig} />
                    ))}
                  </div>
                </div>
              )}
            </Card>
          )}

          {/* ── Tech Momentum ── */}
          {techMomentum.length > 0 && (
            <Card accent="#f59e0b">
              <button type="button" className="w-full flex items-center justify-between mb-1 cursor-pointer group text-left hover:opacity-80 transition-opacity" onClick={() => setMomentumOpen(o => !o)} aria-expanded={momentumOpen} aria-controls="momentum-content">
                <h3 className="text-slate-200 font-semibold md:group-hover:text-lg transition-all duration-200 flex items-center gap-1">
                  Tech Momentum
                  <span onClick={e => e.stopPropagation()}><InfoTooltip text="Which technologies and companies are gaining or losing developer mindshare, based on social discussion patterns." /></span>
                </h3>
                <CollapseButton open={momentumOpen} onClick={() => {}} />
              </button>
              {momentumOpen && (
                <div id="momentum-content">
                  <p className="text-slate-300 text-xs mb-4">Rising and declining technologies based on social discussion volume and sentiment</p>
                  <div>
                    {techMomentum.map(item => (
                      <MomentumRow key={item.technology} item={item} />
                    ))}
                  </div>
                </div>
              )}
            </Card>
          )}

          {/* ── Trending Topics ── */}
          <Card accent="#818cf8">
            <button type="button" className="w-full flex items-center justify-between mb-1 cursor-pointer group text-left hover:opacity-80 transition-opacity" onClick={() => setTopicsOpen(o => !o)} aria-expanded={topicsOpen} aria-controls="topics-content">
              <h3 className="text-slate-200 font-semibold md:group-hover:text-lg transition-all duration-200 flex items-center gap-1">
                Trending Topics
                <span onClick={e => e.stopPropagation()}><InfoTooltip text="Most discussed subjects ranked by engagement volume across Reddit and Hacker News." /></span>
              </h3>
              <CollapseButton open={topicsOpen} onClick={() => {}} />
            </button>
            {topicsOpen && (
              <div id="topics-content">
                <p className="text-slate-500 text-xs mb-4">% bar = relative engagement vs. top topic — click any row to expand subtopics</p>
                <TrendingTopics topics={trendingTopics as Parameters<typeof TrendingTopics>[0]['topics']} />
              </div>
            )}
          </Card>

          {/* ── Prediction Markets ── */}
          <MarketPulse collapsed={!marketsOpen} onToggleCollapse={() => setMarketsOpen(o => !o)} />
        </>
      )}
    </div>
  )
}
