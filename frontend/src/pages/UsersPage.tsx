import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, api } from '../api/client'
import type { User } from '../api/types'
import { useAuth } from '../hooks/useAuth'
import type { TFunction } from '../i18n'
import '../styles/admin.css'

export function UsersPage({ t }: { t: TFunction }) {
  const { user: me } = useAuth()
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [isAdmin, setIsAdmin] = useState(false)
  const [busy, setBusy] = useState(false)

  async function refresh() {
    const res = await api.get<User[]>('/api/users')
    setUsers(res)
  }

  useEffect(() => {
    refresh().finally(() => setLoading(false))
  }, [])

  async function onCreate(e: FormEvent) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      await api.post('/api/users', { username, password, is_admin: isAdmin })
      setUsername('')
      setPassword('')
      setIsAdmin(false)
      await refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('users.errorFallback'))
    } finally {
      setBusy(false)
    }
  }

  async function toggleDisabled(u: User) {
    await api.patch(`/api/users/${u.id}`, { disabled: !u.disabled })
    await refresh()
  }

  async function toggleAdmin(u: User) {
    await api.patch(`/api/users/${u.id}`, { is_admin: !u.is_admin })
    await refresh()
  }

  async function resetPassword(u: User) {
    const next = window.prompt(t('users.resetPasswordPrompt', { username: u.username }))
    if (!next) return
    if (next.length < 8) {
      window.alert(t('users.resetPasswordTooShort'))
      return
    }
    await api.patch(`/api/users/${u.id}`, { password: next })
    window.alert(t('users.resetPasswordDone'))
  }

  async function deleteUser(u: User) {
    if (!window.confirm(t('users.deleteConfirm', { username: u.username }))) return
    await api.del(`/api/users/${u.id}`)
    await refresh()
  }

  return (
    <div className="admin-page">
      <div className="admin-header">
        <h1>{t('users.title')}</h1>
        <p>{t('users.subtitle')}</p>
      </div>

      <div className="admin-panel">
        {!loading && (
          <table className="admin-table">
            <thead>
              <tr>
                <th>{t('users.colUsername')}</th>
                <th>{t('users.colStatus')}</th>
                <th>{t('users.colCreated')}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.username}</td>
                  <td>
                    {u.is_admin && <span className="pill admin">{t('users.pillAdmin')}</span>}{' '}
                    {u.disabled && <span className="pill disabled">{t('users.pillDisabled')}</span>}
                    {u.must_change_password && <span className="pill">{t('users.pillPasswordPending')}</span>}
                  </td>
                  <td>{new Date(u.created_at).toLocaleDateString()}</td>
                  <td>
                    <div className="row-actions">
                      <button type="button" onClick={() => void toggleAdmin(u)} disabled={u.id === me?.id}>
                        {u.is_admin ? t('users.removeAdmin') : t('users.makeAdmin')}
                      </button>
                      <button type="button" onClick={() => void toggleDisabled(u)} disabled={u.id === me?.id}>
                        {u.disabled ? t('users.enable') : t('users.disable')}
                      </button>
                      <button type="button" onClick={() => void resetPassword(u)}>
                        {t('users.resetPassword')}
                      </button>
                      <button
                        className="danger"
                        type="button"
                        onClick={() => void deleteUser(u)}
                        disabled={u.id === me?.id}
                      >
                        {t('users.delete')}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <form className="admin-form" onSubmit={onCreate}>
          <label className="field">
            <span>{t('users.fieldUsername')}</span>
            <input value={username} onChange={(e) => setUsername(e.target.value)} required />
          </label>
          <label className="field">
            <span>{t('users.fieldTempPassword')}</span>
            <input
              type="text"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={8}
              required
            />
          </label>
          <label className="checkbox">
            <input type="checkbox" checked={isAdmin} onChange={(e) => setIsAdmin(e.target.checked)} />
            {t('users.fieldAdmin')}
          </label>
          <button className="admin-submit" type="submit" disabled={busy}>
            {busy ? t('users.adding') : t('users.addUser')}
          </button>
        </form>
        {error && <p className="admin-note" style={{ padding: '0 1rem 1rem', color: 'var(--danger)' }}>{error}</p>}
        <p className="admin-note" style={{ padding: '0 1rem 1rem' }}>
          {t('users.footerNote')}
        </p>
      </div>
    </div>
  )
}
