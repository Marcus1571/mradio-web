import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError, api } from '../api/client'
import type { SpotifyMembership, SpotifyStatus, SpotifyToggleResult } from '../api/types'

export interface SpotifyState {
  configured: boolean
  connected: boolean
  market?: string
  loading: boolean
  error: string
  inPlaylist: boolean
  trackId: string | null
  toggling: boolean
}

export function useSpotify(rawTitle: string) {
  const [state, setState] = useState<SpotifyState>({
    configured: false,
    connected: false,
    loading: true,
    error: '',
    inPlaylist: false,
    trackId: null,
    toggling: false,
  })
  const lastRawTitleRef = useRef('')

  const refreshStatus = useCallback(async () => {
    try {
      const status = await api.get<SpotifyStatus>('/api/spotify/status')
      setState((s) => ({
        ...s,
        configured: status.configured,
        connected: status.connected,
        market: status.market,
        loading: false,
      }))
      return status
    } catch (err) {
      setState((s) => ({ ...s, loading: false, error: err instanceof ApiError ? err.message : 'spotify error' }))
      return null
    }
  }, [])

  const checkMembership = useCallback(async (title: string) => {
    if (!title) return
    try {
      const res = await api.get<SpotifyMembership>(`/api/spotify/membership?raw_title=${encodeURIComponent(title)}`)
      setState((s) => ({ ...s, inPlaylist: res.in_playlist, trackId: res.track_id, error: '' }))
    } catch (err) {
      setState((s) => ({ ...s, inPlaylist: false, trackId: null, error: err instanceof ApiError ? err.message : 'spotify error' }))
    }
  }, [])

  useEffect(() => {
    let alive = true
    refreshStatus().then((status) => {
      if (!alive || !status?.connected) return
      if (rawTitle) void checkMembership(rawTitle)
    })
    return () => {
      alive = false
    }
    // Intentionally run once on mount; adding rawTitle/refreshStatus/checkMembership
    // would defeat the single initial-load behavior.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!state.connected || rawTitle === lastRawTitleRef.current) return
    lastRawTitleRef.current = rawTitle
    if (!rawTitle) {
      setState((s) => ({ ...s, inPlaylist: false, trackId: null }))
      return
    }
    const t = window.setTimeout(() => void checkMembership(rawTitle), 500)
    return () => window.clearTimeout(t)
  }, [rawTitle, state.connected, checkMembership])

  const connect = useCallback(async () => {
    try {
      const res = await api.get<{ url: string }>('/api/spotify/auth-url')
      window.location.href = res.url
    } catch (err) {
      setState((s) => ({ ...s, error: err instanceof ApiError ? err.message : 'spotify error' }))
    }
  }, [])

  const toggle = useCallback(async () => {
    if (!rawTitle || state.toggling) return
    if (!state.connected) {
      await connect()
      return
    }
    setState((s) => ({ ...s, toggling: true, error: '' }))
    try {
      const res = await api.post<SpotifyToggleResult>('/api/spotify/toggle', {
        raw_title: rawTitle,
        add: !state.inPlaylist,
      })
      setState((s) => ({ ...s, inPlaylist: res.in_playlist, trackId: res.track_id, toggling: false }))
    } catch (err) {
      setState((s) => ({
        ...s,
        toggling: false,
        error: err instanceof ApiError ? err.message : 'spotify error',
      }))
    }
  }, [rawTitle, state.inPlaylist, state.toggling, state.connected, connect])

  const disconnect = useCallback(async () => {
    try {
      await api.post<SpotifyStatus>('/api/spotify/disconnect', {})
      setState((s) => ({ ...s, connected: false, inPlaylist: false, trackId: null }))
    } catch (err) {
      setState((s) => ({ ...s, error: err instanceof ApiError ? err.message : 'spotify error' }))
    }
  }, [])

  return {
    ...state,
    refreshStatus,
    connect,
    disconnect,
    toggle,
  }
}
