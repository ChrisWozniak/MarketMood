import { useRef, useState } from 'react'
import { Toaster } from 'react-hot-toast'
import { useStore } from './store'
import SocialDashboard from './components/social/SocialDashboard'
import Settings from './components/Settings'

const HEADER_HEIGHT = 64 // px — sticky header height to offset scroll

export default function App() {
  const { darkMode, toggleDarkMode, setPanelCollapse } = useStore()
  const [collapsed, setCollapsed] = useState(false)

  const settingsRef = useRef<HTMLDivElement>(null)

  const scrollTo = (ref: React.RefObject<HTMLDivElement | null>) => {
    if (!ref.current) return
    const top = ref.current.getBoundingClientRect().top + window.scrollY - HEADER_HEIGHT - 12
    window.scrollTo({ top, behavior: 'smooth' })
  }

  const scrollToTop = () => window.scrollTo({ top: 0, behavior: 'smooth' })

  const toggleAllPanels = () => {
    const next = !collapsed
    setCollapsed(next)
    setPanelCollapse(next)
    setTimeout(() => setPanelCollapse(null), 200)
  }

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col">
      <Toaster
        position="top-right"
        toastOptions={{
          style: { background: '#1e293b', color: '#f1f5f9', border: '1px solid #334155' },
          success: { iconTheme: { primary: '#22c55e', secondary: '#1e293b' } },
          error:   { iconTheme: { primary: '#ef4444', secondary: '#1e293b' } },
        }}
      />

      {/* ── Sticky Header ── */}
      <header className="bg-slate-900 border-b border-slate-800 sticky top-0 z-40" style={{ height: HEADER_HEIGHT }}>
        <div className="max-w-5xl mx-auto px-4 h-full flex items-center justify-between gap-2">

          {/* LEFT — Day/Night + Collapse All */}
          <div className="flex items-center gap-2">
            <button
              onClick={toggleDarkMode}
              className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 text-xs font-medium px-3 py-2 rounded-xl transition-colors whitespace-nowrap"
            >
              {darkMode ? '☀ Day' : '🌙 Night'}
            </button>
            <button
              onClick={toggleAllPanels}
              title={collapsed ? 'Expand all sections' : 'Collapse all sections'}
              className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 text-xs font-medium px-3 py-2 rounded-xl transition-colors whitespace-nowrap"
            >
              <span style={{
                display: 'inline-block',
                transform: collapsed ? 'rotate(0deg)' : 'rotate(180deg)',
                transition: 'transform 0.2s',
              }}>▼</span>
              <span className="hidden sm:inline">{collapsed ? 'Expand All' : 'Collapse All'}</span>
            </button>
          </div>

          {/* CENTER — Logo scrolls to top */}
          <button
            onClick={scrollToTop}
            className="flex items-center gap-2 group"
          >
            <img
              src="/logo.png"
              alt="MoodMarket"
              className="h-10 w-10 rounded-xl object-cover transition-transform duration-300 ease-in-out group-hover:scale-[2] group-hover:shadow-2xl group-hover:z-50"
              style={{ transformOrigin: 'center center' }}
            />
            <div className="flex flex-col items-start">
              <span className="text-slate-100 font-bold text-base leading-tight group-hover:text-indigo-400 transition-colors">
                MoodMarket
              </span>
              <span className="text-slate-500 text-xs leading-tight">Social Sentiment Barometer</span>
            </div>
          </button>

          {/* RIGHT — Scroll anchors */}
          <div className="flex items-center gap-1">
            <button
              onClick={() => scrollTo(settingsRef)}
              className="hidden sm:block px-3 py-2 rounded-lg text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-all whitespace-nowrap"
            >
              ⚙ Settings
            </button>
          </div>
        </div>
      </header>

      {/* ── Single scrollable page ── */}
      <main className="flex-1 max-w-5xl mx-auto w-full px-4 py-6 space-y-10">

        <section>
          <SocialDashboard />
        </section>

        {/* Settings divider + anchor */}
        <div ref={settingsRef} className="flex items-center gap-4 scroll-mt-20">
          <div className="flex-1 h-px bg-slate-800" />
          <span className="text-slate-600 text-xs font-semibold uppercase tracking-widest">Settings</span>
          <div className="flex-1 h-px bg-slate-800" />
        </div>

        <section className="pb-10">
          <Settings />
        </section>

      </main>
    </div>
  )
}
