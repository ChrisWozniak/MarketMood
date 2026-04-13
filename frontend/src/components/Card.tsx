import type { ReactNode } from 'react'

interface Props {
  children: ReactNode
  className?: string
  accent?: string
}

export default function Card({ children, className = '', accent }: Props) {
  return (
    <div
      className={`bg-slate-800 rounded-2xl p-6 shadow-md ${className}`}
      style={accent ? { borderLeft: `4px solid ${accent}` } : {}}
    >
      {children}
    </div>
  )
}
