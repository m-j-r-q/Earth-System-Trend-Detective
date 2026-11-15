const BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

async function get(path, params = {}) {
  const qs = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== null && v !== undefined && v !== '') qs.set(k, v)
  }
  const query = qs.toString()
  let res
  try {
    res = await fetch(`${BASE}${path}${query ? `?${query}` : ''}`)
  } catch {
    throw new Error('Cannot reach the data server. If it was idle it may still be waking up; try again in a moment.')
  }
  if (!res.ok) {
    let detail = res.statusText
    try {
      detail = (await res.json()).detail || detail
    } catch {
      /* keep statusText */
    }
    throw new Error(detail)
  }
  return res.json()
}

const win = (start, end) => ({
  start: start ? `${start}-01-01` : null,
  end: end ? `${end}-12-31` : null,
})

export const api = {
  health: () => get('/api/health'),
  regions: () => get('/api/regions'),
  variables: () => get('/api/variables'),
  analyze: (region, variable, start, end, alpha) =>
    get('/api/analyze', { region, variable, alpha, ...win(start, end) }),
  compareRegions: (variable, regions, start, end, alpha) =>
    get('/api/compare/regions', { variable, regions: regions.join(','), alpha, ...win(start, end) }),
  compareVariables: (region, variables, start, end, alpha) =>
    get('/api/compare/variables', { region, variables: variables.join(','), alpha, ...win(start, end) }),
}
