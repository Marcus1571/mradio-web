import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { EnrichmentItem, Station, WsMessage } from '../api/types'

export interface PlayerState {
  station: Station | null
  stationName: string
  rawTitle: string
  artist: string
  title: string
  performer: string
  enrichment: EnrichmentItem | null
  enriching: boolean
  playing: boolean
  volume: number
  muted: boolean
  connected: boolean
  elapsed: number
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
  playing: false,
  volume: 70,
  muted: false,
  connected: false,
  elapsed: 0,
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
  const [state, setState] = useState<PlayerState>({
    ...INITIAL_STATE,
    volume: initialVolume ?? INITIAL_STATE.volume,
  })

  useEffect(() => {
    const audio = new Audio()
    audio.volume = state.volume / 100
    audioRef.current = audio
    const onPlay = () => setState((s) => ({ ...s, playing: true }))
    const onPause = () => setState((s) => ({ ...s, playing: false }))
    const onTimeUpdate = () => setState((s) => ({ ...s, elapsed: audio.currentTime }))
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
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${proto}//${location.host}/api/ws?sid=${sidRef.current}`)
    wsRef.current = ws
    ws.onopen = () => setState((s) => ({ ...s, connected: true }))
    ws.onclose = () => setState((s) => ({ ...s, connected: false }))
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data) as WsMessage
      if (msg.type === 'station') {
        setState((s) => ({ ...s, stationName: msg.name }))
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
    return () => ws.close()
  }, [])

  const streamUrl = useCallback(
    (station: Station) => `/api/stream?url=${encodeURIComponent(station.url)}&sid=${sidRef.current}`,
    [],
  )

  const play = useCallback(
    (station: Station) => {
      const audio = audioRef.current
      if (!audio) return
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
      }))
      audio.src = streamUrl(station)
      audio.load()
      void audio.play().catch(() => undefined)
      void api.patch('/api/config', { last_url: station.url, last_name: station.name })
    },
    [streamUrl],
  )

  const togglePause = useCallback(() => {
    const audio = audioRef.current
    if (!audio || !state.station) return
    if (audio.paused) void audio.play().catch(() => undefined)
    else audio.pause()
  }, [state.station])

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

  return { state, play, togglePause, reconnect, setVolume, toggleMute, reenrich }
}
