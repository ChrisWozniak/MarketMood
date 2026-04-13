import { useState, useEffect, useRef } from 'react'
import toast from 'react-hot-toast'
import { runNow, getHistory, getDigestRun, getNextRun } from '../api'
import { useStore } from '../store'
import Card from './Card'
import Spinner from './Spinner'

interface HistoryItem { id: number; run_at: string; trigger: string; status: string }
interface DigestRun { id: number; run_at: string; trigger: string; status: string; html: string }

const RUN_STAGES = [
  { delay: 0,     msg: 'Fetching latest news articles…' },
  { delay: 8000,  msg: 'Gathering headlines from all categories…' },
  { delay: 20000, msg: 'Summarizing with AI — please be patient…' },
  { delay: 40000, msg: 'Still summarizing, almost there…' },
  { delay: 65000, msg: 'Composing email report…' },
  { delay: 85000, msg: 'Sending email, nearly done…' },
]

function CollapseButton({ open, onClick }: { open: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="text-slate-400 hover:text-slate-200 transition-colors p-1 rounded-lg hover:bg-slate-700"
      title={open ? 'Collapse' : 'Expand'}
    >
      <span style={{
        display: 'inline-block',
        transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
        transition: 'transform 0.2s',
      }}>▼</span>
    </button>
  )
}

