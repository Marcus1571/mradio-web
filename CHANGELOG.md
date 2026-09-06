# Changelog

## [0.3.8] - 2026-09-06

Fixed "Install as web app" (Edge/Chrome) using a generic icon instead
of mradio's own lightning-bolt mark — the browser tab favicon and an
installed-app icon are two entirely separate systems, and only the
former existed. Added the second: a proper `manifest.webmanifest`
(192×192, 512×512, and a maskable 512×512 variant, all PNG — the
manifest spec requires raster, not the existing SVG) plus an
`apple-touch-icon.png` for iOS home-screen bookmarks, which ignore the
manifest entirely and need their own tag. All generated from the
existing favicon mark, preserving its real proportions and colors, on
a square tile matching the app's own dark background
(`#111419`) with generous safe-zone padding for Android's adaptive
icon masking.

Verified via Chrome's own manifest parser (DevTools Protocol
`Page.getAppManifest`), not just by eyeballing the JSON — confirmed
zero parse errors and all three icons recognized at their declared
sizes.

## [0.3.7] - 2026-09-06

Moved the Analytics page one click closer: a **Dashboard** button now
sits in the top bar itself (between the theme toggle and the account
menu, admin-only), navigating straight to the same page the old
"Analytics" entry in the user dropdown menu used to. That dropdown
entry is now removed — the top-bar button replaces it.

## [0.3.6] - 2026-09-06

Fixed the saved volume being ignored on page reload — it always reset
to the 70% default instead of restoring the level you'd actually set,
even though the correct value was already saved server-side.

Root cause: `usePlayer(config?.volume)` only uses that argument to seed
React's `useState` on the very first render — but the saved config
loads asynchronously (a separate `GET /api/config` after mount), so by
the time it arrived, the 70% default had already been locked in and
nothing re-applied the real value afterward. Theme, mute, and language
were already being explicitly re-applied once config loaded; volume was
the one field that wasn't. Fixed with a new `applySavedVolume()`,
called alongside the existing theme/mute/language sync.

Verified against a real production build (not just the dev server,
which uses React StrictMode's double-effect-invocation in a way that
briefly looked like it also broke mute-persistence — confirmed that was
a dev-only artifact, not a real bug, by testing `vite preview` directly).

## [0.3.5] - 2026-09-06

Added Portuguese as a fourth UI/AI language, alongside English,
Spanish, and Italian — appears in the top-bar language dropdown (🇵🇹
Português). AI-generated liner notes follow it the same way they
already do for the other three.

Also brought README.md's KB.md cross-linking up to the same standard as
the original mradio terminal app's README: a top nav line, an early
"full detail lives in KB.md" pointer, deep links to specific KB.md
sections next to each relevant feature bullet, a full section-by-section
link list under "Getting started," and a closing link to the Knowledge
Base — previously README only had a single bare link to KB.md.

Simplified `Dashboard.tsx`'s language-fallback logic to validate against
the `LANGUAGES` list generically instead of naming each language code —
adding a 5th language in the future shouldn't require touching that line
again.

## [0.3.4] - 2026-09-06

The "Asking the AI provider…" status while waiting for liner notes now
names the actual provider — "Asking opencode…", "Asking NIM…", "Asking
ollama…" — instead of a generic placeholder.

- **Real bug found and fixed along the way**: the provider name shown
  in the UI (top-right pill, and now this status line) was the user's
  *explicitly saved* provider preference, not the one actually doing
  the work — a fresh account with no preference set showed "none" even
  while enrichment was quietly succeeding via opencode's automatic
  fallback. `GET /api/enrich/providers` now reports the fallback-
  resolved active provider (`Enricher.active_provider()`, which already
  existed and was used elsewhere, just not here) instead of the raw
  unset preference.
- Considered and deliberately did not build: staged "phase" progress
  (asking → response received → Wikipedia lookup → composing). The real
  pipeline spends the overwhelming majority of its time in the single
  LLM call (10–90+ seconds observed), with the Wikipedia lookup taking
  well under a second — a phase indicator would sit on "asking" almost
  the whole time and then flicker through the rest, which isn't a
  meaningful improvement over just naming the provider.

## [0.3.3] - 2026-09-06

