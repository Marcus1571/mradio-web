import { useEffect, useRef, useState } from 'react'
import { useAuth } from '../hooks/useAuth'
import { LANGUAGES } from '../i18n'
import type { Language, TFunction } from '../i18n'
import { ChevronDownIcon, MoonIcon, SunIcon } from './Icons'

export type Page = 'dashboard' | 'users' | 'ai-settings' | 'change-password'

export function TopBar({
  theme,
  onToggleTheme,
  page,
  onNavigate,
  language,
  onChangeLanguage,
  t,
}: {
  theme: 'dark' | 'light'
  onToggleTheme: () => void
  page: Page
  onNavigate: (page: Page) => void
  language: Language
  onChangeLanguage: (l: Language) => void
  t: TFunction
}) {
  const { user, logout } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement | null>(null)
  const [langOpen, setLangOpen] = useState(false)
  const langRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!menuOpen) return
    function onClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [menuOpen])

  useEffect(() => {
    if (!langOpen) return
    function onClick(e: MouseEvent) {
      if (langRef.current && !langRef.current.contains(e.target as Node)) setLangOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [langOpen])

  const initials = (user?.username ?? '?').slice(0, 2).toUpperCase()
  const currentLanguage = LANGUAGES.find((l) => l.code === language) ?? LANGUAGES[0]

  return (
    <div className="topbar">
      <button className="brand" type="button" onClick={() => onNavigate('dashboard')}>
        <span className="brand-mark">mradio</span>
        <span className="brand-sub">dial&nbsp;room</span>
      </button>
      <div className="topbar-right">
        <div className="dropdown-picker" ref={langRef}>
          <button className="dropdown-chip" type="button" onClick={() => setLangOpen((v) => !v)}>
            {currentLanguage.flag} {currentLanguage.label}
            <ChevronDownIcon />
          </button>
          {langOpen && (
            <div className="dropdown-menu">
              {LANGUAGES.map((l) => (
                <button
                  key={l.code}
                  className={`dropdown-option ${l.code === language ? 'active' : ''}`}
                  type="button"
                  onClick={() => {
                    void onChangeLanguage(l.code)
                    setLangOpen(false)
                  }}
                >
                  <span>{l.flag} {l.label}</span>
                </button>
              ))}
            </div>
          )}
        </div>
        <span className="app-version">v{__APP_VERSION__}</span>
        {page !== 'dashboard' && (
          <button className="text-btn" type="button" onClick={() => onNavigate('dashboard')}>
            {t('topbar.backToPlayer')}
          </button>
        )}
        <button
          className="icon-btn"
          type="button"
          onClick={onToggleTheme}
          aria-label={theme === 'dark' ? t('topbar.switchToLight') : t('topbar.switchToDark')}
          title={theme === 'dark' ? t('topbar.switchToLight') : t('topbar.switchToDark')}
        >
          {theme === 'dark' ? <MoonIcon /> : <SunIcon />}
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
                    {t('topbar.users')}
                  </button>
                  <button type="button" onClick={() => { onNavigate('ai-settings'); setMenuOpen(false) }}>
                    {t('topbar.aiProviders')}
                  </button>
                  <hr />
                </>
              )}
              <button type="button" onClick={() => { onNavigate('change-password'); setMenuOpen(false) }}>
                {t('topbar.changePassword')}
              </button>
              <hr />
              <button className="danger" type="button" onClick={() => void logout()}>
                {t('topbar.signOut')}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
