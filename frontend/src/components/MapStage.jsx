import { useRef, useState } from 'react'
import RegionMap from './RegionMap'

function HoverCard({ region, catalog, pos, bounds }) {
  const width = 320
  const flip = pos.x + width + 40 > bounds.width
  const style = {
    left: flip ? pos.x - width - 18 : pos.x + 18,
    top: Math.max(8, Math.min(pos.y - 10, bounds.height - 260)),
    width,
    '--region': region.color,
  }
  return (
    <div className="hovercard" style={style} role="status">
      <h3>{region.name}</h3>
      <p className="biome">{region.biome}</p>
      <p className="prose">{region.summary}</p>
      <p className="avail">
        Available: {region.variables.map((v) => catalog[v]?.label).filter(Boolean).join(', ')}.
      </p>
      <p className="hint">Click to open this region.</p>
    </div>
  )
}

export default function MapStage({ regions, catalog, onSelect, onDemos }) {
  const [hover, setHover] = useState({ id: null, pos: null })
  const wrap = useRef(null)
  const bounds = wrap.current?.getBoundingClientRect() ?? { width: 1000, height: 700 }
  const hovered = regions.find((r) => r.id === hover.id)

  return (
    <div className="mapstage" ref={wrap}>
      <RegionMap
        regions={regions}
        hoveredId={hover.id}
        onHover={(id, pos) => setHover({ id, pos: pos ?? null })}
        onSelect={onSelect}
      />

      <nav className="index" aria-label="Regions">
        <h2>Where do you want to look?</h2>
        <p className="prose">
          Each coloured patch is a region with satellite and model data ready to analyze. Choose one on the map or from
          this list.
        </p>
        <ul>
          {regions.map((r) => (
            <li key={r.id} style={{ '--region': r.color }}>
              <button
                className={hover.id === r.id ? 'on' : ''}
                onMouseEnter={() => setHover({ id: r.id, pos: null })}
                onMouseLeave={() => setHover({ id: null, pos: null })}
                onFocus={() => setHover({ id: r.id, pos: null })}
                onBlur={() => setHover({ id: null, pos: null })}
                onClick={() => onSelect(r.id)}
              >
                <span className="dot" aria-hidden="true" />
                <span className="name">{r.name}</span>
                <span className="meta">{r.biome}</span>
              </button>
            </li>
          ))}
        </ul>
        <p className="prose small">
          New here? <button className="link" onClick={onDemos}>Watch a guided demo</button> first.
        </p>
      </nav>

      {hovered && hover.pos && <HoverCard region={hovered} catalog={catalog} pos={hover.pos} bounds={bounds} />}
    </div>
  )
}
