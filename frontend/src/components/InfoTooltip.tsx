import { useState, useId } from 'react'

interface Props {
  text: string
}

export default function InfoTooltip({ text }: Props) {
  const [open, setOpen] = useState(false)
  const tooltipId = useId()

  const show = () => setOpen(true)
  const hide = () => setOpen(false)

  return (
    <span className="relative inline-block ml-1 align-middle">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        onMouseEnter={show}
        onMouseLeave={hide}
        onFocus={show}
        onBlur={hide}
        onKeyDown={e => { if (e.key === 'Escape') hide() }}
        className="w-4 h-4 rounded-full bg-slate-600 text-slate-300 text-xs font-bold leading-none flex items-center justify-center hover:bg-slate-500 transition-colors cursor-help"
        style={{ fontSize: '10px' }}
        aria-label="More info"
        aria-describedby={open ? tooltipId : undefined}
      >
        ?
      </button>
      {open && (
        <div
          id={tooltipId}
          role="tooltip"
          className="absolute z-50 bottom-6 left-1/2 -translate-x-1/2 w-56 bg-slate-700 text-slate-200 text-xs rounded-xl shadow-xl p-3 leading-relaxed border border-slate-600"
        >
          {text}
          <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-700" />
        </div>
      )}
    </span>
  )
}