export default function Dashboard() {
  const [running, setRunning]       = useState(false)
  const [stageMsg, setStageMsg]     = useState('')
  const [history, setHistory]       = useState<HistoryItem[]>([])
  const [selected, setSelected]     = useState<DigestRun | null>(null)
  const [loadingRun, setLoadingRun] = useState<number | null>(null)
  const [nextRun, setNextRun]       = useState<string | null>(null)
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([])

  const [openHistory, setOpenHistory] = useState(true)
  const { panelCollapse } = useStore()
  useEffect(() => {
    if (panelCollapse === null) return
    setOpenHistory(!panelCollapse)
    setSelected(null) // don't re-open a digest when expanding all panels
  }, [panelCollapse])

  const clearTimers = () => {
    timersRef.current.forEach(t => clearTimeout(t))
    timersRef.current = []
  }

  const startStages = () => {
    clearTimers()
    RUN_STAGES.forEach(({ delay, msg }) => {
      const t = setTimeout(() => setStageMsg(msg), delay)
      timersRef.current.push(t)
    })
  }

  const refreshNextRun = () => getNextRun().then(d => setNextRun(d.next_run)).catch(() => {})

  useEffect(() => {
    getHistory(50).then(d => setHistory(d)).catch(() => {})
    refreshNextRun()
    const interval = setInterval(refreshNextRun, 30000)
    return () => clearInterval(interval)
  }, [])

  const handleRunNow = async () => {
    setRunning(true)
    setStageMsg(RUN_STAGES[0].msg)
    startStages()
    try {
      await runNow()
      toast.success('Digest sent successfully!')
      const h = await getHistory()
      setHistory(h.slice(0, 10))
    } catch {
      toast.error('Failed to run digest.')
    } finally {
      clearTimers()
      setRunning(false)
      setStageMsg('')
    }
  }

  const handleSelectRun = async (id: number) => {
    if (selected?.id === id) { setSelected(null); return }
    setLoadingRun(id)
    try {
      const data = await getDigestRun(id)
      setSelected(data)
    } catch {
      toast.error('Could not load digest.')
    } finally {
      setLoadingRun(null)
    }
  }

  const formatDate = (iso: string) => {
    const hasOffset = iso.includes('+') || iso.endsWith('Z') || /\d{2}:\d{2}$/.test(iso.slice(-6))
    const d = new Date(hasOffset ? iso : iso + 'Z')
    return d.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  }

  return (
    <Card accent="#6366f1">
      {/* ── Header row ── */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-slate-200 font-semibold text-lg">📰 News Digest</h2>
          <p className="text-slate-500 text-xs mt-0.5">
            {nextRun && nextRun !== 'null'
              ? <>Next scheduled run: <span className="text-green-400 font-mono">{formatDate(nextRun)}</span></>
              : 'No schedule set — configure in Settings below'
            }
          </p>
        </div>
        <button
          onClick={handleRunNow}
          disabled={running}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-800 disabled:cursor-not-allowed text-white font-medium px-5 py-2.5 rounded-xl transition-colors text-sm shrink-0"
        >
          {running ? <Spinner size={16} /> : '▶'}
          {running ? 'Working…' : 'Run Now'}
        </button>
      </div>

      {/* ── Settings hint (only when not running) ── */}
      {!running && (
        <p className="text-slate-500 text-xs mt-1 mb-1">
          💡 First time?{' '}
          <button
            onClick={() => {
              const el = document.querySelector<HTMLElement>('[data-section="settings"]')
              if (el) {
                const top = el.getBoundingClientRect().top + window.scrollY - 76
                window.scrollTo({ top, behavior: 'smooth' })
              }
            }}
            className="text-indigo-400 hover:text-indigo-300 underline transition-colors"
          >
            Configure your preferences in Settings
          </button>{' '}
          before running.
        </p>
      )}

      {/* ── Progress bar + stage message ── */}
      {running && (
        <div className="mb-4">
          <p className="text-indigo-400 text-xs mb-2 animate-pulse">{stageMsg}</p>
          <div className="w-full h-1 bg-slate-700 rounded-full overflow-hidden">
            <div className="h-full bg-indigo-500 rounded-full animate-pulse" style={{ width: '100%' }} />
          </div>
        </div>
      )}

      {/* ── Divider ── */}
      <div className="border-t border-slate-700 mt-2 mb-4" />

      {/* ── Recent Digests (collapsible) ── */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-slate-300 text-sm font-semibold">
          Recent Digests
          {history.length > 0 && (
            <span className="ml-2 text-slate-600 font-normal">({history.length})</span>
          )}
        </h3>
        <CollapseButton open={openHistory} onClick={() => setOpenHistory(o => !o)} />
      </div>

      {openHistory && (
        history.length === 0 ? (
          <p className="text-slate-500 text-sm">No digests yet — click Run Now to generate your first one.</p>
        ) : (
          <>
            <div className="space-y-2">
              {history.slice(0, 3).map(item => (
                <div key={item.id}>
                  <button
                    onClick={() => handleSelectRun(item.id)}
                    className="w-full flex items-center justify-between px-4 py-3 rounded-xl bg-slate-700 hover:bg-slate-600 transition-colors text-left group"
                  >
                    <div className="flex items-center gap-3">
                      <span className={`w-2 h-2 rounded-full flex-shrink-0 ${item.status === 'success' ? 'bg-green-400' : 'bg-red-400'}`} />
                      <span className="text-slate-200 text-sm font-medium">{formatDate(item.run_at)}</span>
                      <span className="text-slate-500 text-xs capitalize">{item.trigger}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      {loadingRun === item.id && <Spinner size={14} />}
                      <span
                        className="text-slate-500 text-xs group-hover:text-slate-300 transition-colors"
                        style={{
                          display: 'inline-block',
                          transform: selected?.id === item.id ? 'rotate(180deg)' : 'rotate(0deg)',
                          transition: 'transform 0.2s',
                        }}
                      >▼</span>
                    </div>
                  </button>

                  {selected?.id === item.id && (
                    <div className="mt-2 rounded-xl overflow-hidden border border-slate-700">
                      <iframe
                        srcDoc={selected.html}
                        className="w-full"
                        style={{ height: '600px', border: 'none', background: '#0f172a' }}
                        title="Digest preview"
                      />
                    </div>
                  )}
                </div>
              ))}
            </div>

            {history.length > 3 && (
              <p className="text-slate-600 text-xs mt-3">
                {history.length - 3} older digest{history.length - 3 !== 1 ? 's' : ''} saved in{' '}
                <code className="text-slate-500">digest_reports/</code>
                {' · '}
                <a
                  href="/api/digest/reports"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-indigo-500 hover:text-indigo-400 transition-colors"
                >
                  Browse all ↗
                </a>
              </p>
            )}
          </>
        )
      )}
    </Card>
  )
}
