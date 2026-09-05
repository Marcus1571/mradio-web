import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { Station } from '../api/types'
import { NowPlayingPanel } from '../components/NowPlayingPanel'
import { StationBrowserPanel } from '../components/StationBrowserPanel'
import { TopBar } from '../components/TopBar'
import type { Page } from '../components/TopBar'
import { useInitialConfig } from '../hooks/useConfig'
import { usePlayer } from '../hooks/usePlayer'
import { ChangePasswordScreen } from './ChangePasswordScreen'
import { AISettingsPage } from './AISettingsPage'
import { UsersPage } from './UsersPage'
import '../styles/dashboard.css'

export function Dashboard() {
  const config = useInitialConfig()
  const player = usePlayer(config?.volume)
  const [theme, setTheme] = useState<'dark' | 'light'>('dark')
  const [page, setPage] = useState<Page>('dashboard')
  const resumedRef = useRef(false)

  useEffect(() => {
    if (!config) return
    const t = config.theme === 'light' ? 'light' : 'dark'
    setTheme(t)
    document.documentElement.setAttribute('data-theme', t)
    if (config.mute) player.toggleMute()
    if (!resumedRef.current && config.last_url) {
      resumedRef.current = true
      player.play({ name: config.last_name || config.last_url, url: config.last_url, genre: 'other' })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config])

  function toggleTheme() {
    const next = theme === 'dark' ? 'light' : 'dark'
    setTheme(next)
    document.documentElement.setAttribute('data-theme', next)
    void api.patch('/api/config', { theme: next })
  }

  function onPlay(station: Station) {
    player.play(station)
  }

  return (
    <div>
      <TopBar theme={theme} onToggleTheme={toggleTheme} page={page} onNavigate={setPage} />
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
          />
          <StationBrowserPanel currentUrl={player.state.station?.url ?? null} onPlay={onPlay} />
        </div>
      )}
      {page === 'change-password' && <ChangePasswordScreen onDone={() => setPage('dashboard')} />}
      {page === 'users' && <UsersPage />}
      {page === 'ai-settings' && <AISettingsPage />}
    </div>
  )
}
