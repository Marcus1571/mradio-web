import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Config } from '../api/types'

/** One-shot fetch of the user's persisted config (theme, volume, mute,
 * last-played station) — used once on dashboard mount to restore state. */
export function useInitialConfig() {
  const [config, setConfig] = useState<Config | null>(null)

  useEffect(() => {
    api
      .get<Config>('/api/config')
      .then(setConfig)
      .catch(() => setConfig({}))
  }, [])

  return config
}
