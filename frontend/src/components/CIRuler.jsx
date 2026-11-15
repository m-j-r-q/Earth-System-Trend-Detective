import { signed } from '../lib/format'

/**
 * Shows the confidence interval of the trend against zero. When the interval straddles the
 * zero line, "no change" is still a plausible answer, which is what "not significant" means.
 */
export default function CIRuler({ estimate, low, high, unit }) {
  const pad = (high - low) * 0.35 || 1
  const min = Math.min(low, 0) - pad
  const max = Math.max(high, 0) + pad
  const x = (v) => 12 + ((v - min) / (max - min)) * 276
  const color = estimate >= 0 ? 'var(--berry)' : 'var(--tide)'
  const crosses = low <= 0 && high >= 0
  return (
    <figure className="ruler">
      <svg viewBox="0 0 300 54" role="img" aria-label={`Trend ${signed(estimate)} ${unit} per decade, 95% interval ${signed(low)} to ${signed(high)}`}>
        <line x1="12" x2="288" y1="26" y2="26" stroke="var(--hair)" strokeWidth="1" />
        <line x1={x(0)} x2={x(0)} y1="8" y2="44" stroke="var(--ink)" strokeWidth="1.5" />
        <text x={x(0)} y="52" textAnchor="middle" fontSize="10" fill="var(--ink-2)">no change</text>
        <line x1={x(low)} x2={x(high)} y1="26" y2="26" stroke={color} strokeWidth="5" strokeLinecap="round" opacity="0.35" />
        <line x1={x(low)} x2={x(low)} y1="19" y2="33" stroke={color} strokeWidth="2" />
        <line x1={x(high)} x2={x(high)} y1="19" y2="33" stroke={color} strokeWidth="2" />
        <circle cx={x(estimate)} cy="26" r="6" fill={crosses ? 'var(--sheet)' : color} stroke={color} strokeWidth="2.5" />
      </svg>
      <figcaption>
        95% range: {signed(low)} to {signed(high)} {unit} per decade.{' '}
        {crosses ? 'The range includes zero, so no change is still plausible.' : 'The range stays on one side of zero.'}
      </figcaption>
    </figure>
  )
}
