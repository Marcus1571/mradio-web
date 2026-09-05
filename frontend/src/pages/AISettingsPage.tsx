import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, api } from '../api/client'
import type { AISettings } from '../api/types'
import '../styles/admin.css'

export function AISettingsPage() {
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
      setError(err instanceof ApiError ? err.message : 'Could not save settings.')
    } finally {
      setBusy(false)
    }
  }

  if (!settings) return null

  return (
    <div className="admin-page">
      <div className="admin-header">
        <h1>AI providers</h1>
        <p>
          Shared credentials for opencode, Ollama, and any OpenAI-compatible endpoint (e.g. NVIDIA NIM). Each
          person picks which of these they use from the player — nobody needs their own key.
        </p>
      </div>

      <form className="admin-panel" onSubmit={onSubmit}>
        <div className="settings-form">
          <div className="settings-group">
            <h2>Ollama</h2>
            <div className="settings-row">
              <label htmlFor="ollama_url">Server URL</label>
              <input
                id="ollama_url"
                placeholder="http://192.168.1.12:11434"
                value={settings.ollama_url}
                onChange={(e) => field('ollama_url', e.target.value)}
              />
            </div>
            <div className="settings-row">
              <label htmlFor="ollama_model">Model</label>
              <input
                id="ollama_model"
                value={settings.ollama_model}
                onChange={(e) => field('ollama_model', e.target.value)}
              />
            </div>
          </div>

          <div className="settings-group">
            <h2>OpenAI-compatible (NIM, etc.)</h2>
            <p className="admin-note">
              New to NIM? See "Getting an API key" under NVIDIA NIM in the project's KB.md for how to get a
              free API key.
            </p>
            <div className="settings-row">
              <label htmlFor="api_base">API base URL</label>
              <input id="api_base" value={settings.api_base} onChange={(e) => field('api_base', e.target.value)} />
            </div>
            <div className="settings-row">
              <label htmlFor="api_model">Model</label>
              <input id="api_model" value={settings.api_model} onChange={(e) => field('api_model', e.target.value)} />
            </div>
            <div className="settings-row">
              <label htmlFor="api_key">API key</label>
              <input
                id="api_key"
                type="password"
                placeholder={settings.api_key || 'not set'}
                value={apiKeyInput}
                onChange={(e) => setApiKeyInput(e.target.value)}
              />
            </div>
          </div>

          <div className="settings-group">
            <h2>opencode</h2>
            <div className="settings-row">
              <label htmlFor="opencode">Enable (port, or "1" for default)</label>
              <input id="opencode" value={settings.opencode} onChange={(e) => field('opencode', e.target.value)} />
            </div>
          </div>

          {error && <p className="admin-note" style={{ color: 'var(--danger)' }}>{error}</p>}
          <div>
            <button className="admin-submit" type="submit" disabled={busy}>
              {busy ? 'Saving…' : saved ? 'Saved' : 'Save'}
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}
