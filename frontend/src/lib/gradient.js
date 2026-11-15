const smooth = (a, b, x) => {
  const t = Math.min(1, Math.max(0, (x - a) / (b - a)))
  return t * t * (3 - 2 * t)
}

/** Opacity of the region overlay at (u, v) in [0,1]²: zero on the edge, fading in toward the middle. */
export function gradientAlpha(u, v) {
  const d = Math.min(u, 1 - u, v, 1 - v)
  return 0.62 * smooth(0, 0.32, d)
}

export function hexToRgb(hex) {
  const h = hex.replace('#', '')
  return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16))
}

/** Feathered, semi-transparent PNG for a map image source: the box melts into the basemap at its edges. */
export function makeGradientDataURL(hex, size = 192) {
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = size
  const ctx = canvas.getContext('2d')
  const img = ctx.createImageData(size, size)
  const [r, g, b] = hexToRgb(hex)
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const u = (x + 0.5) / size
      const v = (y + 0.5) / size
      const d = Math.min(u, 1 - u, v, 1 - v)
      const deepen = 1 - 0.28 * smooth(0.05, 0.5, d) // slightly darker toward the middle
      const i = (y * size + x) * 4
      img.data[i] = r * deepen
      img.data[i + 1] = g * deepen
      img.data[i + 2] = b * deepen
      img.data[i + 3] = Math.round(255 * gradientAlpha(u, v))
    }
  }
  ctx.putImageData(img, 0, 0)
  return canvas.toDataURL('image/png')
}

// ---- real-shape washes ------------------------------------------------------------------------

const RAD = Math.PI / 180
/** Web-mercator y (in radians-of-latitude units). Map images are stretched linearly in this space. */
export const mercY = (lat) => Math.log(Math.tan(Math.PI / 4 + (lat * RAD) / 2))
export const invMercY = (y) => (2 * Math.atan(Math.exp(y)) - Math.PI / 2) / RAD

/** Distance (in pixels) from every inside pixel to the nearest outside pixel. Two-pass chamfer. */
export function distanceInside(inside, w, h) {
  const INF = 1e9
  const d = new Float32Array(w * h)
  for (let i = 0; i < d.length; i++) d[i] = inside[i] ? INF : 0
  const A = 1
  const B = Math.SQRT2
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const i = y * w + x
      if (!d[i]) continue
      let v = d[i]
      if (x > 0) v = Math.min(v, d[i - 1] + A)
      else v = Math.min(v, A)
      if (y > 0) {
        v = Math.min(v, d[i - w] + A)
        if (x > 0) v = Math.min(v, d[i - w - 1] + B)
        if (x < w - 1) v = Math.min(v, d[i - w + 1] + B)
      } else v = Math.min(v, A)
      d[i] = v
    }
  }
  for (let y = h - 1; y >= 0; y--) {
    for (let x = w - 1; x >= 0; x--) {
      const i = y * w + x
      if (!d[i]) continue
      let v = d[i]
      if (x < w - 1) v = Math.min(v, d[i + 1] + A)
      else v = Math.min(v, A)
      if (y < h - 1) {
        v = Math.min(v, d[i + w] + A)
        if (x < w - 1) v = Math.min(v, d[i + w + 1] + B)
        if (x > 0) v = Math.min(v, d[i + w - 1] + B)
      } else v = Math.min(v, A)
      d[i] = v
    }
  }
  return d
}

function polygonsOf(geometry) {
  return geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.coordinates
}

/** Bounds of a (Multi)Polygon: [west, south, east, north]. */
export function geometryBounds(geometry) {
  let w = 180, s = 90, e = -180, n = -90
  for (const poly of polygonsOf(geometry))
    for (const [x, y] of poly[0]) {
      w = Math.min(w, x); e = Math.max(e, x); s = Math.min(s, y); n = Math.max(n, y)
    }
  return [w, s, e, n]
}

/**
 * Soft colour wash that follows the real outline of a region.
 * Returns { url, coordinates, labelLngLat } for a MapLibre image source.
 * The shape is drawn in mercator space so the image lines up with the basemap, then the opacity
 * fades from a faint edge to a stronger core according to the distance from the edge.
 */
export function makeShapeWash(geometry, hex, maxPx = 640) {
  const pad = 0.04
  let [w, s, e, n] = geometryBounds(geometry)
  const dx = (e - w) * pad
  w -= dx; e += dx
  const yS = mercY(Math.max(-84, s)), yN = mercY(Math.min(84, n))
  const dy = (yN - yS) * pad
  const y0 = yS - dy, y1 = yN + dy
  s = invMercY(y0); n = invMercY(y1)

  const spanX = (e - w) * RAD
  const spanY = y1 - y0
  const scale = maxPx / Math.max(spanX, spanY)
  const W = Math.max(8, Math.round(spanX * scale))
  const H = Math.max(8, Math.round(spanY * scale))

  const canvas = document.createElement('canvas')
  canvas.width = W
  canvas.height = H
  const ctx = canvas.getContext('2d', { willReadFrequently: true })
  ctx.fillStyle = '#000'
  ctx.beginPath()
  for (const poly of polygonsOf(geometry))
    for (const ring of poly) {
      ring.forEach(([lng, lat], i) => {
        const px = ((lng - w) * RAD) * scale
        const py = (y1 - mercY(Math.max(-84, Math.min(84, lat)))) * scale
        if (i === 0) ctx.moveTo(px, py)
        else ctx.lineTo(px, py)
      })
      ctx.closePath()
    }
  ctx.fill('evenodd')

  const mask = ctx.getImageData(0, 0, W, H).data
  const inside = new Uint8Array(W * H)
  for (let i = 0; i < inside.length; i++) inside[i] = mask[i * 4 + 3] > 127 ? 1 : 0
  const dist = distanceInside(inside, W, H)

  let maxD = 0, mx = W / 2, my = H / 2
  for (let i = 0; i < dist.length; i++)
    if (dist[i] > maxD) { maxD = dist[i]; mx = i % W; my = (i / W) | 0 }

  const ramp = Math.max(3, maxD * 0.7)
  const [r, g, b] = hexToRgb(hex)
  const img = ctx.createImageData(W, H)
  for (let i = 0; i < dist.length; i++) {
    const cov = mask[i * 4 + 3] / 255 // antialiased coverage keeps the edge smooth
    const t = smooth(0, ramp, dist[i])
    const a = cov * (0.26 + 0.38 * t)
    const deepen = 1 - 0.28 * t
    img.data[i * 4] = r * deepen
    img.data[i * 4 + 1] = g * deepen
    img.data[i * 4 + 2] = b * deepen
    img.data[i * 4 + 3] = Math.round(255 * a)
  }
  ctx.putImageData(img, 0, 0)

  return {
    url: canvas.toDataURL('image/png'),
    coordinates: [[w, n], [e, n], [e, s], [w, s]],
    labelLngLat: [w + (mx / scale) / RAD, invMercY(y1 - my / scale)],
  }
}
