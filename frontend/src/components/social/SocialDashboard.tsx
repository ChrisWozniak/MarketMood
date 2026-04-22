import { useState, useEffect, useRef } from 'react'
import toast from 'react-hot-toast'
import { getLatestSentiment, analyzeSentiment, getLatestSignals } from '../../api'
import { useStore } from '../../store'
import Card from '../Card'
import Spinner from '../Spinner'
import InfoTooltip from '../InfoTooltip'
import TrendingTopics from './TrendingTopics'
import MarketPulse from './MarketPulse'
import CategoryBarometer from './CategoryBarometer'
import InvestmentSignal, { type InvestmentSignalData } from './InvestmentSignal'
import TechMomentum, { type TechMomentumItem } from './TechMomentum'

// ── Types ──────────────────────────────────────────────────────────────────

interface MoodScore {
  score: number
  label: string
  dominant_emotions?: string[]
  polarization_level?: number
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

// ── Sub-components ─────────────────────────────────────────────────────────

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <span
      aria-hidden="true"
      className="text-slate-400 p-1 shrink-0"
      style={{ display: 'inline-block', transform: open ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}
    >
      ▼
    </span>
  )
}

// ── Main Component ─────────────────────────────────────────────────────────

export default function SocialDashboard() {
  const [data, setData]           = useState<Record<string, unknown> | null>(null)
  const [signals, setSignals]     = useState<{ investment_signals: InvestmentSignalData[]; tech_momentum: TechMomentumItem[] } | null>(null)
  const [loading, setLoading]     = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [stageMsg, setStageMsg]   = useState('')

  const [moodOpen,     setMoodOpen]     = useState(true)
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

  const moodScores        = (data?.mood_scores as Record<string, MoodScore>) || {}
  const trendingTopics    = (data?.trending_topics as unknown[]) || []
  const investmentSignals = signals?.investment_signals || []
  const techMomentum      = signals?.tech_momentum || []

  return (
    <div className="space-y-6" aria-busy={loading}>

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
          type="button"
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
              type="button"
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
                <ChevronIcon open={moodOpen} />
              </button>
              {moodOpen && (
                <div id="mood-content">
                  <p className="text-slate-300 text-xs mb-4">Click any category to see investment signals and tickers</p>
                  <div className="space-y-2">
                    {Object.entries(moodScores).map(([cat, mood]) => {
                      const sig = investmentSignals.find(s => s.category === cat)
                      return (
                        <CategoryBarometer
                          key={cat}
                          category={cat}
                          data={mood}
                          signal={sig ? { signal: sig.signal, insight: sig.insight, tickers: sig.tickers, confidence: sig.confidence } : undefined}
                        />
                      )
                    })}
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
                <ChevronIcon open={signalsOpen} />
              </button>
              {signalsOpen && (
                <div id="signals-content">
                  <p className="text-slate-300 text-xs mb-4">AI-generated market implications based on current social sentiment — not financial advice</p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {investmentSignals.map(sig => (
                      <InvestmentSignal key={sig.category} signal={sig} />
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
                <ChevronIcon open={momentumOpen} />
              </button>
              {momentumOpen && (
                <div id="momentum-content">
                  <p className="text-slate-300 text-xs mb-4">Rising and declining technologies based on social discussion volume and sentiment</p>
                  <TechMomentum items={techMomentum} />
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
              <ChevronIcon open={topicsOpen} />
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
