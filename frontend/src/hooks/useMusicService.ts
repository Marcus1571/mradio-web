import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Config, MusicService } from '../api/types'

const DEFAULT_SERVICE: MusicService = 'spotify'

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

  const service: MusicService =
    config?.music_service === 'spotify' || config?.music_service === 'deezer'
      ? config.music_service
      : DEFAULT_SERVICE

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
