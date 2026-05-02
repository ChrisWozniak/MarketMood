import { useState } from 'react'
import CategoryDetail from './CategoryDetail'
import { useStore } from '../../store'

interface MoodData {
  score: number
  label: string
  dominant_emotions?: string[]
  polarization_level?: number
}

interface SignalData {
  signal: 'bullish' | 'bearish' | 'neutral'
  insight: string
  tickers: string[]
  confidence: 'high' | 'medium' | 'low'
}

interface Props {
  category: string
  data: MoodData
  signal?: SignalData
  watchlistTickers?: string[]
}

function scoreToColor(score: number): string {
  if (score >= 40)  return '#22c55e'
  if (score >= 10)  return '#84cc16'
  if (score >= -10) return '#f59e0b'
  if (score >= -40) return '#f97316'
  return '#ef4444'
}

const SIGNAL_BADGE: Record<string, string> = {
  bullish: 'bg-emerald-950 text-emerald-400 border border-emerald-800',
  bearish: 'bg-red-950 text-red-400 border border-red-800',
  neutral: 'bg-slate-800 text-slate-400 border border-slate-700',
}

const SIGNAL_ICON: Record<string, string> = {
  bullish: '▲',
  bearish: '▼',
  neutral: '●',
}

export default function CategoryBarometer({ category, data, signal, watchlistTickers }: Props) {
  const [expanded, setExpanded] = useState(false)
  const { darkMode } = useStore()

  const noData = data.score === 0 && data.label === 'Neutral'
    && (!data.dominant_emotions || data.dominant_emotions.length === 0)

  function signalAdjustedScore(score: number, sig?: SignalData): number {
    if (!sig) return score
    if (sig.signal === 'bullish') return Math.max(score, 25)
    if (sig.signal === 'bearish') return Math.min(score, -25)
    return score
  }

  const adjusted = noData ? 0 : signalAdjustedScore(data.score, signal)
  const color    = noData ? '#475569' : scoreToColor(adjusted)
  const position = Math.min(Math.max(((adjusted + 100) / 200) * 100, 2), 98)

  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-xl">
      <button
        type="button"
        onClick={() => setExpanded(o => !o)}
        aria-expanded={expanded}
        aria-label={`${expanded ? 'Collapse' : 'Expand'} ${category} details`}
        className="w-full px-4 pt-3 pb-3 text-left hover:bg-slate-700/30 transition-colors"
      >
        {/* Header row */}
        <div className="flex items-center justify-between mb-2.5">
          <span className="text-slate-200 text-sm font-semibold">{category}</span>
          <div className="flex items-center gap-2">
            {!noData && (
              <span className="text-sm font-bold font-mono" style={{ color }}>
                {data.score > 0 ? '+' : ''}{data.score}
              </span>
            )}
            <span className="text-slate-400 text-xs">{noData ? 'No data' : data.label}</span>
            {signal && (
              <span className={`text-xs px-1.5 py-0.5 rounded-full font-medium border ${SIGNAL_BADGE[signal.signal]}`}>
                {SIGNAL_ICON[signal.signal]} Signal
              </span>
            )}
            <span
              aria-hidden="true"
              className="text-slate-500 text-xs ml-1 transition-transform duration-200"
              style={{ display: 'inline-block', transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)' }}
            >▼</span>
          </div>
        </div>

        {/* Gradient bar */}
        <div
          className="relative h-2.5 rounded-full"
          style={{ background: 'linear-gradient(90deg, #ef4444 0%, #f97316 25%, #f59e0b 50%, #84cc16 75%, #22c55e 100%)' }}
        >
          <div
            className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-4 h-4 rounded-full border-2 border-slate-900 shadow-md"
            style={{ left: `${position}%`, background: color }}
          />
        </div>

        {/* Scale labels */}
        <div className="flex justify-between mt-1 px-0.5">
          <div className="flex flex-col items-start">
            <span className="text-red-500 text-xs">−100</span>
            <span className="text-red-400/70 text-[10px] leading-tight">Max Negative</span>
          </div>
          <span className="text-slate-500 text-xs self-start">0</span>
          <div className="flex flex-col items-end">
            <span className="text-green-600 text-xs">+100</span>
            <span className="text-green-600/70 text-[10px] leading-tight">Max Positive</span>
          </div>
        </div>

        {/* Emotion pills */}
        {!noData && data.dominant_emotions && data.dominant_emotions.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {data.dominant_emotions.slice(0, 4).map(e => (
              <span key={e} className="text-xs bg-slate-700 text-slate-300 px-2 py-0.5 rounded-full capitalize inline-block transition-transform duration-150 hover:scale-125">
                {e}
              </span>
            ))}
          </div>
        )}

        {/* Watchlist ticker pills — color reflects signal direction */}
        {watchlistTickers && watchlistTickers.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {watchlistTickers.map(sym => (
              <a
                key={sym}
                href={`https://finance.yahoo.com/quote/${sym}`}
                target="_blank"
                rel="noopener noreferrer"
                onClick={e => e.stopPropagation()}
                className={`text-xs font-mono px-2 py-0.5 rounded-full inline-block transition-colors duration-150 hover:text-white ${
                  signal?.signal === 'bullish'
                    ? darkMode
                      ? 'bg-emerald-950/60 border border-emerald-700/60 text-emerald-300 hover:bg-emerald-600 hover:border-emerald-500'
                      : 'bg-emerald-100 border border-emerald-400 text-emerald-800 hover:bg-emerald-500 hover:text-white hover:border-emerald-500'
                    : signal?.signal === 'bearish'
                    ? darkMode
                      ? 'bg-red-950/60 border border-red-700/60 text-red-300 hover:bg-red-600 hover:border-red-500'
                      : 'bg-red-100 border border-red-400 text-red-800 hover:bg-red-500 hover:text-white hover:border-red-500'
                    : darkMode
                    ? 'bg-slate-800/60 border border-slate-600/60 text-slate-300 hover:bg-slate-600 hover:border-slate-500'
                    : 'bg-slate-200 border border-slate-400 text-slate-700 hover:bg-slate-500 hover:text-white hover:border-slate-500'
                }`}
              >
                {sym}
              </a>
            ))}
          </div>
        )}
      </button>

      {/* Expandable detail */}
      {expanded && (
        <div className="border-t border-slate-700 overflow-hidden rounded-b-xl">
          <CategoryDetail category={category} data={data} signal={signal} />
        </div>
      )}
    </div>
  )
}
