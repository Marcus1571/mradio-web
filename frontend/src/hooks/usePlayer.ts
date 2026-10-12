import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { EnrichmentItem, Station, WsMessage } from '../api/types'

export type PlaybackStatus = 'stopped' | 'playing'

export interface PlayerState {
  station: Station | null
  stationName: string
  hasIcy: boolean | null
  rawTitle: string
  artist: string
  title: string
  performer: string
  enrichment: EnrichmentItem | null
  enriching: boolean
  status: PlaybackStatus
  volume: number
  muted: boolean
  connected: boolean
  elapsed: number
  bitrate: string | null
  sampleRate: string | null
  format: string | null
  bufferedAhead: number
  // Bumped every time a fresh (non-fail) enrichment arrives — the
  // now-playing panel's trivia-history strip is fetched from the server
  // (persisted per user, not client state, see trivia_history.py) and
  // uses this as a dependency to know when to refetch, since the actual
  // history list itself doesn't live here anymore.
  triviaHistoryVersion: number
}

const INITIAL_STATE: PlayerState = {
  station: null,
  stationName: '',
  hasIcy: null,
  rawTitle: '',
  artist: '',
  title: '',
  performer: '',
  enrichment: null,
  enriching: false,
  status: 'stopped',
  volume: 70,
  muted: false,
  connected: false,
  elapsed: 0,
  bitrate: null,
  sampleRate: null,
  format: null,
  bufferedAhead: 0,
  triviaHistoryVersion: 0,
}

/** Wires an <audio> element, the /api/stream proxy, and the /api/ws
 * now-playing socket together — the browser-side replacement for mradio's
 * mpv + IPC socket. `sid` ties one player session's stream request to its
 * WebSocket connection so the server can push metadata parsed off the same
 * proxied bytes (see nowplaying.py). */
