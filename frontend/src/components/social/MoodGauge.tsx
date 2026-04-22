import { RadialBarChart, RadialBar, ResponsiveContainer } from 'recharts'

interface MoodData {
  score: number
  label: string
  dominant_emotions?: string[]
  polarization_level?: number
}

interface Props {
  category: string
  data: MoodData
}

function scoreToColor(score: number): string {
  if (score >= 40) return '#22c55e'
  if (score >= 10) return '#84cc16'
  if (score >= -10) return '#f59e0b'
  if (score >= -40) return '#f97316'
  return '#ef4444'
}

export default function MoodGauge({ category, data }: Props) {
  const noData = data.score === 0 && data.label === 'Neutral' && (!data.dominant_emotions || data.dominant_emotions.length === 0)
  const color = noData ? '#475569' : scoreToColor(data.score)
  const normalised = ((data.score + 100) / 200) * 100

  return (
    <div className="bg-slate-900 rounded-xl p-4 flex flex-col items-center text-center">
      <p className="text-slate-400 text-xs font-semibold uppercase tracking-wider mb-2">{category}</p>
      <div
        style={{ width: 100, height: 60, position: 'relative' }}
        aria-label={noData ? `${category} sentiment gauge - no data available` : `${category} sentiment gauge showing ${data.score > 0 ? '+' : ''}${data.score} score, ${data.label} mood`}
        role="img"
      >
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart
            innerRadius="70%"
            outerRadius="100%"
            startAngle={180}
            endAngle={0}
            data={[{ value: noData ? 50 : normalised, fill: color }]}
          >
            <RadialBar dataKey="value" background={{ fill: '#1e293b' }} />
          </RadialBarChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex items-end justify-center pb-1">
          {noData
            ? <span className="text-sm text-slate-500">—</span>
            : <span className="text-lg font-bold" style={{ color }}>{data.score > 0 ? '+' : ''}{data.score}</span>
          }
        </div>
      </div>
      <p className="text-sm font-medium mt-1" style={{ color: noData ? '#64748b' : '#cbd5e1' }}>
        {noData ? 'No data' : data.label}
      </p>
      {!noData && data.dominant_emotions && data.dominant_emotions.length > 0 && (
        <div className="flex flex-wrap justify-center gap-1 mt-2">
          {data.dominant_emotions.slice(0, 3).map(e => (
            <span key={e} className="text-xs bg-slate-700 text-slate-400 px-2 py-0.5 rounded-full capitalize">{e}</span>
          ))}
        </div>
      )}
    </div>
  )
}
