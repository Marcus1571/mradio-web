import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, Marker, Tooltip, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import 'leaflet.heat'
import { api } from '../api/client'
import type { AnalyticsStats, HistoryEntry, LiveSession } from '../api/types'
import type { TFunction } from '../i18n'
import { displayName } from '../utils/format'
import '../styles/admin.css'
import '../styles/analytics.css'
import '../styles/dashboard.css'

type Since = '7d' | '30d' | 'all'

function formatDuration(seconds: number | null): string {
  if (!seconds) return '0m'
  const h = Math.floor(seconds / 3600)
  const m = Math.round((seconds % 3600) / 60)
  return h > 0 ? `${h}h ${m}m` : `${m}m`
}

function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

function LiveTable({ sessions, t }: { sessions: LiveSession[]; t: TFunction }) {
  if (sessions.length === 0) {
    return <p className="admin-note analytics-empty">{t('analytics.liveEmpty')}</p>
  }
  return (
    <table className="admin-table">
      <thead>
        <tr>
          <th className="admin-table-status-col"></th>
          <th>{t('analytics.colUser')}</th>
          <th>{t('analytics.colStation')}</th>
          <th>{t('analytics.colGenre')}</th>
          <th>{t('analytics.colLocation')}</th>
          <th>{t('analytics.colElapsed')}</th>
        </tr>
      </thead>
      <tbody>
        {sessions.map((s) => (
          <tr key={`${s.user_id}-${s.station}`}>
            <td className="admin-table-status-col">
              <span className="live-dot" />
            </td>
            <td>{displayName(s)}</td>
            <td>{s.station}</td>
            <td>{s.genre}</td>
            <td>{s.city ? `${s.city}, ${s.country}` : s.country || t('analytics.locationLocal')}</td>
            <td>{formatElapsed(s.elapsed_seconds)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function BarList({
  rows,
  labelKey,
  t,
}: {
  rows: { label: string; plays: number; seconds: number | null }[]
  labelKey: string
  t: TFunction
}) {
  const max = Math.max(1, ...rows.map((r) => r.plays))
  if (rows.length === 0) {
    return <p className="admin-note analytics-empty">{t('analytics.statsEmpty')}</p>
  }
  return (
    <div className="bar-list" aria-label={labelKey}>
      {rows.map((r) => (
        <div className="bar-row" key={r.label}>
          <span className="bar-label">{r.label}</span>
          <div className="bar-track">
            <div className="bar-fill" style={{ width: `${(r.plays / max) * 100}%` }} />
          </div>
          <span className="bar-value">
            {r.plays} · {formatDuration(r.seconds)}
          </span>
        </div>
      ))}
    </div>
  )
}

function Sparkline({ days }: { days: { day: string; plays: number }[] }) {
  if (days.length === 0) return null
  const max = Math.max(1, ...days.map((d) => d.plays))
  const w = 400
  const h = 60
  const step = days.length > 1 ? w / (days.length - 1) : 0
  const points = days
    .map((d, i) => `${i * step},${h - (d.plays / max) * h}`)
    .join(' ')
  return (
    <svg className="sparkline" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
      <polyline points={points} fill="none" stroke="var(--accent)" strokeWidth="2" />
    </svg>
  )
}

type Pin = { lat: number; lon: number; label: string; count: number }

function buildPins(sessions: LiveSession[], history: HistoryEntry[]): Pin[] {
  // One marker per unique city, not per session — round to ~1 decimal
  // (~11km) so sessions from the same city cluster onto one pin even if
  // GeoLite2 returns very slightly different coordinates run to run.
  const byKey = new Map<string, Pin>()
  function add(lat: number | null, lon: number | null, city: string | null, country: string | null) {
    if (lat == null || lon == null) return
    const key = `${lat.toFixed(1)},${lon.toFixed(1)}`
    const label = city ? `${city}, ${country}` : country || ''
    const existing = byKey.get(key)
    if (existing) existing.count += 1
    else byKey.set(key, { lat, lon, label, count: 1 })
  }
  for (const s of sessions) add(s.lat, s.lon, s.city, s.country)
  for (const h of history) add(h.lat, h.lon, h.city, h.country)
  return [...byKey.values()]
}

type MapMode = 'pins' | 'heatmap'

const LIVE_DOT_ICON = L.divIcon({
  className: 'map-live-dot-icon',
  html: '<span class="live-dot" />',
  iconSize: [8, 8],
  iconAnchor: [4, 4],
})

function HeatLayer({ pins }: { pins: Pin[] }) {
  const map = useMap()
  useEffect(() => {
    const max = Math.max(1, ...pins.map((p) => p.count))
    const layer = L.heatLayer(
      pins.map((p) => [p.lat, p.lon, p.count / max]),
      {
        radius: 25,
        blur: 20,
        maxZoom: 6,
        minOpacity: 0.4,
        gradient: { 0.2: '#fde68a', 0.5: '#fb923c', 0.8: '#ea580c', 1: '#c2410c' },
      },
    )
    layer.addTo(map)
    return () => {
      layer.remove()
    }
  }, [map, pins])
  return null
}

function AnalyticsMap({
  sessions,
  history,
  mode,
  onModeChange,
  t,
}: {
  sessions: LiveSession[]
  history: HistoryEntry[]
  mode: MapMode
  onModeChange: (m: MapMode) => void
  t: TFunction
}) {
  const pins = buildPins(sessions, history)
  return (
    <div className="analytics-map-wrap">
      <div className="map-mode-picker">
        {(['pins', 'heatmap'] as MapMode[]).map((m) => (
          <button
            key={m}
            type="button"
            className={`since-btn ${mode === m ? 'active' : ''}`}
            onClick={() => onModeChange(m)}
          >
            {t(m === 'pins' ? 'analytics.mapPins' : 'analytics.mapHeatmap')}
          </button>
        ))}
      </div>
      <MapContainer center={[20, 0]} zoom={2} scrollWheelZoom={false} className="analytics-map">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {mode === 'pins' ? (
          pins.map((p, i) => (
            <Marker key={i} position={[p.lat, p.lon]} icon={LIVE_DOT_ICON}>
              <Tooltip>{p.label}</Tooltip>
            </Marker>
          ))
        ) : (
          <HeatLayer pins={pins} />
        )}
      </MapContainer>
    </div>
  )
}

export function AnalyticsPage({ t }: { t: TFunction }) {
  const [live, setLive] = useState<LiveSession[]>([])
  const [history, setHistory] = useState<HistoryEntry[]>([])
  const [stats, setStats] = useState<AnalyticsStats | null>(null)
  const [since, setSince] = useState<Since>('30d')
  const [historyOffset, setHistoryOffset] = useState(0)
  const [mapMode, setMapMode] = useState<MapMode>('pins')

  useEffect(() => {
    let cancelled = false
    async function pollLive() {
      const res = await api.get<LiveSession[]>('/api/analytics/live')
      if (!cancelled) setLive(res)
    }
    pollLive()
    const id = window.setInterval(pollLive, 5000)
    return () => {
      cancelled = true
      window.clearInterval(id)
    }
  }, [])

  useEffect(() => {
    api.get<AnalyticsStats>(`/api/analytics/stats?since=${since}`).then(setStats)
  }, [since])

  useEffect(() => {
    api
      .get<HistoryEntry[]>(`/api/analytics/history?limit=25&offset=${historyOffset}`)
      .then(setHistory)
  }, [historyOffset])

  return (
    <div className="admin-page">
      <div className="admin-header">
        <h1>{t('analytics.title')}</h1>
        <p>{t('analytics.intro')}</p>
      </div>

      <div className="admin-panel">
        <h2 className="analytics-section-title">{t('analytics.liveTitle')}</h2>
        <LiveTable sessions={live} t={t} />
      </div>

      <div className="admin-panel">
        <h2 className="analytics-section-title">{t('analytics.mapTitle')}</h2>
        <AnalyticsMap sessions={live} history={history} mode={mapMode} onModeChange={setMapMode} t={t} />
      </div>

      <div className="admin-panel">
        <div className="analytics-stats-header">
          <h2 className="analytics-section-title">{t('analytics.statsTitle')}</h2>
          <div className="since-picker">
            {(['7d', '30d', 'all'] as Since[]).map((s) => (
              <button
                key={s}
                type="button"
                className={`since-btn ${since === s ? 'active' : ''}`}
                onClick={() => setSince(s)}
              >
                {t(`analytics.since${s === '7d' ? '7d' : s === '30d' ? '30d' : 'All'}`)}
              </button>
            ))}
          </div>
        </div>
        {stats && (
          <div className="analytics-stats-grid">
            <div>
              <h3>{t('analytics.topStations')}</h3>
              <BarList
                labelKey="stations"
                rows={stats.top_stations.map((r) => ({ label: r.station_name, plays: r.plays, seconds: r.seconds }))}
                t={t}
              />
            </div>
            <div>
              <h3>{t('analytics.topGenres')}</h3>
              <BarList
                labelKey="genres"
                rows={stats.top_genres.map((r) => ({ label: r.genre, plays: r.plays, seconds: r.seconds }))}
                t={t}
              />
            </div>
            <div>
              <h3>{t('analytics.topUsers')}</h3>
              <BarList
                labelKey="users"
                rows={stats.top_users.map((r) => ({ label: displayName(r), plays: r.plays, seconds: r.seconds }))}
                t={t}
              />
            </div>
            <div>
              <h3>{t('analytics.byDay')}</h3>
              <Sparkline days={stats.by_day} />
            </div>
          </div>
        )}
      </div>

      <div className="admin-panel">
        <h2 className="analytics-section-title">{t('analytics.historyTitle')}</h2>
        {history.length === 0 ? (
          <p className="admin-note analytics-empty">{t('analytics.historyEmpty')}</p>
        ) : (
          <table className="admin-table">
            <thead>
              <tr>
                <th>{t('analytics.colUser')}</th>
                <th>{t('analytics.colStation')}</th>
                <th>{t('analytics.colGenre')}</th>
                <th>{t('analytics.colStarted')}</th>
                <th>{t('analytics.colLocation')}</th>
              </tr>
            </thead>
            <tbody>
              {history.map((h) => (
                <tr key={h.id}>
                  <td>{displayName(h)}</td>
                  <td>{h.station_name}</td>
                  <td>{h.genre}</td>
                  <td>{new Date(h.started_at).toLocaleString()}</td>
                  <td>{h.city ? `${h.city}, ${h.country}` : h.country || t('analytics.locationLocal')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div className="row-actions history-pagination">
          <button type="button" disabled={historyOffset === 0} onClick={() => setHistoryOffset((o) => Math.max(0, o - 25))}>
            {t('analytics.prevPage')}
          </button>
          <button type="button" disabled={history.length < 25} onClick={() => setHistoryOffset((o) => o + 25)}>
            {t('analytics.nextPage')}
          </button>
        </div>
      </div>
    </div>
  )
}
