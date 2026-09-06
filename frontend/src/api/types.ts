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
  full_name: string | null
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
  last_genre?: Genre
  provider?: string
  language?: 'en' | 'es' | 'it' | 'pt' | 'fr' | 'ru' | 'de' | 'el' | 'nl' | 'da' | 'sv' | 'nb'
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

export interface SmtpSettings {
  host: string
  port: number
  username: string
  password: string
  from_address: string
  use_tls: boolean
  public_url: string
}

export interface EnrichmentItem {
  work: string
  trivia: string
  wiki: string
  movement: number
  fail?: boolean
}

export interface LiveSession {
  user_id: number
  username: string
  full_name: string | null
  station: string
  genre: Genre
  city: string | null
  country: string | null
  lat: number | null
  lon: number | null
  elapsed_seconds: number
}

export interface HistoryEntry {
  id: number
  username: string
  full_name: string | null
  station_name: string
  genre: Genre
  started_at: string
  ended_at: string | null
  city: string | null
  country: string | null
  lat: number | null
  lon: number | null
}

export interface StationCount {
  station_name: string
  plays: number
  seconds: number | null
}

export interface GenreCount {
  genre: Genre
  plays: number
  seconds: number | null
}

export interface UserCount {
  username: string
  full_name: string | null
  plays: number
  seconds: number | null
}

export interface DayCount {
  day: string
  plays: number
}

export interface AnalyticsStats {
  top_stations: StationCount[]
  top_genres: GenreCount[]
  top_users: UserCount[]
  by_day: DayCount[]
}

export interface TriviaHistoryEntry {
  id: number
  raw_title: string
  station_name: string
  artist: string
  title: string
  performer: string
  work: string
  trivia: string
  wiki: string
  created_at: string
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
