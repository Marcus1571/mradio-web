import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import type { ProvidersResponse } from '../api/types'

export function useProviders() {
  const [data, setData] = useState<ProvidersResponse | null>(null)

  const refresh = useCallback(async () => {
    const res = await api.get<ProvidersResponse>('/api/enrich/providers')
    setData(res)
    return res
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const activate = useCallback(
    async (name: string) => {
      await api.post('/api/enrich/providers/activate', { name })
      await refresh()
    },
    [refresh],
  )

  return { providers: data?.providers ?? [], active: data?.active ?? '', activate, refresh }
}
