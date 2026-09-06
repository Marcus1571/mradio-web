import { useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, api } from '../api/client'
import '../styles/auth.css'

// Pre-auth, reached only via an emailed link — no logged-in account and
// so no saved language preference exists to read, same reasoning as
// ChangePasswordScreen's forced path. English-only by design.
export function ResetPasswordScreen() {
  const token = new URLSearchParams(window.location.search).get('token') ?? ''
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(false)

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
      await api.post('/api/auth/reset-password', { token, new_password: next })
      setDone(true)
    } catch (err) {
      setError(
        err instanceof ApiError
          ? 'This reset link is invalid or has expired. Please request a new one.'
          : 'Could not reset password.',
      )
    } finally {
      setBusy(false)
    }
  }

  if (!token) {
    return (
      <div className="auth-screen">
        <div className="auth-card">
          <div className="auth-brand">
            <span className="brand-mark">mradio web</span>
            <span className="brand-sub">player</span>
          </div>
          <h1 className="auth-title">Invalid link</h1>
          <p className="auth-hint">This password reset link is missing its token.</p>
          <a className="auth-submit" style={{ textAlign: 'center' }} href="/">
            Back to sign in
          </a>
        </div>
      </div>
    )
  }

  if (done) {
    return (
      <div className="auth-screen">
        <div className="auth-card">
          <div className="auth-brand">
            <span className="brand-mark">mradio web</span>
            <span className="brand-sub">player</span>
          </div>
          <h1 className="auth-title">Password reset</h1>
          <p className="auth-hint">You can now sign in with your new password.</p>
          <a className="auth-submit" style={{ textAlign: 'center' }} href="/">
            Back to sign in
          </a>
        </div>
      </div>
    )
  }

  return (
    <div className="auth-screen">
      <form className="auth-card" onSubmit={onSubmit}>
        <div className="auth-brand">
          <span className="brand-mark">mradio web</span>
          <span className="brand-sub">player</span>
        </div>
        <h1 className="auth-title">Reset your password</h1>
        <label className="field">
          <span>New password</span>
          <input
            type="password"
            value={next}
            onChange={(e) => setNext(e.target.value)}
            autoComplete="new-password"
            minLength={8}
            autoFocus
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
      </form>
    </div>
  )
}
