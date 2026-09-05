export type Genre =
  | 'classical'
  | 'jazz'
  | 'blues'
  | 'country'
  | 'rock'
  | 'pop'
  | 'focus'
  | 'chill'
  | 'funk'
  | 'other'

export interface Station {
  name: string
  url: string
  genre: Genre
}

export type FavoriteSlot = Station | null

export interface User {
  id: number
  username: string
  email: string | null
  is_admin: boolean
  disabled: boolean
  must_change_password: boolean
  created_at: string
}

export interface GenreInfo {
  genre: Genre
  label: string
  count: number
}

export interface Config {
  theme?: 'dark' | 'light'
  volume?: number
  mute?: boolean
  last_url?: string
  last_name?: string
  provider?: string
  language?: 'en' | 'es'
}

export interface ProviderInfo {
  name: 'opencode' | 'openai' | 'ollama'
  enabled: boolean
}

export interface ProvidersResponse {
  active: string
  providers: ProviderInfo[]
}

export interface AISettings {
  ollama_url: string
  ollama_model: string
  ollama_timeout: number
  ollama_gpu: number
  api_base: string
  api_key: string
  api_model: string
  api_timeout: number
  opencode: string
  opencode_timeout: number
}

export interface AITestResult {
  ok: boolean
  message: string
}

export interface EnrichmentItem {
  work: string
  trivia: string
  wiki: string
  movement: number
  fail?: boolean
}

export type WsMessage =
  | {
      type: 'station'
      name: string
      bitrate: string | null
      sample_rate: string | null
      format: string | null
    }
  | { type: 'now_playing'; raw_title: string; artist: string; title: string; performer: string }
  | { type: 'enrichment'; raw_title: string; item: EnrichmentItem }
  | { type: 'ping' }
