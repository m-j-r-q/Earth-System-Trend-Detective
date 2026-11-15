import { describe, expect, it } from 'vitest'
import { fillTemplate, rolling, sig, signed, pval, strongestLink } from './format'
import { gradientAlpha, hexToRgb } from './gradient'

describe('format', () => {
  it('formats numbers with sign and precision', () => {
    expect(signed(0.34567)).toBe('+0.346')
    expect(signed(-12.3456)).toBe('-12.3')
    expect(sig(1234.5)).toBe('1230')
    expect(sig(NaN)).toBe('—')
  })
  it('formats p-values', () => {
    expect(pval(0.0001)).toBe('<0.001')
    expect(pval(0.04567)).toBe('0.046')
  })
  it('computes a trailing moving average', () => {
    const r = rolling([1, 2, 3, 4], 2)
    expect(r).toEqual([null, 1.5, 2.5, 3.5])
  })
  it('fills templates, with an ellipsis for unknown values', () => {
    expect(fillTemplate('a {{x}} b {{y.z}} c {{nope}}', { x: 1, y: { z: 2 } })).toBe('a 1 b 2 c …')
    expect(fillTemplate('{{prev.p}}', {})).toBe('…')
  })
  it('finds the strongest correlation pair', () => {
    const corr = { A: { A: 1, B: 0.2, C: -0.7 }, B: { A: 0.2, B: 1, C: 0.1 }, C: { A: -0.7, B: 0.1, C: 1 } }
    expect(strongestLink(corr, { A: 'a', B: 'b', C: 'c' })).toContain('a and c')
  })
})

describe('gradient', () => {
  it('is transparent on the edge and strongest in the middle', () => {
    expect(gradientAlpha(0, 0.5)).toBe(0)
    expect(gradientAlpha(0.5, 0.5)).toBeGreaterThan(0.5)
    expect(gradientAlpha(0.5, 0.5)).toBeLessThanOrEqual(0.62)
  })
  it('is symmetric', () => {
    expect(gradientAlpha(0.1, 0.4)).toBeCloseTo(gradientAlpha(0.9, 0.6))
  })
  it('parses hex colours', () => {
    expect(hexToRgb('#2e7d32')).toEqual([46, 125, 50])
  })
})

import { distanceInside, invMercY, mercY, geometryBounds } from './gradient'

describe('shape helpers', () => {
  it('round-trips mercator latitude', () => {
    expect(invMercY(mercY(37.5))).toBeCloseTo(37.5, 6)
  })
  it('measures distance to the nearest outside pixel', () => {
    const w = 9, h = 9
    const inside = new Uint8Array(w * h).fill(1)
    const d = distanceInside(inside, w, h)
    expect(d[0]).toBeCloseTo(1)
    expect(d[4 * w + 4]).toBeCloseTo(5)
    inside[0] = 0
    expect(distanceInside(inside, w, h)[0]).toBe(0)
  })
  it('finds the bounds of a multipolygon', () => {
    const g = { type: 'MultiPolygon', coordinates: [[[[0, 0], [2, 0], [2, 1], [0, 0]]], [[[5, 5], [6, 5], [6, 7], [5, 5]]]] }
    expect(geometryBounds(g)).toEqual([0, 0, 6, 7])
  })
})
