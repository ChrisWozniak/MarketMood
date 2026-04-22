export interface InvestmentSignalData {
  category: string
  signal: 'bullish' | 'bearish' | 'neutral'
  insight: string
  tickers: string[]
  confidence: 'high' | 'medium' | 'low'
}

const SIGNAL_STYLES = {
  bullish: { badge: 'bg-emerald-950 text-emerald-400 border border-emerald-800', label: '▲ Bullish' },
  bearish: { badge: 'bg-red-950 text-red-400 border border-red-800',             label: '▼ Bearish' },
  neutral: { badge: 'bg-slate-800 text-slate-400 border border-slate-700',       label: '● Neutral' },
}

const CONFIDENCE_STYLES = {
  high:   'text-indigo-400',
  medium: 'text-amber-400',
  low:    'text-slate-300',
}

export default function InvestmentSignal({ signal }: { signal: InvestmentSignalData }) {
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
