import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, api } from '../api/client'
import type { AITestResult, SmtpSettings } from '../api/types'
import { IDLE_TEST, KbNote, TestBadge } from '../components/AdminSettingsShared'
import type { TestState } from '../components/AdminSettingsShared'
import type { TFunction } from '../i18n'
import '../styles/admin.css'

export function EmailSettingsPage({ onBack, t }: { onBack?: () => void; t: TFunction }) {
  const [settings, setSettings] = useState<SmtpSettings | null>(null)
  const [passwordInput, setPasswordInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')
  const [test, setTest] = useState<TestState>(IDLE_TEST)

  useEffect(() => {
    api.get<SmtpSettings>('/api/settings/smtp').then(setSettings)
  }, [])

  function field<K extends keyof SmtpSettings>(key: K, value: SmtpSettings[K]) {
    setSettings((s) => (s ? { ...s, [key]: value } : s))
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!settings) return
    setError('')
    setBusy(true)
    try {
      const body: Partial<SmtpSettings> = { ...settings }
      if (passwordInput) body.password = passwordInput
      else delete body.password
      const res = await api.patch<SmtpSettings>('/api/settings/smtp', body)
      setSettings(res)
      setPasswordInput('')
      setSaved(true)
      window.setTimeout(() => setSaved(false), 2500)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('emailSettings.errorFallback'))
    } finally {
      setBusy(false)
    }
  }

  async function sendTest() {
    if (!settings) return
    setTest({ status: 'testing' })
    try {
      const overrides: Partial<SmtpSettings> = {
        host: settings.host,
        port: settings.port,
        username: settings.username,
        from_address: settings.from_address,
        use_tls: settings.use_tls,
        ...(passwordInput ? { password: passwordInput } : {}),
      }
      const res = await api.post<AITestResult>('/api/settings/smtp/test', overrides)
      setTest({ status: res.ok ? 'success' : 'failure', message: res.message })
    } catch {
      setTest({ status: 'failure', message: t('aiSettings.testError') })
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
        <h1>{t('emailSettings.title')}</h1>
        <p>{t('emailSettings.intro')}</p>
      </div>

      <form className="admin-panel" onSubmit={onSubmit}>
        <div className="settings-form">
          <div className="settings-group">
            <h2>{t('emailSettings.gmailGroup')}</h2>
            <KbNote
              prefix={t('emailSettings.kbNotePrefix')}
              linkLabel={t('emailSettings.kbNoteLink')}
              anchor="7-configuring-email-smtp"
              suffix={t('emailSettings.kbNoteSuffix')}
            />
            <ol className="admin-note" style={{ paddingLeft: '1.2rem' }}>
              <li>{t('emailSettings.gmailStep1')}</li>
              <li>
                {t('emailSettings.gmailStep2')}{' '}
                <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener noreferrer">
                  {t('emailSettings.gmailAppPasswordLink')}
                </a>
              </li>
              <li>{t('emailSettings.gmailStep3')}</li>
            </ol>
          </div>

          <div className="settings-group">
            <h2>{t('emailSettings.genericGroup')}</h2>
            <div className="settings-row">
              <label htmlFor="smtp_host">{t('emailSettings.fieldHost')}</label>
              <input
                id="smtp_host"
                placeholder="e.g. smtp.gmail.com"
                value={settings.host}
                onChange={(e) => field('host', e.target.value)}
              />
            </div>
            <div className="settings-row">
              <label htmlFor="smtp_port">{t('emailSettings.fieldPort')}</label>
              <input
                id="smtp_port"
                type="number"
                value={settings.port}
                onChange={(e) => field('port', Number(e.target.value))}
              />
            </div>
            <div className="settings-row">
              <label htmlFor="smtp_username">{t('emailSettings.fieldUsername')}</label>
              <input
                id="smtp_username"
                value={settings.username}
                onChange={(e) => field('username', e.target.value)}
              />
            </div>
            <div className="settings-row">
              <label htmlFor="smtp_password">{t('emailSettings.fieldPassword')}</label>
              <input
                id="smtp_password"
                type="password"
                placeholder={settings.password || t('emailSettings.passwordNotSet')}
                value={passwordInput}
                onChange={(e) => setPasswordInput(e.target.value)}
              />
            </div>
            <div className="settings-row">
              <label htmlFor="smtp_from">{t('emailSettings.fieldFromAddress')}</label>
              <input
                id="smtp_from"
                value={settings.from_address}
                onChange={(e) => field('from_address', e.target.value)}
              />
            </div>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={settings.use_tls}
                onChange={(e) => field('use_tls', e.target.checked)}
              />
              {t('emailSettings.fieldUseTls')}
            </label>
            <div className="settings-row">
              <label htmlFor="smtp_public_url">{t('emailSettings.fieldPublicUrl')}</label>
              <input
                id="smtp_public_url"
                placeholder="e.g. https://radio.example.com"
                value={settings.public_url}
                onChange={(e) => field('public_url', e.target.value)}
              />
            </div>
            <p className="admin-note">{t('emailSettings.publicUrlHint')}</p>
            <div className="test-actions">
              <button className="test-btn" type="button" disabled={test.status === 'testing'} onClick={() => void sendTest()}>
                {test.status === 'testing' ? t('aiSettings.testing') : t('aiSettings.test')}
              </button>
              <TestBadge state={test} t={t} />
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
