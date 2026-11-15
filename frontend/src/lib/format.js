export const sig = (x, n = 3) => (Number.isFinite(x) ? String(Number(x.toPrecision(n))) : '—')
export const signed = (x, n = 3) => (Number.isFinite(x) ? (x > 0 ? '+' : '') + sig(x, n) : '—')
export const pText = (p) => (!Number.isFinite(p) ? '—' : p < 0.001 ? 'p < 0.001' : `p = ${p.toFixed(3)}`)
export const pval = (p) => (!Number.isFinite(p) ? '—' : p < 0.001 ? '<0.001' : p.toFixed(3))

export const LEVEL_LABEL = {
  strong: 'Strong evidence',
  significant: 'Significant',
  weak: 'Weak evidence',
  none: 'Not significant',
}

/** Trailing moving average; the first w-1 entries are null so charts leave a gap. */
export function rolling(arr, w = 12) {
  const out = new Array(arr.length).fill(null)
  let sum = 0
  for (let i = 0; i < arr.length; i++) {
    sum += arr[i]
    if (i >= w) sum -= arr[i - w]
    if (i >= w - 1) out[i] = sum / w
  }
  return out
}

/** Replace {{a.b}} placeholders with values from ctx; unknown values become an ellipsis. */
export function fillTemplate(text, ctx) {
  return text.replace(/\{\{([\w.]+)\}\}/g, (_, path) => {
    const v = path.split('.').reduce((o, k) => (o == null ? o : o[k]), ctx)
    return v == null ? '…' : String(v)
  })
}

export const direction = (r) => (r.sen.per_decade > 0 ? 'rising' : 'falling')
export const sigWord = (r) => (r.mann_kendall.significant ? 'significant' : 'not significant')

/** Values the demo guide can quote. */
export function ctxFromResult(r) {
  return {
    region: r.region.name,
    variable: r.variable.label,
    unit: r.unit,
    slope: signed(r.sen.per_decade),
    ci: `${signed(r.sen.per_decade_ci[0])} to ${signed(r.sen.per_decade_ci[1])}`,
    p: pText(r.mann_kendall.p_value),
    level: r.verdict.level,
    verdict: r.verdict.text,
    direction: direction(r),
    start: r.start.slice(0, 4),
    end: r.end.slice(0, 4),
    span: Math.round(r.span_years),
  }
}

export function summarizeRegions(results) {
  return results
    .map((r) => `${r.region.name}: ${signed(r.sen.per_decade)} ${r.unit} per decade (${sigWord(r)})`)
    .join('; ')
}

export function summarizeVariables(results) {
  return results
    .map((r) => `${r.variable.label}: ${signed(r.sen.per_decade)} ${r.unit} per decade (${sigWord(r)})`)
    .join('; ')
}

/** Strongest off-diagonal correlation, as a sentence. */
export function strongestLink(corr, labels) {
  let best = null
  const ids = Object.keys(corr || {})
  for (const a of ids) {
    for (const b of ids) {
      if (a < b && (best === null || Math.abs(corr[a][b]) > Math.abs(best.r))) best = { a, b, r: corr[a][b] }
    }
  }
  if (!best) return 'Not enough overlapping months to compare.'
  return `${labels[best.a]} and ${labels[best.b]} (r = ${best.r.toFixed(2)})`
}