Made trivia history per-user and persisted (was session-only, in-memory,
since 0.3.2), and fixed two real AI enrichment bugs found from production
logs and a user report ("sometimes AI won't give anything and
re-requesting fails, and if I change AI provider yields nothing — I need
to reload the page").

- **Trivia history now survives logout/reload.** New `trivia_history`
  SQLite table, one row per track per user (author, title, station,
  trivia, wiki link — same fields as before, now persisted instead of
  living in browser memory). The "Recently played" filmstrip fetches
  from `GET /api/enrich/trivia-history` instead of a local array;
  re-asking AI for a track still updates that entry in place rather
  than duplicating it, now enforced in SQL.
- **Real bug fixed**: a single AI failure — from *any* user, on *any*
  provider — set a global 2-minute cooldown that silently blocked every
  retry attempt for *everyone*, including a deliberate "Re-ask AI"
  click. That's what "re-requesting fails" was. Fixed: a manual re-ask
  now clears the cooldown first, since a human explicitly asking again
  is exactly the case it shouldn't block.
- **Real bug fixed**: switching AI providers updated which provider was
  active but never actually re-asked it about the currently-playing
  track — the panel just kept showing the previous (often failed/empty)
  result until a separate manual re-ask, which itself could still be
  blocked by the bug above. That's "change AI provider yields nothing."
  Fixed: switching providers now immediately triggers a fresh
  enrichment attempt for the current track.
- Verified live end-to-end: forced a real Ollama connection failure,
  confirmed the panel showed no liner notes, then confirmed switching
  to opencode alone (no manual re-ask) produced a fresh, successful
  enrichment ~30s later — the exact reported failure sequence, now
  fixed.

## [0.3.2] - 2026-09-05

Added a "Recently played" trivia history to the now-playing panel — the
last 10 AI liner-note blurbs from this session, re-readable while
something else plays.

- A horizontal filmstrip of small chips (track + station) appears below
  the transport controls once the first trivia arrives — nothing shown
  on an empty session. Click a chip to expand it in place, showing the
  full trivia text and Wikipedia link exactly like the live trivia
  block (same clamp/"show more" behavior); click again to collapse.
  Only one entry expands at a time.
- Session-only, in-memory, personal to each listener — no backend
  changes, no new persistence. Re-asking AI for the currently-playing
  track updates that track's own history entry in place rather than
  adding a duplicate.
- Confirmed the shared AI trivia cache already keys on language (added
  in 0.2.1) generically, not just for the languages that existed then —
  switching from English to Italian on the same track correctly misses
  the cache and re-asks in the new language, no code change needed.

## [0.3.1] - 2026-09-05

Added Italian as a third UI/AI language, alongside English and Spanish
— appears in the top-bar language dropdown (🇮🇹 Italiano). AI-generated
liner notes follow it the same way they already do for Spanish.

## [0.3.0] - 2026-09-05

New admin-only **Analytics** page (user menu → Analytics) — live sessions,
a world map of listeners, top stations/genres/listeners, and a full play
history. Loosely inspired by Tracearr, scoped down to this app's actual
size (a handful of accounts, one SQLite file) rather than adopting its
full multi-service stack.

- **Live now**: who's listening, to what, and from where, refreshed every
  5 seconds — served entirely from memory, no database round-trip.
- **Listener map**: a Leaflet + OpenStreetMap world map, one marker per
  city, sized by play count. Uses each listener's real IP (captured via
  the reverse proxy's `X-Forwarded-For` header, now correctly trusted —
  see below) resolved against a local, self-hosted GeoLite2-City
  database. Connections from a LAN/Tailscale address correctly show no
  location, same as any self-hosted geolocation tool — there's no
  meaningful "location" for traffic that never left the local network.
- **Stats**: top 5 stations/genres/listeners by play count and total
  listening time, plus a 7-day/30-day/all-time sessions-per-day trend —
  all hand-rolled SVG, no charting library added.
- **History**: every play session ever recorded (station, genre, user,
  start/end time, approximate location), paginated.
- New `play_history` SQLite table, one row per stream connection, written
  by the existing stream proxy's connect/disconnect lifecycle — no new
  hook points needed, it already had a clean `try/finally` around every
  connection.
