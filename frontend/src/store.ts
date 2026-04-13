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

export const useStore = create<AppStore>((set) => ({
  darkMode: true,
  toggleDarkMode: () => set((s) => {
    const next = !s.darkMode
    document.documentElement.classList.toggle('light', !next)
    document.body.style.background = next ? '#0f172a' : '#f0f4f8'
    return { darkMode: next }
  }),
  loading: {},
  setLoading: (key, val) => set((s) => ({ loading: { ...s.loading, [key]: val } })),
  panelCollapse: null,
  setPanelCollapse: (v) => set({ panelCollapse: v }),
}))
