import { useEffect, useRef, useState } from 'react'
import type { PlayerState } from '../hooks/usePlayer'
import { useProviders } from '../hooks/useProviders'
import { formatCache, formatElapsed, formatKHz, formatKbps } from '../utils/format'
import {
  ChevronDownIcon,
  ExternalLinkIcon,
  MuteIcon,
  PauseIcon,
  PlayIcon,
  RefreshIcon,
  SparkleIcon,
  VolumeIcon,
} from './Icons'

const _PROVIDER_LABEL: Record<string, string> = {
  opencode: 'opencode',
  ollama: 'ollama',
  openai: 'NIM',
}

export function NowPlayingPanel({
  state,
  togglePause,
  reconnect,
  setVolume,
  toggleMute,
  reenrich,
}: {
  state: PlayerState
  togglePause: () => void
  reconnect: () => void
  setVolume: (v: number) => void
  toggleMute: () => void
  reenrich: () => void
}) {
  const { providers, active, activate } = useProviders()
  const [providerOpen, setProviderOpen] = useState(false)
  const [triviaExpanded, setTriviaExpanded] = useState(false)
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
    <section className="panel now-playing" aria-label="Now playing">
      <div className="panel-head">
        <div className="station-strip">
          {hasStation && <span className="live-dot" aria-hidden="true" />}
          <span className="station-name-strong">{hasStation ? state.stationName : 'Nothing playing'}</span>
        </div>
      </div>

      <div className="np-body">
        {!hasStation && <p className="np-empty">Pick a station from favorites or genres to start listening.</p>}

        {hasStation && !hasTrack && <p className="np-empty">Connecting…</p>}

        {hasTrack && (
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
              Liner notes
            </div>

            {state.enriching && !state.enrichment && <p className="trivia-placeholder">Asking the AI provider…</p>}

            {!state.enriching && !state.enrichment && (
              <p className="trivia-placeholder">No liner notes for this track.</p>
            )}

            {state.enrichment && (
              <>
                <p className={`trivia ${triviaExpanded ? '' : 'clamped'}`}>{state.enrichment.trivia}</p>
                <div className="trivia-actions">
                  {state.enrichment.trivia.length > 280 && (
                    <button className="text-btn" type="button" onClick={() => setTriviaExpanded((v) => !v)}>
                      {triviaExpanded ? 'Show less' : 'Show more'}
                    </button>
                  )}
                  {state.enrichment.wiki && (
                    <a
                      className="wiki-link"
                      href={state.enrichment.wiki}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Read on Wikipedia
                      <ExternalLinkIcon />
                    </a>
                  )}
                  <button className="text-btn" type="button" onClick={reenrich} disabled={state.enriching}>
                    <RefreshIcon />
                    Re-ask AI
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
          onClick={togglePause}
          disabled={!hasStation}
          aria-label={state.playing ? 'Pause' : 'Play'}
        >
          {state.playing ? <PauseIcon /> : <PlayIcon />}
        </button>

        <button
          className="icon-btn reconnect-btn"
          type="button"
          onClick={reconnect}
          disabled={!hasStation}
          aria-label="Reconnect"
          title="Reconnect"
        >
          <RefreshIcon />
        </button>

        <div className="vol-group">
          <button
            className={`mute-btn ${state.muted ? 'active' : ''}`}
            type="button"
            onClick={toggleMute}
            aria-label={state.muted ? 'Unmute' : 'Mute'}
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
            aria-label="Volume"
          />
          <span className="vol-pct">{state.volume}%</span>
        </div>

        <div className="provider-picker" ref={providerRef}>
          <button className="provider-chip" type="button" onClick={() => setProviderOpen((v) => !v)}>
            AI provider · <b>{_PROVIDER_LABEL[active] || 'none'}</b>
            <ChevronDownIcon />
          </button>
          {providerOpen && (
            <div className="provider-dropdown">
              {providers.map((p) => (
                <button
                  key={p.name}
                  className={`provider-option ${p.name === active ? 'active' : ''}`}
                  type="button"
                  disabled={!p.enabled}
                  onClick={() => {
                    void activate(p.name)
                    setProviderOpen(false)
                  }}
                >
                  <span>{_PROVIDER_LABEL[p.name]}</span>
                  {!p.enabled && <span>not configured</span>}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
