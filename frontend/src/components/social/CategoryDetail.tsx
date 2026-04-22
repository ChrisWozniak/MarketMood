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

const SIGNAL_STYLES = {
  bullish: { badge: 'bg-emerald-950 text-emerald-400 border border-emerald-800', label: '▲ Bullish' },
  bearish: { badge: 'bg-red-950 text-red-400 border border-red-800',             label: '▼ Bearish' },
  neutral: { badge: 'bg-slate-800 text-slate-400 border border-slate-700',       label: '● Neutral' },
}

const CONFIDENCE_COLOR = {
  high:   'text-indigo-400',
  medium: 'text-amber-400',
  low:    'text-slate-400',
}

const CONFIDENCE_WIDTH = { high: '100%', medium: '66%', low: '33%' }
const CONFIDENCE_BG    = { high: 'bg-indigo-500', medium: 'bg-amber-500', low: 'bg-slate-500' }

function newsSearchUrl(query: string): string {
  return `https://news.google.com/search?q=${encodeURIComponent(query)}&hl=en`
}

export default function CategoryDetail({ category, data, signal }: Props) {
  return (
    <div className="px-4 py-4 space-y-4 bg-slate-800/30">

      {signal ? (
        <>
          {/* Signal badge + confidence */}
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${SIGNAL_STYLES[signal.signal].badge}`}>
              {SIGNAL_STYLES[signal.signal].label}
            </span>
            <div className="flex items-center gap-2">
              <span className={`text-xs font-medium ${CONFIDENCE_COLOR[signal.confidence]}`}>
                {signal.confidence} confidence
              </span>
              <div className="w-16 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${CONFIDENCE_BG[signal.confidence]}`}
                  style={{ width: CONFIDENCE_WIDTH[signal.confidence] }}
                />
              </div>
            </div>
          </div>

          {/* Insight */}
          <p className="text-slate-300 text-xs leading-relaxed">{signal.insight}</p>

          {/* Tickers */}
          {signal.tickers.length > 0 && (
            <div>
              <p className="text-slate-500 text-xs mb-1.5 font-medium uppercase tracking-wider">Related tickers</p>
              <div className="flex gap-1.5 flex-wrap">
                {signal.tickers.map(t => (
                  <span key={t} className="text-xs font-mono bg-slate-700 text-slate-300 px-2 py-0.5 rounded border border-slate-600">
                    {t}
                  </span>
                ))}
              </div>
            </div>
          )}
        </>
      ) : (
        <p className="text-slate-500 text-xs">No investment signal available for this category yet.</p>
      )}

      {/* Polarization bar (only when meaningful) */}
      {data.polarization_level !== undefined && data.polarization_level > 20 && (
        <div className="flex items-center gap-2">
          <span className="text-slate-500 text-xs shrink-0">Polarization</span>
          <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-orange-500 rounded-full"
              style={{ width: `${data.polarization_level}%` }}
            />
          </div>
          <span className="text-slate-400 text-xs">{data.polarization_level}%</span>
        </div>
      )}

      {/* News link */}
      <a
        href={newsSearchUrl(category)}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
      >
        Search news for {category} →
      </a>
    </div>
  )
}
