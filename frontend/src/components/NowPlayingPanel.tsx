import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { Station, TriviaHistoryEntry } from '../api/types'
import type { TFunction } from '../i18n'
import type { PlayerState } from '../hooks/usePlayer'
import { useProviders } from '../hooks/useProviders'
import { useStationLogo } from '../hooks/useStationLogo'
import { formatCache, formatElapsed, formatKHz, formatKbps } from '../utils/format'
import {
  ChevronDownIcon,
  ExternalLinkIcon,
  MuteIcon,
  PlayIcon,
  RefreshIcon,
  SparkleIcon,
  StopIcon,
  VolumeIcon,
} from './Icons'

const _PROVIDER_LABEL: Record<string, string> = {
  opencode: 'OpenCode',
  ollama: 'Ollama',
  openai: 'NIM',
  codex: 'ChatGPT',
}

function TriviaHistoryStrip({ version, t }: { version: number; t: TFunction }) {
  const [history, setHistory] = useState<TriviaHistoryEntry[]>([])
  const [expanded, setExpanded] = useState<number | null>(null)
  const [showFullExpanded, setShowFullExpanded] = useState(false)

  useEffect(() => {
    api.get<TriviaHistoryEntry[]>('/api/enrich/trivia-history').then(setHistory)
    // version bumps whenever a fresh enrichment lands (see usePlayer.ts) —
    // this is a persisted-per-user list now (trivia_history.py), not
    // client state, so a refetch is how a new entry shows up.
  }, [version])

  if (history.length === 0) return null

  const active = history.find((h) => h.id === expanded) ?? null

  return (
    <div className="trivia-history">
      <div className="trivia-label">
        <SparkleIcon />
        {t('nowPlaying.historyTitle')}
      </div>
      <div className="trivia-history-strip">
        {history.map((h) => (
          <button
            key={h.id}
            type="button"
            className={`trivia-history-chip ${h.id === expanded ? 'active' : ''}`}
            onClick={() => {
              setExpanded((cur) => (cur === h.id ? null : h.id))
              setShowFullExpanded(false)
            }}
          >
            <span className="trivia-history-chip-title">{h.title || h.raw_title}</span>
            <span className="trivia-history-chip-station">{h.station_name}</span>
          </button>
        ))}
      </div>
      {active && (
        <div className="trivia-history-expanded">
          {active.artist && <p className="np-composer">{active.artist}</p>}
          <p className="np-track-small">{active.title || active.raw_title}</p>
          <p className={`trivia ${showFullExpanded ? '' : 'clamped'}`}>{active.trivia}</p>
          <div className="trivia-actions">
            {active.trivia.length > 280 && (
              <button className="text-btn" type="button" onClick={() => setShowFullExpanded((v) => !v)}>
                {showFullExpanded ? t('nowPlaying.showLess') : t('nowPlaying.showMore')}
              </button>
            )}
            {active.wiki && (
              <a className="wiki-link" href={active.wiki} target="_blank" rel="noopener noreferrer">
                {t('nowPlaying.readOnWikipedia')}
                <ExternalLinkIcon />
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export function NowPlayingPanel({
  state,
  play,
  stop,
  reconnect,
  setVolume,
  toggleMute,
  reenrich,
  t,
}: {
  state: PlayerState
  play: (station: Station) => void
  stop: () => void
  reconnect: () => void
  setVolume: (v: number) => void
  toggleMute: () => void
  reenrich: () => void
  t: TFunction
}) {
  const { providers, active, activate } = useProviders()
  const [providerOpen, setProviderOpen] = useState(false)
  const [triviaExpanded, setTriviaExpanded] = useState(true)
  const providerRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!providerOpen) return
    function onClick(e: MouseEvent) {
      if (providerRef.current && !providerRef.current.contains(e.target as Node)) setProviderOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [providerOpen])

  const hasStation = state.station !== null
  const hasTrack = state.rawTitle !== ''
  const logo = useStationLogo(state.station)
  const [logoFailed, setLogoFailed] = useState(false)

  useEffect(() => {
    setLogoFailed(false)
  }, [logo])

  const showLogo = hasStation && !!logo && !logoFailed

  return (
    <section className="panel now-playing" aria-label={t('nowPlaying.ariaLabel')}>
      {showLogo && <img className="station-logo" src={logo} alt="" onError={() => setLogoFailed(true)} />}
      <div className={showLogo ? 'panel-head panel-head-with-logo' : 'panel-head'}>
        <div className="station-strip">
          {hasStation && <span className="live-dot" aria-hidden="true" />}
          <span className="station-name-strong">{hasStation ? state.stationName : t('nowPlaying.nothingPlaying')}</span>
        </div>
      </div>

      <div className="np-body">
        {!hasStation && <p className="np-empty">{t('nowPlaying.pickStation')}</p>}

        {hasStation && state.status === 'stopped' && (
          <p className="np-empty">{t('nowPlaying.stopped')}</p>
        )}

        {hasStation && state.status === 'playing' && !hasTrack && <p className="np-empty">{t('nowPlaying.connecting')}</p>}

        {hasTrack && state.status === 'playing' && (
          <>
            <div className="np-metrics">
              {formatKbps(state.bitrate) && <span className="np-metric">{formatKbps(state.bitrate)}</span>}
              {formatKHz(state.sampleRate) && <span className="np-metric">{formatKHz(state.sampleRate)}</span>}
              {state.format && (
                <span className="np-metric">{state.format.split('/')[1]?.toUpperCase() || state.format}</span>
              )}
              <span className="np-metric">{formatCache(state.bufferedAhead)}</span>
              <span className="np-metric">{formatElapsed(state.elapsed)}</span>
            </div>
            {state.artist && <p className="np-composer">{state.artist}</p>}
            <h1 className="np-track">{state.title || state.rawTitle}</h1>
            {state.performer && <p className="np-performer">{state.performer}</p>}

            <div className="trivia-label">
              <SparkleIcon />
              {t('nowPlaying.linerNotes')}
            </div>

            {state.enriching && !state.enrichment && (
              <p className="trivia-placeholder">
                {active
                  ? t('nowPlaying.askingNamedProvider', { provider: _PROVIDER_LABEL[active] || active })
                  : t('nowPlaying.askingProvider')}
              </p>
            )}

            {!state.enriching && !state.enrichment && (
              <p className="trivia-placeholder">{t('nowPlaying.noLinerNotes')}</p>
            )}

            {state.enrichment && (
              <>
                <p className={`trivia ${triviaExpanded ? '' : 'clamped'}`}>{state.enrichment.trivia}</p>
                <div className="trivia-actions">
                  {state.enrichment.trivia.length > 280 && (
                    <button className="text-btn" type="button" onClick={() => setTriviaExpanded((v) => !v)}>
                      {triviaExpanded ? t('nowPlaying.showLess') : t('nowPlaying.showMore')}
                    </button>
                  )}
                  {state.enrichment.wiki && (
                    <a
                      className="wiki-link"
                      href={state.enrichment.wiki}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {t('nowPlaying.readOnWikipedia')}
                      <ExternalLinkIcon />
                    </a>
                  )}
                  <button className="text-btn" type="button" onClick={reenrich} disabled={state.enriching}>
                    <RefreshIcon />
                    {t('nowPlaying.reAskAi')}
                  </button>
                </div>
              </>
            )}
          </>
        )}
      </div>

      <div className="transport">
        <button
          className="transport-btn"
          type="button"
          onClick={state.status === 'playing' ? stop : () => state.station && play(state.station)}
          disabled={!hasStation}
          aria-label={state.status === 'playing' ? t('nowPlaying.stop') : t('nowPlaying.play')}
        >
          {state.status === 'playing' ? <StopIcon /> : <PlayIcon />}
        </button>

        <button
          className="icon-btn reconnect-btn"
          type="button"
          onClick={reconnect}
          disabled={!hasStation}
          aria-label={t('nowPlaying.reconnect')}
          title={t('nowPlaying.reconnect')}
        >
          <RefreshIcon />
        </button>

        <div className="vol-group">
          <button
            className={`mute-btn ${state.muted ? 'active' : ''}`}
            type="button"
            onClick={toggleMute}
            aria-label={state.muted ? t('nowPlaying.unmute') : t('nowPlaying.mute')}
          >
            {state.muted ? <MuteIcon /> : <VolumeIcon />}
          </button>
          <input
            className="vol-slider"
            type="range"
            min={0}
            max={100}
            value={state.volume}
            onChange={(e) => setVolume(Number(e.target.value))}
            aria-label={t('nowPlaying.volume')}
          />
          <span className="vol-pct">{state.volume}%</span>
        </div>

        <div className="provider-picker dropdown-picker" ref={providerRef}>
          <button className="dropdown-chip" type="button" onClick={() => setProviderOpen((v) => !v)}>
            {t('nowPlaying.aiProvider')} · <b>{_PROVIDER_LABEL[active] || t('nowPlaying.none')}</b>
            <ChevronDownIcon />
          </button>
          {providerOpen && (
            <div className="dropdown-menu dropdown-menu--up">
              {providers.map((p) => (
                <button
                  key={p.name}
                  className={`dropdown-option ${p.name === active ? 'active' : ''}`}
                  type="button"
                  disabled={!p.enabled}
                  onClick={() => {
                    void activate(p.name)
                    setProviderOpen(false)
                  }}
                >
                  <span>{_PROVIDER_LABEL[p.name]}</span>
                  {!p.enabled && <span>{t('nowPlaying.notConfigured')}</span>}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <TriviaHistoryStrip version={state.triviaHistoryVersion} t={t} />
    </section>
  )
}
