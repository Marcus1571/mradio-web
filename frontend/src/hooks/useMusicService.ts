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
    // Deliberately NOT optimistic: `service` here also drives useMusicLink's
    // effect (see NowPlayingPanel.tsx), which fires a GET /api/music-link the
    // instant `service` changes. That endpoint resolves the active service
    // itself server-side from the persisted config (routers/music_link.py),
    // not from anything the client sends — so if `service` flips client-side
    // BEFORE this PATCH has actually landed, the GET can race ahead of it,
    // read the still-old service from disk, and return a URL for the OLD
    // service tagged (client-side) as belonging to the NEW one. Confirmed
    // live 2026-09-15: switching Spotify -> Apple Music opened a Spotify
    // link on a click that landed in that window, despite the icon already
    // showing "resolved" for Apple Music. Waiting for the PATCH to resolve
    // before updating `service` closes the race at its actual source,
    // rather than trying to detect the mismatch after the fact.
    try {
      const updated = await api.patch<Config>('/api/config', { music_service: next })
      setConfig(updated)
    } catch {
      // Leave the previous value in place; the next refresh will reconcile.
    }
  }, [])

  return { service, setMusicService, loading }
}
