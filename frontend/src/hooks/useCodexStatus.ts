import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { CodexStatus } from '../api/types'

/** Polls /api/settings/codex/status every 3s only while a device-code
 * login is pending, so the settings page can flip from "waiting" to
 * "connected" without the admin needing to refresh the page. */
export function useCodexStatus() {
  const [status, setStatus] = useState<CodexStatus | null>(null)
  const pollingRef = useRef(false)

  const refresh = useCallback(async () => {
    const res = await api.get<CodexStatus>('/api/settings/codex/status')
    setStatus(res)
    return res
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  useEffect(() => {
    if (!status?.pending || pollingRef.current) return
    pollingRef.current = true
    let cancelled = false
    const id = window.setInterval(async () => {
      const res = await refresh()
      if (!cancelled && !res.pending) {
        window.clearInterval(id)
        pollingRef.current = false
      }
    }, 3000)
    return () => {
      cancelled = true
      window.clearInterval(id)
      pollingRef.current = false
    }
  }, [status?.pending, refresh])

  return { status, refresh }
}