export function usePlayer(initialVolume?: number) {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const sidRef = useRef<string>(crypto.randomUUID())
  // Whether the user currently wants to be connected — true from the moment
  // they hit Play until they hit Stop. The WS reconnect loop below checks
  // this before retrying, so a deliberate Stop doesn't fight its own
  // keepalive logic and silently reconnect behind the user's back.
  const wantsConnectionRef = useRef(true)
  const unmountedRef = useRef(false)
  const reconnectAttemptRef = useRef(0)
  const reconnectTimerRef = useRef<number | null>(null)
  // Audio-stream recovery: an unexpected stall/error has no built-in retry
  // (unlike the WS, which reconnects itself) — the browser just goes quiet.
  // audioReconnectRef always points at the latest reconnect(), so the
  // error/stalled listeners (registered once, in the effect below) can call
  // it without needing to re-subscribe every time the current station
  // changes.
  const audioReconnectRef = useRef<() => void>(() => undefined)
  const audioReconnectTimerRef = useRef<number | null>(null)
  // Retry-with-backoff for automatic stream recovery, mirroring the WS
  // reconnect loop above — added after a real dropout confirmed that a
  // failed audio.play() during auto-recovery (rejected promise, no new
  // native error/stalled event to re-trigger onFailure) left playback
  // silently dead with no further retry, requiring a manual Stop/Play.
  // Reset to 0 whenever a retry actually starts playing successfully.
  const audioRetryAttemptRef = useRef(0)
  const MAX_AUDIO_RETRIES = 6
  // connectWsRef always points at the WS effect's own connectWs() (defined
  // inside that effect, closed over wsRef/reconnectAttemptRef/etc.) — see
  // ensureWsConnected() below for why play()/reconnect() need this.
  const connectWsRef = useRef<() => void>(() => undefined)
  const [state, setState] = useState<PlayerState>({
    ...INITIAL_STATE,
    volume: initialVolume ?? INITIAL_STATE.volume,
  })

  // Fire-and-forget — a logging call must never itself block or break
  // playback recovery, so failures here are swallowed silently rather
  // than surfaced (there's nowhere useful to surface them to).
  const logClientEvent = useCallback(
    (event: string, extra?: { detail?: string; attempt?: number }) => {
      void api
        .post('/api/stream/client-event', { sid: sidRef.current, event, ...extra })
        .catch(() => undefined)
    },
    [],
  )

  // The shared retry-with-backoff loop for automatic stream recovery —
  // called from two different triggers: onFailure() below (a native
  // error/stalled event fired on the <audio> element) and reconnect()'s
  // own play().catch() (a rejected play() promise, which does NOT fire a
  // new native error/stalled event — see reconnect()'s docstring). Without
  // this shared path, a play() rejection during auto-recovery previously
  // had nothing left to retry it, ending the retry loop permanently and
  // requiring a manual Stop/Play — the actual bug this fixes.
  const retryAudioAfterPlayFailure = useCallback(
    (triggerEvent: string) => {
      if (!wantsConnectionRef.current) return
      const attempt = ++audioRetryAttemptRef.current
      logClientEvent('retry_triggered', { detail: triggerEvent, attempt })
      if (attempt > MAX_AUDIO_RETRIES) {
        logClientEvent('retry_exhausted', { attempt })
        return
      }
      const delay = Math.min(2000 * 2 ** (attempt - 1), 30000)
      logClientEvent('retry_scheduled', { detail: `${delay}ms`, attempt })
      audioReconnectTimerRef.current = window.setTimeout(() => {
        audioReconnectTimerRef.current = null
        if (!wantsConnectionRef.current) return
        logClientEvent('retry_attempt', { attempt })
        audioReconnectRef.current()
      }, delay)
    },
    [logClientEvent],
  )

  useEffect(() => {
    const audio = new Audio()
    audio.volume = state.volume / 100
    audioRef.current = audio
    const onPlay = () => setState((s) => ({ ...s, status: 'playing' }))
    // A native `pause` fires both for an intentional stop() and for the
    // browser giving up on a dead/stalled stream — only stop() itself
    // should decide `status`, so this no longer touches it. Recovery from
    // an unintentional stall is handled by onFailure below instead.
    const onTimeUpdate = () => {
      const buffered = audio.buffered
      let bufferedAhead = 0
      if (buffered.length > 0) {
        const end = buffered.end(buffered.length - 1)
        bufferedAhead = Math.max(0, end - audio.currentTime)
      }
      setState((s) => ({ ...s, elapsed: audio.currentTime, bufferedAhead }))
    }
    const onFailure = (ev: Event) => {
      if (!wantsConnectionRef.current) return // user pressed Stop — leave it alone
      logClientEvent(ev.type === 'stalled' ? 'audio_stalled' : 'audio_error')
      if (audioReconnectTimerRef.current !== null) return // a retry is already queued
      retryAudioAfterPlayFailure(ev.type)
    }
    audio.addEventListener('play', onPlay)
    audio.addEventListener('timeupdate', onTimeUpdate)
    audio.addEventListener('error', onFailure)
    audio.addEventListener('stalled', onFailure)
    return () => {
      audio.pause()
      audio.removeEventListener('play', onPlay)
      audio.removeEventListener('timeupdate', onTimeUpdate)
      audio.removeEventListener('error', onFailure)
      audio.removeEventListener('stalled', onFailure)
      if (audioReconnectTimerRef.current !== null) window.clearTimeout(audioReconnectTimerRef.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    function connectWs() {
      // A no-op guard, not just an optimization: without it, calling
      // connectWs() from ensureWsConnected() (below) while a previous
      // socket is still mid-handshake would open a second one, and
      // whichever finishes connecting last silently orphans the other —
      // wsRef would point at one while messages could still arrive on
      // the discarded one for a moment. CONNECTING/OPEN both count as
      // "already have a socket in flight," only CLOSING/CLOSED need a
      // fresh one.
      const existing = wsRef.current
      if (existing && (existing.readyState === WebSocket.CONNECTING || existing.readyState === WebSocket.OPEN)) {
        return
      }
      const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
      const ws = new WebSocket(`${proto}//${location.host}/api/ws?sid=${sidRef.current}`)
      wsRef.current = ws
      ws.onopen = () => {
        reconnectAttemptRef.current = 0
        setState((s) => ({ ...s, connected: true }))
      }
      ws.onclose = () => {
        setState((s) => ({ ...s, connected: false }))
        if (unmountedRef.current || !wantsConnectionRef.current) return
        const attempt = reconnectAttemptRef.current++
        const delay = Math.min(1000 * 2 ** attempt, 30000)
        reconnectTimerRef.current = window.setTimeout(connectWs, delay)
      }
      ws.onmessage = (ev) => {
        const msg = JSON.parse(ev.data) as WsMessage
        if (msg.type === 'ping') {
          // keepalive only — nothing to do
        } else if (msg.type === 'station') {
          setState((s) => ({
            ...s,
            stationName: msg.name,
            bitrate: msg.bitrate,
            sampleRate: msg.sample_rate,
            format: msg.format,
            hasIcy: msg.has_icy,
          }))
        } else if (msg.type === 'now_playing') {
          setState((s) => ({
            ...s,
            rawTitle: msg.raw_title,
            artist: msg.artist,
            title: msg.title,
            performer: msg.performer,
            enrichment: null,
            enriching: true,
          }))
        } else if (msg.type === 'no_title') {
          // metaint is present (hasIcy was true) but the station never
          // actually populates StreamTitle (confirmed live: TSF Jazz sends
          // StreamTitle='' forever) — same dead-end for the listener as no
          // ICY support at all, so it collapses onto the same UI state.
          setState((s) => (s.rawTitle ? s : { ...s, hasIcy: false }))
        } else if (msg.type === 'enrichment') {
          setState((s) => {
            if (s.rawTitle !== msg.raw_title) return s
            if (msg.item.fail) return { ...s, enrichment: null, enriching: false }
            return {
              ...s,
              enrichment: msg.item,
              enriching: false,
              triviaHistoryVersion: s.triviaHistoryVersion + 1,
            }
          })
        }
      }
    }

    connectWs()
    connectWsRef.current = connectWs
    return () => {
      unmountedRef.current = true
      if (reconnectTimerRef.current !== null) window.clearTimeout(reconnectTimerRef.current)
      wsRef.current?.close()
    }
  }, [])

  /** Guards against the actual bug reported live: Stop sets
   * wantsConnectionRef to false, which makes the WS's own onclose handler
   * above skip its reconnect-with-backoff entirely (by design — a
   * deliberate Stop shouldn't fight its own keepalive). But if the socket
   * happens to die for an unrelated reason (proxy idle timeout, laptop
   * sleep/wake, a network blip) while stopped, nothing was left to ever
   * revive it — confirmed live: audio played fine on the next Play click
   * (a fully independent HTTP request), but station/title/enrichment
   * never arrived because the WebSocket carrying them was dead and
   * nothing reconnected it, only recoverable before this fix by a full
   * page reload (a fresh usePlayer() instance = a fresh socket). Called
   * from play()/reconnect() — the two moments the user is explicitly
   * asking for a live connection again — to actively check and, if
   * needed, kick the socket back open immediately rather than depending
   * solely on the passive onclose-triggered backoff loop, which only
   * fires for a close that happens *after* this point, not one that
   * already happened while stopped. */
  const ensureWsConnected = useCallback(() => {
    const ws = wsRef.current
    if (ws && (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN)) return
    if (reconnectTimerRef.current !== null) {
      window.clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }
    reconnectAttemptRef.current = 0
    connectWsRef.current()
  }, [])

  const streamUrl = useCallback(
    (station: Station) =>
      `/api/stream?url=${encodeURIComponent(station.url)}&sid=${sidRef.current}` +
      `&genre=${encodeURIComponent(station.genre)}` +
      `&station_name=${encodeURIComponent(station.name)}`,
    [],
  )

  /** Populates the panel with a station's identity (name/logo/"Stopped"
   * state) without starting playback — used only to restore the last
   * station after a reload that finds last_status: 'stopped', so the
   * user sees what they had selected instead of an empty "Nothing
   * playing" panel, without audio starting on its own. Doesn't touch
   * audioRef, wantsConnectionRef, or persist to /api/config — this is
   * purely a one-time local reflection of state the server already has. */
  const selectStation = useCallback((station: Station) => {
    setState((s) => ({
      ...s,
      station,
      stationName: station.name,
      hasIcy: null,
      rawTitle: '',
      artist: '',
      title: '',
      performer: '',
      enrichment: null,
      enriching: false,
    }))
  }, [])

  const play = useCallback(
    (station: Station) => {
      const audio = audioRef.current
      if (!audio) return
      wantsConnectionRef.current = true
      ensureWsConnected()
      setState((s) => ({
        ...s,
        station,
        stationName: station.name,
        hasIcy: null,
        rawTitle: '',
        artist: '',
        title: '',
        performer: '',
        enrichment: null,
        enriching: false,
        elapsed: 0,
        bitrate: null,
        sampleRate: null,
        format: null,
        bufferedAhead: 0,
      }))
      audio.src = streamUrl(station)
      audio.load()
      void audio.play().catch(() => undefined)
      void api.patch('/api/config', {
        last_url: station.url,
        last_name: station.name,
        last_genre: station.genre,
        last_status: 'playing',
      })
    },
    [streamUrl, ensureWsConnected],
  )

  /** A live stream has no meaningful "paused" state — there's nothing to
   * resume "from," only the broadcast as it is right now. Stop actually
   * releases the connection (rather than native audio.pause(), which
   * would leave the browser silently buffering and the backend's proxy
   * silently fetching from the station with nobody listening) by
   * clearing src and reloading — the same abort mechanism play()/
   * reconnect() already rely on, which the backend detects as a client
   * disconnect and cleans up via stream.py's existing finally block. */
  const stop = useCallback(() => {
    const audio = audioRef.current
    if (!audio) return
    wantsConnectionRef.current = false
    audio.pause()
    audio.removeAttribute('src')
    audio.load()
    setState((s) => ({ ...s, status: 'stopped' }))
    // Without this, a reload/app-reopen after Stop still auto-resumed
    // playback — Dashboard.tsx's mount effect only checked whether a
    // last_url existed at all, not whether the user had actually left
    // it playing, since play() always persists last_url regardless of
    // how the session later ends.
    void api.patch('/api/config', { last_status: 'stopped' })
  }, [])

  /** Re-establish the connection to the current station — the web
   * equivalent of mradio's `r` reconnect key, which killed and relaunched
   * mpv. A stalled live stream has no other recovery than a fresh request.
   * A rejected play() here (e.g. an interrupted-request or autoplay-policy
   * DOMException — these do NOT fire a new native error/stalled event, see
   * retryAudioAfterPlayFailure()'s docstring) chains into the backoff retry
   * loop instead of failing silently — the actual fix for dropouts that
   * previously needed a manual Stop/Play to recover from. */
  const reconnect = useCallback(() => {
    const audio = audioRef.current
    if (!audio || !state.station) return
    ensureWsConnected()
    setState((s) => ({ ...s, hasIcy: null, rawTitle: '', artist: '', title: '', performer: '' }))
    audio.src = streamUrl(state.station)
    audio.load()
    audio
      .play()
      .then(() => {
        audioRetryAttemptRef.current = 0
        logClientEvent('play_resolved')
      })
      .catch((err: unknown) => {
        const name = err instanceof DOMException ? err.name : String(err)
        logClientEvent('play_rejected', { detail: name })
        retryAudioAfterPlayFailure(`play_rejected:${name}`)
      })
  }, [state.station, streamUrl, ensureWsConnected, logClientEvent, retryAudioAfterPlayFailure])

  useEffect(() => {
    audioReconnectRef.current = reconnect
  }, [reconnect])

  const setVolume = useCallback((volume: number) => {
    const audio = audioRef.current
    if (audio) audio.volume = volume / 100
    setState((s) => ({ ...s, volume, muted: false }))
    void api.patch('/api/config', { volume, mute: false })
  }, [])

  /** Applies the account's saved volume once /api/config resolves —
   * distinct from setVolume() above, which is for the user's own slider
   * input and always re-persists (and would incorrectly clear a saved
   * mute). usePlayer(config?.volume)'s constructor argument only seeds
   * useState on the very first render; config always arrives async
   * (a separate GET, after mount), so by the time it's loaded the
   * initial value has already been locked in at the 70 default and
   * nothing else re-applies it — this is the fix for that. */
  const applySavedVolume = useCallback((volume: number) => {
    const audio = audioRef.current
    if (audio) audio.volume = volume / 100
    setState((s) => ({ ...s, volume }))
  }, [])

  const toggleMute = useCallback(() => {
    setState((s) => {
      const muted = !s.muted
      const audio = audioRef.current
      if (audio) audio.muted = muted
      void api.patch('/api/config', { mute: muted })
      return { ...s, muted }
    })
  }, [])

  /** force=false (default, used for a language/provider switch — see
   * Dashboard.tsx's setLanguage()/AISettingsPage's provider activation):
   * prefer an existing cached answer for the new language/provider over
   * a fresh LLM call. force=true (the "Re-ask AI" button only): always
   * ask again even if one is cached — see enricher.py's invalidate()
   * for the full reasoning and the bug this distinction fixes. */
  const reenrich = useCallback((force = false) => {
    if (!state.rawTitle) return
    setState((s) => ({ ...s, enriching: true }))
    wsRef.current?.send(JSON.stringify({ type: 'reenrich', force }))
  }, [state.rawTitle])

  return { state, play, stop, reconnect, setVolume, applySavedVolume, toggleMute, reenrich, selectStation }
}
