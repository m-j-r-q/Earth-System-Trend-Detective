import { useEffect } from 'react'
import Plot, { INK_2 } from './Plot'
import { api } from '../api'
import { useFetch } from '../lib/useFetch'
import { LEVEL_LABEL, pText, rolling, signed, strongestLink, summarizeVariables } from '../lib/format'

const PALETTE = ['#1F6FA8', '#A8326B', '#4C7A5A', '#B07A1A', '#6B5B95', '#2A8C8C', '#8A5A44', '#5B6B78']

function corrColor(r) {
  const a = Math.min(1, Math.abs(r))
  return r >= 0 ? `rgba(168,50,107,${0.12 + a * 0.5})` : `rgba(31,111,168,${0.12 + a * 0.5})`
}

export default function CompareVariables({ region, catalog, config, onCtx }) {
  const vars = config.variables
  const enabled = vars.length >= 2
  const { data, error, loading } = useFetch(
    () => api.compareVariables(region.id, vars, config.start, config.end, config.alpha),
    [region.id, vars.join(), config.start, config.end, config.alpha],
    enabled,
  )

  useEffect(() => {
    if (!data) return
    const labels = Object.fromEntries(data.results.map((r) => [r.variable.id, r.variable.label.toLowerCase()]))
    onCtx?.({
      summary: summarizeVariables(data.results),
      link: strongestLink(data.anomaly_correlation, labels),
    })
  }, [data]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!enabled) {
    return <p className="notice" data-tour="tour-compare">Tick at least two variables on the left to compare them in {region.name}.</p>
  }
  if (error) return <p className="notice" data-tour="tour-compare">{error}</p>
  if (!data) return <p className="notice" data-tour="tour-compare">Loading…</p>

  const traces = data.results.map((r, i) => ({
    x: r.series.dates,
    y: rolling(r.series.anomalies_z, 12),
    type: 'scatter',
    mode: 'lines',
    name: r.variable.label,
    line: { color: PALETTE[i % PALETTE.length], width: 2.2 },
  }))
  const ids = data.results.map((r) => r.variable.id)
  const corr = data.anomaly_correlation

  return (
    <div className={loading ? 'stale' : ''} data-tour="tour-compare">
      <article className="sheet">
        <header>
          <div>
            <h2>Variables side by side</h2>
            <p className="meta">{region.name}</p>
          </div>
        </header>
        <p className="prose lede">
          Each line is a 12-month average of the seasonal anomaly, divided by its own spread so different units share one
          axis. Lines that move together may be linked, though a link alone does not prove one drives the other.
        </p>
        <Plot
          data={traces}
          height={320}
          layout={{ yaxis: { title: { text: 'Standard deviations from normal', font: { color: INK_2 } }, zeroline: true, zerolinecolor: INK_2, gridcolor: '#E1E8EA' } }}
        />
      </article>

      <article className="sheet">
        <header>
          <h2>Trend of each variable</h2>
        </header>
        <table className="table">
          <thead>
            <tr>
              <th>Variable</th>
              <th>Trend per decade</th>
              <th>95% range</th>
              <th>Verdict</th>
            </tr>
          </thead>
          <tbody>
            {data.results.map((r) => (
              <tr key={r.variable.id}>
                <td>{r.variable.label}</td>
                <td className={r.sen.per_decade > 0 ? 'up' : 'down'}>
                  {signed(r.sen.per_decade)} {r.unit}
                </td>
                <td>
                  {signed(r.sen.per_decade_ci[0])} to {signed(r.sen.per_decade_ci[1])}
                </td>
                <td>
                  <span className={`pill ${r.verdict.level}`}>{LEVEL_LABEL[r.verdict.level]}</span> {pText(r.mann_kendall.p_value)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </article>

      {Object.keys(corr).length > 0 && (
        <article className="sheet">
          <header>
            <h2>Do they move together?</h2>
          </header>
          <p className="prose lede">
            Correlation of the month-by-month anomalies. +1 means they rise and fall together, −1 means one rises as the
            other falls, 0 means no relationship.
          </p>
          <table className="table corr">
            <thead>
              <tr>
                <th />
                {ids.map((id) => (
                  <th key={id}>{catalog[id]?.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ids.map((a) => (
                <tr key={a}>
                  <th>{catalog[a]?.label}</th>
                  {ids.map((b) => (
                    <td key={b} style={{ background: corrColor(corr[a][b]) }}>
                      {corr[a][b].toFixed(2)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </article>
      )}
    </div>
  )
}
