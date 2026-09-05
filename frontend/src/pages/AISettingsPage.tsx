import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, api } from '../api/client'
import type { AISettings } from '../api/types'
import type { TFunction } from '../i18n'
import '../styles/admin.css'

export function AISettingsPage({ t }: { t: TFunction }) {
  const [settings, setSettings] = useState<AISettings | null>(null)
  const [apiKeyInput, setApiKeyInput] = useState('')
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
      const body: Partial<AISettings> = { ...settings }
      if (apiKeyInput) body.api_key = apiKeyInput
      else delete body.api_key
      const res = await api.patch<AISettings>('/api/settings/ai', body)
      setSettings(res)
      setApiKeyInput('')
      setSaved(true)
      window.setTimeout(() => setSaved(false), 2500)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('aiSettings.errorFallback'))
    } finally {
      setBusy(false)
    }
  }

  if (!settings) return null

  return (
    <div className="admin-page">
      <div className="admin-header">
        <h1>{t('aiSettings.title')}</h1>
        <p>{t('aiSettings.intro')}</p>
      </div>

      <form className="admin-panel" onSubmit={onSubmit}>
        <div className="settings-form">
          <div className="settings-group">
            <h2>{t('aiSettings.ollamaGroup')}</h2>
            <div className="settings-row">
              <label htmlFor="ollama_url">{t('aiSettings.serverUrl')}</label>
              <input
                id="ollama_url"
                placeholder="http://192.168.1.12:11434"
                value={settings.ollama_url}
                onChange={(e) => field('ollama_url', e.target.value)}
              />
            </div>
            <div className="settings-row">
              <label htmlFor="ollama_model">{t('aiSettings.model')}</label>
              <input
                id="ollama_model"
                value={settings.ollama_model}
                onChange={(e) => field('ollama_model', e.target.value)}
              />
            </div>
          </div>

          <div className="settings-group">
            <h2>{t('aiSettings.openaiGroup')}</h2>
            <p className="admin-note">{t('aiSettings.nimNote')}</p>
            <div className="settings-row">
              <label htmlFor="api_base">{t('aiSettings.apiBaseUrl')}</label>
              <input id="api_base" value={settings.api_base} onChange={(e) => field('api_base', e.target.value)} />
            </div>
            <div className="settings-row">
              <label htmlFor="api_model">{t('aiSettings.model')}</label>
              <input id="api_model" value={settings.api_model} onChange={(e) => field('api_model', e.target.value)} />
            </div>
            <div className="settings-row">
              <label htmlFor="api_key">{t('aiSettings.apiKey')}</label>
              <input
                id="api_key"
                type="password"
                placeholder={settings.api_key || t('aiSettings.apiKeyNotSet')}
                value={apiKeyInput}
                onChange={(e) => setApiKeyInput(e.target.value)}
              />
            </div>
          </div>

          <div className="settings-group">
            <h2>{t('aiSettings.opencodeGroup')}</h2>
            <div className="settings-row">
              <label htmlFor="opencode">{t('aiSettings.opencodeEnable')}</label>
              <input id="opencode" value={settings.opencode} onChange={(e) => field('opencode', e.target.value)} />
            </div>
          </div>

          {error && <p className="admin-note" style={{ color: 'var(--danger)' }}>{error}</p>}
          <div>
            <button className="admin-submit" type="submit" disabled={busy}>
              {busy ? t('common.saving') : saved ? t('common.saved') : t('common.save')}
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}
