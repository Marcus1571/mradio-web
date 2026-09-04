import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, api } from '../api/client'
import type { User } from '../api/types'
import { useAuth } from '../hooks/useAuth'
import '../styles/admin.css'

export function UsersPage() {
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
      setError(err instanceof ApiError ? err.message : 'Could not create user.')
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
    const next = window.prompt(`New temporary password for ${u.username} (min 8 characters):`)
    if (!next) return
    if (next.length < 8) {
      window.alert('Password must be at least 8 characters.')
      return
    }
    await api.patch(`/api/users/${u.id}`, { password: next })
    window.alert(`Password reset. They'll be asked to set their own on next sign-in.`)
  }

  async function deleteUser(u: User) {
    if (!window.confirm(`Delete ${u.username}? This cannot be undone.`)) return
    await api.del(`/api/users/${u.id}`)
    await refresh()
  }

  return (
    <div className="admin-page">
      <div className="admin-header">
        <h1>Users</h1>
        <p>Accounts are created here — there's no public sign-up.</p>
      </div>

      <div className="admin-panel">
        {!loading && (
          <table className="admin-table">
            <thead>
              <tr>
                <th>Username</th>
                <th>Status</th>
                <th>Created</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.username}</td>
                  <td>
                    {u.is_admin && <span className="pill admin">admin</span>}{' '}
                    {u.disabled && <span className="pill disabled">disabled</span>}
                    {u.must_change_password && <span className="pill">password pending</span>}
                  </td>
                  <td>{new Date(u.created_at).toLocaleDateString()}</td>
                  <td>
                    <div className="row-actions">
                      <button type="button" onClick={() => void toggleAdmin(u)} disabled={u.id === me?.id}>
                        {u.is_admin ? 'Remove admin' : 'Make admin'}
                      </button>
                      <button type="button" onClick={() => void toggleDisabled(u)} disabled={u.id === me?.id}>
                        {u.disabled ? 'Enable' : 'Disable'}
                      </button>
                      <button type="button" onClick={() => void resetPassword(u)}>
                        Reset password
                      </button>
                      <button
                        className="danger"
                        type="button"
                        onClick={() => void deleteUser(u)}
                        disabled={u.id === me?.id}
                      >
                        Delete
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
            <span>Username</span>
            <input value={username} onChange={(e) => setUsername(e.target.value)} required />
          </label>
          <label className="field">
            <span>Temporary password</span>
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
            Admin
          </label>
          <button className="admin-submit" type="submit" disabled={busy}>
            {busy ? 'Adding…' : 'Add user'}
          </button>
        </form>
        {error && <p className="admin-note" style={{ padding: '0 1rem 1rem', color: 'var(--danger)' }}>{error}</p>}
        <p className="admin-note" style={{ padding: '0 1rem 1rem' }}>
          New accounts must change this password on first sign-in.
        </p>
      </div>
    </div>
  )
}
