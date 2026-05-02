import { test, expect, afterEach } from 'vitest'
import { render, screen, fireEvent, cleanup } from '@testing-library/react'
import CategoryBarometer from './CategoryBarometer'

afterEach(cleanup)

// ── Shared fixtures ───────────────────────────────────────────────────────────

// noData=true: score===0 && label==='Neutral' && no emotions
const DATA_NO_DATA  = { score: 0,   label: 'Neutral',  dominant_emotions: [] }

// noData=false: score===0 but label !== 'Neutral' — signal adjustment applies
const DATA_ZERO     = { score: 0,   label: 'Mixed',    dominant_emotions: ['optimism'] }

const DATA_POSITIVE = { score: 60,  label: 'Positive', dominant_emotions: ['optimism'] }
const DATA_NEGATIVE = { score: -60, label: 'Negative', dominant_emotions: ['pessimism'] }

const SIG_BULLISH: Parameters<typeof CategoryBarometer>[0]['signal'] = {
  signal: 'bullish', insight: 'Strong economy.', tickers: ['SPY'], confidence: 'high',
}
const SIG_BEARISH: Parameters<typeof CategoryBarometer>[0]['signal'] = {
  signal: 'bearish', insight: 'Weak outlook.',  tickers: ['SH'],  confidence: 'low',
}
const SIG_NEUTRAL_SIG: Parameters<typeof CategoryBarometer>[0]['signal'] = {
  signal: 'neutral', insight: 'Mixed signals.', tickers: [],      confidence: 'medium',
}

/** Read the slider dot's `left` percentage from its inline style. */
function sliderLeft(container: HTMLElement): number {
  const el = container.querySelector('[style*="left:"]') as HTMLElement | null
  return el ? parseFloat(el.style.left) : -1
}


// ── Signal badge ──────────────────────────────────────────────────────────────

test('bullish signal renders ▲ Signal badge', () => {
  render(<CategoryBarometer category="Economy" data={DATA_ZERO} signal={SIG_BULLISH} />)
  expect(screen.getByText('▲ Signal')).toBeInTheDocument()
})

test('bearish signal renders ▼ Signal badge', () => {
  render(<CategoryBarometer category="Economy" data={DATA_ZERO} signal={SIG_BEARISH} />)
  expect(screen.getByText('▼ Signal')).toBeInTheDocument()
})

test('neutral signal renders ● Signal badge', () => {
  render(<CategoryBarometer category="Economy" data={DATA_ZERO} signal={SIG_NEUTRAL_SIG} />)
  expect(screen.getByText('● Signal')).toBeInTheDocument()
})

test('no signal prop: no badge rendered', () => {
  render(<CategoryBarometer category="Economy" data={DATA_POSITIVE} />)
  expect(screen.queryByText(/[▲▼●] Signal/)).not.toBeInTheDocument()
})


// ── Signal-adjusted slider position ──────────────────────────────────────────
// position = ((adjusted + 100) / 200) * 100, clamped [2, 98]
// 50% == score 0; >50% == positive zone; <50% == negative zone
// Note: DATA_ZERO has noData=false so signal adjustment applies.

test('score 0 + bullish: slider in green zone (> 50%)', () => {
  // adjusted = max(0, 25) = 25 → position = 62.5%
  const { container } = render(
    <CategoryBarometer category="Economy" data={DATA_ZERO} signal={SIG_BULLISH} />
  )
  expect(sliderLeft(container)).toBeGreaterThan(50)
})

test('score 0 + bearish: slider in red zone (< 50%)', () => {
  // adjusted = min(0, -25) = -25 → position = 37.5%
  const { container } = render(
    <CategoryBarometer category="Economy" data={DATA_ZERO} signal={SIG_BEARISH} />
  )
  expect(sliderLeft(container)).toBeLessThan(50)
})

test('score +60 + bullish: slider at 80% (already >= 25, unchanged)', () => {
  // adjusted = max(60, 25) = 60 → position = 80%
  const { container } = render(
    <CategoryBarometer category="Economy" data={DATA_POSITIVE} signal={SIG_BULLISH} />
  )
  expect(sliderLeft(container)).toBeCloseTo(80, 1)
})

test('score -60 + bearish: slider at 20% (already <= -25, unchanged)', () => {
  // adjusted = min(-60, -25) = -60 → position = 20%
  const { container } = render(
    <CategoryBarometer category="Economy" data={DATA_NEGATIVE} signal={SIG_BEARISH} />
  )
  expect(sliderLeft(container)).toBeCloseTo(20, 1)
})

