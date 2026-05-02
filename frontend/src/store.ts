import { create } from 'zustand'

interface AppStore {
  darkMode: boolean
  toggleDarkMode: () => void
  // Shared loading registry — keyed by operation name
  loading: Record<string, boolean>
  setLoading: (key: string, val: boolean) => void
  // Global collapse/expand signal — null = idle, true = collapse all, false = expand all
  panelCollapse: boolean | null
  setPanelCollapse: (v: boolean | null) => void
}

const savedDark = localStorage.getItem('mm_dark_mode')
const initDark = savedDark !== null ? savedDark === 'true' : false

document.documentElement.classList.toggle('light', !initDark)
document.body.style.background = initDark ? '#0f172a' : '#f4ead8'

export const useStore = create<AppStore>((set) => ({
  darkMode: initDark,
  toggleDarkMode: () => set((s) => {
    const next = !s.darkMode
    document.documentElement.classList.toggle('light', !next)
    document.body.style.background = next ? '#0f172a' : '#f4ead8'
    localStorage.setItem('mm_dark_mode', String(next))
    return { darkMode: next }
  }),
  loading: {},
  setLoading: (key, val) => set((s) => ({ loading: { ...s.loading, [key]: val } })),
  panelCollapse: null,
  setPanelCollapse: (v) => set({ panelCollapse: v }),
}))
