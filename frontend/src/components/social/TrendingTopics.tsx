import { useState } from 'react'

interface Topic {
  rank: number
  category: string
  volume_score: number
  trend: string
  platforms: string[]
  sub_topics: string[]
  mood_score?: number
}

interface Props {
  topics: Topic[]
}

const TREND_ARROW: Record<string, string> = {
  rising: '↑', declining: '↓', stable: '→', cyclical: '↻',
}
const TREND_COLOR: Record<string, string> = {
  rising: 'text-green-400', declining: 'text-red-400',
  stable: 'text-slate-400', cyclical: 'text-yellow-400',
}
const CATEGORY_COLOR: Record<string, string> = {
  'Politics':             '#f59e0b',
  'Economy & Finance':    '#22c55e',
  'Technology & AI':      '#6366f1',
  'Entertainment':        '#ec4899',
  'Health & Wellness':    '#0ea5e9',
  'Science':              '#8b5cf6',
  'Environment & Climate':'#10b981',
  'Sports':               '#f97316',
  'Memes & Viral':        '#a78bfa',
}
const PLATFORM_ICON: Record<string, string> = {
  'Reddit':      '🟠',
  'Hacker News': '🔶',
  'YouTube':     '▶',
}

function newsSearchUrl(query: string): string {
  return `https://news.google.com/search?q=${encodeURIComponent(query)}&hl=en`
}

function TopicRow({ t }: { t: Topic }) {
  const [open, setOpen] = useState(false)
  const color = CATEGORY_COLOR[t.category] || '#94a3b8'
  const trendKey = (t.trend || 'stable').toLowerCase()

  return (
    <div className="bg-slate-700 border border-slate-600 rounded-xl overflow-hidden">
      {/* Header row — click anywhere to expand */}
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-slate-600 transition-colors text-left"
      >
        <span className="text-slate-400 text-sm w-6 text-right font-mono shrink-0">#{t.rank}</span>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className="text-xs font-semibold px-2 py-0.5 rounded-full shrink-0"
              style={{ background: color + '25', color }}
            >
              {t.category}
            </span>
            <span className={`text-sm font-bold shrink-0 ${TREND_COLOR[trendKey] || 'text-slate-400'}`}>
              {TREND_ARROW[trendKey] || '→'}
            </span>
            {t.mood_score !== undefined && t.mood_score !== 0 && (
              <span className={`text-xs font-medium shrink-0 ${t.mood_score >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {t.mood_score > 0 ? '+' : ''}{t.mood_score}
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 mt-1 flex-wrap">
            {t.platforms?.map(p => (
              <span key={p} className="text-xs text-slate-400 flex items-center gap-1">
                <span>{PLATFORM_ICON[p] || '•'}</span>
                <span>{p}</span>
              </span>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <div className="flex flex-col items-end gap-0.5">
            <span className="text-xs font-semibold" style={{ color }}>{t.volume_score}%</span>
            <div className="w-20 h-1.5 bg-slate-600 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full"
                style={{ width: `${Math.min(t.volume_score, 100)}%`, background: color }}
              />
            </div>
            <span className="text-slate-600 text-xs leading-none">engagement</span>
          </div>
          <span
            className="text-slate-400 text-xs transition-transform duration-200 ml-1"
            style={{ display: 'inline-block', transform: open ? 'rotate(180deg)' : 'rotate(0deg)' }}
          >
            ▼
          </span>
        </div>
      </button>

      {/* Subtopics — shown when open */}
      {open && (
        <div className="px-4 pb-4 pt-2 border-t border-slate-600 bg-slate-800">
          {t.sub_topics && t.sub_topics.length > 0 ? (
            <>
              <p className="text-slate-400 text-xs mb-2 font-semibold uppercase tracking-wider">
                Hot subtopics — click to read news
              </p>
              <div className="flex flex-wrap gap-2">
                {t.sub_topics.map(st => (
                  <a
                    key={st}
                    href={newsSearchUrl(`${t.category} ${st}`)}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={e => e.stopPropagation()}
                    className="text-xs px-3 py-1.5 rounded-full transition-all hover:opacity-80 hover:scale-105 cursor-pointer"
                    style={{ background: color + '25', color, border: `1px solid ${color}55` }}
                  >
                    🔍 {st}
                  </a>
                ))}
              </div>
              <a
                href={newsSearchUrl(t.category)}
                target="_blank"
                rel="noopener noreferrer"
                onClick={e => e.stopPropagation()}
                className="inline-flex items-center gap-1 mt-3 text-xs text-slate-500 hover:text-slate-300 transition-colors"
              >
                View all {t.category} news →
              </a>
            </>
          ) : (
            <div className="flex items-center gap-3">
              <p className="text-slate-500 text-sm">No subtopics available.</p>
              <a
                href={newsSearchUrl(t.category)}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
              >
                Search {t.category} news →
              </a>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function TrendingTopics({ topics }: Props) {
  if (!topics.length) return (
    <p className="text-slate-500 text-sm py-4">No trending topics yet. Run a social analysis first.</p>
  )

  return (
    <div className="space-y-2">
      {topics.slice(0, 10).map(t => (
        <TopicRow key={t.rank} t={t} />
      ))}
    </div>
  )
}
