import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import type { FavoriteSlot } from '../api/types'

export function useFavorites() {
  const [favorites, setFavorites] = useState<FavoriteSlot[]>([])
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    const res = await api.get<{ favorites: FavoriteSlot[] }>('/api/favorites')
    setFavorites(res.favorites)
  }, [])

  useEffect(() => {
    refresh().finally(() => setLoading(false))
  }, [refresh])

  const add = useCallback(async (url: string, name: string) => {
    const res = await api.post<{ favorites: FavoriteSlot[]; added: boolean }>('/api/favorites', {
      url,
      name,
    })
    setFavorites(res.favorites)
    return res.added
  }, [])

  const remove = useCallback(async (url: string) => {
    const res = await api.del<{ favorites: FavoriteSlot[]; removed: boolean }>(
      `/api/favorites?url=${encodeURIComponent(url)}`,
    )
    setFavorites(res.favorites)
    return res.removed
  }, [])

  const move = useCallback(async (src: number, dst: number) => {
    const res = await api.post<{ favorites: FavoriteSlot[] }>('/api/favorites/move', { src, dst })
    setFavorites(res.favorites)
  }, [])

  return { favorites, loading, add, remove, move, refresh }
}
