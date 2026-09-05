import { useEffect, useRef, useState } from 'react'
import type { Station } from '../api/types'
import type { TFunction } from '../i18n'
import type { PlayerState } from '../hooks/usePlayer'
import { useProviders } from '../hooks/useProviders'
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
  opencode: 'opencode',
  ollama: 'ollama',
  openai: 'NIM',
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

  return (
    <section className="panel now-playing" aria-label={t('nowPlaying.ariaLabel')}>
      <div className="panel-head">
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

            {state.enriching && !state.enrichment && <p className="trivia-placeholder">{t('nowPlaying.askingProvider')}</p>}

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
    </section>
  )
}
