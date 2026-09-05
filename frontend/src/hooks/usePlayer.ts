import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { EnrichmentItem, Station, WsMessage } from '../api/types'

export type PlaybackStatus = 'stopped' | 'playing'

export interface TriviaHistoryEntry {
  rawTitle: string
  stationName: string
  artist: string
  title: string
  performer: string
  item: EnrichmentItem
  at: number
}

const MAX_TRIVIA_HISTORY = 10

export interface PlayerState {
  station: Station | null
  stationName: string
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
  triviaHistory: TriviaHistoryEntry[]
}

const INITIAL_STATE: PlayerState = {
  station: null,
  stationName: '',
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
  triviaHistory: [],
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
  const [state, setState] = useState<PlayerState>({
    ...INITIAL_STATE,
    volume: initialVolume ?? INITIAL_STATE.volume,
  })

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
    const onFailure = () => {
      if (!wantsConnectionRef.current) return // user pressed Stop — leave it alone
      if (audioReconnectTimerRef.current !== null) return // a retry is already queued
      audioReconnectTimerRef.current = window.setTimeout(() => {
        audioReconnectTimerRef.current = null
        if (wantsConnectionRef.current) audioReconnectRef.current()
      }, 2000)
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
        } else if (msg.type === 'enrichment') {
          setState((s) => {
            if (s.rawTitle !== msg.raw_title) return s
            if (msg.item.fail) return { ...s, enrichment: null, enriching: false }
            const entry: TriviaHistoryEntry = {
              rawTitle: msg.raw_title,
              stationName: s.stationName,
              artist: s.artist,
              title: s.title,
              performer: s.performer,
              item: msg.item,
              at: Date.now(),
            }
            // A re-ask (existing "Re-ask AI" button) re-arrives as another
            // 'enrichment' message for the same rawTitle — update that
            // entry in place instead of appending a duplicate chip.
            const withoutExisting = s.triviaHistory.filter((h) => h.rawTitle !== msg.raw_title)
            const triviaHistory = [entry, ...withoutExisting].slice(0, MAX_TRIVIA_HISTORY)
            return { ...s, enrichment: msg.item, enriching: false, triviaHistory }
          })
        }
      }
    }

    connectWs()
    return () => {
      unmountedRef.current = true
      if (reconnectTimerRef.current !== null) window.clearTimeout(reconnectTimerRef.current)
      wsRef.current?.close()
    }
  }, [])

  const streamUrl = useCallback(
    (station: Station) =>
      `/api/stream?url=${encodeURIComponent(station.url)}&sid=${sidRef.current}` +
      `&genre=${encodeURIComponent(station.genre)}`,
    [],
  )

  const play = useCallback(
    (station: Station) => {
      const audio = audioRef.current
      if (!audio) return
      wantsConnectionRef.current = true
      setState((s) => ({
        ...s,
        station,
        stationName: station.name,
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
      })
    },
    [streamUrl],
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
  }, [])

  /** Re-establish the connection to the current station — the web
   * equivalent of mradio's `r` reconnect key, which killed and relaunched
   * mpv. A stalled live stream has no other recovery than a fresh request. */
  const reconnect = useCallback(() => {
    const audio = audioRef.current
    if (!audio || !state.station) return
    audio.src = streamUrl(state.station)
    audio.load()
    void audio.play().catch(() => undefined)
  }, [state.station, streamUrl])

  useEffect(() => {
    audioReconnectRef.current = reconnect
  }, [reconnect])

  const setVolume = useCallback((volume: number) => {
    const audio = audioRef.current
    if (audio) audio.volume = volume / 100
    setState((s) => ({ ...s, volume, muted: false }))
    void api.patch('/api/config', { volume, mute: false })
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

  const reenrich = useCallback(() => {
    if (!state.rawTitle) return
    setState((s) => ({ ...s, enriching: true }))
    wsRef.current?.send(JSON.stringify({ type: 'reenrich' }))
  }, [state.rawTitle])

  return { state, play, stop, reconnect, setVolume, toggleMute, reenrich }
}
