import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { Station } from '../api/types'
import { NowPlayingPanel } from '../components/NowPlayingPanel'
import { StationBrowserPanel } from '../components/StationBrowserPanel'
import { TopBar } from '../components/TopBar'
import type { Page } from '../components/TopBar'
import { useInitialConfig } from '../hooks/useConfig'
import { usePlayer } from '../hooks/usePlayer'
import { LANGUAGES, applyDirection, useTranslation } from '../i18n'
import type { Language } from '../i18n'
import { ChangePasswordScreen } from './ChangePasswordScreen'
import { AISettingsPage } from './AISettingsPage'
import { AnalyticsPage } from './AnalyticsPage'
import { EmailSettingsPage } from './EmailSettingsPage'
import { SettingsPage } from './SettingsPage'
import { SpotifySettingsPage } from './SpotifySettingsPage'
import { UsersPage } from './UsersPage'
import '../styles/dashboard.css'

export function Dashboard() {
  const config = useInitialConfig()
  const player = usePlayer(config?.volume)
  const [theme, setTheme] = useState<'dark' | 'light'>('light')
  const [language, setLanguageState] = useState<Language>('en')
  const [page, setPage] = useState<Page>('dashboard')
  const resumedRef = useRef(false)
  const t = useTranslation(language)

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (window.location.pathname === '/settings' || params.has('spotify')) {
      setPage('spotify-settings')
      if (params.get('spotify') === 'connected') {
        // The status will refresh from the settings page; no toast needed.
      }
    }
  }, [])

  useEffect(() => {
    if (!config) return
    // Light is now the default for anyone with no saved preference yet
    // (a fresh config.json, or one that predates the theme key) —
    // 'dark' only wins when explicitly saved, the inverse of the old
    // fallback direction.
    const nextTheme = config.theme === 'dark' ? 'dark' : 'light'
    setTheme(nextTheme)
    document.documentElement.setAttribute('data-theme', nextTheme)
    const nextLanguage: Language = LANGUAGES.some((l) => l.code === config.language)
      ? (config.language as Language)
      : 'en'
    setLanguageState(nextLanguage)
    applyDirection(nextLanguage)
    if (typeof config.volume === 'number') player.applySavedVolume(config.volume)
    if (config.mute) player.toggleMute()
    if (!resumedRef.current && config.last_url) {
      resumedRef.current = true
      const station = {
        name: config.last_name || config.last_url,
        url: config.last_url,
        genre: config.last_genre || 'other',
      }
      // last_status === 'playing': actually resume the stream. Anything
      // else (including a legacy config with no last_status at all):
      // still show the last-picked station in the panel, in its
      // "Stopped" state, rather than either silently auto-playing audio
      // the user explicitly stopped, or dropping the selection entirely
      // and showing an empty "Nothing playing" panel — see 1.4.2's
      // STATUS.md entry for why last_status exists and 1.4.3 for why
      // selectStation() exists.
      if (config.last_status === 'playing') player.play(station)
      else player.selectStation(station)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config])

  function toggleTheme() {
    const next = theme === 'dark' ? 'light' : 'dark'
    setTheme(next)
    document.documentElement.setAttribute('data-theme', next)
    void api.patch('/api/config', { theme: next })
  }

  async function setLanguage(next: Language) {
    setLanguageState(next)
    applyDirection(next)
    // Awaited (unlike theme's fire-and-forget PATCH): the backend Enricher
    // only picks up the new language once this lands, and re-asking the
    // current track's liner notes right after depends on that having
    // already happened — otherwise the re-ask could race ahead of it and
    // still come back in the old language.
    await api.patch('/api/config', { language: next })
    player.reenrich()
  }

  function onPlay(station: Station) {
    player.play(station)
  }

  return (
    <div>
      <TopBar
        theme={theme}
        onToggleTheme={toggleTheme}
        page={page}
        onNavigate={setPage}
        language={language}
        onChangeLanguage={setLanguage}
        t={t}
      />
      {page === 'dashboard' && (
        <div className="dashboard">
          <NowPlayingPanel
            state={player.state}
            play={player.play}
            stop={player.stop}
            reconnect={player.reconnect}
            setVolume={player.setVolume}
            toggleMute={player.toggleMute}
            reenrich={player.reenrich}
            t={t}
          />
          <StationBrowserPanel currentUrl={player.state.station?.url ?? null} onPlay={onPlay} t={t} />
        </div>
      )}
      {page === 'change-password' && <ChangePasswordScreen onDone={() => setPage('dashboard')} t={t} />}
      {page === 'settings' && <SettingsPage onNavigate={setPage} t={t} />}
      {page === 'users' && <UsersPage onBack={() => setPage('settings')} t={t} />}
      {page === 'ai-settings' && <AISettingsPage onBack={() => setPage('settings')} t={t} />}
      {page === 'email-settings' && <EmailSettingsPage onBack={() => setPage('settings')} t={t} />}
      {page === 'spotify-settings' && <SpotifySettingsPage onBack={() => setPage('settings')} t={t} />}
      {page === 'analytics' && <AnalyticsPage t={t} />}
    </div>
  )
}
