import { useRef, useState, useEffect } from 'react'
import { Toaster } from 'react-hot-toast'
import { useStore } from './store'
import SocialDashboard from './components/social/SocialDashboard'
import Settings from './components/Settings'

const HEADER_HEIGHT = 72 // px — sticky header height to offset scroll

export default function App() {
  const { darkMode, toggleDarkMode, setPanelCollapse } = useStore()

  // Blink the green/red dots in the browser tab every 3 seconds
  useEffect(() => {
    const on  = '▲🟢 Market Mood 🔴▼'
    const off = '▲🟠 Market Mood 🟣▼'
    let show = true
    const id = setInterval(() => {
      show = !show
      document.title = show ? on : off
    }, 3000)
    return () => clearInterval(id)
  }, [])
  const [collapsed, setCollapsed] = useState(false)
  const [showScrollTop, setShowScrollTop] = useState(false)

  useEffect(() => {
    const onScroll = () => setShowScrollTop(window.scrollY > 400)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const settingsRef = useRef<HTMLDivElement>(null)
  const [settingsBlink, setSettingsBlink] = useState(false)

  const scrollTo = (ref: React.RefObject<HTMLDivElement | null>) => {
    if (!ref.current) return
    const top = ref.current.getBoundingClientRect().top + window.scrollY - HEADER_HEIGHT - 12
    window.scrollTo({ top, behavior: 'smooth' })
  }

  const scrollToSettings = () => {
    scrollTo(settingsRef)
    setSettingsBlink(true)
    setTimeout(() => setSettingsBlink(false), 2500)
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
      <header className="bg-slate-900 border-b border-slate-800 sticky top-0 z-40" style={{ height: HEADER_HEIGHT + 'px' }}>
        <div className="max-w-5xl mx-auto px-4 h-full flex items-center justify-between gap-2">

          {/* LEFT — Day/Night + Collapse All */}
          <div className="flex items-center gap-2">
            <button
              onClick={toggleDarkMode}
              className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 text-xs font-medium px-3 py-2 rounded-xl transition-all duration-200 hover:scale-110 whitespace-nowrap"
            >
              {darkMode ? '☀ Day' : '🌙 Night'}
            </button>
            <button
              onClick={toggleAllPanels}
              title={collapsed ? 'Expand all sections' : 'Collapse all sections'}
              className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 text-xs font-medium px-3 py-2 rounded-xl transition-all duration-200 hover:scale-110 whitespace-nowrap"
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
            className="flex items-center gap-3 group"
          >
            <img
              src="/logo1.png"
              alt="Market Mood"
              className="h-14 w-14 rounded-xl object-cover transition-transform duration-300 ease-in-out group-hover:scale-150 group-hover:shadow-2xl group-hover:z-50"
              style={{ transformOrigin: 'center center' }}
            />
            <div className="flex flex-col items-center">
              <span className="text-slate-100 font-bold text-lg leading-tight group-hover:text-indigo-400 transition-colors">
                Market Mood
              </span>
              <span className="text-slate-500 text-xs leading-tight">Social Sentiment Barometer</span>
            </div>
          </button>

          {/* RIGHT — Scroll anchors */}
          <div className="flex items-center gap-1">
            <button
              onClick={scrollToSettings}
              className="hidden sm:flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 text-xs font-medium px-3 py-2 rounded-xl transition-all duration-200 hover:scale-110 whitespace-nowrap"
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
          <span className={`text-xs font-semibold uppercase tracking-widest transition-colors ${settingsBlink ? 'settings-blink' : 'text-slate-600'}`}>Settings</span>
          <div className="flex-1 h-px bg-slate-800" />
        </div>

        <section>
          <Settings />
        </section>

        {/* ── Footer ── */}
        <footer className="border-t border-slate-800 pt-8 pb-12 flex flex-col items-center gap-4">
          <button
            onClick={scrollToTop}
            className="group flex flex-col items-center gap-2 text-slate-500 hover:text-slate-200 transition-all duration-200"
          >
            <span className="flex items-center justify-center w-10 h-10 rounded-full border border-slate-700 bg-slate-800 group-hover:bg-indigo-600 group-hover:border-indigo-500 transition-all duration-200 group-hover:scale-110 text-lg">
              ↑
            </span>
            <span className="text-xs font-medium tracking-wide uppercase group-hover:text-indigo-400 transition-colors">
              Back to top
            </span>
          </button>
          <p className="text-slate-700 text-xs">
            Market Mood &nbsp;·&nbsp; Social Sentiment Barometer &nbsp;·&nbsp; {new Date().getFullYear()}
          </p>
        </footer>

      </main>

      {/* ── Floating scroll-to-top button (appears after 400px scroll) ── */}
      <button
        onClick={scrollToTop}
        aria-label="Back to top"
        className={`fixed bottom-6 right-6 z-50 w-11 h-11 rounded-full bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg flex items-center justify-center text-lg font-bold transition-all duration-300 hover:scale-110 ${
          showScrollTop ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4 pointer-events-none'
        }`}
      >
        ↑
      </button>
    </div>
  )
}
