import { useState, useEffect, useRef } from 'react'
import toast from 'react-hot-toast'
import { getLatestSocial, analyzeSocial } from '../../api'
import { useStore } from '../../store'
import Card from '../Card'
import Spinner from '../Spinner'
import InfoTooltip from '../InfoTooltip'
import TrendingTopics from './TrendingTopics'
import MoodGauge from './MoodGauge'
import MarketPulse from './MarketPulse'

const ANALYSIS_STAGES = [
  { delay: 0,    msg: 'Connecting to Reddit & Hacker News…' },
  { delay: 6000, msg: 'Fetching trending posts…' },
  { delay: 14000, msg: 'Scoring sentiment with AI…' },
  { delay: 28000, msg: 'Extracting subtopics…' },
  { delay: 45000, msg: 'Almost there, saving results…' },
  { delay: 70000, msg: 'Still working, please be patient…' },
]

function CollapseButton({ open, onClick }: { open: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="text-slate-400 hover:text-slate-200 transition-colors p-1 rounded-lg hover:bg-slate-700"
      title={open ? 'Collapse' : 'Expand'}
    >
      <span
        style={{
          display: 'inline-block',
          transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
          transition: 'transform 0.2s',
        }}
      >
        ▼
      </span>
    </button>
  )
}

export default function SocialDashboard() {
  const [data, setData] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [stageMsg, setStageMsg] = useState('')

  const [moodOpen, setMoodOpen]       = useState(true)
  const [topicsOpen, setTopicsOpen]   = useState(true)
  const [marketsOpen, setMarketsOpen] = useState(true)

  const { panelCollapse } = useStore()
  useEffect(() => {
    if (panelCollapse === null) return
    setMoodOpen(!panelCollapse)
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

  const load = () => {
    setLoading(true)
    getLatestSocial()
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleAnalyze = async () => {
    setAnalyzing(true)
    setStageMsg(ANALYSIS_STAGES[0].msg)
    startStageMessages()
    try {
      await analyzeSocial()
      toast.success('Social analysis complete!')
      load()
    } catch {
      toast.error('Analysis failed.')
    } finally {
      clearStageTimers()
      setAnalyzing(false)
      setStageMsg('')
    }
  }

  const moodScores = data?.mood_scores as Record<string, { score: number; label: string; dominant_emotions?: string[] }> || {}
  const trendingTopics = (data?.trending_topics as unknown[]) || []

  return (
    <div className="space-y-6">
      {/* Header action */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-slate-200 font-semibold text-lg">Social Intelligence</h2>
          {data && !analyzing && (
            <p className="text-slate-500 text-xs mt-0.5">
              Last updated: {new Date((data.captured_at as string) + 'Z').toLocaleString()}
            </p>
          )}
          {analyzing && stageMsg && (
            <p className="text-indigo-400 text-xs mt-0.5 animate-pulse">{stageMsg}</p>
          )}
        </div>
        <button
          onClick={handleAnalyze}
          disabled={analyzing}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-colors"
        >
          {analyzing ? <Spinner size={14} /> : '⚡'}
          {analyzing ? 'Working…' : 'Refresh Now'}
        </button>
      </div>

      {/* Progress bar shown during analysis */}
      {analyzing && (
        <div className="w-full h-1 bg-slate-800 rounded-full overflow-hidden">
          <div className="h-full bg-indigo-500 rounded-full animate-pulse" style={{ width: '100%' }} />
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-16"><Spinner size={36} /></div>
      ) : !data ? (
        <Card>
          <div className="text-center py-8">
            <p className="text-slate-400 mb-4">No social data yet. Run your first analysis to see trends and mood indicators.</p>
            <button
              onClick={handleAnalyze}
              disabled={analyzing}
              className="flex items-center gap-2 mx-auto bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-xl transition-colors"
            >
              {analyzing && <Spinner size={14} />}
              {analyzing ? 'Working…' : '⚡ Run Analysis'}
            </button>
          </div>
        </Card>
      ) : (
        <>
          {/* Mood Gauges */}
          {Object.keys(moodScores).length > 0 && (
            <Card accent="#6366f1">
              <div className="flex items-center justify-between mb-1">
                <h3 className="text-slate-200 font-semibold">
                  Social Mood
                  <InfoTooltip text="Sentiment score from -100 (very negative) to +100 (very positive), based on Reddit and Hacker News post analysis." />
                </h3>
                <CollapseButton open={moodOpen} onClick={() => setMoodOpen(o => !o)} />
              </div>
              {moodOpen && (
                <>
                  <p className="text-slate-500 text-xs mb-4">Crowd sentiment per category — scored by AI from social posts</p>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {Object.entries(moodScores).map(([cat, mood]) => (
                      <MoodGauge key={cat} category={cat} data={mood} />
                    ))}
                  </div>
                </>
              )}
            </Card>
          )}

          {/* Trending Topics */}
          <Card accent="#f59e0b">
            <div className="flex items-center justify-between mb-1">
              <h3 className="text-slate-200 font-semibold">
                Trending Topics
                <InfoTooltip text="Most discussed subjects ranked by engagement volume across Reddit and Hacker News. Click any topic to expand subtopics." />
              </h3>
              <CollapseButton open={topicsOpen} onClick={() => setTopicsOpen(o => !o)} />
            </div>
            {topicsOpen && (
              <>
                <p className="text-slate-500 text-xs mb-4">% bar = relative engagement vs. top topic (100% = most active) — click any row to expand</p>
                <TrendingTopics topics={trendingTopics as Parameters<typeof TrendingTopics>[0]['topics']} />
              </>
            )}
          </Card>

          {/* Prediction Market Pulse */}
          <MarketPulse collapsed={!marketsOpen} onToggleCollapse={() => setMarketsOpen(o => !o)} />
        </>
      )}
    </div>
  )
}
