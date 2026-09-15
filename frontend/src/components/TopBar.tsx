import { useEffect, useRef, useState } from 'react'
import { useAuth } from '../hooks/useAuth'
import { LANGUAGES } from '../i18n'
import type { Language, TFunction } from '../i18n'
import type { Theme } from '../api/types'
import { displayName } from '../utils/format'
import { AnchorIcon, ChevronDownIcon, DropletIcon, LeafIcon, MoonIcon, RefreshIcon, SunIcon } from './Icons'
import type { ComponentType } from 'react'
import type { IconProps } from './Icons'

const THEME_ORDER: Theme[] = ['light', 'dark', 'sapphire', 'jade', 'harbor']

const THEME_ICON: Record<Theme, ComponentType<IconProps>> = {
  light: SunIcon,
  dark: MoonIcon,
  sapphire: DropletIcon,
  jade: LeafIcon,
  harbor: AnchorIcon,
}

const THEME_LABEL_KEY: Record<Theme, string> = {
  light: 'topbar.themeDay',
  dark: 'topbar.themeNight',
  sapphire: 'topbar.themeSapphire',
  jade: 'topbar.themeJade',
  harbor: 'topbar.themeHarbor',
}

export type Page =
  | 'dashboard'
  | 'settings'
  | 'users'
  | 'ai-settings'
  | 'email-settings'
  | 'spotify-settings'
  | 'deezer-settings'
  | 'analytics'
  | 'change-password'

export function TopBar({
  theme,
  onChangeTheme,
  page,
  onNavigate,
  language,
  onChangeLanguage,
  t,
}: {
  theme: Theme
  onChangeTheme: (theme: Theme) => void
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
  const [themeOpen, setThemeOpen] = useState(false)
  const themeRef = useRef<HTMLDivElement | null>(null)

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

  useEffect(() => {
    if (!themeOpen) return
    function onClick(e: MouseEvent) {
      if (themeRef.current && !themeRef.current.contains(e.target as Node)) setThemeOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [themeOpen])

  const name = user ? displayName(user) : '?'
  const initials = name.slice(0, 2).toUpperCase()
  const currentLanguage = LANGUAGES.find((l) => l.code === language) ?? LANGUAGES[0]

  return (
    <div className="topbar">
      <button className="brand" type="button" onClick={() => onNavigate('dashboard')}>
        <span className="brand-mark">mradio web</span>
        <span className="brand-sub">player</span>
      </button>
      <div className="topbar-right">
        <div className="dropdown-picker" ref={langRef}>
          <button className="dropdown-chip" type="button" onClick={() => setLangOpen((v) => !v)}>
            <span aria-hidden="true">{currentLanguage.flag}</span>
            <span className="lang-label">{currentLanguage.label}</span>
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
        <div className="dropdown-picker" ref={themeRef}>
          <button
            className="icon-btn"
            type="button"
            onClick={() => setThemeOpen((v) => !v)}
            aria-label={t('topbar.theme')}
            title={t('topbar.theme')}
          >
            {(() => {
              const CurrentThemeIcon = THEME_ICON[theme]
              return <CurrentThemeIcon />
            })()}
          </button>
          {themeOpen && (
            <div className="dropdown-menu">
              {THEME_ORDER.map((themeOption) => {
                const OptionIcon = THEME_ICON[themeOption]
                return (
                  <button
                    key={themeOption}
                    className={`dropdown-option ${themeOption === theme ? 'active' : ''}`}
                    type="button"
                    onClick={() => {
                      onChangeTheme(themeOption)
                      setThemeOpen(false)
                    }}
                  >
                    <span className="dropdown-option-icon">
                      <OptionIcon /> {t(THEME_LABEL_KEY[themeOption])}
                    </span>
                  </button>
                )
              })}
            </div>
          )}
        </div>
        <button
          className="icon-btn"
          type="button"
          onClick={() => window.location.reload()}
          aria-label={t('topbar.reloadApp')}
          title={t('topbar.reloadApp')}
        >
          <RefreshIcon />
        </button>
        {user?.is_admin && (
          <button className="dropdown-chip" type="button" onClick={() => onNavigate('analytics')}>
            {t('topbar.dashboard')}
          </button>
        )}
        <div className="user-menu" ref={menuRef}>
          <button className="user-chip" type="button" onClick={() => setMenuOpen((v) => !v)}>
            <span className="avatar">{initials}</span>
            <span className="user-name">{name}</span>
            <ChevronDownIcon />
          </button>
          {menuOpen && (
            <div className="user-dropdown">
              {user?.is_admin && (
                <>
                  <button type="button" onClick={() => { onNavigate('settings'); setMenuOpen(false) }}>
                    {t('topbar.settings')}
                  </button>
                  <hr />
                </>
              )}
              <a href="https://github.com/Marcus1571/mradio-web/tree/main" target="_blank" rel="noopener noreferrer">
                {t('topbar.githubProject')}
              </a>
              <hr />
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
