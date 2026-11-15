import { useEffect } from 'react'
import Plot, { INK, INK_2 } from './Plot'
import { api } from '../api'
import { useFetch } from '../lib/useFetch'
import { LEVEL_LABEL, pText, rolling, signed, summarizeRegions } from '../lib/format'

export default function CompareRegions({ region, regions, catalog, config, setConfig, onCtx }) {
  // Variables that this region has; the comparison variable is chosen among them.
  const varOptions = region.variables
  const cmpVar = varOptions.includes(config.cmpVar) ? config.cmpVar : varOptions[0]
  const candidates = regions.filter((r) => r.variables.includes(cmpVar))
  const picked = config.cmpRegions.filter((id) => candidates.some((r) => r.id === id))
  const enabled = picked.length >= 2

  const { data, error, loading } = useFetch(
    () => api.compareRegions(cmpVar, picked, config.start, config.end, config.alpha),
    [cmpVar, picked.join(), config.start, config.end, config.alpha],
    enabled,
  )

  useEffect(() => {
    if (!data) return
    onCtx?.({
      summary: summarizeRegions(data.results),
      opposite: data.opposite_significant_trends
        ? 'Yes: at least two regions show statistically significant trends in opposite directions.'
        : 'No: no pair of regions has significant trends pointing in opposite directions.',
    })
  }, [data]) // eslint-disable-line react-hooks/exhaustive-deps

  const toggle = (id) =>
    setConfig((c) => ({
      ...c,
      cmpVar,
      cmpRegions: c.cmpRegions.includes(id) ? c.cmpRegions.filter((x) => x !== id) : [...c.cmpRegions, id],
    }))

  const controls = (
    <article className="sheet controls">
      <div className="field">
        <label htmlFor="cmpvar">Compare this measurement</label>
        <select id="cmpvar" value={cmpVar} onChange={(e) => setConfig((c) => ({ ...c, cmpVar: e.target.value }))}>
          {varOptions.map((v) => (
            <option key={v} value={v}>
              {catalog[v].label}
            </option>
          ))}
        </select>
      </div>
      <fieldset>
        <legend>across these regions (choose two or more)</legend>
        <div className="checks">
          {candidates.map((r) => (
            <label key={r.id} style={{ '--region': r.color }}>
              <input type="checkbox" checked={picked.includes(r.id)} onChange={() => toggle(r.id)} />
              <span className="dot" aria-hidden="true" />
              {r.name}
            </label>
          ))}
        </div>
      </fieldset>
    </article>
  )

  let body = null
  if (!enabled) {
    body = <p className="notice">Choose at least two regions to compare.</p>
  } else if (error) {
    body = <p className="notice">{error}</p>
  } else if (!data) {
    body = <p className="notice">Loading…</p>
  } else {
    const colorOf = Object.fromEntries(regions.map((r) => [r.id, r.color]))
    const unit = data.results[0].unit
    const overlay = data.results.map((r) => ({
      x: r.series.dates,
      y: rolling(r.series.anomalies_z, 12),
      type: 'scatter',
      mode: 'lines',
      name: r.region.name,
      line: { color: colorOf[r.region.id], width: 2.2 },
    }))
    const sorted = [...data.results].sort((a, b) => a.sen.per_decade - b.sen.per_decade)
    const forest = [
      {
        type: 'scatter',
        mode: 'markers',
        x: sorted.map((r) => r.sen.per_decade),
        y: sorted.map((r) => r.region.name),
        error_x: {
          type: 'data',
          symmetric: false,
          array: sorted.map((r) => r.sen.per_decade_ci[1] - r.sen.per_decade),
          arrayminus: sorted.map((r) => r.sen.per_decade - r.sen.per_decade_ci[0]),
          color: INK_2,
          thickness: 1.5,
        },
        marker: {
          size: 12,
          symbol: 'circle',
          color: sorted.map((r) => (r.mann_kendall.significant ? colorOf[r.region.id] : '#F8FAF8')),
          line: { color: sorted.map((r) => colorOf[r.region.id]), width: 2.5 },
        },
        hovertemplate: '%{y}: %{x:.3g}<extra></extra>',
        showlegend: false,
      },
    ]

    body = (
      <div className={loading ? 'stale' : ''} data-tour="tour-compare">
        {data.opposite_significant_trends && (
          <p className="callout">
            These regions are moving in opposite directions, and both trends are statistically significant. The same
            planet-wide processes can push one place up and another down.
          </p>
        )}
        <article className="sheet">
          <header>
            <div>
              <h2>Trend per decade</h2>
              <p className="meta">
                {catalog[cmpVar].label} · {unit}
              </p>
            </div>
          </header>
          <p className="prose lede">
            Each dot is the trend and each bar is its 95% range. Filled dots are significant; hollow dots are not. Bars
            crossing the zero line mean &ldquo;no change&rdquo; cannot be ruled out.
          </p>
          <Plot
            data={forest}
            height={90 + 52 * sorted.length}
            layout={{
              margin: { l: 150, r: 20, t: 10, b: 44 },
              hovermode: 'closest',
              xaxis: { title: { text: `Trend (${unit} per decade)`, font: { color: INK_2 } }, zeroline: true, zerolinecolor: INK, zerolinewidth: 1.5, gridcolor: '#E1E8EA' },
              yaxis: { automargin: true },
            }}
          />
        </article>

        <article className="sheet">
          <header>
            <h2>The same measurement over time</h2>
          </header>
          <p className="prose lede">12-month averages of the seasonal anomaly, scaled so regions with different ranges can share one axis.</p>
          <Plot
            data={overlay}
            height={320}
            layout={{ yaxis: { title: { text: 'Standard deviations from normal', font: { color: INK_2 } }, zeroline: true, zerolinecolor: INK_2, gridcolor: '#E1E8EA' } }}
          />
        </article>

        <article className="sheet">
          <table className="table">
            <thead>
              <tr>
                <th>Region</th>
                <th>Trend per decade</th>
                <th>95% range</th>
                <th>Verdict</th>
              </tr>
            </thead>
            <tbody>
              {data.results.map((r) => (
                <tr key={r.region.id}>
                  <td>{r.region.name}</td>
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
      </div>
    )
  }

  return (
    <div>
      {controls}
      {body}
    </div>
  )
}
