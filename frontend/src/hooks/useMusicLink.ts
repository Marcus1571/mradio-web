import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { MusicLinkResponse, MusicService } from '../api/types'

/** Resolves to the current track's public page URL on the active music
 * service, or null while unresolved / no confident match / no service
 * chosen yet. Keyed on both rawTitle and service — switching either
 * resets to null and re-fetches, per the agreed (track, active_service)
 * lookup shape. No debounce: the backend caches per (service, raw_title),
 * so repeated calls for the same pair are cheap and this hook doesn't
 * need to protect against them.
 *
 * service === null (no service picked yet, e.g. a fresh account) skips
 * the request entirely — there's nothing to search against, and the
 * caller (NowPlayingPanel) renders no icon at all in that state rather
 * than an inert greyed-out one, since there's no service to represent. */
export function useMusicLink(rawTitle: string, service: MusicService | null): string | null {
  const [url, setUrl] = useState<string | null>(null)

  useEffect(() => {
    setUrl(null)
    if (!rawTitle || !service) return
    let cancelled = false
    // service isn't sent — the backend resolves the active service itself
    // from the user's config (see routers/music_link.py), so a stale
    // client-side value can't return a mismatched URL. It's still a
    // dependency below purely to re-trigger this effect on switch.
    api
      .get<MusicLinkResponse>(`/api/music-link?raw_title=${encodeURIComponent(rawTitle)}`)
      .then((res) => {
        if (!cancelled) setUrl(res.url)
      })
      .catch(() => {
        if (!cancelled) setUrl(null)
      })
    return () => {
      cancelled = true
    }
  }, [rawTitle, service])

  return url
}
