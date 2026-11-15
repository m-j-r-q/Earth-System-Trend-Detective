import Plot, { INK, INK_2, TIDE, BERRY } from './Plot'
import { rolling } from '../lib/format'

/** Monthly series, its 12-month average, and the fitted (Sen) trend line. */
export default function SeriesChart({ result, mode }) {
  const s = result.series
  const anomaly = mode === 'anomaly'
  const y = anomaly ? s.anomalies : s.values
  // Trend lines are fitted on anomalies; shift by the mean to overlay them on raw values.
  const trend = anomaly ? s.trend_line : s.trend_line.map((v) => v + result.mean)
  const trendColor = result.sen.per_decade >= 0 ? BERRY : TIDE

  const data = [
    { x: s.dates, y, type: 'scatter', mode: 'lines', name: 'Monthly', line: { color: '#9FB1BC', width: 1 } },
    { x: s.dates, y: rolling(y, 12), type: 'scatter', mode: 'lines', name: '12-month average', line: { color: INK, width: 2 } },
    { x: s.dates, y: trend, type: 'scatter', mode: 'lines', name: 'Trend', line: { color: trendColor, width: 3, dash: 'dash' } },
  ]
  const layout = {
    yaxis: {
      title: { text: anomaly ? `Change from normal (${result.unit})` : result.unit, font: { color: INK_2 } },
      gridcolor: '#E1E8EA',
      zeroline: anomaly,
      zerolinecolor: INK_2,
    },
  }
  return <Plot data={data} layout={layout} height={300} />
}
