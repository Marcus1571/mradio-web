import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, api } from '../api/client'
import type { AISettings, AITestResult } from '../api/types'
import type { TFunction } from '../i18n'
import '../styles/admin.css'

type Provider = 'ollama' | 'openai' | 'opencode'

type TestState = { status: 'idle' | 'testing' | 'success' | 'failure'; message?: string }

const IDLE: TestState = { status: 'idle' }

function TestBadge({ state, t }: { state: TestState; t: TFunction }) {
  if (state.status === 'idle') return null
  const pillClass =
    state.status === 'success' ? 'pill admin' : state.status === 'failure' ? 'pill disabled' : 'pill'
  const label =
    state.status === 'testing'
      ? t('aiSettings.testing')
      : state.status === 'success'
        ? t('aiSettings.testSuccess')
        : state.message || t('aiSettings.testFailure')
  return <span className={pillClass}>{label}</span>
}

export function AISettingsPage({ t }: { t: TFunction }) {
  const [settings, setSettings] = useState<AISettings | null>(null)
  const [apiKeyInput, setApiKeyInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')
  const [ollamaTest, setOllamaTest] = useState<TestState>(IDLE)
  const [openaiTest, setOpenaiTest] = useState<TestState>(IDLE)
  const [opencodeTest, setOpencodeTest] = useState<TestState>(IDLE)

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

  async function testProvider(
    provider: Provider,
    overrides: Partial<AISettings>,
    setState: (s: TestState) => void,
  ) {
    setState({ status: 'testing' })
    try {
      const res = await api.post<AITestResult>(`/api/settings/ai/test?provider=${provider}`, overrides)
      setState({ status: res.ok ? 'success' : 'failure', message: res.message })
    } catch {
      setState({ status: 'failure', message: t('aiSettings.testError') })
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
            <p className="admin-note">{t('aiSettings.ollamaNote')}</p>
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
            <div className="row-actions">
              <button
                type="button"
                disabled={ollamaTest.status === 'testing'}
                onClick={() =>
                  void testProvider(
                    'ollama',
                    {
                      ollama_url: settings.ollama_url,
                      ollama_model: settings.ollama_model,
                      ollama_timeout: settings.ollama_timeout,
                      ollama_gpu: settings.ollama_gpu,
                    },
                    setOllamaTest,
                  )
                }
              >
                {ollamaTest.status === 'testing' ? t('aiSettings.testing') : t('aiSettings.test')}
              </button>
              <TestBadge state={ollamaTest} t={t} />
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
            <div className="row-actions">
              <button
                type="button"
                disabled={openaiTest.status === 'testing'}
                onClick={() =>
                  void testProvider(
                    'openai',
                    {
                      api_base: settings.api_base,
                      api_model: settings.api_model,
                      api_timeout: settings.api_timeout,
                      ...(apiKeyInput ? { api_key: apiKeyInput } : {}),
                    },
                    setOpenaiTest,
                  )
                }
              >
                {openaiTest.status === 'testing' ? t('aiSettings.testing') : t('aiSettings.test')}
              </button>
              <TestBadge state={openaiTest} t={t} />
            </div>
          </div>

          <div className="settings-group">
            <h2>{t('aiSettings.opencodeGroup')}</h2>
            <div className="settings-row">
              <label htmlFor="opencode">{t('aiSettings.opencodeEnable')}</label>
              <input id="opencode" value={settings.opencode} onChange={(e) => field('opencode', e.target.value)} />
            </div>
            <div className="row-actions">
              <button
                type="button"
                disabled={opencodeTest.status === 'testing'}
                onClick={() =>
                  void testProvider(
                    'opencode',
                    { opencode: settings.opencode, opencode_timeout: settings.opencode_timeout },
                    setOpencodeTest,
                  )
                }
              >
                {opencodeTest.status === 'testing' ? t('aiSettings.testing') : t('aiSettings.test')}
              </button>
              <TestBadge state={opencodeTest} t={t} />
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
