import { useState } from 'react'
import SeriesChart from './SeriesChart'
import CIRuler from './CIRuler'
import { LEVEL_LABEL, pText, sig, signed } from '../lib/format'

function Headline({ r }) {
  const up = r.sen.per_decade > 0
  const level = r.verdict.level
  const unit = r.unit
  const size = `${signed(r.sen.per_decade)} ${unit} per decade`
  return (
    <div className={`headline ${level} ${up ? 'up' : 'down'}`}>
      <span className="mark" aria-hidden="true" />
      <div>
        <h3>{level === 'none' ? 'No clear trend' : up ? 'Rising' : 'Falling'}</h3>
        <p className="size">{level === 'none' ? `Measured change: ${size}` : size}</p>
        <p className="level">
          {LEVEL_LABEL[level]} · {pText(r.mann_kendall.p_value)}
        </p>
      </div>
    </div>
  )
}

function Explainer() {
  return (
    <details className="explainer">
      <summary>How to read this</summary>
      <div className="prose">
        <p>
          <b>Seasons removed.</b> Every month is compared with the average for that calendar month, so summer and winter
          do not hide a slow change.
        </p>
        <p>
          <b>The trend.</b> It is Sen&rsquo;s slope: the median of the slopes between every pair of months. A few extreme
          months barely move it.
        </p>
        <p>
          <b>The 95% range.</b> If the trend were measured again from similar data, the answer would fall inside this
          range 95 times out of 100. A range that includes zero means we cannot rule out no change.
        </p>
        <p>
          <b>The p-value.</b> From the Mann-Kendall test. It is the chance of seeing a trend this strong from random
          variation alone. Below 0.05 is the usual bar for &ldquo;significant&rdquo;.
        </p>
        <p>
          <b>Months are not independent.</b> A warm month tends to follow a warm month, which can fake a trend. Both
          tests are adjusted for this, which makes them harder to pass, on purpose.
        </p>
      </div>
    </details>
  )
}

export default function VariableSheet({ result, error, label, first }) {
  const [mode, setMode] = useState('anomaly')

  if (error) {
    return (
      <article className="sheet">
        <header>
          <h2>{label}</h2>
        </header>
        <p className="notice">{error}</p>
      </article>
    )
  }

  const r = result
  return (
    <article className="sheet">
      <header>
        <div>
          <h2>{r.variable.label}</h2>
          <p className="meta">
            {r.variable.source} · {r.start.slice(0, 4)} to {r.end.slice(0, 4)} · {r.n_months} months
          </p>
        </div>
        <div className="seg" role="group" aria-label="What to plot">
          <button className={mode === 'anomaly' ? 'on' : ''} onClick={() => setMode('anomaly')}>
            Seasons removed
          </button>
          <button className={mode === 'raw' ? 'on' : ''} onClick={() => setMode('raw')}>
            Raw values
          </button>
        </div>
      </header>

      <p className="prose lede">{r.variable.definition}</p>

      <div className="sheetgrid">
        <div data-tour={first ? 'tour-stats' : undefined}>
          <Headline r={r} />
          <CIRuler estimate={r.sen.per_decade} low={r.sen.per_decade_ci[0]} high={r.sen.per_decade_ci[1]} unit={r.unit} />
          <dl className="facts">
            <div>
              <dt>Change over the record</dt>
              <dd>
                {signed(r.sen.total_change)} {r.unit}
              </dd>
            </div>
            {r.percent_per_decade != null && (
              <div>
                <dt>Relative to the average</dt>
                <dd>{signed(r.percent_per_decade, 2)}% per decade</dd>
              </div>
            )}
            <div>
              <dt>Cross-check (linear fit)</dt>
              <dd>
                {signed(r.ols.slope_per_year * 10)} {r.unit} per decade, {pText(r.ols.p_value)}
              </dd>
            </div>
            <div>
              <dt>Month-to-month memory</dt>
              <dd>
                r = {sig(r.ols.lag1_autocorr, 2)}, so {Math.round(r.ols.n_effective)} of {r.n_months} months count as independent
              </dd>
            </div>
          </dl>
          {r.warnings.map((w) => (
            <p className="notice" key={w}>
              {w}
            </p>
          ))}
        </div>
        <div data-tour={first ? 'tour-chart' : undefined} className="chartwrap">
          <SeriesChart result={r} mode={mode} />
        </div>
      </div>
      <Explainer />
    </article>
  )
}
