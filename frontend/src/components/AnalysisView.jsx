import { useEffect, useState } from 'react'
import Rail from './Rail'
import VariableSheet from './VariableSheet'
import CompareVariables from './CompareVariables'
import CompareRegions from './CompareRegions'
import DemoGuide from './DemoGuide'
import { api } from '../api'
import { useFetch } from '../lib/useFetch'
import { ctxFromResult } from '../lib/format'

const TABS = [
  ['trends', 'Trends'],
  ['vars', 'Compare Variables'],
  ['regions', 'Compare Regions'],
]

export default function AnalysisView({ region, regions, catalog, config, setConfig, demo, goStep, exitDemo }) {
  const [ctxs, setCtxs] = useState({})
  const vars = config.variables
  const onTrends = config.tab === 'trends'

  const { data, loading } = useFetch(
    () =>
      Promise.all(
        vars.map((v) =>
          api
            .analyze(region.id, v, config.start, config.end, config.alpha)
            .then((result) => ({ id: v, result }))
            .catch((e) => ({ id: v, error: e.message })),
        ),
      ),
    [region.id, vars.join(), config.start, config.end, config.alpha],
    onTrends && vars.length > 0,
  )

  // The guide quotes the first variable that analyzed successfully.
  useEffect(() => {
    const first = data?.find((d) => d.result)
    if (first) setCtxs((c) => ({ ...c, trends: ctxFromResult(first.result) }))
  }, [data])

  const setCtx = (tab) => (ctx) => setCtxs((c) => ({ ...c, [tab]: ctx }))

  return (
    <div className="analysis">
      <Rail region={region} catalog={catalog} config={config} setConfig={setConfig} />

      <section className="report">
        <div className="tabs" role="tablist">
          {TABS.map(([id, label]) => (
            <button
              key={id}
              role="tab"
              aria-selected={config.tab === id}
              className={config.tab === id ? 'on' : ''}
              onClick={() => setConfig((c) => ({ ...c, tab: id }))}
            >
              {label}
            </button>
          ))}
        </div>

        {onTrends && vars.length === 0 && (
          <p className="notice">Choose at least one measurement on the left to see its trend.</p>
        )}
        {onTrends && vars.length > 0 && !data && <p className="notice">Loading…</p>}
        {onTrends && data && (
          <div className={loading ? 'stale' : ''}>
            {data.map((d, i) => (
              <VariableSheet
                key={d.id}
                result={d.result}
                error={d.error}
                label={catalog[d.id]?.label ?? d.id}
                first={i === 0}
              />
            ))}
          </div>
        )}
        {config.tab === 'vars' && (
          <CompareVariables region={region} catalog={catalog} config={config} onCtx={setCtx('vars')} />
        )}
        {config.tab === 'regions' && (
          <CompareRegions
            region={region}
            regions={regions}
            catalog={catalog}
            config={config}
            setConfig={setConfig}
            onCtx={setCtx('regions')}
          />
        )}
      </section>

      {demo && (
        <DemoGuide
          demo={demo.def}
          step={demo.step}
          goStep={goStep}
          ctx={ctxs[config.tab] ?? null}
          busy={loading}
          onExit={exitDemo}
        />
      )}
    </div>
  )
}
