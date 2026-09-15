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
 * than an inert greyed-out one, since there's no service to represent.
 *
 * The fetched url is stored tagged with the service it was resolved for.
 * useEffect's own reset (setResult(... url: null)) only runs AFTER the
 * render that already picked up a new `service` commits — for one frame,
 * on every service switch, the newly switched-to service's icon would
 * otherwise render wrapped around the PREVIOUS service's still-held url,
 * clickable and indistinguishable from a resolved link. Confirmed live
 * 2026-09-15: switching to Apple Music opened a stale Spotify link on a
 * click that landed in that window; a reload masked it by forcing a
 * clean resync. Fixed by comparing the tagged service against the
 * current `service` at render time below, so a stale url is discarded
 * immediately rather than waiting for the effect to catch up. */
export function useMusicLink(rawTitle: string, service: MusicService | null): string | null {
  const [result, setResult] = useState<{ service: MusicService | null; url: string | null }>({
    service: null,
    url: null,
  })

  useEffect(() => {
    setResult({ service, url: null })
    if (!rawTitle || !service) return
    let cancelled = false
    // service isn't sent — the backend resolves the active service itself
    // from the user's config (see routers/music_link.py), so a stale
    // client-side value can't return a mismatched URL. It's still a
    // dependency below purely to re-trigger this effect on switch.
    api
      .get<MusicLinkResponse>(`/api/music-link?raw_title=${encodeURIComponent(rawTitle)}`)
      .then((res) => {
        if (!cancelled) setResult({ service, url: res.url })
      })
      .catch(() => {
        if (!cancelled) setResult({ service, url: null })
      })
    return () => {
      cancelled = true
    }
  }, [rawTitle, service])

  return result.service === service ? result.url : null
}
