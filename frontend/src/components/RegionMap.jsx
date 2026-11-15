import { useEffect, useRef } from 'react'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { makeShapeWash } from '../lib/gradient'

const STYLE = 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json'
const box = ([w, s, e, n]) => [[[w, s], [e, s], [e, n], [w, n], [w, s]]]

/**
 * World map with each region drawn as a feathered, semi-transparent colour wash.
 * Each wash follows the region's real outline and fades toward its edge into the basemap.
 */
export default function RegionMap({ regions, hoveredId, onHover, onSelect }) {
  const container = useRef(null)
  const mapRef = useRef(null)
  const loaded = useRef(false)
  const prevHover = useRef(null)
  const handlers = useRef({})
  handlers.current = { onHover, onSelect }

  useEffect(() => {
    const map = new maplibregl.Map({
      container: container.current,
      style: STYLE,
      bounds: [[-125, -18], [105, 82]], // all seven regions, clear of the list panel on the left
      fitBoundsOptions: { padding: { left: 400, top: 30, right: 30, bottom: 30 } },
      minZoom: 0.8,
      attributionControl: { compact: true },
    })
    mapRef.current = map
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-right')
    const markers = []
    let cancelled = false

    // Real outlines (public-domain Natural Earth features). If the file is missing, fall back to boxes.
    const loadShapes = async () => {
      try {
        const res = await fetch(`${import.meta.env.BASE_URL}regions.geojson`)
        if (!res.ok) throw new Error(String(res.status))
        const fc = await res.json()
        return Object.fromEntries(fc.features.map((f) => [f.properties.id, f.geometry]))
      } catch {
        return {}
      }
    }

    map.on('load', async () => {
      const shapes = await loadShapes()
      if (cancelled) return
      const geometry = Object.fromEntries(
        regions.map((r) => [r.id, shapes[r.id] ?? { type: 'Polygon', coordinates: box(r.bbox) }]),
      )
      const wash = Object.fromEntries(regions.map((r) => [r.id, makeShapeWash(geometry[r.id], r.color)]))

      for (const r of regions) {
        map.addSource(`wash-${r.id}`, { type: 'image', url: wash[r.id].url, coordinates: wash[r.id].coordinates })
        map.addLayer({
          id: `wash-${r.id}`,
          type: 'raster',
          source: `wash-${r.id}`,
          paint: { 'raster-opacity': 0.85, 'raster-fade-duration': 0, 'raster-resampling': 'linear' },
        })
        const label = document.createElement('div')
        label.className = 'map-label'
        label.textContent = r.name
        markers.push(new maplibregl.Marker({ element: label, anchor: 'top', offset: [0, 10] }).setLngLat(wash[r.id].labelLngLat).addTo(map))
      }

      map.addSource('regions', {
        type: 'geojson',
        promoteId: 'id',
        data: {
          type: 'FeatureCollection',
          features: regions.map((r) => ({
            type: 'Feature',
            properties: { id: r.id },
            geometry: geometry[r.id],
          })),
        },
      })
      map.addSource('dots', {
        type: 'geojson',
        promoteId: 'id',
        data: {
          type: 'FeatureCollection',
          features: regions.map((r) => ({
            type: 'Feature',
            properties: { id: r.id, color: r.color },
            geometry: { type: 'Point', coordinates: wash[r.id].labelLngLat },
          })),
        },
      })
      // Invisible-but-queryable hit area covering the real outline.
      map.addLayer({ id: 'region-hit', type: 'fill', source: 'regions', paint: { 'fill-color': '#ffffff', 'fill-opacity': 0.01 } })
      // A faint outline always shows the true boundary; it darkens on hover.
      map.addLayer({
        id: 'region-outline',
        type: 'line',
        source: 'regions',
        paint: {
          'line-color': '#12212E',
          'line-width': ['case', ['boolean', ['feature-state', 'hover'], false], 1.8, 0.9],
          'line-opacity': ['case', ['boolean', ['feature-state', 'hover'], false], 0.85, 0.3],
        },
      })
      // A dot at each centre keeps small regions findable at world zoom.
      map.addLayer({
        id: 'region-dot',
        type: 'circle',
        source: 'dots',
        paint: {
          'circle-radius': ['case', ['boolean', ['feature-state', 'hover'], false], 8, 5],
          'circle-color': ['get', 'color'],
          'circle-stroke-color': '#ffffff',
          'circle-stroke-width': 2,
        },
      })

      for (const layer of ['region-hit', 'region-dot']) {
        map.on('mousemove', layer, (e) => {
          const id = e.features?.[0]?.id
          if (id == null) return
          map.getCanvas().style.cursor = 'pointer'
          handlers.current.onHover(String(id), { x: e.point.x, y: e.point.y })
        })
        map.on('mouseleave', layer, () => {
          map.getCanvas().style.cursor = ''
          handlers.current.onHover(null)
        })
        map.on('click', layer, (e) => {
          const id = e.features?.[0]?.id
          if (id != null) handlers.current.onSelect(String(id))
        })
      }
      loaded.current = true
    })

    return () => {
      cancelled = true
      loaded.current = false
      markers.forEach((m) => m.remove())
      map.remove()
    }
    // The map is built once; regions never change after the first load.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Reflect the hovered region (from the map or from the list) on the map.
  useEffect(() => {
    const map = mapRef.current
    if (!map || !loaded.current) return
    const setState = (id, on) => {
      if (!id) return
      for (const source of ['regions', 'dots']) map.setFeatureState({ source, id }, { hover: on })
      map.setPaintProperty(`wash-${id}`, 'raster-opacity', on ? 1 : 0.85)
    }
    setState(prevHover.current, false)
    setState(hoveredId, true)
    prevHover.current = hoveredId
  }, [hoveredId])

  return <div ref={container} className="map" role="application" aria-label="Map of regions you can analyze" />
}
