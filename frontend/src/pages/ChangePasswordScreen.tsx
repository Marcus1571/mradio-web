import { useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError } from '../api/client'
import { useAuth } from '../hooks/useAuth'
import type { TFunction } from '../i18n'
import '../styles/auth.css'

// Only used when this screen is reached from App.tsx's pre-auth `forced`
// path (no logged-in account yet, so no saved language preference exists
// to read) — that render is always English. When reached voluntarily from
// the Dashboard (user menu -> Change password), the real `t` is passed in.
const _EN_FALLBACK: TFunction = (key) => {
  const fallbacks: Record<string, string> = {
    'changePassword.title': 'Change password',
    'changePassword.tooShort': 'New password must be at least 8 characters.',
    'changePassword.mismatch': 'Passwords do not match.',
    'changePassword.errorFallback': 'Could not change password.',
    'changePassword.currentPassword': 'Current password',
    'changePassword.newPassword': 'New password',
    'changePassword.confirmNewPassword': 'Confirm new password',
    'changePassword.submit': 'Set password',
    'changePassword.cancel': 'Cancel',
    'common.saving': 'Saving…',
  }
  return fallbacks[key] ?? key
}

export function ChangePasswordScreen({
  forced = false,
  onDone,
  t = _EN_FALLBACK,
}: {
  forced?: boolean
  onDone?: () => void
  t?: TFunction
}) {
  const { changePassword, logout } = useAuth()
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    if (next.length < 8) {
      setError(t('changePassword.tooShort'))
      return
    }
    if (next !== confirm) {
      setError(t('changePassword.mismatch'))
      return
    }
    setBusy(true)
    try {
      await changePassword(current, next)
      onDone?.()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('changePassword.errorFallback'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-screen">
      <form className="auth-card" onSubmit={onSubmit}>
        <div className="auth-brand">
          <span className="brand-mark">mradio</span>
          <span className="brand-sub">dial&nbsp;room</span>
        </div>
        <h1 className="auth-title">{forced ? 'Choose a password' : t('changePassword.title')}</h1>
        {forced && (
          <p className="auth-hint">This account was created with a temporary password. Set your own before continuing.</p>
        )}
        <label className="field">
          <span>{t('changePassword.currentPassword')}</span>
          <input
            type="password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            autoComplete="current-password"
            autoFocus
            required
          />
        </label>
        <label className="field">
          <span>{t('changePassword.newPassword')}</span>
          <input
            type="password"
            value={next}
            onChange={(e) => setNext(e.target.value)}
            autoComplete="new-password"
            minLength={8}
            required
          />
        </label>
        <label className="field">
          <span>{t('changePassword.confirmNewPassword')}</span>
          <input
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            autoComplete="new-password"
            minLength={8}
            required
          />
        </label>
        {error && <p className="auth-error">{error}</p>}
        <button className="auth-submit" type="submit" disabled={busy}>
          {busy ? t('common.saving') : t('changePassword.submit')}
        </button>
        {forced && (
          <button className="auth-secondary" type="button" onClick={() => void logout()}>
            Sign out instead
          </button>
        )}
        {!forced && (
          <button className="auth-secondary" type="button" onClick={onDone}>
            {t('changePassword.cancel')}
          </button>
        )}
      </form>
    </div>
  )
}