test('no signal: slider at exact score position', () => {
  // score=60, no signal → adjusted=60, position=80%
  const { container } = render(
    <CategoryBarometer category="Economy" data={DATA_POSITIVE} />
  )
  expect(sliderLeft(container)).toBeCloseTo(80, 1)
})


// ── Watchlist ticker pill colors ──────────────────────────────────────────────

test('bullish signal: ticker pills have emerald class', () => {
  const { container } = render(
    <CategoryBarometer category="Economy" data={DATA_ZERO} signal={SIG_BULLISH} watchlistTickers={['NVDA']} />
  )
  const pill = container.querySelector('a[href*="NVDA"]')
  expect(pill?.className).toMatch(/emerald/)
})

test('bearish signal: ticker pills have red class', () => {
  const { container } = render(
    <CategoryBarometer category="Economy" data={DATA_ZERO} signal={SIG_BEARISH} watchlistTickers={['SH']} />
  )
  const pill = container.querySelector('a[href*="SH"]')
  expect(pill?.className).toMatch(/red/)
})

test('no signal: ticker pills have slate class', () => {
  const { container } = render(
    <CategoryBarometer category="Economy" data={DATA_POSITIVE} watchlistTickers={['SPY']} />
  )
  const pill = container.querySelector('a[href*="SPY"]')
  expect(pill?.className).toMatch(/slate/)
})


// ── Expand / collapse toggle ──────────────────────────────────────────────────

test('initial state: aria-expanded is false', () => {
  render(<CategoryBarometer category="Economy" data={DATA_POSITIVE} />)
  expect(screen.getByRole('button')).toHaveAttribute('aria-expanded', 'false')
})

test('click expands panel: aria-expanded becomes true', () => {
  render(<CategoryBarometer category="Economy" data={DATA_POSITIVE} />)
  fireEvent.click(screen.getByRole('button'))
  expect(screen.getByRole('button')).toHaveAttribute('aria-expanded', 'true')
})

test('second click collapses: aria-expanded returns to false', () => {
  render(<CategoryBarometer category="Economy" data={DATA_POSITIVE} />)
  fireEvent.click(screen.getByRole('button'))
  fireEvent.click(screen.getByRole('button'))
  expect(screen.getByRole('button')).toHaveAttribute('aria-expanded', 'false')
})


// ── No-data state ─────────────────────────────────────────────────────────────
// noData: score===0 && label==='Neutral' && no dominant_emotions

test('noData: renders "No data" text', () => {
  render(<CategoryBarometer category="Economy" data={DATA_NO_DATA} />)
  expect(screen.getByText('No data')).toBeInTheDocument()
})

test('noData: category label "Neutral" is not shown', () => {
  render(<CategoryBarometer category="Economy" data={DATA_NO_DATA} />)
  expect(screen.queryByText('Neutral')).not.toBeInTheDocument()
})


// ── Emotion pills (slice to 4) ────────────────────────────────────────────────

test('5 emotions: only first 4 are rendered, 5th is absent', () => {
  const data = {
    score: 50,
    label: 'Positive',
    dominant_emotions: ['optimism', 'excitement', 'confidence', 'enthusiasm', 'hope'],
  }
  render(<CategoryBarometer category="Economy" data={data} />)
  expect(screen.getByText('optimism')).toBeInTheDocument()
  expect(screen.getByText('excitement')).toBeInTheDocument()
  expect(screen.getByText('confidence')).toBeInTheDocument()
  expect(screen.getByText('enthusiasm')).toBeInTheDocument()
  expect(screen.queryByText('hope')).not.toBeInTheDocument()
})


// ── Yahoo Finance links ───────────────────────────────────────────────────────

test('watchlist tickers each link to Yahoo Finance', () => {
  render(
    <CategoryBarometer
      category="Economy"
      data={DATA_POSITIVE}
      watchlistTickers={['SPY', 'QQQ']}
    />
  )
  expect(screen.getByRole('link', { name: 'SPY' }))
    .toHaveAttribute('href', 'https://finance.yahoo.com/quote/SPY')
  expect(screen.getByRole('link', { name: 'QQQ' }))
    .toHaveAttribute('href', 'https://finance.yahoo.com/quote/QQQ')
})
