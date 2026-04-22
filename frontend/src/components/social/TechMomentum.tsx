export interface TechMomentumItem {
  technology: string
  direction: 'rising' | 'declining' | 'stable'
  momentum_score: number
  insight: string
  key_companies: string[]
  proxy_tickers: string[]
}

const DIRECTION_STYLES = {
  rising:   { icon: '↑', color: 'text-emerald-400', bar: 'bg-emerald-500' },
  declining:{ icon: '↓', color: 'text-red-400',     bar: 'bg-red-500'     },
  stable:   { icon: '→', color: 'text-slate-300',   bar: 'bg-slate-500'   },
}

function MomentumItem({ item }: { item: TechMomentumItem }) {
  const dir = DIRECTION_STYLES[item.direction]
  return (
    <div className="space-y-1.5 py-3 border-b border-slate-800 last:border-0">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className={`text-base font-bold ${dir.color}`} aria-hidden="true">{dir.icon}</span>
          <span className="text-slate-200 font-medium text-sm">{item.technology}</span>
          <span className={`text-xs ${dir.color}`}>
            {item.direction.charAt(0).toUpperCase() + item.direction.slice(1)}
          </span>
        </div>
        <span className="text-slate-400 text-xs shrink-0">{item.momentum_score}/100</span>
      </div>

      <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${dir.bar}`}
          style={{ width: `${item.momentum_score}%` }}
          role="progressbar"
          aria-valuenow={item.momentum_score}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`${item.technology} momentum: ${item.momentum_score} out of 100`}
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

export default function TechMomentum({ items }: { items: TechMomentumItem[] }) {
  if (!items.length) return null
  return (
    <div>
      {items.map(item => (
        <MomentumItem key={item.technology} item={item} />
      ))}
    </div>
  )
}
