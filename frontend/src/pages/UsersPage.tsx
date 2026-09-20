import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, api } from '../api/client'
import type { User } from '../api/types'
import { ChevronDownIcon, KeyIcon, MailIcon, PencilIcon, PowerIcon, ShieldIcon, TrashIcon } from '../components/Icons'
import { Modal } from '../components/Modal'
import { useAuth } from '../hooks/useAuth'
import type { TFunction } from '../i18n'
import { displayName } from '../utils/format'
import '../styles/admin.css'

type SortKey = 'username' | 'status' | 'created'
type SortDir = 'asc' | 'desc'

function statusRank(u: User): number {
  if (u.disabled) return 2
  if (u.is_admin) return 0
  return 1
}

type CreateForm = {
  username: string
  password: string
  fullName: string
  email: string
  isAdmin: boolean
}

const EMPTY_CREATE_FORM: CreateForm = { username: '', password: '', fullName: '', email: '', isAdmin: false }

export function UsersPage({ onBack, t }: { onBack?: () => void; t: TFunction }) {
  const { user: me } = useAuth()
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [sortKey, setSortKey] = useState<SortKey>('created')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  const [createOpen, setCreateOpen] = useState(false)
  const [createForm, setCreateForm] = useState<CreateForm>(EMPTY_CREATE_FORM)
  const [createBusy, setCreateBusy] = useState(false)
  const [createError, setCreateError] = useState('')

  const [editTarget, setEditTarget] = useState<User | null>(null)
  const [editFullName, setEditFullName] = useState('')
  const [editEmail, setEditEmail] = useState('')
  const [editBusy, setEditBusy] = useState(false)
  const [editError, setEditError] = useState('')

  async function refresh() {
    const res = await api.get<User[]>('/api/users')
    setUsers(res)
  }

  useEffect(() => {
    refresh().finally(() => setLoading(false))
  }, [])

  const sortedUsers = useMemo(() => {
    const dir = sortDir === 'asc' ? 1 : -1
    return [...users].sort((a, b) => {
      switch (sortKey) {
        case 'username':
          return dir * displayName(a).localeCompare(displayName(b))
        case 'status':
          return dir * (statusRank(a) - statusRank(b))
        case 'created':
          return dir * (new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
      }
    })
  }, [users, sortKey, sortDir])

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  function openCreate() {
    setCreateForm(EMPTY_CREATE_FORM)
    setCreateError('')
    setCreateOpen(true)
  }

  async function onCreate(e: FormEvent) {
    e.preventDefault()
    setCreateError('')
    setCreateBusy(true)
    try {
      await api.post('/api/users', {
        username: createForm.username,
        password: createForm.email ? undefined : createForm.password,
        is_admin: createForm.isAdmin,
        full_name: createForm.fullName || undefined,
        email: createForm.email || undefined,
      })
      setCreateOpen(false)
      await refresh()
    } catch (err) {
      setCreateError(err instanceof ApiError ? err.message : t('users.errorFallback'))
    } finally {
      setCreateBusy(false)
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

  async function resendInvite(u: User) {
    try {
      await api.post(`/api/users/${u.id}/resend-invite`)
      window.alert(t('users.resendInviteDone'))
    } catch (err) {
      window.alert(err instanceof ApiError ? err.message : t('users.resendInviteFailed'))
    }
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

  function openEdit(u: User) {
    setEditTarget(u)
    setEditFullName(u.full_name ?? '')
    setEditEmail(u.email ?? '')
    setEditError('')
  }

  async function onEditSubmit(e: FormEvent) {
    e.preventDefault()
    if (!editTarget) return
    setEditError('')
    setEditBusy(true)
    try {
      await api.patch(`/api/users/${editTarget.id}`, { full_name: editFullName, email: editEmail })
      setEditTarget(null)
      await refresh()
    } catch (err) {
      setEditError(err instanceof ApiError ? err.message : t('users.errorFallback'))
    } finally {
      setEditBusy(false)
    }
  }

  return (
    <div className="admin-page">
      {onBack && (
        <button className="admin-breadcrumb" type="button" onClick={onBack}>
          {t('settings.backToSettings')}
        </button>
      )}
      <div className="admin-header">
        <h1>{t('users.title')}</h1>
        <p>{t('users.subtitle')}</p>
      </div>

      <div className="admin-panel">
        {!loading && (
          <table className="admin-table admin-table-users">
            <thead>
              <tr>
                <th>
                  <button type="button" className="sort-header" onClick={() => toggleSort('username')}>
                    {t('users.colUsername')}
                    {sortKey === 'username' && (
                      <ChevronDownIcon className={`sort-chevron ${sortDir === 'asc' ? 'sort-chevron-up' : ''}`} />
                    )}
                  </button>
                </th>
                <th>
                  <button type="button" className="sort-header" onClick={() => toggleSort('status')}>
                    {t('users.colStatus')}
                    {sortKey === 'status' && (
                      <ChevronDownIcon className={`sort-chevron ${sortDir === 'asc' ? 'sort-chevron-up' : ''}`} />
                    )}
                  </button>
                </th>
                <th>
                  <button type="button" className="sort-header" onClick={() => toggleSort('created')}>
                    {t('users.colCreated')}
                    {sortKey === 'created' && (
                      <ChevronDownIcon className={`sort-chevron ${sortDir === 'asc' ? 'sort-chevron-up' : ''}`} />
                    )}
                  </button>
                </th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {sortedUsers.map((u) => (
                <tr key={u.id}>
                  <td>
                    {displayName(u)}
                    {u.full_name && <span className="user-name-sub">{u.username}</span>}
                    {u.email && <span className="user-name-sub">{u.email}</span>}
                  </td>
                  <td>
                    {u.is_admin && <span className="pill admin">{t('users.pillAdmin')}</span>}{' '}
                    {u.disabled && <span className="pill disabled">{t('users.pillDisabled')}</span>}
                    {u.must_change_password && <span className="pill">{t('users.pillPasswordPending')}</span>}
                  </td>
                  <td>{new Date(u.created_at).toLocaleDateString()}</td>
                  <td>
                    <div className="row-actions">
                      <button
                        type="button"
                        title={u.is_admin ? t('users.removeAdmin') : t('users.makeAdmin')}
                        onClick={() => void toggleAdmin(u)}
                        disabled={u.id === me?.id}
                      >
                        <ShieldIcon />
                      </button>
                      <button
                        type="button"
                        title={u.disabled ? t('users.enable') : t('users.disable')}
                        onClick={() => void toggleDisabled(u)}
                        disabled={u.id === me?.id}
                      >
                        <PowerIcon />
                      </button>
                      <button type="button" title={t('users.editProfile')} onClick={() => openEdit(u)}>
                        <PencilIcon />
                      </button>
                      {u.email && (
                        <button type="button" title={t('users.resendInvite')} onClick={() => void resendInvite(u)}>
                          <MailIcon />
                        </button>
                      )}
                      <button type="button" title={t('users.resetPassword')} onClick={() => void resetPassword(u)}>
                        <KeyIcon />
                      </button>
                      <button
                        className="danger row-actions-divider"
                        type="button"
                        title={t('users.delete')}
                        onClick={() => void deleteUser(u)}
                        disabled={u.id === me?.id}
                      >
                        <TrashIcon />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <div style={{ padding: 'var(--space-md)' }}>
          <button className="admin-submit" type="button" onClick={openCreate}>
            {t('users.addUser')}
          </button>
        </div>
        <p className="admin-note" style={{ padding: '0 1rem 1rem' }}>
          {t('users.footerNote')}
        </p>
      </div>

      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title={t('users.addUser')}>
        <form onSubmit={onCreate}>
          <label className="field">
            <span>{t('users.fieldUsername')}</span>
            <input
              value={createForm.username}
              onChange={(e) => setCreateForm((f) => ({ ...f, username: e.target.value }))}
              autoFocus
              required
            />
          </label>
          <label className="field">
            <span>{t('users.fieldFullName')}</span>
            <input
              value={createForm.fullName}
              onChange={(e) => setCreateForm((f) => ({ ...f, fullName: e.target.value }))}
            />
          </label>
          <label className="field">
            <span>{t('users.fieldEmail')}</span>
            <input
              type="email"
              value={createForm.email}
              onChange={(e) => setCreateForm((f) => ({ ...f, email: e.target.value }))}
            />
          </label>
          {createForm.email ? (
            <p className="admin-note">{t('users.fieldTempPasswordAuto')}</p>
          ) : (
            <label className="field">
              <span>{t('users.fieldTempPassword')}</span>
              <input
                type="text"
                value={createForm.password}
                onChange={(e) => setCreateForm((f) => ({ ...f, password: e.target.value }))}
                minLength={8}
                required
              />
            </label>
          )}
          <label className="checkbox">
            <input
              type="checkbox"
              checked={createForm.isAdmin}
              onChange={(e) => setCreateForm((f) => ({ ...f, isAdmin: e.target.checked }))}
            />
            {t('users.fieldAdmin')}
          </label>
          {createError && <p className="admin-note" style={{ color: 'var(--danger)' }}>{createError}</p>}
          <div className="modal-actions">
            <button className="modal-cancel" type="button" onClick={() => setCreateOpen(false)}>
              {t('common.cancel')}
            </button>
            <button className="admin-submit" type="submit" disabled={createBusy}>
              {createBusy ? t('users.adding') : t('users.addUser')}
            </button>
          </div>
        </form>
      </Modal>

      <Modal open={editTarget !== null} onClose={() => setEditTarget(null)} title={t('users.editProfile')}>
        <form onSubmit={onEditSubmit}>
          <label className="field">
            <span>{t('users.fieldFullName')}</span>
            <input value={editFullName} onChange={(e) => setEditFullName(e.target.value)} autoFocus />
          </label>
          <label className="field">
            <span>{t('users.fieldEmail')}</span>
            <input type="email" value={editEmail} onChange={(e) => setEditEmail(e.target.value)} />
          </label>
          {editError && <p className="admin-note" style={{ color: 'var(--danger)' }}>{editError}</p>}
          <div className="modal-actions">
            <button className="modal-cancel" type="button" onClick={() => setEditTarget(null)}>
              {t('common.cancel')}
            </button>
            <button className="admin-submit" type="submit" disabled={editBusy}>
              {editBusy ? t('common.saving') : t('common.save')}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
