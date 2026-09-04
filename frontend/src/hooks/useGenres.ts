import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Genre, GenreInfo, Station } from '../api/types'

export function useGenres() {
  const [genres, setGenres] = useState<GenreInfo[]>([])
  const [active, setActive] = useState<Genre | null>(null)
  const [stations, setStations] = useState<Station[]>([])
  const [loadingStations, setLoadingStations] = useState(false)

  useEffect(() => {
    api.get<{ genres: GenreInfo[] }>('/api/stations/genres').then((res) => {
      setGenres(res.genres)
      if (res.genres.length > 0) setActive(res.genres[0].genre)
    })
  }, [])

  const selectGenre = useCallback((genre: Genre) => {
    setActive(genre)
  }, [])

  useEffect(() => {
    if (!active) return
    setLoadingStations(true)
    api
      .get<{ genre: Genre; stations: Station[] }>(`/api/stations/genres/${active}`)
      .then((res) => setStations(res.stations))
      .finally(() => setLoadingStations(false))
  }, [active])

  return { genres, active, stations, loadingStations, selectGenre }
}