- **Real bug found and fixed along the way**: the proxy's per-connection
  cleanup (which now also closes out the history row) could silently get
  cut short when a client disconnected abruptly, because `await` inside
  an async generator's `finally` block isn't reliably run to completion
  once the generator itself is being torn down via cancellation — caught
  via a live Playwright test that found `ended_at` sometimes left `NULL`.
  Fixed by shielding the cleanup in its own task
  (`asyncio.shield(asyncio.create_task(...))`), which also fixes a
  latent, lower-stakes version of the same issue for the stream's own
  httpx client cleanup that predates this feature.
- **Also fixed**: genre was being re-guessed from the station's name on
  every play (a ~35% misclassification rate against the curated station
  list — e.g. "WQXR" has no genre keyword in its name, so it was
  recorded as "other" instead of "classical"), even though the frontend
  already knows the correct genre for every favorite/curated station.
  The player now sends the real genre through; the name-based guess is
  now only a fallback for arbitrary custom stream URLs. The same
  hardcoded `'other'` gap existed in the page-reload auto-resume path
  (`config.last_genre` is now persisted and used there too).
- **Prerequisite infra fix**: `uvicorn` now runs with `--proxy-headers
  --forwarded-allow-ips=*`, so `request.client.host` reflects the real
  visitor's IP behind Nginx Proxy Manager instead of NPM's internal
  Docker IP — required for the map to show anything real at all.

## [0.2.4] - 2026-09-05

Two more fixes found testing 0.2.3 against the real production NIM key:

- The KB.md "New to NIM/Ollama?" notes were plain text — "KB.md" wasn't
  actually clickable. Now a real link to the file's section on GitHub
  (`.../blob/main/KB.md#nvidia-nim-openai-compatible` /
  `.../blob/main/KB.md#ollama`), verified to scroll straight to the right
  section.
