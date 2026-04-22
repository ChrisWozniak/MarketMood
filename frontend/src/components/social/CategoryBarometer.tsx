import { useState } from 'react'
import CategoryDetail from './CategoryDetail'

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
}

function scoreToColor(score: number): string {
  if (score >= 40)  return '#22c55e'
  if (score >= 10)  return '#84cc16'
  if (score >= -10) return '#f59e0b'
  if (score >= -40) return '#f97316'
  return '#ef4444'
}

const SIGNAL_DOT: Record<string, string> = {
  bullish: 'bg-emerald-400',
  bearish: 'bg-red-400',
  neutral: 'bg-slate-400',
}

export default function CategoryBarometer({ category, data, signal }: Props) {
  const [expanded, setExpanded] = useState(false)

  const noData = data.score === 0 && data.label === 'Neutral'
    && (!data.dominant_emotions || data.dominant_emotions.length === 0)

  const color    = noData ? '#475569' : scoreToColor(data.score)
  const position = Math.min(Math.max(((data.score + 100) / 200) * 100, 2), 98)

  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-xl overflow-hidden">
      <button
        type="button"
        onClick={() => setExpanded(o => !o)}
        aria-expanded={expanded}
        aria-label={`${expanded ? 'Collapse' : 'Expand'} ${category} details`}
        className="w-full px-4 pt-3 pb-3 text-left hover:bg-slate-700/30 transition-colors"
      >
        {/* Header row */}
        <div className="flex items-center justify-between mb-2.5">
          <div className="flex items-center gap-2">
            <span className="text-slate-200 text-sm font-semibold">{category}</span>
            {signal && (
              <span className={`w-2 h-2 rounded-full shrink-0 ${SIGNAL_DOT[signal.signal]}`} aria-hidden="true" />
            )}
          </div>
          <div className="flex items-center gap-2">
            {!noData && (
              <span className="text-sm font-bold font-mono" style={{ color }}>
                {data.score > 0 ? '+' : ''}{data.score}
              </span>
            )}
            <span className="text-slate-400 text-xs">{noData ? 'No data' : data.label}</span>
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
          <span className="text-red-400 text-xs opacity-50">−100</span>
          <span className="text-slate-600 text-xs">0</span>
          <span className="text-green-400 text-xs opacity-50">+100</span>
        </div>

        {/* Emotion pills */}
        {!noData && data.dominant_emotions && data.dominant_emotions.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {data.dominant_emotions.slice(0, 4).map(e => (
              <span key={e} className="text-xs bg-slate-700 text-slate-300 px-2 py-0.5 rounded-full capitalize">
                {e}
              </span>
            ))}
          </div>
        )}
      </button>

      {/* Expandable detail */}
      {expanded && (
        <div className="border-t border-slate-700">
          <CategoryDetail category={category} data={data} signal={signal} />
        </div>
      )}
    </div>
  )
}
