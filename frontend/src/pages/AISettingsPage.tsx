import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, api } from '../api/client'
import type { AISettings, AITestResult, CodexConnectResponse, GrokConnectResponse } from '../api/types'
import { IDLE_TEST, KbNote, ProviderBubble, TestBadge } from '../components/AdminSettingsShared'
import type { TestState } from '../components/AdminSettingsShared'
import { ChatGPTIcon, GeminiIcon, GrokIcon, NimIcon, OllamaIcon, OpenCodeIcon } from '../components/Icons'
import { useCodexStatus } from '../hooks/useCodexStatus'
import { useGrokStatus } from '../hooks/useGrokStatus'
import { useProviders } from '../hooks/useProviders'
import type { TFunction } from '../i18n'
import '../styles/admin.css'

type Provider = 'ollama' | 'openai' | 'opencode' | 'codex' | 'grok' | 'gemini'

export function AISettingsPage({ onBack, t }: { onBack?: () => void; t: TFunction }) {
  const [settings, setSettings] = useState<AISettings | null>(null)
  const [apiKeyInput, setApiKeyInput] = useState('')
  const [grokApiKeyInput, setGrokApiKeyInput] = useState('')
  const [geminiApiKeyInput, setGeminiApiKeyInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')
  const [ollamaTest, setOllamaTest] = useState<TestState>(IDLE_TEST)
  const [openaiTest, setOpenaiTest] = useState<TestState>(IDLE_TEST)
  const [opencodeTest, setOpencodeTest] = useState<TestState>(IDLE_TEST)
  const [codexTest, setCodexTest] = useState<TestState>(IDLE_TEST)
  const [grokTest, setGrokTest] = useState<TestState>(IDLE_TEST)
  const [geminiTest, setGeminiTest] = useState<TestState>(IDLE_TEST)
  const { status: codexStatus, refresh: refreshCodexStatus } = useCodexStatus()
  const [codexConnecting, setCodexConnecting] = useState(false)
  const [codexPromptResult, setCodexPromptResult] = useState<CodexConnectResponse | null>(null)
  const { status: grokStatus, refresh: refreshGrokStatus } = useGrokStatus()
  const [grokConnecting, setGrokConnecting] = useState(false)
  const [grokPromptResult, setGrokPromptResult] = useState<GrokConnectResponse | null>(null)
  const { providers, refresh: refreshProviders } = useProviders()

  function isEnabled(name: Provider): boolean {
    return providers.find((p) => p.name === name)?.enabled ?? false
  }

  useEffect(() => {
    api.get<AISettings>('/api/settings/ai').then(setSettings)
  }, [])

  useEffect(() => {
    if (codexStatus?.connected) {
      setCodexPromptResult(null)
      void refreshProviders()
    }
  }, [codexStatus?.connected, refreshProviders])

  useEffect(() => {
    if (grokStatus?.connected) {
      setGrokPromptResult(null)
      void refreshProviders()
    }
  }, [grokStatus?.connected, refreshProviders])

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
      if (grokApiKeyInput) body.grok_api_key = grokApiKeyInput
      else delete body.grok_api_key
      if (geminiApiKeyInput) body.gemini_api_key = geminiApiKeyInput
      else delete body.gemini_api_key
      const res = await api.patch<AISettings>('/api/settings/ai', body)
      setSettings(res)
      setApiKeyInput('')
      setGrokApiKeyInput('')
      setGeminiApiKeyInput('')
      setSaved(true)
      await refreshProviders()
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
      await refreshProviders()
    } finally {
      setCodexConnecting(false)
    }
  }

  async function disconnectCodex() {
    await api.post('/api/settings/codex/disconnect', {})
    setCodexPromptResult(null)
    setCodexTest(IDLE_TEST)
    await refreshCodexStatus()
    await refreshProviders()
  }

  // Independent of the main Save button, like connectGrok()'s immediate
  // grok_mode PATCH below — an admin flipping this needs it to take
  // effect right away (e.g. hiding a provider the moment it hits its
  // usage quota), not only after also filling in and submitting the
  // rest of the form.
  async function setCodexManuallyEnabled(value: boolean) {
    const res = await api.patch<AISettings>('/api/settings/ai', { codex_manually_enabled: value })
    setSettings(res)
    await refreshProviders()
  }

  async function setGrokManuallyEnabled(value: boolean) {
    const res = await api.patch<AISettings>('/api/settings/ai', { grok_manually_enabled: value })
    setSettings(res)
    await refreshProviders()
  }

  async function testGrok() {
    setGrokTest({ status: 'testing' })
    try {
      const res = await api.post<AITestResult>('/api/settings/grok/test', {})
      setGrokTest({ status: res.ok ? 'success' : 'failure', message: res.message })
    } catch {
      setGrokTest({ status: 'failure', message: t('aiSettings.testError') })
    }
  }

  async function connectGrok() {
    setGrokConnecting(true)
    setGrokPromptResult(null)
    try {
      // Persist grok_mode: 'subscription' immediately, independent of the
      // main form's Save button — Connect is a self-contained action from
      // the admin's point of view (confirmed live: an admin can select
      // Subscription, click Connect, and complete sign-in without ever
      // touching Save, leaving settings.json's saved grok_mode at its old
      // "api_key" value while grok_settings.json shows genuinely
      // connected — Test then read the stale saved mode and reported "No
      // API key configured." for an account that was actually connected).
      // Every other settings field defers to Save on purpose; grok_mode
      // is the one exception because Connect/Disconnect below already
      // write directly to the server outside the form's own save cycle.
      const updated = await api.patch<AISettings>('/api/settings/ai', { grok_mode: 'subscription' })
      setSettings(updated)
      const res = await api.post<GrokConnectResponse>('/api/settings/grok/connect', {})
      setGrokPromptResult(res)
      await refreshGrokStatus()
      await refreshProviders()
    } finally {
      setGrokConnecting(false)
    }
  }

  async function disconnectGrok() {
    await api.post('/api/settings/grok/disconnect', {})
    setGrokPromptResult(null)
    setGrokTest(IDLE_TEST)
    await refreshGrokStatus()
    await refreshProviders()
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
            <ProviderBubble
              icon={<ChatGPTIcon className="provider-mark" />}
              name={t('aiSettings.codexGroup')}
              enabled={isEnabled('codex')}
              defaultOpen={isEnabled('codex') || codexStatus?.pending === true}
            >
              <p className="admin-note">{t('aiSettings.codexIntro')}</p>
              <label className="provider-enable-toggle">
                <input
                  type="checkbox"
                  checked={settings.codex_manually_enabled}
                  onChange={(e) => void setCodexManuallyEnabled(e.target.checked)}
                />
                {t('aiSettings.providerEnableToggle')}
              </label>
              <p className="admin-note admin-note-hint">{t('aiSettings.providerEnableToggleHint')}</p>
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
                      <a href={codexPromptResult.verification_uri} target="_blank" rel="noopener noreferrer">
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
            </ProviderBubble>

            <ProviderBubble
              icon={<GrokIcon className="provider-mark" />}
              name={t('aiSettings.grokGroup')}
              enabled={isEnabled('grok')}
              defaultOpen={isEnabled('grok') || grokStatus?.pending === true}
            >
              <p className="admin-note">{t('aiSettings.grokIntro')}</p>
              <label className="provider-enable-toggle">
                <input
                  type="checkbox"
                  checked={settings.grok_manually_enabled}
                  onChange={(e) => void setGrokManuallyEnabled(e.target.checked)}
                />
                {t('aiSettings.providerEnableToggle')}
              </label>
              <p className="admin-note admin-note-hint">{t('aiSettings.providerEnableToggleHint')}</p>

              <div className="grok-mode-toggle" role="radiogroup" aria-label={t('aiSettings.grokModeLabel')}>
                <label className="grok-mode-option">
                  <input
                    type="radio"
                    name="grok_mode"
                    checked={settings.grok_mode === 'api_key'}
                    onChange={() => field('grok_mode', 'api_key')}
                  />
                  {t('aiSettings.grokModeApiKey')}
                </label>
                <label className="grok-mode-option">
                  <input
                    type="radio"
                    name="grok_mode"
                    checked={settings.grok_mode === 'subscription'}
                    onChange={() => field('grok_mode', 'subscription')}
                  />
                  {t('aiSettings.grokModeSubscription')}
                </label>
              </div>

              {settings.grok_mode === 'api_key' ? (
                <>
                  <div className="settings-row">
                    <label htmlFor="grok_api_base">{t('aiSettings.apiBaseUrl')}</label>
                    <input
                      id="grok_api_base"
                      value={settings.grok_api_base}
                      onChange={(e) => field('grok_api_base', e.target.value)}
                    />
                  </div>
                  <div className="settings-row">
                    <label htmlFor="grok_model">{t('aiSettings.model')}</label>
                    <input
                      id="grok_model"
                      value={settings.grok_model}
                      onChange={(e) => field('grok_model', e.target.value)}
                    />
                  </div>
                  <div className="settings-row">
                    <label htmlFor="grok_api_key">{t('aiSettings.apiKey')}</label>
                    <input
                      id="grok_api_key"
                      type="password"
                      placeholder={settings.grok_api_key || t('aiSettings.apiKeyNotSet')}
                      value={grokApiKeyInput}
                      onChange={(e) => setGrokApiKeyInput(e.target.value)}
                    />
                  </div>
                  <div className="test-actions">
                    <button
                      className="test-btn"
                      type="button"
                      disabled={grokTest.status === 'testing'}
                      onClick={() =>
                        void testProvider(
                          'grok',
                          {
                            grok_mode: 'api_key',
                            grok_api_base: settings.grok_api_base,
                            grok_model: settings.grok_model,
                            grok_timeout: settings.grok_timeout,
                            ...(grokApiKeyInput ? { grok_api_key: grokApiKeyInput } : {}),
                          },
                          setGrokTest,
                        )
                      }
                    >
                      {grokTest.status === 'testing' ? t('aiSettings.testing') : t('aiSettings.test')}
                    </button>
                    <TestBadge state={grokTest} t={t} />
                  </div>
                </>
              ) : grokStatus?.connected ? (
                <>
                  <p className="admin-note">{t('aiSettings.grokConnected')}</p>
                  <div className="test-actions">
                    <button className="test-btn" type="button" onClick={() => void disconnectGrok()}>
                      {t('aiSettings.codexDisconnect')}
                    </button>
                    <button
                      className="test-btn"
                      type="button"
                      disabled={grokTest.status === 'testing'}
                      onClick={() => void testGrok()}
                    >
                      {grokTest.status === 'testing' ? t('aiSettings.testing') : t('aiSettings.test')}
                    </button>
                    <TestBadge state={grokTest} t={t} />
                  </div>
                </>
              ) : grokStatus?.pending || grokPromptResult ? (
                <div className="admin-note">
                  <p>{t('aiSettings.codexWaiting')}</p>
                  {grokPromptResult && (
                    <p>
                      {t('aiSettings.codexUserCodeHint', { code: grokPromptResult.user_code })}{' '}
                      <a href={grokPromptResult.verification_uri} target="_blank" rel="noopener noreferrer">
                        {grokPromptResult.verification_uri}
                      </a>
                    </p>
                  )}
                </div>
              ) : (
                <div className="test-actions">
                  <button
                    className="test-btn"
                    type="button"
                    disabled={grokConnecting}
                    onClick={() => void connectGrok()}
                  >
                    {grokConnecting ? t('aiSettings.testing') : t('aiSettings.grokConnect')}
                  </button>
                </div>
              )}
            </ProviderBubble>

            <ProviderBubble
              icon={<GeminiIcon className="provider-mark" />}
              name={t('aiSettings.geminiGroup')}
              enabled={isEnabled('gemini')}
              defaultOpen={isEnabled('gemini')}
            >
              <p className="admin-note">{t('aiSettings.geminiIntro')}</p>
              <KbNote
                prefix={t('aiSettings.geminiNotePrefix')}
                linkLabel={t('aiSettings.geminiNoteLink')}
                anchor="google-gemini"
                suffix={t('aiSettings.geminiNoteSuffix')}
              />
              <div className="settings-row">
                <label htmlFor="gemini_model">{t('aiSettings.model')}</label>
                <input
                  id="gemini_model"
                  value={settings.gemini_model}
                  onChange={(e) => field('gemini_model', e.target.value)}
                />
              </div>
              <div className="settings-row">
                <label htmlFor="gemini_api_key">{t('aiSettings.apiKey')}</label>
                <input
                  id="gemini_api_key"
                  type="password"
                  placeholder={settings.gemini_api_key || t('aiSettings.apiKeyNotSet')}
                  value={geminiApiKeyInput}
                  onChange={(e) => setGeminiApiKeyInput(e.target.value)}
                />
              </div>
              <div className="test-actions">
                <button
                  className="test-btn"
                  type="button"
                  disabled={geminiTest.status === 'testing'}
                  onClick={() =>
                    void testProvider(
                      'gemini',
                      {
                        gemini_model: settings.gemini_model,
                        gemini_timeout: settings.gemini_timeout,
                        ...(geminiApiKeyInput ? { gemini_api_key: geminiApiKeyInput } : {}),
                      },
                      setGeminiTest,
                    )
                  }
                >
                  {geminiTest.status === 'testing' ? t('aiSettings.testing') : t('aiSettings.test')}
                </button>
                <TestBadge state={geminiTest} t={t} />
              </div>
            </ProviderBubble>

            <ProviderBubble
              icon={<OpenCodeIcon className="provider-mark" />}
              name={t('aiSettings.opencodeGroup')}
              enabled={isEnabled('opencode')}
              defaultOpen={isEnabled('opencode')}
            >
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
            </ProviderBubble>

            <ProviderBubble
              icon={<OllamaIcon className="provider-mark" />}
              name={t('aiSettings.ollamaGroup')}
              enabled={isEnabled('ollama')}
              defaultOpen={isEnabled('ollama')}
            >
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
            </ProviderBubble>

            <ProviderBubble
              icon={<NimIcon className="provider-mark" />}
              name={t('aiSettings.openaiGroup')}
              enabled={isEnabled('openai')}
              defaultOpen={isEnabled('openai')}
            >
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
            </ProviderBubble>
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
