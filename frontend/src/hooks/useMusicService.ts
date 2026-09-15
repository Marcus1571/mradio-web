import { useCallback, useState } from 'react'
import type { MusicService } from '../api/types'

/** Session-only, never persisted. Every app launch (or reload) starts at
 * "no service" — the operator's explicit call, 2026-09-15: this used to
 * be saved server-side via /api/config like every other preference, but
 * that meant a listener who picked a service once, out of curiosity or
 * by accident, would keep spending music-service search-API quota
 * (particularly Apple's tighter iTunes Search limit) on every future
 * session whether they cared about the feature or not. A plain useState
 * with no persistence enforces "opt in for this session only" at the
 * source, rather than relying on remembering to click "Select one"
 * again after every reload. */
export function useMusicService() {
  const [service, setService] = useState<MusicService | null>(null)

  const setMusicService = useCallback((next: MusicService | null) => {
    setService(next)
  }, [])

  return { service, setMusicService, loading: false }
}
