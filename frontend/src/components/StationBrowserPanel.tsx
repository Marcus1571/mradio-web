import { useState } from 'react'
import type { FormEvent, MouseEvent } from 'react'
import { useFavorites } from '../hooks/useFavorites'
import { useGenres } from '../hooks/useGenres'
import type { Station } from '../api/types'
import { MoveIcon, StarIcon, TrashIcon } from './Icons'

export function StationBrowserPanel({
  currentUrl,
  onPlay,
}: {
  currentUrl: string | null
  onPlay: (station: Station) => void
}) {
  const [tab, setTab] = useState<'favorites' | 'genres'>('favorites')
  const { favorites, add, remove, move } = useFavorites()
  const { genres, active, stations, selectGenre } = useGenres()

  const [editing, setEditing] = useState(false)
  const [marked, setMarked] = useState<number | null>(null)

  const [addUrl, setAddUrl] = useState('')
  const [addBusy, setAddBusy] = useState(false)
  const [status, setStatus] = useState<{ text: string; error?: boolean } | null>(null)

  function flash(text: string, error = false) {
    setStatus({ text, error })
    window.setTimeout(() => setStatus(null), 3000)
  }

  function onSlotClick(index: number, station: Station | null) {
    if (!editing) {
      if (station) onPlay(station)
      return
    }
    if (marked === null) {
      if (station) setMarked(index)
      return
    }
    if (marked === index) {
      setMarked(null)
      return
    }
    void move(marked, index)
    setMarked(null)
  }

  async function onDelete(e: MouseEvent, url: string) {
    e.stopPropagation()
    if (!window.confirm('Remove this favorite?')) return
    await remove(url)
    setMarked(null)
  }

  async function onAddStream(e: FormEvent) {
    e.preventDefault()
    const url = addUrl.trim()
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      flash('Must be a valid http(s) stream URL.', true)
      return
    }
    setAddBusy(true)
    try {
      const host = new URL(url).host
      const added = await add(url, host)
      flash(added ? 'Added to favorites.' : 'Already a favorite, or no free slots.', !added)
      if (added) {
        onPlay({ name: host, url, genre: 'other' })
        setAddUrl('')
      }
    } catch {
      flash('Could not add that URL.', true)
    } finally {
      setAddBusy(false)
    }
  }

  async function onStar(station: Station) {
    const already = favorites.some((f) => f?.url === station.url)
    if (already) {
      flash('Already a favorite.')
      return
    }
    const added = await add(station.url, station.name)
    flash(added ? `Added ${station.name} to favorites.` : 'No free slots — remove one first.', !added)
  }

  return (
    <aside className="panel" aria-label="Station browser">
      <div className="panel-head">
        <div className="panel-title">
          Your stations
          <small>12 favorite slots</small>
        </div>
        <div className="browser-tabs">
          <button className={`tab ${tab === 'favorites' ? 'active' : ''}`} type="button" onClick={() => setTab('favorites')}>
            Favorites
          </button>
          <button className={`tab ${tab === 'genres' ? 'active' : ''}`} type="button" onClick={() => setTab('genres')}>
            Genres
          </button>
        </div>
      </div>

      {tab === 'favorites' && (
        <>
          <div className="panel-actions">
            <button
              className="text-btn"
              type="button"
              onClick={() => {
                setEditing((v) => !v)
                setMarked(null)
              }}
            >
              {editing ? 'Done editing' : 'Edit favorites'}
            </button>
          </div>

          <div className="fav-grid">
            {favorites.map((fav, i) => {
              const playing = fav !== null && fav.url === currentUrl
              const isMarked = marked === i
              if (fav === null) {
                return (
                  <button key={i} className="fav-slot empty" type="button" onClick={() => onSlotClick(i, null)}>
                    {i === 9 ? '0' : i + 1} — empty{editing && marked !== null ? ' · move here' : ''}
                  </button>
                )
              }
              return (
                <button
                  key={i}
                  className={`fav-slot ${playing ? 'playing' : ''} ${isMarked ? 'marked' : ''}`}
                  type="button"
                  onClick={() => onSlotClick(i, fav)}
                >
                  <span className="fav-num">{i === 9 ? '0' : i + 1}</span>
                  <span className="fav-info">
                    <span className="fav-name">{fav.name}</span>
                    <span className="fav-genre">{fav.genre}</span>
                  </span>
                  {editing && !isMarked && (
                    <span className="fav-delete" onClick={(e) => void onDelete(e, fav.url)} role="button" tabIndex={-1}>
                      <TrashIcon />
                    </span>
                  )}
                  {editing && isMarked && <MoveIcon className="fav-delete" />}
                </button>
              )
            })}
          </div>

          {editing && (
            <p className="edit-hint">
              {marked === null
                ? 'Tap a station to pick it up, then tap a slot to move it there.'
                : 'Tap a slot to drop it there — tap the same slot again to cancel.'}
            </p>
          )}

          <form className="add-stream-row" onSubmit={onAddStream}>
            <input
              type="url"
              placeholder="Add a stream URL…"
              value={addUrl}
              onChange={(e) => setAddUrl(e.target.value)}
            />
            <button type="submit" disabled={addBusy || !addUrl.trim()}>
              {addBusy ? 'Adding…' : 'Add'}
            </button>
          </form>
        </>
      )}

      {tab === 'genres' && (
        <>
          <div className="genre-rail">
            {genres.map((g) => (
              <button
                key={g.genre}
                className={`genre-chip ${g.genre === active ? 'active' : ''}`}
                type="button"
                onClick={() => selectGenre(g.genre)}
              >
                {g.label} <span className="count">{g.count}</span>
              </button>
            ))}
          </div>

          <div className="station-list">
            {stations.map((s) => {
              const starred = favorites.some((f) => f?.url === s.url)
              let host = ''
              try {
                host = new URL(s.url).host
              } catch {
                host = s.url
              }
              return (
                <button key={s.url} className="station-row" type="button" onClick={() => onPlay(s)}>
                  <span
                    className={`star-btn ${starred ? 'starred' : ''}`}
                    onClick={(e) => {
                      e.stopPropagation()
                      void onStar(s)
                    }}
                    role="button"
                    tabIndex={-1}
                  >
                    <StarIcon filled={starred} />
                  </span>
                  <span className="station-row-name">{s.name}</span>
                  <span className="station-row-host">{host}</span>
                </button>
              )
            })}
          </div>
          <div className="panel-foot">
            {genres.find((g) => g.genre === active)?.label} · {stations.length} stations · favorites shown first
          </div>
        </>
      )}

      {status && <p className={`status-msg ${status.error ? 'error' : ''}`}>{status.text}</p>}
    </aside>
  )
}
