import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, api } from '../api/client'
import type { AISettings } from '../api/types'
import type { TFunction } from '../i18n'
import '../styles/admin.css'

export function DeezerSettingsPage({ onBack, t }: { onBack?: () => void; t: TFunction }) {
  const [settings, setSettings] = useState<AISettings | null>(null)
  const [secretInput, setSecretInput] = useState('')
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
        deezer_app_id: settings.deezer_app_id,
      }
      if (secretInput) body.deezer_secret = secretInput
      const res = await api.patch<AISettings>('/api/settings/ai', body)
      setSettings(res)
      setSecretInput('')
      setSaved(true)
      window.setTimeout(() => setSaved(false), 2500)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('deezerSettings.errorFallback'))
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
        <h1>{t('deezerSettings.title')}</h1>
        <p>{t('deezerSettings.intro')}</p>
      </div>

      <form className="admin-panel" onSubmit={onSubmit}>
        <div className="settings-form">
          <h3>{t('deezerSettings.credsGroup')}</h3>
          <div className="settings-row">
            <label htmlFor="deezer_app_id">{t('deezerSettings.appId')}</label>
            <input
              id="deezer_app_id"
              value={settings.deezer_app_id}
              onChange={(e) => field('deezer_app_id', e.target.value)}
            />
          </div>
          <div className="settings-row">
            <label htmlFor="deezer_secret">{t('deezerSettings.secret')}</label>
            <input
              id="deezer_secret"
              type="password"
              placeholder={settings.deezer_secret ? '••••••••' : ''}
              value={secretInput}
              onChange={(e) => setSecretInput(e.target.value)}
            />
          </div>
          <p className="admin-note admin-note-hint">{t('deezerSettings.redirectUriNote')}</p>

          {error && <p className="admin-note" style={{ color: 'var(--danger)' }}>{error}</p>}
          <div>
            <button className="admin-submit" type="submit" disabled={busy}>
              {busy ? t('deezerSettings.saving') : saved ? t('deezerSettings.saved') : t('deezerSettings.save')}
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}
