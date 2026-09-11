import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, api } from '../api/client'
import type { AISettings } from '../api/types'
import type { TFunction } from '../i18n'
import '../styles/admin.css'

export function SpotifySettingsPage({ onBack, t }: { onBack?: () => void; t: TFunction }) {
  const [settings, setSettings] = useState<AISettings | null>(null)
  const [clientSecretInput, setClientSecretInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get<AISettings>('/api/settings/ai').then(setSettings)
  }, [])

  function field<K extends keyof AISettings>(key: K, value: AISettings[K]) {
    setSettings((s) => (s ? { ...s, [key]: value } : s))
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!settings) return
    setError('')
    setBusy(true)
    try {
      const body: Partial<AISettings> = {
        spotify_client_id: settings.spotify_client_id,
      }
      if (clientSecretInput) body.spotify_client_secret = clientSecretInput
      const res = await api.patch<AISettings>('/api/settings/ai', body)
      setSettings(res)
      setClientSecretInput('')
      setSaved(true)
      window.setTimeout(() => setSaved(false), 2500)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('spotifySettings.errorFallback'))
    } finally {
      setBusy(false)
    }
  }

  if (!settings) return null

  return (
    <div className="admin-page">
      {onBack && (
        <button className="admin-breadcrumb" type="button" onClick={onBack}>
          {t('settings.backToSettings')}
        </button>
      )}
      <div className="admin-header">
        <h1>{t('spotifySettings.title')}</h1>
        <p>{t('spotifySettings.intro')}</p>
      </div>

      <form className="admin-panel" onSubmit={onSubmit}>
        <div className="settings-form">
          <h3>{t('spotifySettings.credsGroup')}</h3>
          <div className="settings-row">
            <label htmlFor="spotify_client_id">{t('spotifySettings.clientId')}</label>
            <input
              id="spotify_client_id"
              value={settings.spotify_client_id}
              onChange={(e) => field('spotify_client_id', e.target.value)}
            />
          </div>
          <div className="settings-row">
            <label htmlFor="spotify_client_secret">{t('spotifySettings.clientSecret')}</label>
            <input
              id="spotify_client_secret"
              type="password"
              placeholder={settings.spotify_client_secret ? '••••••••' : ''}
              value={clientSecretInput}
              onChange={(e) => setClientSecretInput(e.target.value)}
            />
          </div>
          <p className="admin-note admin-note-hint">{t('spotifySettings.redirectUriNote')}</p>

          {error && <p className="admin-note" style={{ color: 'var(--danger)' }}>{error}</p>}
          <div>
            <button className="admin-submit" type="submit" disabled={busy}>
              {busy ? t('spotifySettings.saving') : saved ? t('spotifySettings.saved') : t('spotifySettings.save')}
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}
