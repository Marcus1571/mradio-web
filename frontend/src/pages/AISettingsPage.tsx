import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, api } from '../api/client'
import type { AISettings, AITestResult, CodexConnectResponse } from '../api/types'
import { IDLE_TEST, KbNote, TestBadge } from '../components/AdminSettingsShared'
import type { TestState } from '../components/AdminSettingsShared'
import { useCodexStatus } from '../hooks/useCodexStatus'
import type { TFunction } from '../i18n'
import '../styles/admin.css'

type Provider = 'ollama' | 'openai' | 'opencode' | 'codex'

export function AISettingsPage({ onBack, t }: { onBack?: () => void; t: TFunction }) {
  const [settings, setSettings] = useState<AISettings | null>(null)
  const [apiKeyInput, setApiKeyInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')
  const [ollamaTest, setOllamaTest] = useState<TestState>(IDLE_TEST)
  const [openaiTest, setOpenaiTest] = useState<TestState>(IDLE_TEST)
  const [opencodeTest, setOpencodeTest] = useState<TestState>(IDLE_TEST)
  const [codexTest, setCodexTest] = useState<TestState>(IDLE_TEST)
  const { status: codexStatus, refresh: refreshCodexStatus } = useCodexStatus()
  const [codexConnecting, setCodexConnecting] = useState(false)
  const [codexPromptResult, setCodexPromptResult] = useState<CodexConnectResponse | null>(null)

  useEffect(() => {
    api.get<AISettings>('/api/settings/ai').then(setSettings)
  }, [])

  useEffect(() => {
    if (codexStatus?.connected) setCodexPromptResult(null)
  }, [codexStatus?.connected])

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

  async function testCodex() {
    setCodexTest({ status: 'testing' })
    try {
      const res = await api.post<AITestResult>('/api/settings/codex/test', {})
      setCodexTest({ status: res.ok ? 'success' : 'failure', message: res.message })
    } catch {
      setCodexTest({ status: 'failure', message: t('aiSettings.testError') })
    }
  }

  async function connectCodex() {
    setCodexConnecting(true)
    setCodexPromptResult(null)
    try {
      const res = await api.post<CodexConnectResponse>('/api/settings/codex/connect', {})
      setCodexPromptResult(res)
      await refreshCodexStatus()
    } finally {
      setCodexConnecting(false)
    }
  }

  async function disconnectCodex() {
    await api.post('/api/settings/codex/disconnect', {})
    setCodexPromptResult(null)
    setCodexTest(IDLE_TEST)
    await refreshCodexStatus()
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
        <h1>{t('aiSettings.title')}</h1>
        <p>{t('aiSettings.intro')}</p>
      </div>

      <form className="admin-panel" onSubmit={onSubmit}>
        <div className="settings-form">
          <div className="provider-bubbles">
            <div className="settings-group">
              <div className="settings-group-head">
                <h2>
                  <span className={`provider-status-dot ${codexStatus?.connected ? 'on' : ''}`} aria-hidden="true" />
                  {t('aiSettings.codexGroup')}
                </h2>
              </div>
              <p className="admin-note">{t('aiSettings.codexIntro')}</p>
              {codexStatus?.connected ? (
                <>
                  <p className="admin-note">
                    {t('aiSettings.codexConnected', { plan: codexStatus.chatgpt_plan_type || '—' })}
                  </p>
                  <div className="test-actions">
                    <button className="test-btn" type="button" onClick={() => void disconnectCodex()}>
                      {t('aiSettings.codexDisconnect')}
                    </button>
                    <button
                      className="test-btn"
                      type="button"
                      disabled={codexTest.status === 'testing'}
                      onClick={() => void testCodex()}
                    >
                      {codexTest.status === 'testing' ? t('aiSettings.testing') : t('aiSettings.test')}
                    </button>
                    <TestBadge state={codexTest} t={t} />
                  </div>
                </>
              ) : codexStatus?.pending || codexPromptResult ? (
                <div className="admin-note">
                  <p>{t('aiSettings.codexWaiting')}</p>
                  {codexPromptResult && (
                    <p>
                      {t('aiSettings.codexUserCodeHint', { code: codexPromptResult.user_code })}{' '}
                      <a
                        href={codexPromptResult.verification_uri}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {codexPromptResult.verification_uri}
                      </a>
                    </p>
                  )}
                </div>
              ) : (
                <div className="test-actions">
                  <button
                    className="test-btn"
                    type="button"
                    disabled={codexConnecting}
                    onClick={() => void connectCodex()}
                  >
                    {codexConnecting ? t('aiSettings.testing') : t('aiSettings.codexConnect')}
                  </button>
                </div>
              )}
            </div>

            <div className="settings-group">
              <div className="settings-group-head">
                <h2>
                  <span className={`provider-status-dot ${settings.opencode ? 'on' : ''}`} aria-hidden="true" />
                  {t('aiSettings.opencodeGroup')}
                </h2>
              </div>
              <div className="settings-row">
                <label htmlFor="opencode">{t('aiSettings.opencodeEnable')}</label>
                <input id="opencode" value={settings.opencode} onChange={(e) => field('opencode', e.target.value)} />
              </div>
              <div className="test-actions">
                <button
                  className="test-btn"
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

            <div className="settings-group">
              <div className="settings-group-head">
                <h2>
                  <span className={`provider-status-dot ${settings.ollama_url ? 'on' : ''}`} aria-hidden="true" />
                  {t('aiSettings.ollamaGroup')}
                </h2>
              </div>
              <KbNote
                prefix={t('aiSettings.ollamaNotePrefix')}
                linkLabel={t('aiSettings.ollamaNoteLink')}
                anchor="ollama"
                suffix={t('aiSettings.ollamaNoteSuffix')}
              />
              <div className="settings-row">
                <label htmlFor="ollama_url">{t('aiSettings.serverUrl')}</label>
                <input
                  id="ollama_url"
                  placeholder="e.g. http://192.168.1.12:11434"
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
              <div className="test-actions">
                <button
                  className="test-btn"
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
              <div className="settings-group-head">
                <h2>
                  <span className={`provider-status-dot ${settings.api_key ? 'on' : ''}`} aria-hidden="true" />
                  {t('aiSettings.openaiGroup')}
                </h2>
              </div>
              <KbNote
                prefix={t('aiSettings.nimNotePrefix')}
                linkLabel={t('aiSettings.nimNoteLink')}
                anchor="nvidia-nim-openai-compatible"
                suffix={t('aiSettings.nimNoteSuffix')}
              />
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
              <div className="test-actions">
                <button
                  className="test-btn"
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
