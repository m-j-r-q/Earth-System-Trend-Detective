import { useEffect } from 'react'
import { DEMOS } from '../demos'

export default function DemoPanel({ regions, onStart, onClose }) {
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const nameOf = (id) => regions.find((r) => r.id === id)?.name

  return (
    <div className="modal" role="dialog" aria-modal="true" aria-labelledby="demo-title" onClick={onClose}>
      <div className="modalbody" onClick={(e) => e.stopPropagation()}>
        <header>
          <h2 id="demo-title">Guided demos</h2>
          <button className="link" onClick={onClose}>Close</button>
        </header>
        <p className="prose">
          Each demo walks through a real question step by step. The numbers in the explanations come from the live data,
          so you see exactly what the tool finds.
        </p>
        <ul className="demolist">
          {DEMOS.map((d) => (
            <li key={d.id}>
              <div>
                <h3>{d.title}</h3>
                <p className="prose">{d.blurb}</p>
                <p className="meta">
                  {[d.region, ...(d.cmpRegions ?? [])]
                    .filter((v, i, a) => a.indexOf(v) === i)
                    .map(nameOf)
                    .filter(Boolean)
                    .join(', ')}
                </p>
              </div>
              <button className="primary" onClick={() => onStart(d)}>
                Start demo
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
