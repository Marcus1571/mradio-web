import { useState } from 'react'
import type { FormEvent } from 'react'
import { api } from '../api/client'
import '../styles/auth.css'

// Pre-auth, no saved language preference exists yet — English-only,
// same reasoning as LoginScreen/ChangePasswordScreen's forced path.
export function ForgotPasswordScreen({ onBack }: { onBack: () => void }) {
  const [email, setEmail] = useState('')
  const [busy, setBusy] = useState(false)
  const [sent, setSent] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    try {
      await api.post('/api/auth/forgot-password', { email })
    } finally {
      // Always show the same outcome regardless of the response — the
      // backend itself never reveals whether the email was registered,
      // and the UI shouldn't undo that by branching on success/failure.
      setBusy(false)
      setSent(true)
    }
  }

  if (sent) {
    return (
      <div className="auth-screen">
        <div className="auth-card">
          <div className="auth-brand">
            <span className="brand-mark">mradio</span>
            <span className="brand-sub">dial&nbsp;room</span>
          </div>
          <h1 className="auth-title">Check your email</h1>
          <p className="auth-hint">
            If that email is registered, a reset link was sent. It expires in 1 hour.
          </p>
          <button className="auth-secondary" type="button" onClick={onBack}>
            Back to sign in
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="auth-screen">
      <form className="auth-card" onSubmit={onSubmit}>
        <div className="auth-brand">
          <span className="brand-mark">mradio</span>
          <span className="brand-sub">dial&nbsp;room</span>
        </div>
        <h1 className="auth-title">Forgot password?</h1>
        <p className="auth-hint">Enter your account's email and we'll send you a reset link.</p>
        <label className="field">
          <span>Email</span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            autoFocus
            required
          />
        </label>
        <button className="auth-submit" type="submit" disabled={busy}>
          {busy ? 'Sending…' : 'Send reset link'}
        </button>
        <button className="auth-secondary" type="button" onClick={onBack}>
          Back to sign in
        </button>
      </form>
    </div>
  )
}
