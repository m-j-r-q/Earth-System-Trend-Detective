import { useEffect, useState } from 'react'

function YearInput({ label, value, min, max, placeholder, onCommit }) {
  const [text, setText] = useState(value ?? '')
  useEffect(() => setText(value ?? ''), [value])
  const commit = () => {
    const n = parseInt(text, 10)
    if (!text) return onCommit(null)
    if (Number.isFinite(n) && n >= min && n <= max) return onCommit(n)
    setText(value ?? '')
  }
  return (
    <label className="year">
      <span>{label}</span>
      <input
        inputMode="numeric"
        value={text}
        placeholder={placeholder}
        onChange={(e) => setText(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => e.key === 'Enter' && e.currentTarget.blur()}
      />
    </label>
  )
}

const fmtBox = ([w, s, e, n]) => {
  const lon = (v) => `${Math.abs(v)}°${v < 0 ? 'W' : 'E'}`
  const lat = (v) => `${Math.abs(v)}°${v < 0 ? 'S' : 'N'}`
  return `${lon(w)} to ${lon(e)}, ${lat(s)} to ${lat(n)}`
}

export default function Rail({ region, catalog, config, setConfig }) {
  const [open, setOpen] = useState(null)
  const toggle = (id) =>
    setConfig((c) => ({
      ...c,
      variables: c.variables.includes(id) ? c.variables.filter((v) => v !== id) : [...c.variables, id],
    }))

  return (
    <aside className="rail">
      <section data-tour="tour-region" style={{ '--region': region.color }} className="regionhead">
        <h2>{region.name}</h2>
        <p className="biome">{region.biome}</p>
        <p className="prose">{region.summary}</p>
        <p className="prose small">
          Numbers are averaged over the rectangle {fmtBox(region.bbox)} that encloses this region.
        </p>
      </section>

      <section data-tour="tour-variables">
        <h3>What to measure</h3>
        <ul className="varlist">
          {region.variables.map((id) => {
            const v = catalog[id]
            return (
              <li key={id}>
                <div className="varrow">
                  <label>
                    <input type="checkbox" checked={config.variables.includes(id)} onChange={() => toggle(id)} />
                    <span className="vname">{v.label}</span>
                    <span className="vsrc">{v.source}</span>
                  </label>
                  <button
                    className="info"
                    aria-expanded={open === id}
                    aria-label={`What is ${v.label}?`}
                    onClick={() => setOpen(open === id ? null : id)}
                  >
                    i
                  </button>
                </div>
                {open === id && (
                  <div className="vardef prose">
                    <p>{v.definition}</p>
                    <p>
                      <b>Why it matters:</b> {v.why_it_matters}
                    </p>
                  </div>
                )}
              </li>
            )
          })}
        </ul>
      </section>

      <section data-tour="tour-dates">
        <h3>Time window</h3>
        <div className="years">
          <YearInput label="From" value={config.start} min={1948} max={2026} placeholder="start" onCommit={(n) => setConfig((c) => ({ ...c, start: n }))} />
          <YearInput label="To" value={config.end} min={1948} max={2026} placeholder="latest" onCommit={(n) => setConfig((c) => ({ ...c, end: n }))} />
        </div>
        <button className="link" onClick={() => setConfig((c) => ({ ...c, start: null, end: null }))}>
          Use the full record
        </button>
        <p className="prose small">Short windows give noisy trends. Try changing the years and watch the verdict.</p>
      </section>

      <section>
        <h3>How sure must we be?</h3>
        <div className="seg" role="group" aria-label="Significance level">
          {[0.1, 0.05, 0.01].map((a) => (
            <button key={a} className={config.alpha === a ? 'on' : ''} onClick={() => setConfig((c) => ({ ...c, alpha: a }))}>
              {Math.round((1 - a) * 100)}%
            </button>
          ))}
        </div>
      </section>
    </aside>
  )
}
