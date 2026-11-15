import { useCallback, useEffect, useState } from 'react'
import { api } from './api'
import MapStage from './components/MapStage'
import AnalysisView from './components/AnalysisView'
import DemoPanel from './components/DemoPanel'

const BASE_CONFIG = { variables: [], start: null, end: null, alpha: 0.05, tab: 'trends', cmpVar: null, cmpRegions: [] }

/** Configuration for a given demo step, limited to what is actually cached. */
function demoConfig(def, regions, stepIndex) {
  const region = regions.find((r) => r.id === def.region)
  let variables = def.variables.filter((v) => region.variables.includes(v))
  if (!variables.length) variables = region.default_variables
  const cmpVar = def.cmpVar && region.variables.includes(def.cmpVar) ? def.cmpVar : variables[0]
  const cmpRegions = (def.cmpRegions ?? []).filter((id) => regions.find((r) => r.id === id)?.variables.includes(cmpVar))
  return { ...BASE_CONFIG, variables, cmpVar, cmpRegions, ...def.steps[stepIndex].set }
}

function Splash({ error, onRetry }) {
  return (
    <main className="splash">
      <h1>Earth System Trend Detective</h1>
      {error ? (
        <>
          <p className="notice">{error}</p>
          <button className="primary" onClick={onRetry}>Try again</button>
        </>
      ) : (
        <p className="prose">Waking up the data server…</p>
      )}
    </main>
  )
}

export default function App() {
  const [boot, setBoot] = useState({ loading: true, error: null, regions: [], catalog: {}, health: null })
  const [regionId, setRegionId] = useState(null)
  const [config, setConfig] = useState(BASE_CONFIG)
  const [demo, setDemo] = useState(null)
  const [showDemos, setShowDemos] = useState(false)

  const load = useCallback(() => {
    setBoot((b) => ({ ...b, loading: true, error: null }))
    Promise.all([api.regions(), api.variables(), api.health()])
      .then(([regions, catalog, health]) => setBoot({ loading: false, error: null, regions, catalog, health }))
      .catch((e) => setBoot((b) => ({ ...b, loading: false, error: e.message })))
  }, [])
  useEffect(load, [load])

  const { regions, catalog, health } = boot
  const region = regions.find((r) => r.id === regionId)

  const selectRegion = (id) => {
    const r = regions.find((x) => x.id === id)
    const variables = r.default_variables.length ? r.default_variables : r.variables.slice(0, 2)
    setDemo(null)
    setConfig({ ...BASE_CONFIG, variables, cmpVar: variables[0], cmpRegions: [id] })
    setRegionId(id)
  }

  const startDemo = (def) => {
    setConfig(demoConfig(def, regions, 0))
    setDemo({ def, step: 0 })
    setRegionId(def.region)
    setShowDemos(false)
  }

  const goStep = (i) => {
    setDemo((d) => ({ ...d, step: i }))
    setConfig((c) => ({ ...c, ...demo.def.steps[i].set }))
  }

  const backToMap = () => {
    setDemo(null)
    setRegionId(null)
  }

  if (boot.loading && !regions.length) return <Splash />
  if (boot.error && !regions.length) return <Splash error={boot.error} onRetry={load} />
  if (!regions.length) {
    return <Splash error="No data is cached on the server yet. Run the cache builder, or the synthetic data script, and reload." onRetry={load} />
  }

  return (
    <div className="app">
      <header className="top">
        <button className="brand" onClick={backToMap} aria-label="Earth System Trend Detective, back to the map">
          Earth System Trend Detective
        </button>
        <nav>
          {region && <button className="link" onClick={backToMap}>All regions</button>}
          <button className="link" onClick={() => setShowDemos(true)}>Guided demos</button>
        </nav>
      </header>

      {health?.data?.synthetic && (
        <p className="banner" role="alert">
          This server is using synthetic practice data, not NASA measurements. Do not draw conclusions from it.
        </p>
      )}

      <main className="stage">
        {region ? (
          <AnalysisView
            key={`${region.id}-${demo?.def.id ?? 'free'}`}
            region={region}
            regions={regions}
            catalog={catalog}
            config={config}
            setConfig={setConfig}
            demo={demo}
            goStep={goStep}
            exitDemo={() => setDemo(null)}
          />
        ) : (
          <MapStage regions={regions} catalog={catalog} onSelect={selectRegion} onDemos={() => setShowDemos(true)} />
        )}
      </main>

      <footer className="foot">
        Data: NASA MERRA-2, GLDAS and GPM IMERG, averaged over each region&rsquo;s box. Built for the NASA Space Apps Challenge.
      </footer>

      {showDemos && <DemoPanel regions={regions} onStart={startDemo} onClose={() => setShowDemos(false)} />}
    </div>
  )
}
