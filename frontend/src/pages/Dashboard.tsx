import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { Station } from '../api/types'
import { NowPlayingPanel } from '../components/NowPlayingPanel'
import { StationBrowserPanel } from '../components/StationBrowserPanel'
import { TopBar } from '../components/TopBar'
import type { Page } from '../components/TopBar'
import { useInitialConfig } from '../hooks/useConfig'
import { usePlayer } from '../hooks/usePlayer'
import { useTranslation } from '../i18n'
import type { Language } from '../i18n'
import { ChangePasswordScreen } from './ChangePasswordScreen'
import { AISettingsPage } from './AISettingsPage'
import { AnalyticsPage } from './AnalyticsPage'
import { UsersPage } from './UsersPage'
import '../styles/dashboard.css'

export function Dashboard() {
  const config = useInitialConfig()
  const player = usePlayer(config?.volume)
  const [theme, setTheme] = useState<'dark' | 'light'>('dark')
  const [language, setLanguageState] = useState<Language>('en')
  const [page, setPage] = useState<Page>('dashboard')
  const resumedRef = useRef(false)
  const t = useTranslation(language)

  useEffect(() => {
    if (!config) return
    const nextTheme = config.theme === 'light' ? 'light' : 'dark'
    setTheme(nextTheme)
    document.documentElement.setAttribute('data-theme', nextTheme)
    const nextLanguage: Language = config.language === 'es' ? 'es' : 'en'
    setLanguageState(nextLanguage)
    if (config.mute) player.toggleMute()
    if (!resumedRef.current && config.last_url) {
      resumedRef.current = true
      player.play({
        name: config.last_name || config.last_url,
        url: config.last_url,
        genre: config.last_genre || 'other',
      })
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
      {page === 'users' && <UsersPage t={t} />}
      {page === 'ai-settings' && <AISettingsPage t={t} />}
      {page === 'analytics' && <AnalyticsPage t={t} />}
    </div>
  )
}
