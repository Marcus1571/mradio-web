import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { EnrichmentItem, Station, WsMessage } from '../api/types'

export type PlaybackStatus = 'stopped' | 'playing'

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
  const [state, setState] = useState<PlayerState>({
    ...INITIAL_STATE,
    volume: initialVolume ?? INITIAL_STATE.volume,
  })

  useEffect(() => {
    const audio = new Audio()
    audio.volume = state.volume / 100
    audioRef.current = audio
    const onPlay = () => setState((s) => ({ ...s, status: 'playing' }))
    const onPause = () => setState((s) => (s.status === 'stopped' ? s : { ...s, status: 'stopped' }))
    const onTimeUpdate = () => {
      const buffered = audio.buffered
      let bufferedAhead = 0
      if (buffered.length > 0) {
        const end = buffered.end(buffered.length - 1)
        bufferedAhead = Math.max(0, end - audio.currentTime)
      }
      setState((s) => ({ ...s, elapsed: audio.currentTime, bufferedAhead }))
    }
    audio.addEventListener('play', onPlay)
    audio.addEventListener('pause', onPause)
    audio.addEventListener('timeupdate', onTimeUpdate)
    return () => {
      audio.pause()
      audio.removeEventListener('play', onPlay)
      audio.removeEventListener('pause', onPause)
      audio.removeEventListener('timeupdate', onTimeUpdate)
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
          setState((s) =>
            s.rawTitle === msg.raw_title
              ? { ...s, enrichment: msg.item.fail ? null : msg.item, enriching: false }
              : s,
          )
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
    (station: Station) => `/api/stream?url=${encodeURIComponent(station.url)}&sid=${sidRef.current}`,
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
      void api.patch('/api/config', { last_url: station.url, last_name: station.name })
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
