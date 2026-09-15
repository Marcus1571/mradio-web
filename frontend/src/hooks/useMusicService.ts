import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Config, MusicService } from '../api/types'

/** No default service — a fresh account (or one that's never touched the
 * dropdown) starts agnostic, with no music-service icon shown at all,
 * until the listener explicitly picks one. That choice is then persisted
 * server-side (via /api/config, same as every other saved preference) and
 * follows the account across devices. */
export function useMusicService() {
  const [config, setConfig] = useState<Config | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api
      .get<Config>('/api/config')
      .then((c) => {
        setConfig(c)
        setLoading(false)
      })
      .catch(() => {
        setConfig({})
        setLoading(false)
      })
  }, [])

  const service: MusicService | null =
    config?.music_service === 'spotify' || config?.music_service === 'deezer' || config?.music_service === 'apple'
      ? config.music_service
      : null

  const setMusicService = useCallback(async (next: MusicService) => {
    setConfig((c) => ({ ...c, music_service: next }))
    try {
      const updated = await api.patch<Config>('/api/config', { music_service: next })
      setConfig(updated)
    } catch {
      // Leave the optimistic value in place; the next refresh will reconcile.
    }
  }, [])

  return { service, setMusicService, loading }
}
