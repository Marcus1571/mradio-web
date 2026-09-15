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
 * service === null (no service picked yet, e.g. every fresh app
 * launch — useMusicService.ts no longer persists a choice, see that
 * file) skips the request entirely — there's nothing to search against,
 * and the caller (NowPlayingPanel) renders no icon at all in that state
 * rather than an inert greyed-out one, since there's no service to
 * represent.
 *
 * `service` is sent to the backend explicitly (routers/music_link.py no
 * longer resolves it from a persisted config, since there isn't one
 * anymore) — the result is still tagged with the service it was
 * resolved for and compared against the current `service` at render
 * time, so a response for a service the listener has since switched
 * away from (e.g. a slow in-flight request from before a quick
 * double-switch) is discarded rather than shown against the wrong
 * icon. */
export function useMusicLink(rawTitle: string, service: MusicService | null): string | null {
  const [result, setResult] = useState<{ service: MusicService | null; url: string | null }>({
    service: null,
    url: null,
  })

  useEffect(() => {
    setResult({ service, url: null })
    if (!rawTitle || !service) return
    let cancelled = false
    const params = new URLSearchParams({ raw_title: rawTitle, service })
    api
      .get<MusicLinkResponse>(`/api/music-link?${params.toString()}`)
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
