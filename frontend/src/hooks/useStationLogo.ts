import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Station, StationLogo } from '../api/types'

export function useStationLogo(station: Station | null): string | null {
  const [logo, setLogo] = useState<string | null>(null)

  useEffect(() => {
    setLogo(null)
    if (!station) return
    let cancelled = false
    api
      .get<StationLogo>(
        `/api/stations/logo?url=${encodeURIComponent(station.url)}&name=${encodeURIComponent(station.name)}`,
      )
      .then((res) => {
        if (!cancelled) setLogo(res.logo)
      })
      .catch(() => {
        if (!cancelled) setLogo(null)
      })
    return () => {
      cancelled = true
    }
    // Only re-fetch when the station's identity actually changes, not on
    // every render of a new-but-equal station object.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [station?.url, station?.name])

  return logo
}
