import { useCallback, useEffect, useState } from "react"

// Tiny data hook: { data, error, loading, retry } for any async fn.
export function useAsync(fn, deps = []) {
  const [state, setState] = useState({ data: null, error: null, loading: true })
  const [tick, setTick] = useState(0)

  useEffect(() => {
    let cancelled = false
    // eslint-disable-next-line react-hooks/set-state-in-effect -- standard fetch-hook reset on refetch
    setState((s) => ({ ...s, error: null, loading: true }))
    fn().then(
      (data) => !cancelled && setState({ data, error: null, loading: false }),
      (error) => !cancelled && setState({ data: null, error, loading: false })
    )
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick])

  const retry = useCallback(() => setTick((t) => t + 1), [])
  return { ...state, retry }
}