- The NIM ("OpenAI-compatible") Test button was failing with "Could not
  reach ...:" and no reason after the colon. Root cause: it ran a real
  chat completion against the configured model, and NVIDIA's free-tier
  `minimaxai/minimax-m3` genuinely took longer than the 5s test timeout
  to respond (confirmed up to 20s+) — an `httpx.ReadTimeout`, which
  stringifies to an empty message, hence the blank reason. Switched the
  test to `GET /v1/models` (checks connectivity + the key is valid,
  matching Ollama's `/api/tags` approach) instead of paying for a real,
  slow inference call on every click. Also added a fallback so any
  exception with an empty message shows its type name instead of nothing.

## [0.2.3] - 2026-09-05

Fixed the Test buttons shipped in 0.2.2 rendering as unstyled, button-less
text with no visible pass/fail indicator — they were reusing `.row-actions`
(the Users table's plain-text action-link style), which is wrong for a
primary action in a settings form. Added a dedicated `.test-btn`/
`.test-actions` style (bordered button, same visual language as the rest
of the settings form) and verified live in a browser: Ollama and NIM
correctly report "No server URL configured." / "No API key configured."
when empty, and a real, working opencode install reports "Working" with
a green pill.

## [0.2.2] - 2026-09-05

Three small fixes from a review pass:

- Fixed the dark/light theme toggle icon showing the *destination* theme
  instead of the current one — it now reflects what the app currently
  looks like, not what clicking it would change to.
- Added a **Test** button to each AI provider group on the AI providers
  page (Ollama, OpenAI-compatible/NIM, opencode). Clicking it makes a
  real, lightweight, read-only call against that provider with whatever's
  currently in the form — never against the saved value alone, and never
  persists anything — and shows a pass/fail pill with the actual reason
  on failure (unreachable server, missing model, bad key, etc.). New
  backend endpoint: `POST /api/settings/ai/test?provider=<name>`.
- KB.md's Ollama section was missing the install/setup walkthrough NIM's
  already had — added a matching "Setting up Ollama" section (install,
  pull a model, confirm reachability), and the AI providers page now
  links to it the same way it already links to NIM's setup section.

## [0.2.1] - 2026-09-05

AI liner notes now follow the UI language (0.2.0 only switched the UI
text, not the AI output). Switching to Spanish re-asks the currently
playing track's liner notes immediately — no need to wait for the next
track.

- `enricher.py`: the prompt now carries a language instruction (Spanish
  only — English stays fully implicit, zero cost for the common case).
  The Wikipedia link lookup is explicitly protected: `"wiki"` always
  stays the English article title regardless of trivia language, since
  it's a lookup key into English Wikipedia.
- The shared trivia cache now includes language in its key
  (`provider::language::raw_title`), so two accounts listening to the
  same track in different languages don't collide on one cached blurb.
- `PATCH /api/config`'s `language` field now also pushes a live update
  into that user's running Enricher, so a language switch takes effect
  on the very next AI request — no restart needed.
- Verified via a full local test: the WebSocket's existing `reenrich`
  message fires automatically on language switch, the config file
  persists `language` correctly, and cache entries for the same track in
  different languages are confirmed independent.

## [0.2.0] - 2026-09-05

Added a language switcher — English and Spanish, with a flag + language
name dropdown in the top bar (left of the version number). Switching
applies instantly across the whole UI, including admin pages (Users, AI
providers) and dynamic dialogs (delete/reset-password confirmations),
and persists per account.

- New `frontend/src/i18n/` module: hand-rolled dictionary + `t()` lookup,
  no library — English is the canonical key shape, Spanish is typed
  against it so a missing translation key is a build-time TypeScript
  error, not a silent runtime gap.
- ~130 hardcoded strings extracted across every page/component.
- The login screen and the forced first-time password-change screen stay
  English-only — they render before any account is authenticated, so
  there's no saved preference to read yet.
- Backend: `PATCH /api/config` now accepts and persists a `language`
  field, same pattern as the existing `theme` preference.
- AI-generated liner notes are not yet translated — that's a separate,
  upcoming change to the enrichment prompt/cache; today, switching
  language only affects UI text.

## [0.1.10] - 2026-09-05

Trimmed the top bar's padding and the dashboard's outer padding/gap so
the header takes up less vertical space and the panels sit closer to
the edges of the window.

## [0.1.9] - 2026-09-05

Long liner notes (the normal case — the AI is prompted for ~750-850
characters) were wrapping into a tall, narrow column and pushing content
below the fold. Widened the now-playing panel relative to the stations
panel (1.4:1 → 1.7:1) and the dashboard's overall max width, and loosened
the trivia text's own line-width cap (62ch → 84ch) so it actually
benefits from the wider column instead of leaving the extra space
unused. Verified with a full-length liner-notes sample: the same text
that spanned ~18 lines before now wraps into ~7, fitting on screen
without scrolling. Also trimmed a bit more padding around the panel
header and body.

## [0.1.8] - 2026-09-05

The stream-metrics row (bitrate/sample rate/format/cache/elapsed) had
noticeably more empty space above it than below — its own top padding
was stacking on top of the panel's outer padding. Removed the
double-counted padding so the gap above and below the row is even.

## [0.1.7] - 2026-09-05

Tightened up vertical space in the now-playing panel:

- Liner notes now default to expanded ("Show more" state) instead of
  clamped to 4 lines — no need to click through on every track.
- Trimmed padding/margins around the stream-metrics row, performer line,
  liner-notes actions, and the transport bar so more fits on screen
  without scrolling.

## [0.1.6] - 2026-09-05

0.1.5 fixed the now-playing WebSocket dying and never recovering, but
missed the actual audio stream: when the underlying connection died for
any reason (network blip, proxy hiccup), the `<audio>` element just went
silent with nothing watching for it — the WS reconnecting on its own
didn't help, since it's a completely separate connection. Confirmed via
production logs and a live test that killed and restarted the backend
mid-stream.

- The audio element now listens for `error`/`stalled` and automatically
  reconnects (same mechanism the manual Reconnect button already used)
  as long as the user hasn't pressed Stop — verified live: killing the
  backend mid-stream produced automatic reconnect attempts roughly every
  2 seconds until the connection came back, entirely on its own.
- Fixed a related regression from 0.1.5: the native `pause` event (which
  fires both for an intentional Stop *and* for the browser giving up on
  a dead stream) was being used to decide playback status — meaning an
  unintentional drop could get misclassified the same as a real Stop.
  Only `stop()` itself sets `status: 'stopped'` now.
- Added the app version to the top bar (top right), read from
  `package.json` at build time so it never drifts from the actual
  release.

## [0.1.5] - 2026-09-05

Fixed the now-playing WebSocket dying silently and never recovering
(audio kept playing, but metadata/liner notes would just stop updating
until a manual reconnect or page reload) — and reworked pause into a
real Stop, since a live broadcast has no meaningful "paused" state.

- The socket now sends a `{"type":"ping"}` keepalive every 30 seconds,
  so reverse-proxy idle timeouts (the likely cause, confirmed via
  `mradio.ws INFO disconnected` gaps in production logs with no error)
  stop killing it silently.
- If it does still drop for any reason, the frontend now reconnects
  itself automatically with exponential backoff, instead of requiring a
  manual reconnect or page reload.
- Replaced the Pause button with a real Stop: pressing it now actually
  releases the connection to the station (same mechanism the existing
  Reconnect button already used to abort and re-request), instead of
  just muting playback while the backend kept fetching from the live
  station in the background with nobody listening. Resuming always
  reconnects to what's airing now, never stale buffered audio.

## [0.1.4] - 2026-09-05

Fixed the "Read on Wikipedia" link not showing up for non-classical
tracks (pop, soul, disco, etc.) — two separate bugs stacked on top of
each other:

- The AI prompt only ever asked for a Wikipedia link when the track was
  part of a classical "work" (a symphony, opus, etc.) — for a plain song
  it always returned an empty `wiki` field by design, regardless of
  provider. The prompt now also asks for the song's own Wikipedia
  article when there's no classical work to link to instead.
- Separately, even when a Wikipedia article *was* found, the backend was
  sending the frontend a `{title, url}` object where a plain URL string
  was expected — the link element rendered, but its `href` resolved to
  `"[object Object]"` instead of a working URL. Fixed to send the URL
  string directly.

Verified against live Wikipedia for all three tracks reported as broken
(Ariana Grande, Aretha Franklin, Elton John & Kiki Dee) — all resolve
correctly now.

## [0.1.3] - 2026-09-05

Fixed a real playback bug found right after deploying 0.1.2: stations could
get stuck showing "Connecting…" forever, even though audio played fine —
only clicking Reconnect fixed it.

- Root cause: the audio stream connection and the now-playing WebSocket are
  two independent requests with no ordering guarantee. If the stream's
  `station`/`title` events arrived before the WebSocket had finished
  connecting, they were silently dropped — pre-existing since the
  WebSocket was first built, but far more likely to show up over a real
  network (reverse proxy) than on localhost, which is why it went
  unnoticed until now.
- Fix: the backend now remembers the latest `station`/`title` event per
  player session and replays it immediately when the WebSocket connects,
  instead of dropping events sent to nobody.
- Added structured logging (`mradio.stream`, `mradio.nowplaying`,
  `mradio.ws` loggers) for connect/disconnect/publish/subscribe events, so
  this kind of issue is visible in `docker logs` instead of requiring code
  archaeology to diagnose.

## [0.1.2] - 2026-09-05

Four small UI/UX bugs found reviewing the live 0.1.1 deployment against the
original design mockup:

- Wikipedia link now uses `rel="noopener noreferrer"`.
- NIM provider fields prefill with NVIDIA's hosted endpoint and
  `minimaxai/minimax-m3` on new installs, instead of OpenAI defaults;
  KB.md gained the missing "how to get an API key" walkthrough, linked
  from the AI providers page.
- Genre tag no longer crowds the station name in the favorites grid.
- Now-playing panel gained a stream metadata row (bitrate, sample rate,
  format, buffer health, elapsed time) that was entirely missing before.

## [0.1.1] - 2026-09-05

Confirmed working end-to-end: first real `docker compose build && docker
compose up` (previously only tested piece-by-piece), deployed to LT behind
Nginx Proxy Manager, logged in, played a stream, got AI liner notes.

- No pre-release flag — this build is verified, not just built.
- README: added a measured "Footprint" section (client JS heap, CPU,
  bundle size, server-side container resource use) from profiling the
  live deployment.

## [0.1.0] - 2026-09-04

First fully working build of mradio-web — a self-hosted, multi-user
rewrite of mradio as a browser-based internet radio player.

- Multi-user accounts (SQLite), admin-created, no public sign-up
- Per-user favorites (12 slots) and settings, matching mradio's own file format
- Browser-native playback via a stream proxy (fixes HTTPS-page/HTTP-station blocking)
- Live now-playing over WebSocket, parsed from ICY metadata
- AI liner notes: opencode (bundled), Ollama, or any OpenAI-compatible
  endpoint (e.g. NVIDIA NIM) — shared cache, admin-managed credentials,
  per-user provider choice
- Single-container Docker deployment (see KB.md)

Marked pre-release: not yet verified with a real docker build/compose up
outside this build's own testing.
