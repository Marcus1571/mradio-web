import { useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError } from '../api/client'
import { useAuth } from '../hooks/useAuth'
import '../styles/auth.css'

export function ChangePasswordScreen({
  forced = false,
  onDone,
}: {
  forced?: boolean
  onDone?: () => void
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
      setError('New password must be at least 8 characters.')
      return
    }
    if (next !== confirm) {
      setError('Passwords do not match.')
      return
    }
    setBusy(true)
    try {
      await changePassword(current, next)
      onDone?.()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not change password.')
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
        <h1 className="auth-title">{forced ? 'Choose a password' : 'Change password'}</h1>
        {forced && (
          <p className="auth-hint">This account was created with a temporary password. Set your own before continuing.</p>
        )}
        <label className="field">
          <span>Current password</span>
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
          <span>New password</span>
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
          <span>Confirm new password</span>
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
          {busy ? 'Saving…' : 'Set password'}
        </button>
        {forced && (
          <button className="auth-secondary" type="button" onClick={() => void logout()}>
            Sign out instead
          </button>
        )}
        {!forced && (
          <button className="auth-secondary" type="button" onClick={onDone}>
            Cancel
          </button>
        )}
      </form>
    </div>
  )
}
