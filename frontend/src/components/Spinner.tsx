interface Props {
  size?: number
  label?: string
  hidden?: boolean
}

export default function Spinner({ size = 20, label, hidden = false }: Props) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      className="animate-spin"
      style={{ display: 'inline-block' }}
      aria-hidden={hidden || !label ? true : undefined}
      role={!hidden && label ? 'status' : undefined}
      aria-label={!hidden && label ? label : undefined}
    >
      <circle cx="12" cy="12" r="10" stroke="#334155" strokeWidth="3" />
      <path d="M12 2a10 10 0 0 1 10 10" stroke="#6366f1" strokeWidth="3" strokeLinecap="round" />
    </svg>
  )
}
