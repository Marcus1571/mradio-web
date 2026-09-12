import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError, api } from '../api/client'
import type { DeezerMembership, DeezerStatus, DeezerToggleResult } from '../api/types'

export interface DeezerState {
  configured: boolean
  connected: boolean
  loading: boolean
  error: string
  inPlaylist: boolean
  trackId: string | null
  toggling: boolean
}

export function useDeezer(rawTitle: string) {
  const [state, setState] = useState<DeezerState>({
    configured: false,
    connected: false,
    loading: true,
    error: '',
    inPlaylist: false,
    trackId: null,
    toggling: false,
  })
  const [pendingAuth, setPendingAuth] = useState(false)
  const lastRawTitleRef = useRef('')

  const refreshStatus = useCallback(async () => {
    try {
      const status = await api.get<DeezerStatus>('/api/deezer/status')
      setState((s) => ({
        ...s,
        configured: status.configured,
        connected: status.connected,
        loading: false,
      }))
      return status
    } catch (err) {
      setState((s) => ({ ...s, loading: false, error: err instanceof ApiError ? err.message : 'deezer error' }))
      return null
    }
  }, [])

  const checkMembership = useCallback(async (title: string) => {
    if (!title) return
    try {
      const res = await api.get<DeezerMembership>(`/api/deezer/membership?raw_title=${encodeURIComponent(title)}`)
      setState((s) => ({ ...s, inPlaylist: res.in_playlist, trackId: res.track_id, error: '' }))
    } catch (err) {
      setState((s) => ({ ...s, inPlaylist: false, trackId: null, error: err instanceof ApiError ? err.message : 'deezer error' }))
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
      const res = await api.get<{ url: string }>('/api/deezer/auth-url')
      const features = 'noopener,noreferrer,width=700,height=600'
      const win = window.open(res.url, '_blank', features)
      if (!win) {
        setState((s) => ({
          ...s,
          error: 'Popup blocked. Allow popups for this site and try again.',
        }))
        return
      }
      setPendingAuth(true)
    } catch (err) {
      setState((s) => ({ ...s, error: err instanceof ApiError ? err.message : 'deezer error' }))
    }
  }, [])

  useEffect(() => {
    if (!pendingAuth) return
    const id = window.setInterval(() => {
      void refreshStatus().then((status) => {
        if (status?.connected) {
          setPendingAuth(false)
          if (rawTitle) void checkMembership(rawTitle)
        }
      })
    }, 3000)
    return () => window.clearInterval(id)
  }, [pendingAuth, rawTitle, refreshStatus, checkMembership])

  const toggle = useCallback(async () => {
    if (!rawTitle || state.toggling) return
    if (!state.connected) {
      await connect()
      return
    }
    setState((s) => ({ ...s, toggling: true, error: '' }))
    try {
      const res = await api.post<DeezerToggleResult>('/api/deezer/toggle', {
        raw_title: rawTitle,
        add: !state.inPlaylist,
      })
      setState((s) => ({ ...s, inPlaylist: res.in_playlist, trackId: res.track_id, toggling: false }))
    } catch (err) {
      setState((s) => ({
        ...s,
        toggling: false,
        error: err instanceof ApiError ? err.message : 'deezer error',
      }))
    }
  }, [rawTitle, state.inPlaylist, state.toggling, state.connected, connect])

  const disconnect = useCallback(async () => {
    try {
      await api.post<DeezerStatus>('/api/deezer/disconnect', {})
      setState((s) => ({ ...s, connected: false, inPlaylist: false, trackId: null }))
    } catch (err) {
      setState((s) => ({ ...s, error: err instanceof ApiError ? err.message : 'deezer error' }))
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
