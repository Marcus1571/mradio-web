import { useEffect, useRef, useState } from 'react'
import { useAuth } from '../hooks/useAuth'
import { ChevronDownIcon, MoonIcon, SunIcon } from './Icons'

export type Page = 'dashboard' | 'users' | 'ai-settings' | 'change-password'

export function TopBar({
  theme,
  onToggleTheme,
  page,
  onNavigate,
}: {
  theme: 'dark' | 'light'
  onToggleTheme: () => void
  page: Page
  onNavigate: (page: Page) => void
}) {
  const { user, logout } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!menuOpen) return
    function onClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [menuOpen])

  const initials = (user?.username ?? '?').slice(0, 2).toUpperCase()

  return (
    <div className="topbar">
      <button className="brand" type="button" onClick={() => onNavigate('dashboard')}>
        <span className="brand-mark">mradio</span>
        <span className="brand-sub">dial&nbsp;room</span>
      </button>
      <div className="topbar-right">
        {page !== 'dashboard' && (
          <button className="text-btn" type="button" onClick={() => onNavigate('dashboard')}>
            Back to player
          </button>
        )}
        <button
          className="icon-btn"
          type="button"
          onClick={onToggleTheme}
          aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
          title={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
        >
          {theme === 'dark' ? <SunIcon /> : <MoonIcon />}
        </button>
        <div className="user-menu" ref={menuRef}>
          <button className="user-chip" type="button" onClick={() => setMenuOpen((v) => !v)}>
            <span className="avatar">{initials}</span>
            <span className="user-name">{user?.username}</span>
            <ChevronDownIcon />
          </button>
          {menuOpen && (
            <div className="user-dropdown">
              {user?.is_admin && (
                <>
                  <button type="button" onClick={() => { onNavigate('users'); setMenuOpen(false) }}>
                    Users
                  </button>
                  <button type="button" onClick={() => { onNavigate('ai-settings'); setMenuOpen(false) }}>
                    AI providers
                  </button>
                  <hr />
                </>
              )}
              <button type="button" onClick={() => { onNavigate('change-password'); setMenuOpen(false) }}>
                Change password
              </button>
              <hr />
              <button className="danger" type="button" onClick={() => void logout()}>
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
