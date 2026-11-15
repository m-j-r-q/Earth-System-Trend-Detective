import { useEffect, useState } from 'react'

/**
 * Runs `fetcher` whenever `deps` change (debounced), keeping the previous data on screen while
 * the next request is in flight. Set `enabled` false to skip fetching.
 */
export function useFetch(fetcher, deps, enabled = true) {
  const [state, setState] = useState({ data: null, error: null, loading: false })

  useEffect(() => {
    if (!enabled) {
      setState({ data: null, error: null, loading: false })
      return undefined
    }
    let cancelled = false
    setState((s) => ({ ...s, loading: true, error: null }))
    const timer = setTimeout(() => {
      fetcher()
        .then((data) => !cancelled && setState({ data, error: null, loading: false }))
        .catch((e) => !cancelled && setState({ data: null, error: e.message, loading: false }))
    }, 200)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, enabled])

  return state
}
