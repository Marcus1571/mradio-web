import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { GrokStatus } from '../api/types'

/** Polls /api/settings/grok/status every 3s only while a device-code
 * login is pending — mirrors useCodexStatus.ts exactly. Unlike Codex's
 * background asyncio.Task, the backend's OAuth poll loop for Grok is
 * itself driven by this same status endpoint (see routers/grok.py's
 * grok_status()), so this polling isn't just a UI convenience here —
 * it's what actually advances the login. */
export function useGrokStatus() {
  const [status, setStatus] = useState<GrokStatus | null>(null)
  const pollingRef = useRef(false)

  const refresh = useCallback(async () => {
    const res = await api.get<GrokStatus>('/api/settings/grok/status')
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
