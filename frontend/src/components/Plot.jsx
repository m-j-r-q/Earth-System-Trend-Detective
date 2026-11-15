import Plotly from 'plotly.js-cartesian-dist-min'
import createPlotlyComponent from 'react-plotly.js/factory'

// Vite hands CommonJS packages over as `default` in some builds and not in others.
const factory = createPlotlyComponent.default || createPlotlyComponent
const PlotlyLib = Plotly.default || Plotly
const PlotlyPlot = factory(PlotlyLib)

export const INK = '#12212E'
export const INK_2 = '#4A5B68'
export const HAIR = '#CBD5D8'
export const TIDE = '#1F6FA8'
export const BERRY = '#A8326B'

export const baseLayout = {
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor: 'rgba(0,0,0,0)',
  font: { family: 'Bricolage Grotesque, system-ui, sans-serif', color: INK, size: 12 },
  margin: { l: 54, r: 14, t: 10, b: 36 },
  xaxis: { gridcolor: '#E1E8EA', linecolor: HAIR, zeroline: false },
  yaxis: { gridcolor: '#E1E8EA', linecolor: HAIR },
  legend: { orientation: 'h', y: 1.14, x: 0 },
  hovermode: 'x unified',
}

export default function Plot({ data, layout, height = 320 }) {
  return (
    <PlotlyPlot
      data={data}
      layout={{ ...baseLayout, ...layout, height, autosize: true }}
      config={{ displaylogo: false, responsive: true, modeBarButtonsToRemove: ['lasso2d', 'select2d', 'autoScale2d'] }}
      useResizeHandler
      style={{ width: '100%' }}
    />
  )
}
