# Changelog

## [1.28.2] - 2026-09-20

Fixed the tap-to-reveal labels (v1.28.1) overflowing past the Users
table's right edge instead of wrapping — `.row-actions` was a
non-wrapping flex row, so a row with a long name/email and all six
labels revealed (e.g. "Resend invite", "Reset password") got clipped
mid-word at the panel boundary. Now wraps onto a second line when the
revealed labels don't fit on one.

## [1.28.1] - 2026-09-20

Fixed two problems with v1.28.0's icon-button toolbar: the hover-only
`title` tooltip had no touch equivalent, so a phone user tapping an icon
had no way to know what it did before acting on it. Tapping anywhere on
a Users row (outside the icon buttons themselves) now reveals a text
label next to each icon in that row; tapping again, or tapping a
different row, hides it. Also fixed a pre-existing responsive bug found
while testing this on a narrow viewport: the Users table's Created and
action columns were silently clipped off-screen below ~700px width
(`.admin-panel`'s `overflow: hidden` was cutting the table rather than
scrolling it) — the table now scrolls horizontally on narrow screens
instead of hiding content with no visual indication anything was cut
off.

## [1.28.0] - 2026-09-20

Redesigned the admin Users page: the six per-row actions (make/remove
admin, enable/disable, edit profile, resend invite, reset password,
delete) are now monoline SVG icon buttons with hover tooltips instead of
six stacked text labels — reusing the app's existing `Icons.tsx` system
(new `ShieldIcon`, `PowerIcon`, `MailIcon`, `KeyIcon`, alongside the
already-existing `PencilIcon`/`TrashIcon`), not emoji, which render
inconsistently across platforms. The three columns (Username, Status,
Created) are now sortable by clicking the header, with a chevron
indicating the active sort and direction — default sort is newest-first
by creation date, same as before. The email address is now shown under
the username/full name in the first column when the account has one.

## [1.27.0] - 2026-09-20

Login accepts either the username or the email address in the same
field, with the password unchanged — `/api/auth/login` tries username
first, falls back to email if no match. `LoginScreen.tsx`'s field label
now reads "Username or email" to match. Also reverts the Ollama default
model from `gemma3:4b` (no longer pulled on the LT instance) to
`gpt-oss:20b` after `phi4-mini:latest` failed its accuracy battery
(empty trivia on 2/5 tracks, a fabricated wrong death date, an invented
band lineup) — see `AI.md`'s Ollama section.

## [1.26.1] - 2026-09-18

No code change — a deployment/infra fix on LT. `data/settings.json` (the
file this app's own settings UI writes real AI-provider API keys to) was
found at OS permission `644` (world-readable) during an unrelated
secrets-exposure audit of LT. Tightened to `600` directly on the
production instance; the app's own process runs as `root` inside its
container and already owned the file, so this doesn't affect the app's
ability to read or rewrite its settings. See `findings.md`'s 2026-09-18
entry for the check performed before applying this.

## [1.26.0] - 2026-09-17

Extends `GET /api/public/stats` (added in 1.25.0) with two more counts:
`ai_requests_today` and `music_link_requests_this_hour` — for the
homepage.dev widget's expansion from 2 to 4 tile fields.

- `history.py`: new `ai_requests_today()` — `COUNT(*)` against the
  existing `ai_requests` table (already populated by
  `enricher.py`'s `_record_ai_request` for AI.md's numbers) for the
  current UTC calendar day.
- `db.py`: new `music_link_requests` table (`service`, `started_at`) —
  nothing previously logged individual `/api/music-link` calls;
  `music_link_cache.py`'s cache stores resolved title→URL pairs, not a
  request log, so it can't answer "how many requests."
- `routers/music_link.py`: logs a best-effort row to the new table on
  every `GET /api/music-link` call (hits and misses both — tracks
  listener demand, not backend lookup cost), mirroring
  `_record_ai_request`'s never-break-the-real-feature pattern.
- `history.py`: new `music_link_requests_this_hour()` — `COUNT(*)`
  against the new table for the current UTC clock hour (a snapshot of
  "this hour so far," not a trailing 60-minute window).

## [1.25.0] - 2026-09-17

Adds a new public, unauthenticated stats endpoint — `GET
/api/public/stats` — returning `{"live_listeners": <int>,
"unique_listeners_today": <int>}`. This is the first and only
deliberately unauthenticated data endpoint in the app; every other
route (including the existing `/api/analytics/*` admin routes it sits
alongside conceptually) requires a session cookie. Scoped to two
harmless aggregate counts only — no usernames, IPs, or location data —
specifically so an external dashboard (e.g. a self-hosted
[gethomepage.dev](https://gethomepage.dev) instance, via its
`customapi` widget) can show live listener counts without a login flow
or a new API-key mechanism.

- `routers/public.py` (new): the endpoint, `Cache-Control: no-store`
  (matching `stream.py`/`music_link.py`'s existing precedent for
  answers that shouldn't be proxy-cached).
- `history.py`: new `unique_listeners_today()` — `COUNT(DISTINCT
  user_id)` against `play_history` for the current UTC calendar day.
  Nothing computed this before; `by_day` in the existing `/analytics/stats`
  admin route counts play-session rows, not distinct listeners.
- `live_listeners` reuses the existing in-memory `nowplaying.live_snapshot()`
  — no new state, no DB round-trip.
- `KB.md` §11 documents the new endpoint and its deliberately-public
  scope explicitly, so it doesn't read as an oversight next to every
  other admin-gated route in the same section.

## [1.24.0] - 2026-09-15

Adds three new named themes — **Sapphire** (deep saturated navy),
**Jade** (deep saturated emerald), and **Harbor** (flat sage/khaki
"vintage LCD") — alongside the existing Day/Night pair, and replaces
the old click-to-cycle theme toggle button with a proper dropdown
listing all five.

This shipped after an extensive, multi-round design process (see
`design-mockups/` in the repo root for the full iteration history):
an initial "Dawn/Dusk" day-cycle concept was designed, tested, and
explicitly rejected by the operator; a second "Omarchy-inspired" vibe-
theme direction went through several rounds of real color research
(pixel-sampling actual reference screenshots, then researching named
real-world color references — Rosé Pine Dawn, Petrol Blue, Deep Moss
Green, Deep Navy, Dark Emerald — to correct two different failure
modes: colors that were too pale/washed-out, then colors that were too
vivid/artificial, before landing on genuinely dark-but-saturated
"jewel tone" palettes that avoid both the "everything is basically
black" problem of typical dark themes and the desaturated/muddy look
of themes like Dracula or Nord).

- `index.css`: three new `[data-theme="X"]` token blocks (`sapphire`,
  `jade`, `harbor`), same 15-token shape as the existing Day/Night
  blocks. OS `prefers-color-scheme` auto-detection remains Day/Night
  only — the three new themes are explicit-pick only, since a binary
  media query can't represent a 5-way choice.
- `dashboard.css`: the station-logo blend-mode fix (for light-on-dark
  logo artwork) now also applies under Harbor, which is light-like the
  same way Day is.
- `Icons.tsx`: three new monoline icons matching the existing Sun/Moon
  visual language — a droplet (Sapphire), a leaf (Jade), an anchor
  (Harbor).
- `TopBar.tsx`: the old single icon-button toggle (binary flip between
  Day/Night) is replaced with a `dropdown-picker` — the same UI pattern
  already used for the language switcher and the music-service picker
  — listing all five themes with icon + label, current selection
  highlighted.
- `api/types.ts`: new exported `Theme` type (mirroring the existing
  `MusicService` pattern) used everywhere `theme` was previously typed
  inline as `'dark' | 'light'`.
- i18n: new `topbar.theme` / `topbar.themeDay` / `topbar.themeNight` /
  `topbar.themeSapphire` / `topbar.themeJade` / `topbar.themeHarbor`
  keys added to all 16 language files; the now-unused
  `switchToLight`/`switchToDark` keys (no longer referenced anywhere)
  were removed rather than left as dead entries.
- Verified: `npm run build`/`lint` clean; per `AGENTS.md`'s
  verification-discipline rule, actually rendered the dropdown and all
  five themes' real token values via static HTML fixtures + Playwright
  screenshots (not just a passing build) before shipping.

## [1.23.0] - 2026-09-15

**Music-service choice is now session-only, never persisted.** Every
app launch (or reload) starts at "no service"/"Select one" — the
operator's explicit design decision, made after confirming v1.22.4's
fix correctly persisted a cleared preference: persisting the choice at
all meant a listener who picked a service once (out of curiosity, or
by accident) would keep spending music-service search-API quota
(particularly Apple's tighter iTunes Search rate limit) on every future
session, whether they actually used the feature or not. Session-only
enforces "opt in for this session" at the source, rather than relying
on remembering to click "Select one" again after every reload.

- `routers/config.py`: `music_service` removed entirely from
  `ConfigUpdate` and the persisted config schema — it's no longer part
  of `/api/config` at all.
- `routers/music_link.py`: `GET /api/music-link` now takes `service` as
  an explicit query parameter instead of resolving it from the user's
  stored config (there isn't one to resolve anymore). This does
  reintroduce client-supplied service selection, which the original
  v1.21.0 design deliberately avoided for correctness reasons — an
  unavoidable tradeoff of going session-only, since there's no
  server-side ground truth left to fall back on. The response is still
  cached per `(service, raw_title)` and tagged/verified against the
  current `service` at render time client-side (`useMusicLink.ts`), so
  a slow in-flight request from before a quick double-switch can't
  surface against the wrong icon.
- `useMusicService.ts` rewritten as a plain `useState`, no `/api/config`
  fetch or PATCH at all.
- Existing accounts with an old saved `music_service` value in their
  `config.json` (from before this change) are unaffected in practice —
  the field is simply no longer read by anything; left in place rather
  than actively cleaned up, consistent with this project's "no DB
  migration tooling, additive-only schema" convention.

## [1.22.4] - 2026-09-15

Fixes a real bug reported right after v1.22.3 shipped: clicking "Select
one" in the music-service dropdown didn't stick — the preference
reverted to whatever service was previously chosen.

**Root cause**: `userdata.py`'s `_persist_cfg_sync()` silently skipped
writing any field whose value was `None` (`if v is not None: d[k] = v`).
This predates the music-service feature entirely and was harmless until
now, because no config field had ever needed an explicit "clear this
back to unset" write — every prior caller only ever set fields to real
values. v1.22.3's fix to `routers/config.py` correctly let
`music_service: null` reach `persist_cfg()`, but `persist_cfg()` itself
then threw the `None` away before it ever reached disk, so the config
file's old `music_service` value was untouched and `load_cfg()` kept
returning it.

- `userdata.py`: `_persist_cfg_sync()` now writes every field it's
  given, `None` included — confirmed via a direct persist/load
  round-trip that clearing `music_service` to `None` now actually
  survives a reload.
- Reconfirms the "Select one" default (no music service picked) is the
  intended standing behavior for new/unset accounts, not a stepping
  stone toward a fixed default service — the operator explicitly ruled
  out defaulting to any one service in favor of quota-conscious opt-in.

## [1.22.3] - 2026-09-15

Adds a **"Select one"** option to the top of the music-service dropdown,
letting a listener explicitly opt back out to no service once they've
picked one — previously the dropdown was a one-way ratchet into
Spotify/Apple Music/Deezer with no way back to the unset state short of
never touching it in the first place. Requested by the operator
specifically to avoid spending Apple's tighter iTunes Search API quota
(and Spotify's/Deezer's) on listeners who don't care about the feature
and accidentally (or curiously) picked a service.

- `routers/config.py`: `PATCH /api/config` now accepts an explicit
  `music_service: null` to clear the saved preference — previously any
  non-`None` check rejected `null` with a 400, since the valid-service
  set didn't special-case it.
- `useMusicService.ts`: `setMusicService()` widened to accept `null`.
- Dropdown order is now **Select one, Spotify, Apple Music, Deezer**.
- New `nowPlaying.selectOne` i18n key added to all 16 language files.

## [1.22.2] - 2026-09-15

Fixes the actual root cause behind the bug v1.22.1 attempted to fix:
switching services (e.g. Spotify → Apple Music, within the same
playing track) could still open the *previous* service's link, even
though the icon had already turned "resolved"/colored for the new
service. v1.22.1's fix (tagging the held url with its service,
discarding a mismatched tag at render time) addressed a real but
secondary hazard and did not fix this reproduction, as reported by the
operator immediately after v1.22.1 shipped.

**Real root cause**, found by tracing the actual request race rather
than the rendering layer: `useMusicService.ts`'s `setMusicService()`
updated its local `config` state **optimistically**, before awaiting
the `PATCH /api/config` call that persists the switch server-side.
Since `NowPlayingPanel.tsx`'s `effectiveService` (drives the icon) and
`useMusicLink`'s effect (fires `GET /api/music-link` on `service`
change) both derive from that same optimistic state, the GET could —
and did — fire and return **before** the PATCH had actually landed.
`routers/music_link.py` resolves the active service from the persisted
config on disk, not from anything the client sends, so a GET that
outraces its own PATCH reads the **old** service, returns the old
service's URL, and the frontend — already showing the new service's
icon — tags that response (client-side, from its own already-flipped
`service` value) as belonging to the new service. This is a strictly
worse bug than v1.21.2's browser-HTTP-caching issue: it's a genuine
server-side stale read, not a stale cached response, and no
`Cache-Control` header can fix a request that legitimately asked the
question too early.

- `useMusicService.ts`: `setMusicService()` no longer updates `config`
  optimistically. `service` (and everything derived from it — the icon,
  the music-link lookup) now only changes once the `PATCH` has actually
  resolved, so the two can never observe different server-side states.
  Trades a small amount of UI snappiness (the icon/label update waits
  for one round-trip) for correctness, which matters here because the
  wrong answer is a link to the wrong service's page, not just a
  flicker.
- v1.22.1's render-time service-tag guard in `useMusicLink.ts` is kept
  as defense-in-depth for the original (different, real) one-frame
  effect-timing gap it targeted — not reverted, since it protects
  against a separate hazard than this fix addresses.

## [1.22.1] - 2026-09-15

Fixes a real bug the operator reported in v1.22.0: switching to Apple
Music sometimes still opened Spotify — until a full page reload, after
which switching worked correctly. Also reorders the music-service
dropdown to Spotify → Apple Music → Deezer.

Root cause, confirmed via the live `music_link_cache.json` on
production (the server-side cache already held the correct
`apple::...` entry with the right `music.apple.com` URL — ruling out
the backend and the v1.21.2-style HTTP-caching bug entirely): this was
a frontend React timing bug in `useMusicLink.ts`. The hook cleared its
held `url` inside a `useEffect`, which only runs **after** the render
that already picked up the newly switched `service` commits. That left
a one-frame window, on every service switch, where the icon for the
new service (e.g. Apple Music) rendered wrapped in an `<a>` still
pointing at the *previous* service's URL (e.g. Spotify) — clickable and
visually indistinguishable from a resolved link. A page reload masked
it by forcing a full clean resync, which is why it looked
service-specific and reload-fixable rather than what it actually was: a
race present since the original music-link feature shipped (v1.21.0),
just never landed-on before because there were only two services to
switch between.

- `useMusicLink.ts` now tags the held url with the service it was
  resolved for, and compares that tag against the current `service` at
  render time — a stale url from the previous service is discarded the
  instant `service` changes, synchronously, rather than waiting for the
  effect to catch up.
- `NowPlayingPanel.tsx`: dropdown order is now Spotify, Apple Music,
  Deezer (was Spotify, Deezer, Apple Music).

## [1.22.0] - 2026-09-15

Adds **Apple Music** as a third music-service link option, alongside
Spotify and Deezer — same read-only, search-only pattern (no OAuth, no
playlist write, no per-user connection state). Uses Apple's free,
keyless iTunes Search API (`itunes.apple.com/search`), not MusicKit, so
no $99/year Apple Developer Program membership is required. See
`findings.md`'s 2026-09-14 iTunes Search API entry for the investigation
this implements.

- New `backend/app/apple_music.py`: searches the iTunes catalog and makes
  the same executive-decision title/artist match as `spotify.py`'s and
  `deezer.py`'s `find_best_track()`, adapted for this API's field names
  (`trackName`/`artistName`/`trackViewUrl`) and its one real gap — no
  ISRC field, so dedup falls back to `trackId`.
- `routers/music_link.py` and `routers/config.py` now accept `"apple"` as
  a third valid `music_service` value, resolved the same server-side way
  as the existing two.
- Frontend: `MusicService` widened to include `'apple'`; a new
  `AppleMusicIcon` (real brand mark, gradient rounded square) added
  alongside `SpotifyIcon`/`DeezerIcon`; the music-service dropdown and
  now-playing link both support the third option.
- **Fixed a real, pre-existing bug found while verifying this change**:
  `.dropdown-option-icon` had no `svg` sizing rule, so the Spotify/Deezer
  marks in the music-service dropdown rendered at the browser's oversized
  default intrinsic size and were clipped by the menu — invisible in the
  dropdown even though the same icons render correctly elsewhere (e.g.
  the now-playing link, which has its own explicit sizing). This affected
  the existing two services already in production, not just the new
  third option; fixed with one shared `.dropdown-option-icon svg` rule
  rather than per-option overrides.
- Verified live: `apple_music.find_best_track()` returns a real
  `music.apple.com` URL for a known track against the live iTunes API.
  Verified visually via a static fixture screenshot (playwright), per
  `AGENTS.md`'s verification-discipline rule — confirmed all three
  service icons now render at consistent size in the dropdown.

## [1.21.3] - 2026-09-14

The music-service dropdown now defaults to **None**, not Spotify.
Previously a brand-new account (or any account that had never touched
the dropdown) silently behaved as if Spotify were chosen — the icon
would try to resolve against Spotify without the listener ever picking
it. Now the icon area shows nothing at all until a service is
explicitly selected; the dropdown's chip label reads "None" in that
state. Once picked, the choice persists server-side exactly as before
(the existing `music_service` config field, unchanged) and follows the
account across devices.

- `MusicService | null` throughout the frontend (`useMusicService`,
  `useMusicLink`, `NowPlayingPanel.tsx`) — `null` means "no service
  chosen," not an error state.
- `routers/music_link.py` no longer silently defaults an unset service
  to `"spotify"` — with no service configured, it returns `{"url":
  null}` immediately, matching the frontend's own choice to skip the
  lookup request entirely rather than guessing a service.
- Existing accounts that already have a saved `spotify`/`deezer`
  preference are unaffected — this only changes the *default* for
  accounts that have never set one.

## [1.21.2] - 2026-09-14

Fixes a real bug the operator reported: switching to Deezer, then
clicking the (correctly Deezer-colored) music-service icon, opened a
Spotify URL instead.

Root cause: `GET /api/music-link?raw_title=...`'s query string is
deliberately just the raw title — the active service is resolved
server-side, not sent by the client — but that means the exact same URL
returns a different answer depending on server-side state the browser
can't see. With no `Cache-Control` header, the browser's default
heuristic HTTP caching (a GET response with no cache directives may
still be cached and reused for an identical URL) served an old Spotify
response after the user had already switched to Deezer, without the
server ever seeing the second request. Verified live: server-side, the
`(service, raw_title)`-keyed cache and service resolution were both
already correct — a fresh request for the exact same track, after
switching, does return the right Deezer URL. The bug was entirely a
missing cache-control header letting the browser skip that request.

- `routers/music_link.py`: sets `Cache-Control: no-store` on every
  response, matching the same pattern already used by `stream.py`.

## [1.21.1] - 2026-09-14

Fixes the music-service link icon from v1.21.0: it was a rough hand-drawn
approximation ("suggestive of" Spotify/Deezer's marks, per the old code
comments) rendered at 17px, meant for small toolbar icons — much too
small and not actually recognizable next to a hero-sized track title.

- `SpotifyIcon`/`DeezerIcon` now use the real official brand marks (path
  data sourced from Wikimedia Commons' Spotify and Deezer logo files),
  in their real brand colors (`#1ED760` green, `#A238FF` purple) instead
  of `currentColor`.
- Sized up to 2.25rem (from the shared `.icon-btn` default of 17px) via
  a dedicated `.music-service-link` override — big enough to actually
  read the mark at a glance.
- Verified visually via a static fixture screenshot (playwright), not
  just a clean build, per `AGENTS.md`'s verification-discipline rule for
  visual changes.

## [1.21.0] - 2026-09-14

Replaces the dead-end OAuth playlist-write star button with a read-only
music-service link: search the current track against whichever service
(Spotify or Deezer) the listener has picked as active, and show a
greyed-out (unresolved) or full-color (matched) service icon in the
track row that opens the track's public page in a new tab. No OAuth, no
playlist write, no per-user connection state — the listener does any
"add"/"heart" themselves in their own already-logged-in service session.
Sidesteps both blockers that killed the old feature (Spotify's 5-user
Development Mode cap, Deezer's closed developer-app registration) since
neither applies to read-only catalog search.

- New `GET /api/music-link?raw_title=...` endpoint (`routers/music_link.py`),
  resolves the active service server-side from the listener's own config
  (not a client-supplied param), dispatches to the existing
  `find_best_track()` matching pipeline in `spotify.py`/`deezer.py`,
  caches results (including misses) in a new shared
  `music_link_cache.py`.
- `spotify.py`: new `get_app_token()` — Client Credentials grant (app-level
  auth, no user login), confirmed live exempt from the Development Mode
  5-user cap. Live-verified end to end with real credentials.
- **Two real pre-existing bugs found and fixed while verifying this
  feature**, both dormant since the original star feature never exercised
  these exact code paths in production:
  - `spotify.py`'s `search_tracks()` defaulted to `limit=20`; Spotify's
    `/search` now hard-caps at 10 (a 2026 API change) and silently
    returned zero results for any larger request. Now clamped to 10.
  - `deezer.py`'s `_api()` always sent `access_token=""` in the query
    string for unauthenticated calls; Deezer's API accepts a *missing*
    token param but rejects a *present-but-empty* one with a 200-status
    error body that looked like "no results" to any caller checking only
    the status code. Now omitted entirely when there's no real token.
- Deletes `useSpotify.ts`/`useDeezer.ts` (OAuth-connect/toggle/mirror
  hooks, ~90% irrelevant to a read-only lookup) and the dead
  `configuredServices` UI gate; the existing "Music service" dropdown
  (unchanged styling/position) now always renders and drives the new
  lookup instead of the old star toggle.
- The OAuth backend (`routers/spotify.py`/`deezer.py`'s connect/status/
  toggle endpoints, the DB playlist-mirror tables) is untouched and
  dormant, not removed — out of scope for this change.

## [1.20.3] - 2026-09-14

Fixes a real production incident: DAHL auto-hid itself hours after
v1.20.2 shipped a `dahl_timeout` 30→90s fix, because that fix never
actually applied. `settings.load()` merges code defaults underneath
whatever's already saved in `settings.json` — a value saved once (while
the old default was still live) stays saved forever, regardless of later
default changes. Confirmed via a real `ai_requests` row
(`elapsed_ms=30042`) and manually patched the live setting. This is not
DAHL-specific — the same class of bug affected NIM's model default
before — but no general fix was built this session; see `findings.md`
for the open question about whether one is worth building.

- Manually corrected the already-persisted `dahl_timeout` on the
  production install (no code change fixes an already-saved value).
- **Fixed a real gap in the intra-DAHL model fallback** (added in
  v1.20.2): it only retried the next model on an HTTP 429, not on a
  client-side timeout — exactly the failure mode that caused this
  incident. `llm_dahl()` now retries on timeout too, splitting
  `dahl_timeout` (the total budget) unevenly across attempts rather than
  giving every fallback model the full configured timeout, which could
  otherwise multiply total wait time well past what a live request
  should tolerate.
- Full incident writeup and the budget-splitting design in
  `findings.md` and `AI.md`'s dahl section.

## [1.20.2] - 2026-09-14

DAHL quality investigation (DeepSeek-V4-Flash, GLM-4.3-flash, Qwen3-235B
attempted per the operator's request) plus two real fixes it surfaced.

- **DeepSeek/GLM/Qwen could not be tested** — all three returned HTTP 429
  `model_concurrency` continuously for 30+ minutes on this free-tier key;
  only MiniMax-M2.7 was reachable. No accuracy data collected; re-test
  once DAHL's capacity allows.
- **Found and ruled out a MiniMax-M2.7 character-counting reasoning
  loop**: under a raw prompt with an exact character-count target, the
  model gets stuck counting its own output character-by-character and
  never answers. Confirmed via 4/4 clean runs that this does **not**
  occur under DAHL's real hardened production prompt, which replaces
  that exact phrasing — no prompt fix needed.
- **Fixed: `dahl_timeout` raised from 30s to 90s.** The hardened prompt's
  real latency (42-58s observed, 4/4 runs) exceeded the old default on
  every run, which would silently fall through to the next provider in
  the fallback chain and make DAHL look unreliable for reasons unrelated
  to model quality.
- **Added: intra-DAHL model fallback.** `llm_dahl()` now tries the
  admin-configured model first, then falls through a fixed,
  hand-maintained list of DAHL's other known models
  (MiniMax-M2.7 → DeepSeek-V4-Flash → GLM-4.3-flash → Qwen3-235B) on an
  HTTP 429 specifically — DAHL's own error body sometimes suggests a
  "switch to this model" alternative, but live testing found that
  suggestion unreliable (a named model itself 429'd seconds later), so
  the fallback order is fixed rather than following it. `ai_requests`
  now logs whichever model actually answered, not just the configured
  one, when a fallback occurs.
- Full investigation, evidence, and reasoning in `findings.md` and
  `AI.md`'s dahl section.

## [1.20.1] - 2026-09-14

Bug fix: DAHL's API key couldn't be saved and Test always failed with
"Could not reach the server to run the test." Root cause: v1.20.0 wired
DAHL into `providers.py`/`settings.py`/`enricher.py`/`textutil.py`, but
missed the two files that actually expose the admin-facing API —
`AISettingsUpdate` (`models.py`) had no `dahl_*` fields, so FastAPI
silently dropped them from every PATCH body before saving; and the
`/api/settings/ai/test` route's `Literal[...]` provider list didn't
include `"dahl"`, so FastAPI rejected the request with a 422 before it
reached the test logic, which the frontend's generic error handler
rendered as a network-reachability error rather than a validation one.
Also fixes a display bug where DAHL-generated trivia would render an
undefined provider label in the now-playing trivia history strip.

- `models.py`: add `dahl_api_key`/`dahl_model`/`dahl_timeout`/
  `dahl_manually_enabled` to `AISettingsUpdate`.
- `routers/settings.py`: add `"dahl"` to the test endpoint's `Literal`.
- `NowPlayingPanel.tsx`: add `dahl: 'DAHL'` to `_PROVIDER_LABEL`.

## [1.20.0] - 2026-09-14

Adds DAHL as a new AI provider (research-only status): a free,
OpenAI-compatible inference endpoint serving MiniMax-M2.7. Reuses the
existing OpenAI-compatible request path with a 4096-token budget (the
model's chain-of-thought needs the headroom) and strips its
`<think>...</think>` reasoning block before returning the answer. Gets
the same categorical-hallucination prompt hardening and Wikipedia
grounding as Mistral/Gemini/OpenRouter/Ollama/NIM.

- `providers.py`: `llm_dahl()`, `_test_dahl()`, added to `PROVIDERS` and
  `AUTO_HIDE_PROVIDERS`.
- `settings.py`: `dahl_api_key`/`dahl_model`/`dahl_timeout`/
  `dahl_manually_enabled` defaults; key added to `_SECRET_FIELDS`.
- `textutil.py`: added to `_CATEGORICAL_PROVIDERS`.
- `enricher.py`: dispatch + model-settings-key entry.
- Frontend: new provider bubble in `AISettingsPage.tsx`, `DahlIcon`,
  `types.ts` union, i18n strings in all 16 languages (non-English
  strings are untranslated English placeholders for now).
- `KB.md`: "Getting an API key" section for DAHL.

## [1.19.3] - 2026-09-13

Bug fix: station name now wraps cleanly away from the station logo on mobile.
The `min-width: 0` on `.panel-head` was insufficient because the logo is
absolutely positioned — it occupies no flex space. Adds `padding-inline-end`
on `.station-strip` inside the `max-width: 480px` media query to reserve
the logo's width, so the name wraps correctly instead of rendering under it.

- `dashboard.css`: add `padding-inline-end: 4.5rem` to `.station-strip` in the
  mobile media query; the value accounts for the 44px-tall logo's width range.

## [1.19.2] - 2026-09-13

Bug fix: station names longer than one line now wrap to two lines in the
now-playing panel header without crowding or overlapping the station logo.
The logo's reserved space is always respected. Short names stay on one
line as before. Desktop layout is unaffected.

- `dashboard.css`: `.station-name-strong` now uses `-webkit-line-clamp: 2`
  instead of `white-space: nowrap`, allowing multi-line wrap with ellipsis.
- `dashboard.css`: `.panel-head` gains `min-width: 0` so flex children can
  shrink below their content size, ensuring the station name always leaves
  the logo's right-side space intact.

## [1.19.1] - 2026-09-13

Security fix: close an SSRF bypass in the stream proxy via HTTP redirects.

- `backend/app/routers/stream.py`'s SSRF guard (`_reject_private_targets`)
  correctly resolved and checked the target IP before the first request, but
  `httpx.AsyncClient(follow_redirects=True)` then silently followed any 3xx
  redirect with no further check — a public station URL that passed the
  guard could redirect to a private/loopback/link-local address (e.g. cloud
  metadata, `127.0.0.1`, other containers on the LAN) and the proxy would
  fetch and stream it back. Fixed with an httpx response event hook that
  re-runs the same guard on every redirect hop before it's followed. Also
  fixes a pre-existing resource leak on this path: `HTTPException` raised
  mid-`send()` isn't an `httpx.HTTPError`, so it skipped the existing
  cleanup block and never closed the client — added a broader `except`
  around the send to close it on any exception. Verified against live
  redirect chains (redirect to loopback: blocked; redirect to link-local/
  metadata address: blocked; normal public-to-public redirect: still
  works) before shipping, not just unit-tested in isolation. Found via a
  full-codebase security audit.

Replace World genre with Latin/Hispanic, add a new Afrobeat genre.

- Renamed the `world` genre key to `latin` throughout (`GENRES`,
  `GENRE_LABELS`, `_GENRE_KEYWORDS`, `Genre` TS union, `genre_of()` and
  `genre_stations_for()`'s classification tuples) and relabeled it
  "Latin/Hispanic". Replaced its 10 stations: dropped Bollywood, Afrobeat,
  and the generic French/world-music filler entries, added Andalusian
  flamenco (Canal Sur Radio Andalucía, Energía Flamenca), Portuguese fado
  (Rádio Amália, Antena 1 Fado), and South American salsa/samba (Colombia,
  Mexico, Argentina, Brazil).
- Added a new `afrobeat` genre, 10 stations, mostly Nigerian (Softlife
  Afrofusion, LagosJump, Fresh 105.9 FM Ibadan, and others) plus Côte
  d'Ivoire and South Africa, sourced from radio-browser.info by listener
  count.
- 15 genres total now (was 14); genre counts verified: Latin 10, Afrobeat
  10, all other genres unchanged.

## [1.18.4] - 2026-09-13

Force-disable Spotify and Deezer playlist saving — both are dead ends right now.

- Spotify is capped at 5 allowlisted users per Spotify's February 2026
  Development Mode policy, with no self-service path past that for a project
  this size. Deezer's developer portal has closed new app registration with
  no reopening date. Both `configuredServices.spotify` and `.deezer` are now
  hardcoded `false` in `NowPlayingPanel.tsx`, hiding the star button and
  "Music service" dropdown regardless of server-side credentials. Backend
  code, Settings pages, and DB schema for both services are untouched —
  reversible the moment either blocker lifts.

## [1.18.3] - 2026-09-13

Fix a crash on failed OAuth callback (Spotify and Deezer).

- The OAuth popup callback page (`_callback_response` in `backend/app/main.py`,
  shared by `/spotify-callback` and `/deezer-callback`) used `str.format()` on
  an HTML template containing literal CSS and JS braces (e.g.
  `body { font-family: ... }`). `.format()` treats every `{...}` as a
  placeholder, so any connection failure — not just the happy path — crashed
  with `KeyError` instead of showing the "connection failed" message. Switched
  to plain `.replace()` for the three real placeholders (`service`, `message`,
  `script`), leaving the CSS/JS braces untouched. Found live: a real Spotify
  OAuth failure (403 from `/v1/me`, "user not registered for this
  application" — a Development Mode app restriction, unrelated to this bug)
  surfaced this crash instead of a readable error.

Re-enable Spotify.

- A new Spotify Developer app was registered under a Premium-subscription
  account, and its Client ID/Secret entered in Settings → Spotify. Reverted
  the v1.18.1 force-disable in `NowPlayingPanel.tsx` — the star button now
  reflects real server-side `spotify.configured` state again, so Spotify and
  Deezer are both offered via the "Music service" dropdown.

## [1.18.1] - 2026-09-13

Deploy fix, Spotify parked in the UI, three new genres.

- Fixed the production deploy path: the GitHub Actions workflow and manual
  deploy commands checked for a git checkout directly under
  `<appdata>/mradio-web`, but it actually lives one level deeper at
  `<appdata>/mradio-web/app`. Both `deploy.yml` and `AGENTS.md` corrected;
  `deploy.yml` now also dumps a directory listing on failure for faster
  diagnosis next time.
- Retracted a false claim in `AGENTS.md` that a safety classifier blocks the
  assistant from running direct SSH commands against the production host —
  it doesn't; direct SSH deploys are the current path until the GitHub
  Actions workflow has its secrets configured.
- Spotify is documented as "parked" (pending a Premium-owned Developer app)
  but was never actually disabled in the UI: the star button still showed
  and routed to Spotify OAuth whenever the server had Spotify credentials
  configured. `NowPlayingPanel.tsx` now force-disables Spotify regardless of
  server config, so only Deezer is offered until Spotify is deliberately
  re-enabled.
- Added three new station genres — Electronic, World, and Metal — with 10
  curated stations each, sourced from radio-browser.info ranked by listener
  count. Fixed a latent classifier bug where `"metal"` was a `rock` keyword,
  which would have shadowed the new Metal genre in auto-classification.

## [1.18.0] - 2026-09-12

Deezer per-user playlist integration and selectable music service.

- Added a parallel Deezer backend path mirroring Spotify: OAuth flow, encrypted
  token storage, private per-user "mradio-web" playlist, executive-decision
  track matching, and local playlist mirror (`backend/app/deezer.py`,
  `backend/app/routers/deezer.py`, new `deezer_*` DB tables).
- Added `music_service` to per-user config: listeners can choose whether the
  star button saves tracks to Spotify or Deezer.
- Added a "Music service" dropdown to the Now Playing panel (visible only when
  both services are configured), with inline Spotify and Deezer icons.
- Added a Deezer admin settings page and registered it in Settings,
  Dashboard, and TopBar.
- Updated i18n strings across all 15 locales for Deezer and the new music
  service labels.
- Unified the OAuth token encryption key: `MRADIO_TOKEN_KEY` is now preferred
  and covers both services; `MRADIO_SPOTIFY_TOKEN_KEY` still works as a
  fallback for existing installs.
- Updated `KB.md`, `README.md`, `docker-compose.yml`, and `STATUS.md` with
  Deezer setup instructions.

## [1.17.6] - 2026-09-12

Spotify OAuth logging and error visibility.

- Added structured logging in `backend/app/spotify.py` for the token exchange,
  `/v1/me` profile fetch, and connection outcome so we can see why Spotify
  rejects the connection.
- Added `show_dialog=true` to the Spotify authorization URL to force a fresh
  approval dialog and avoid stale/incomplete scopes from a previous grant.
- `backend/app/main.py`: on OAuth errors the callback page now stays open and
  shows the failure detail instead of closing immediately.
- `frontend/src/hooks/useSpotify.ts`: made the auth popup wider (700×600).

## [1.17.5] - 2026-09-12

Spotify OAuth callback page fix.

- `backend/app/main.py`: the `/spotify-callback` page added in v1.17.4 used
  `str.format()` on an HTML template that contained CSS braces, causing a 500.
  Switched to a plain `replace()` placeholder so the page renders and closes
  the popup correctly.

## [1.17.4] - 2026-09-12

Spotify OAuth popup close fix (partial).

- Added a dedicated `/spotify-callback` page intended to close the OAuth popup
  after Spotify redirects back, instead of leaving the user on the Settings →
  Spotify admin page inside the popup. The HTML template used `str.format()`,
  which crashed on CSS braces, so v1.17.5 finishes the fix.
- `backend/app/routers/spotify.py`: callback now redirects every user to
  `/spotify-callback?status=...`; removed the admin-vs-non-admin redirect split.
- `frontend/src/pages/Dashboard.tsx`: removed the stale effect that opened the
  Spotify settings page from `/settings?spotify=connected`.
- `frontend/src/hooks/useSpotify.ts`: open the auth popup as a sized window and
  surface a clear error if the browser blocks it.

## [1.17.3] - 2026-09-12

Spa fallback class fix.

- `backend/app/main.py`: the SPA fallback added in v1.17.2 now catches
  `starlette.exceptions.HTTPException` (the one `StaticFiles` raises) instead
  of FastAPI's subclass, so `/settings?spotify=connected` actually serves
  `index.html`.

## [1.17.2] - 2026-09-12

Spotify OAuth return fix (partial).

- `backend/app/main.py`: added an SPA fallback to the static-files handler
  intended to make direct GETs to frontend routes serve `index.html` instead
  of a 404. Caught the wrong exception class, so v1.17.3 finishes the fix.

## [1.17.1] - 2026-09-12

Spotify OAuth popup fix.

- `frontend/src/hooks/useSpotify.ts`: Spotify authorization now opens in a
  new browser tab/window instead of navigating the player away, and the
  player polls `/api/spotify/status` every 3 seconds until the popup
  completes so the star button reflects the connected state.

## [1.17.0] - 2026-09-12

Spotify per-user playlist integration.

- Added per-user Spotify playlist support. Admin enters the Spotify app
  credentials in Settings; each listener connects their own account from the
  player and gets a private "mradio-web" playlist.
- Added a star button to the Now Playing panel that adds or removes the
  currently-playing track. The star is filled when the track is already in the
  user's playlist.
- Implemented executive-decision track matching in `backend/app/spotify.py`:
  multi-query Spotify search, ISRC deduplication, title/artist/performer
  scoring, album-type preference (album > single > compilation), popularity
  tiebreaker, and a conservative acceptance threshold.
- Mirrored playlist contents in `spotify_playlist_tracks` so the filled-star
  state is instant and doesn't hit Spotify on every UI tick.
- Encrypted refresh tokens at rest with `cryptography.fernet` using the
  `MRADIO_SPOTIFY_TOKEN_KEY` env var; falls back to "plain:" when no key is
  configured (development only).
- Auto-detected the user's Spotify market from the OAuth profile for
  region-aware search and track relinking.
- Added OAuth state cleanup (`delete_expired_oauth_states`) in the Spotify
  callback handler.

## [1.16.9] - 2026-09-11

Wikipedia grounding speed fix.

- Optimized `backend/app/wiki.py` grounding lookups. Extracts for the
  top opensearch results are now fetched in a single batched API call
  instead of three sequential calls, concurrent lookups for the same
  track are coalesced, and the inter-call throttle was reduced from
  1.0s to 0.5s. Cold-start title resolution now takes ~1s instead of
  ~4s, which restores Mistral/Grok/Gemini/NIM's snappy feel while
  keeping the grounded anti-hallucination benefits.

## [1.16.8] - 2026-09-11

AI liner-notes grounding + provider hardening.

- Added English Wikipedia snippet grounding for every hardened AI
  provider. `backend/app/wiki.py` resolves the played work to a Wikipedia
  article, fetches the intro extract (~600 chars), and `enricher.py`
  prepends it to the prompt as "GROUNDING CONTEXT". The resolver uses a
  1-hour in-memory cache, a 1-second API throttle, 429/5xx retry,
  title-first search, and scoring that strongly prefers exact title
  matches (+1000) and music-specific articles (+200) while penalizing
  disambiguation pages (-300). This eliminates the most egregious
  fabrications on less-documented tracks (e.g. Gemini's invented "1978
  Los Angeles" date for Maria Muldaur's "Empty Bed Blues").
- Fixed `_llm_openai_compatible()` in `backend/app/providers.py` crashing
  with `AttributeError` when a provider returns `"content": null`
  (observed with OpenRouter reasoning outputs); it now coerces `None`
  to `""` before `.strip()`. Applied the same fix to `llm_grok()`.
- Replaced the EOL NVIDIA NIM default model
  (`minimaxai/minimax-m3`, HTTP 410) with
  `meta/llama-3.2-11b-vision-instruct`, the only model that was both
  account-invokable and returning valid JSON within the timeout in live
  probing.

## [1.16.7] - 2026-09-10

Fixed a real playback-recovery bug: an audio dropout would sometimes
require a manual Stop/Play to recover from, instead of the app's
automatic recovery kicking in. Root cause — the automatic retry called
`audio.play().catch(() => undefined)`, silently discarding the
rejection. A rejected `play()` promise (interrupted request, autoplay
policy, etc.) does NOT fire a new native `error`/`stalled` event, so
nothing was left to trigger another retry attempt; playback just
stayed dead. Fixed with a shared retry-with-backoff loop (mirroring
the existing WebSocket reconnect pattern) that both the native
`error`/`stalled` listener and a rejected `play()` now feed into,
capped at 6 attempts with exponential backoff (2s up to 30s).

Also added light client-side event logging for this exact retry state
machine (`POST /api/stream/client-event`, relayed into the same server
log as everything else) — rare, state-transition events only (a
handful of lines per real incident, never steady-state ticks), so a
future dropout can be diagnosed end-to-end instead of only from the
server's side of the connection.

## [1.16.6] - 2026-09-10

Fixed a real, silent analytics gap: the Dashboard's "Live now" panel and
listener map showed nobody listening even during active sessions.
Root cause — `routers/stream.py`'s history/live-session tracking only
fired `if station_name:`, where that name came solely from the origin
stream's `icy-name` header. Confirmed live via container logs: the
large majority of real sessions on this deployment have a blank
`icy-name` (`station=''`), despite the stream playing fine with real
`StreamTitle` metadata — so most actual listening was never recorded
at all, not just an edge case. Fix: the frontend now also sends the
station's own known name (from the curated/favorites list, already
known client-side) as a new `station_name` query param on
`/api/stream`; the backend prefers that over the ICY-derived name for
history/live-session tracking and genre resolution, falling back to
ICY only when the app doesn't have one. The ICY-derived name is
unchanged for its other use (the WS "station" event).

## [1.16.5] - 2026-09-09

Fixed a real, root-cause bug in the categorical hallucination rules
(applies to every hardened provider): the "unknown artist/work" skip
instruction was conflating two different situations — genuinely not
recognizing an artist at all, vs. recognizing a real, well-known artist
but not knowing this SPECIFIC track by name. Both were collapsing to
the same blanket "No confident details are available" refusal, even
when the model had real, certain, general facts about the artist
themselves (era, nationality, style, notable associations). User
flagged this as making the tool feel non-functional — declines that
throw away real available knowledge instead of just staying silent on
the part that's genuinely uncertain. Split into two explicit cases:
unknown artist still declines fully (unchanged, still required); known
artist/unknown track now fills SLOT 1 with genuine artist-level facts
and skips the track-specific slots (year/city/character) rather than
guessing at them or declining everything. Verified live via the real
production Grok subscription: both previously-declined tracks (Herb
Ellis' "Country Boy," Théodore Dubois' cello Fantaisie-Stück) now
correctly surface real artist facts, consistently across repeat runs;
the genuine fabrication trap still declines correctly, unaffected.

## [1.16.4] - 2026-09-09

Added an 8th fact category to the hallucination allowlist (applies to
every hardened provider): for a well-known WORK, who first
recorded/premiered it (year + label if certain), and up to 2-3 other
well-known artists who notably recorded the same work (name + era
only, no anecdotes, no rankings). Caught live on Thelonious Monk's
"Ruby, My Dear" — the model demonstrably knew real, checkable facts
(first recorded 1947 for Blue Note, later recorded by John Coltrane)
that the previous rules had no category for. **Known limitation,
tested and documented rather than papered over**: this category lands
inconsistently — repeat runs on the same track sometimes surface it,
sometimes skip it and stay thin, even though the underlying knowledge
is there. No fabrication risk either way (skipping is always safe);
shipped as a net improvement over the prior baseline of "structurally
impossible to surface," not a guarantee of consistent richness.

## [1.16.3] - 2026-09-09

Added a 7th fact category to the categorical hallucination allowlist
(applies to every hardened provider — Mistral/NIM/Gemini/OpenRouter/
Ollama/Grok): whether the current track is a cover/version of an
earlier song, plus the original artist and year, when genuinely
certain — nothing more about the original beyond that. Caught live:
the existing rules were correctly declining to pad answers with
unverifiable detail, but had no category for this specific, checkable,
low-risk fact, so answers on well-known covers read thinner than
necessary even when the model plainly knew the original. Verified live
(Grok, via the real production subscription token) on 4 tracks: a
previously-thin cover now correctly states "The Tourists... cover of
the song originally recorded by Dusty Springfield in 1963"; a
non-cover correctly does NOT invent a cover claim; a fabrication trap
still correctly declines; a second real cover (Puff Daddy's "I'll Be
Missing You," built on The Police's "Every Breath You Take") also
resolves correctly.

## [1.16.2] - 2026-09-09

Extended the anti-hallucination categorical rules (already applied to
Mistral/NIM/Gemini/OpenRouter/Ollama) to Grok. Caught live: on a Kora
Jazz Trio cover of "Chan Chan," Grok gave a confident, detailed
biography of the original composer (Compay Segundo) and the original
1990s recording's history — richer-sounding than the other providers,
but none of it re-verified, and about the wrong recording (the
original, not the cover actually playing). Grok now gets the same
fact-category allowlist, worked examples, and mandatory-slot structure
as every other cloud provider. One-line change
(`_CATEGORICAL_PROVIDERS` frozenset in `textutil.py`) — no other code
needed, since `apply_provider_rules()` already gates generically on
provider name.

## [1.16.1] - 2026-09-09

Fixed a real, previously undiagnosed failure mode for the `gpt-oss:20b`
Ollama model: on the app's actual trivia prompt, it could enter a
non-convergent internal reasoning loop (repeatedly re-litigating one
uncertain fact, e.g. an ambiguous anniversary year) and burn its entire
token budget without ever emitting a response — not a wrong answer, no
answer at all. Diagnosed live against the model's own `thinking` field
(gpt-oss is a genuine reasoning model per its Ollama capabilities
listing), confirmed NOT fixed by a bigger token budget alone (the loop
just runs longer). Fixed with a targeted anti-deliberation instruction
(gpt-oss-specific, not applied to other Ollama models) plus a higher
`num_predict` ceiling as backup headroom — verified over 7 live runs
across 5 different tracks, including the exact track that previously
triggered the loop and a fabricated-track hallucination trap, all
converging cleanly with valid, non-fabricated output.

## [1.16.0] - 2026-09-09

Two AI providers page usability improvements, both user-requested:

- **Ollama's "Model" field is now a dropdown** of whatever's actually
  installed on the configured server, instead of a name typed by
  hand. Probes the server's real model list (size included) whenever
  the Server URL field is saved or blurred; falls back to a plain text
  field if the server isn't reachable yet. Sorted largest-first with a
  "largest installed" label on that one — deliberately NOT framed as a
  quality recommendation, since size doesn't predict which model
  answers best (this session's own testing found a smaller model more
  accurate than a larger one on the same tracks). A note next to the
  dropdown says so directly and points at the existing Test button as
  the real way to compare.
- **Every provider bubble now has its own Save button** in its header,
  not just one at the very bottom of the page — the same single form
  submit as before (no new save path), just reachable without
  scrolling past every other bubble after tweaking one.

## [1.15.1] - 2026-09-09

Extended the same anti-hallucination prompt hardening (v1.15.0) to
**Ollama** — user spotted `gemma4:e4b-it-qat` inventing vague, unverifiable
filler ("featured in live sets and radio rotations that celebrate
contemporary jazz innovation") for a real Robert Glasper track. Verified
live: the same prompt against the same model now stays to disciplined,
checkable facts only.

## [1.15.0] - 2026-09-09

Three real, live-confirmed provider fixes from a full provider-by-
provider quality/speed comparison:

- **NIM's default model was dead.** `minimaxai/minimax-m3` was retired
  by NVIDIA hours before this was caught (confirmed live: `410 Gone`).
  Replaced with `mistralai/mistral-nemotron`, the only genuinely
  working non-reasoning model found after probing all ~80 models
  NVIDIA's own catalogue lists for this account (most 404 as "not
  found for account" — the public model list is not a reliable guide
  to what's actually usable).
- **Gemini and NIM had zero/weak anti-hallucination hardening.** A
  live test found Gemini — despite excellent, fully accurate answers
  on well-documented tracks — invented a complete fake biography for a
  nonexistent artist/track, the same failure Mistral was hardened
  against in 1.13.0. Extended that same category-based prompt hardening
  (renamed `CATEGORICAL_HALLUCINATION_RULES`, no longer Mistral-only)
  to `openai` (NIM) and `gemini`. Result: Gemini went from a 50s fully
  fabricated answer to a 1.3s honest "no confident details available",
  and got noticeably faster on well-documented tracks too (30-50s to
  ~1s) since there's less to reason through with a shorter, more
  disciplined target.
- **OpenRouter's free auto-router was unreliable.** Live testing found
  most of its genuinely free models are reasoning models whose
  chain-of-thought counts against the same token budget as the reply —
  at the app's original 1200-token budget, several exhausted the whole
  budget reasoning and returned empty content, never reaching real
  JSON. Bumped OpenRouter's `max_tokens` to 3000 and timeout to 90s,
  and applied the same categorical hardening (which also reduces how
  much reasoning is needed). One model (`nex-agi/nex-n2.5-pro:free`)
  got every fact right on a well-documented test, including the
  correct dedicatee no other provider that day got right — but took
  84s on one run even with the fix, a real reminder that OpenRouter's
  free-tier response times are genuinely unpredictable depending on
  which underlying model you land on.

## [1.14.1] - 2026-09-09

Fixed a wrong station logo: "Heart 70s (UK)" was showing the generic
Heart brand heart-icon instead of a decade-specific logo. Root cause:
when the exact station name finds nothing in the Radio-Browser
directory, the app retries with a shortened, "loose" search (here,
just "Heart") and sanity-checks results against the station's own
distinguishing words — but that check only required *any one* shared
word to pass, so a result named plain "Heart" or "Heart 80s" slipped
through on the shared word "heart" alone, without the actually
distinguishing word "70s" ever matching. Now requires every
distinguishing word to match, not just one — the same rule the
Wikipedia-image fallback tier already used correctly.

## [1.14.0] - 2026-09-09

Fixed a real gap found while investigating a user report: when the
new-account invite email failed to send (bad SMTP credentials,
provider hiccup, etc.), the account was still created successfully
and nothing anywhere — API response or server log — showed that the
email didn't go out. Send failures are now logged
(`mradio.users` logger), and admins can manually trigger a fresh
invite at any time via a new **Resend invite** button on the Users
page (also useful after correcting a user's email address, since
changing it there never sends anything on its own by design).

## [1.13.0] - 2026-09-09

Hardened Mistral's enrichment prompt with a much stronger,
category-based constraint set, arrived at by iterating live against
the real API across 20+ test runs on 4 tracks (well-documented
classical, well-documented jazz, an obscure classical work, and a
fabricated nonexistent track used as a hallucination trap). Replaces
the base prompt's 750-850 character target for Mistral specifically
(that instruction was reliably winning over any later "be careful"
rule) with a mandatory sentence-slot structure (composer/era, then
year+city only, then musical character, then one optional certain
fact — no closing "legacy/popularity" sentence, which is where
fabrication kept sneaking back in), two worked GOOD/BAD examples, a
self-check pass, and an explicit allowance to skip every slot and say
so plainly for a genuinely unrecognized artist/track. Full account of
what didn't work along the way is in `textutil.py`'s comments.

Also fixed a real, pre-existing inconsistency unrelated to Mistral:
every provider's hardcoded system message said "You are a helpful
classical-music metadata assistant", contradicting the actual prompt's
own explicit "classical, jazz, rock, pop, or any other genre" scope.
Fixed across all 4 call sites (NIM/OpenRouter/Mistral's shared helper,
Gemini, Grok, Codex) to a genre-neutral phrasing.

## [1.12.1] - 2026-09-09

Made **Mistral** admin-only (like ChatGPT/Grok/OpenRouter), by explicit
request, immediately after 1.12.0 shipped it as free-for-everyone. Not
a quota-driven restriction — just kept for admins for now. Updated the
provider's intro copy (all 15 languages) and KB.md to match.

## [1.12.0] - 2026-09-09

Added **Mistral AI** as an 8th AI liner-notes provider — their free
"Experiment" tier on La Plateforme, no credit card required, not
admin-only (free for everyone once configured, same as Gemini/
OpenRouter). Dropdown/settings order is now Codex, Grok, Mistral,
OpenCode, Ollama, NIM, Gemini, OpenRouter — the two subscription
providers first, per explicit request.

Checked live before building (same discipline as the OpenRouter/Gemini
research): Mistral's flagship `mistral-small-latest` returns a valid
200 from `GET /v1/models` but is rate-limited to **0 requests/minute**
on this free tier — a live completions call is the only way to catch
that, so defaults to `open-mistral-nemo` (12B) instead, which along
with the Ministral 3B/8B family gets real, generous quota (625K-1.3M
tokens/min, 188-750 requests/min — the most generous free quota of any
provider in the app, just on smaller models). The Test button makes a
real completion call rather than trusting `/models`, for the same
reason OpenRouter's does.

A live spot-check also found real fabrication on niche classical-music
facts at this model size (wrong dedicatee, an invented "three weeks"
composition claim) despite an accurate-sounding reply — Mistral gets
the same anti-hallucination `SINCERITY_RULES` prompt hardening the NIM
provider already had. Separately hardened the shared prompt template
for every provider to spell out dates unambiguously ("8 December 1813",
never "12/8" or "8/12") after that same spot-check produced a US/EU
day-month mixup on an otherwise-correct date.

## [1.11.0] - 2026-09-09

- **Auto-generated temporary passwords for email invites**: when an admin
  creates a user with an email address, mradio-web now generates the
  temporary password itself instead of asking the admin to pick one — the
  admin never sees or types it, since the invited person always sets
  their own via the emailed invite link. The Add User form's "Temporary
  password" field is only shown (and required) when no email is given,
  which remains the only case with no invite-link path. Fixes a UX
  dead-end where the field was still marked required even though nothing
  ever consumed the value once an email was set.

## [1.10.0] - 2026-09-09

- **Username reminder**: the password-reset and welcome/invite emails
  now always state the account's username, and so does the set-your-
  password page they link to. A forgot-password email now doubles as a
  forgot-username recovery — click the link only to see your username,
  then go back and sign in normally with the password you actually
  remembered; the unused link just expires, it doesn't block login.
- **Remember me for 30 days**: a checkbox on the login screen,
  checked by default. Unchecked, the session cookie is dropped when
  the browser closes instead of persisting; checked matches today's
  existing behavior exactly.
- **Email design switched from dark to light theme**, matching the
  app's own light palette. Logo is ~35% bigger.
- **Light is now the default theme** for any account with no saved
  preference yet (new signups, or an existing config that predates the
  theme setting) — previously defaulted to dark.

## [1.9.1] - 2026-09-09

Gave the email logo real depth — a gradient fill, hairline dark stroke,
and drop shadow instead of a flat single-color fill, which read as a
sticker rather than a mark. Also fixed the production domain used to
verify the previous release (`mradioweb.legba.myddns.rocks`, not the
stale `radio.legba.myddns.rocks` from an outdated note).

## [1.9.0] - 2026-09-09

Both outbound emails are now real branded HTML — dark theme, the app's
own logo mark, teal accent, serif headline — instead of plain text:

- **Password reset**: same link and expiry as before, now with a
  proper design.
- **New: welcome/invite email.** When an admin creates a new user
  *with* an email address filled in right at creation, that person now
  gets an invitation to set their own password directly, instead of
  relying on the admin to hand them a temporary one. Adding an email
  to an existing account later doesn't trigger this — only having one
  at creation time does. The invite link lasts 7 days (vs. 1 hour for
  a password-reset link, since an invite is checked on the recipient's
  own schedule, not urgently).

## [1.8.0] - 2026-09-08

ChatGPT, Grok, Gemini, and OpenRouter now hide themselves from the
player's AI menu automatically when they fail — no more picking a
provider that's silently broken. If a real enrichment request through
one of them fails (bad key, expired token, quota hit, network error),
it drops out of the dropdown immediately for everyone. A background
check retests it every 30 minutes and only brings it back once that
retest actually succeeds — never blindly after a timer. The AI
providers settings page shows a note when a provider is in this state,
distinct from the manual enable/disable toggle. Ollama and NIM don't
get this — a failure there is almost always a config mistake that
won't fix itself.

## [1.7.1] - 2026-09-08

Fixed a real bug from the 1.7.0 release: Gemini and OpenRouter both
appeared in the player's AI menu as a blank, unlabeled entry — the
dropdown's provider-name lookup was never updated when either was
added, so it silently rendered empty text instead of "Gemini" or
"OpenRouter".

Also: made OpenRouter admin-only (its free tier is a single quota
shared by everyone using the one saved key — 50 requests/day — unlike
Gemini's per-account allowance, so it needed the same protection
ChatGPT/Grok already have). Added the "Show in the player's AI menu"
enable/disable toggle to Gemini and OpenRouter, matching ChatGPT/Grok.

## [1.7.0] - 2026-09-08

Added **OpenRouter** as a 7th AI liner-notes provider — genuinely free
(no credit card needed to sign up), available to every account once
configured, not admin-only. Defaults to `openrouter/free`,
OpenRouter's own router that always picks a currently-free model
rather than pinning to one specific model ID that could later be
pulled from the free lineup.

While researching this, checked Groq and Cerebras (also on the
candidate list) against their real, current APIs — both turned out not
to actually be free anymore (Groq's free models were pulled from
self-serve access; Cerebras now requires a card on file to activate
API access at all), so neither was built. Findings recorded in
`findings.md`.

## [1.6.0] - 2026-09-08

Added a "GitHub project page" link to the user menu (avatar → dropdown),
between Settings and Change password — opens
[github.com/Marcus1571/mradio-web](https://github.com/Marcus1571/mradio-web/tree/main)
in a new tab. Visible to every account, not just admins.

## [1.5.1] - 2026-09-08

Changed Gemini's default model from `gemini-3.8-flash` to
`gemini-3.5-flash-lite`. Confirmed via a real account's AI Studio
rate-limit dashboard: every non-Lite free-tier Flash model shares a
20-requests-**per-day** cap (resets only at midnight Pacific) — trivial
to exhaust with normal use. The Lite variants get 500/day instead, on
the same free tier. Existing installs with a saved `gemini_model` keep
whatever they already have; this only changes the default for new/
unconfigured setups.

## [1.5.0] - 2026-09-08

Fixed Gemini's Test button showing "Connected, but model
'gemini-3.8-flash' was not found on this endpoint." even with a valid
key and a real, working model. Root cause: Gemini was calling Google's
older OpenAI-compatibility endpoint, whose own model listing turned out
to be stale — the model works fine, it just wasn't showing up there.
Switched to Google's own Interactions API instead (confirmed live,
including the exact response shape), which is what Google's current
docs recommend. The "API base URL" field is gone from Gemini's
settings — the new endpoint isn't swappable like Ollama's/NIM's, so
there was nothing left for that field to do.

Also bumped Gemini's request timeout (30s → 45s) after confirming live
that its "thinking" mode can genuinely take that long to reply.

## [1.4.3] - 2026-09-08

Fixed a gap from 1.4.2: after Stop then reload, the panel now correctly
shows nothing playing at all instead of restoring the station in a
stopped state. Reloading after Stop now shows the station you had
selected — name, logo, highlighted in Favorites — in a "Stopped, press
play to reconnect" state, matching what was on screen before the
reload. Only actual playback doesn't auto-resume; the selection itself
does.

## [1.4.2] - 2026-09-08

Fixed: reloading the app (or reopening it) after pressing Stop
auto-resumed playback anyway. The "resume last station" feature only
checked whether a last-played station existed at all, not whether
playback had actually been left running — so a deliberate Stop never
stuck across a reload. Now persists whether you were playing or
stopped, and only auto-resumes if you were still playing.

## [1.4.1] - 2026-09-08

Fixed the player's AI provider dropdown: a disabled provider (either
unconfigured or hidden via the new 1.4.0 "Show in the player's AI menu"
toggle) still appeared as a greyed-out "not configured" line — now it's
omitted from the list entirely, matching how the toggle was meant to
work. Also removed the now-unused `notConfigured` i18n string from all
15 languages.

## [1.4.0] - 2026-09-08

Added a "Show in the player's AI menu" toggle to the ChatGPT and Grok
bubbles on the AI providers settings page.

Both are subscription-based, so they can hit an external usage quota
that has nothing to do with mradio-web itself (see 1.3.2) — until now,
the only way to stop everyone seeing a provider that's temporarily
exhausted was to fully disconnect it, losing the saved sign-in and
having to redo the OAuth flow once the quota reset. The toggle just
hides the provider from the player's dropdown for everyone while
leaving the connection intact — flip it back on the moment the quota
clears. Ollama, NIM, and Gemini don't get this toggle: they don't share
this "connected but temporarily can't be used" failure mode.

## [1.3.2] - 2026-09-08

Fixed the ChatGPT/Codex Test button showing a generic "ChatGPT/Codex did
not respond." for every failure, including genuine usage-limit
exhaustion — you couldn't tell a real quota problem from a network
hiccup or an expired token.

Confirmed live: Codex enforces its own 30-day rolling usage quota that's
separate from the ChatGPT app/CLI's own token-usage graph — a plan can
show plenty of headroom there and still get a `usage_limit_reached` 429
from the Codex API specifically. The Test button now parses that error
and shows the real reason with the reset date, e.g. "Codex usage limit
reached (separate from your ChatGPT app's own usage — resets 2026-10-06
16:28 UTC)."

## [1.3.1] - 2026-09-08

Added a "New to Gemini? See 'Getting an API key' in KB.md" link to the
Gemini section of the AI providers page — it was missing the same
deep-link Ollama and NIM already have, so getting a Gemini API key had
no in-app guidance beyond a one-line intro.

## [1.3.0] - 2026-09-08

Added **Google Gemini** as a 6th AI liner-notes provider — free (no
credit card needed for the free tier) and, unlike ChatGPT or Grok,
available to every account once an admin configures it, not
admin-only.

Also reworked the AI providers settings page: each provider is now a
collapsible card instead of always showing its full fields — a
configured/connected provider starts open, everything else starts
collapsed. With 6 providers now, this keeps the page short and
scannable instead of one long scroll.

## [1.2.0] - 2026-09-08

Added the ability to **rename a favorite**, right in place. In Edit
favorites mode, each station now has a pencil icon next to the trash
icon — tap it to turn the name into an editable field, press Enter (or
tap away) to save, Escape to cancel. This only changes your own label
for that slot; the station's genre and everything else about it stay
as-is.

## [1.1.2] - 2026-09-07

**ChatGPT and Grok are now admin-only to use**, not just to configure.
Every other AI provider (OpenCode, Ollama, NIM/OpenAI-compatible) stays
available to every account. Regular accounts no longer see ChatGPT or
Grok as options in the player's AI provider dropdown, can't select
them directly, and will never receive them via automatic fallback if
their own pick fails — since both ultimately spend a real personal
subscription or paid API budget that belongs to the admin.

## [1.1.1] - 2026-09-07

Fixed Grok's Test button reporting "No API key configured." right
after a successful subscription sign-in. Connecting a subscription
wasn't saving that Subscription mode was actually selected unless the
main Save button was also clicked separately — Connect now persists
that immediately, the same moment the sign-in itself completes.

## [1.1.0] - 2026-09-07

Added **Grok (xAI)** as a 5th AI liner-notes provider, with a choice of
two sign-in methods:

- **API key** — a metered, pay-per-token key from xAI's own developer
  console, same shape as the existing NIM/OpenAI-compatible option.
- **Subscription** — sign in with a SuperGrok or X Premium+ subscription
  instead, via a device-code flow, no per-token billing. Unlike the
  ChatGPT option, this uses xAI's genuinely documented OAuth endpoint
  and its public API — no bundled CLI binary needed.

Pick either from a toggle in the new Grok card on the AI providers page
(user menu → Settings → AI providers, admin only). See
[KB §6](KB.md#6-configuring-ai-providers) for setup steps for both.

## [1.0.7] - 2026-09-07

Fixed a major bug: stopping playback and pressing Play again (same
station or a different one) could leave the now-playing metadata stuck
on "Connecting…" forever — audio played fine, but track info, AI liner
notes, and everything else driven by the metadata socket never came
back, and only a full page reload fixed it. Root cause: if that socket
happened to drop while playback was stopped (a proxy idle timeout, a
laptop sleep/wake cycle, a brief network blip), nothing ever reconnected
it — pressing Play only restarted the audio, not the metadata
connection. Play, and the Reconnect button, now actively check and
revive it if needed.

Also fixed a related bug that could show the "does not support
metadata" message on a station that actually does, if it happened to
send a real title once and then an empty one moments later — some
stations do this as an encoder quirk (confirmed live: Heart 70s (UK)).
A station that has proven it can send a real title is never reclassified
as unsupported.

## [1.0.6] - 2026-09-07

Fixed AI liner notes re-querying the AI provider every time you switched
back to a language (or provider) you'd already used for the current
track, even when a cached answer already existed — the panel would sit
on "Asking the AI provider…" and a real network call would fire, instead
of instantly showing the cached blurb. Switching languages/providers now
checks the cache first, the same way playing a fresh track already did;
the "Re-ask AI" button still always asks fresh, as intended.

## [1.0.5] - 2026-09-07

Fixed the station logo overlapping the now-playing panel's metrics row
in Hebrew, caught right after 1.0.4 shipped. The logo and a couple of
dropdown menus were pinned to a fixed physical side (`right`) instead
of a direction-aware one, so they didn't move to the mirrored side
along with the rest of the RTL layout. Both now flip correctly.

## [1.0.4] - 2026-09-07

Added Hebrew as the 15th UI/AI-liner-notes language — this app's first
right-to-left language. The whole interface now mirrors automatically
(text alignment, the volume slider, everything) when Hebrew is active,
and switches back instantly for every other language.

## [1.0.3] - 2026-09-07

Added Turkish as the 14th UI/AI-liner-notes language — same top-bar
language switcher as the other 13.

## [1.0.2] - 2026-09-07

1.0.1 shipped a fix for stations with no ICY metadata support at all, but
some real stations (confirmed live: TSF Jazz) implement ICY framing fully
— `icy-metaint` present and correct — yet never actually populate the
track title (`StreamTitle='';`, always empty). That's indistinguishable
from "no support" to a listener, but 1.0.1's fix didn't cover it, so
those stations were still stuck on "Connecting…" forever. The stream
proxy now recognizes a confirmed-empty title the same way it recognizes
no metadata support at all, and shows the same explanatory message.

## [1.0.1] - 2026-09-07

Fixed a real bug and a misleading UI state, both in the now-playing panel:

- **Metadata mix-up when switching stations quickly.** The audio-stream
  proxy connection for a station you just left could still be finishing
  up in the background and emit one more title/station update after you'd
  already switched — occasionally landing on the new station's display.
  Each stream connection is now tagged with its own generation id server
  side, so a straggler from an abandoned connection is dropped instead of
  overwriting the current one's metadata.
- **"Connecting…" no longer lies forever for stations with no ICY
  metadata.** Some stations simply never send a track title (no
  `icy-metaint` support) — the panel used to sit on "Connecting…"
  indefinitely, which reads as a failure. It now says up front that the
  station doesn't support metadata, once that's actually known.
- Added a **Reload app** button next to the theme toggle, as a quick
  recovery option if the player ever gets into a stuck state.

## [1.0.0] - 2026-09-07

First stable release. The app has been running in production
continuously since v0.1.1 and everything below is in daily use.

**What it does**

- Plays 104 curated stations across ten genres (classical, jazz,
  blues, country, rock, pop, focus, chill, funk, hip-hop), plus any
  stream URL you add, with 12 favourite slots per account.
- Shows live now-playing metadata pushed over a WebSocket, with AI
  liner notes about the artist and track — from OpenCode (bundled),
  Ollama, ChatGPT, or any OpenAI-compatible endpoint. Results are
  cached and shared, so the same track is never queried twice.
- Speaks 13 languages, in both the interface and the AI liner notes.
- Supports multiple accounts, admin-created, each with their own
  favourites, provider choice and display name — plus self-service
  password reset once email is configured.
- Includes an admin dashboard: who's listening and from where on a
  live map, full play history, and station/genre/listener stats.

**Notes for new installations**

- A reverse proxy with HTTPS is required — session cookies are set
  `Secure`. See the "Before you install" section in the README.
- The ChatGPT provider uses an unofficial sign-in mechanism and may
  stop working if OpenAI changes it. Every other provider is
  unaffected, and the app runs fine with none configured.

## [0.5.47] - 2026-09-07

Fixed the top bar overflowing on phones, which pushed the account menu
— and with it Settings and Sign out — off the right edge where it
couldn't be reached at all. On narrow screens the bar now sheds the
optional chrome (version number, language label, the "player"
sub-title) and keeps the account menu and theme toggle. Verified down
to 320px.

## [0.5.46] - 2026-09-06

Each AI provider on the settings page now has its own small mark
beside its name. Drawn inline in the same monoline style as the app's
other icons, so they inherit the page's ink and adapt to dark mode
with no extra work.

## [0.5.45] - 2026-09-06

Fixed .977 Jamz showing the logo of 97.9 JAMZ, an unrelated US FM
station — similar enough digits to fool the name check, so it's now
pinned to the correct one.

## [0.5.44] - 2026-09-06

Replaced Country Radio (CZ) with America's Country, a mainstream US
country station — the country genre had one Czech outlier among nine
American ones.

Fixed WSM 650 AM showing no logo: the image-search results were being
scanned too shallowly, and the first slots are routinely filled by
icon-library noise, so a valid logo further down was never reached.
103 of 104 stations now have a logo.

## [0.5.43] - 2026-09-06

Station logos can now fall back to a self-hosted SearXNG instance,
which finds logos for the stations nothing else could — 103 of 104
curated stations now have one, up from 95. Optional: set
MRADIO_SEARXNG_URL if you run one, otherwise nothing changes. See
KB.md § 8.

## [0.5.42] - 2026-09-06

Station logos that are only available flattened onto a white
rectangle (France Musique, and others) no longer show that box — the
white now blends into the panel so only the artwork shows. Applies in
light mode only, where it works; dark mode is unchanged.

## [0.5.41] - 2026-09-06

181.FM stations now use the broadcaster's own transparent logo instead
of the version flattened onto a white box.

Also fixed logo validation rejecting perfectly good images served
without a content-type header — it now checks the file's actual bytes
when the header is missing, which is what made the above possible.

## [0.5.40] - 2026-09-06

Added Wikipedia as a last-resort logo source, for stations that have
neither a directory logo nor one on their own site. It only accepts an
article whose title genuinely matches the station, so it stays quiet
rather than risking a similarly-named station's logo — TSF Jazz gains
its real logo this way.

## [0.5.39] - 2026-09-06

Much better station logos again: when the directory only offers a
blurry 16x16 favicon, the station's own website is now asked for the
logo it publishes for link previews. That's how 181.FM and 1.FM get
their real full-size logos instead of a fuzzy icon. 94 of 104 curated
stations show a logo.

Also fixed a lookup that could hang for over a minute on a handful of
stations, and stopped one station showing an unrelated broadcaster's
logo.

## [0.5.38] - 2026-09-06

Radio Paradise now streams at 320 kbps instead of 128.

Fixed and improved station logos: some stations showed no logo because
the directory had a homepage URL where the image should be (it passed
the reachability check but rendered as nothing), and others showed a
blurry site favicon even when a proper logo was listed alongside it.
Logos are now verified to actually be images, and real logos are
preferred over favicons.

## [0.5.37] - 2026-09-06

Centred the playback metadata vertically between the two divider lines
(it was sitting closer to the lower one), and made the station logo
bigger with tighter, even margins on all three sides.

## [0.5.36] - 2026-09-06

Shaved the station logo's size and surrounding padding further, all
evenly, to fit more compactly on smaller/phone screens — the logo now
also shrinks a bit more on narrow viewports so the station name has
more room before truncating.

## [0.5.35] - 2026-09-06

Reduced the gap below the metrics divider when a station logo is
showing — it was noticeably bigger than the top/right padding around
the logo. Also switched the logo's size and this spacing from
hardcoded pixel values to a single shared, relatively-sized token, so
they can't drift out of sync with each other again.

## [0.5.34] - 2026-09-06

Fixed an oversized gap above the playback metrics that 0.5.33
introduced when a station logo is showing — the metrics row was being
pushed down as a whole to make room for the logo. It now stays flush
under the header like normal; only the space below it (before its own
divider) grows to clear the logo, keeping equal padding on all three
of the logo's open sides.

## [0.5.33] - 2026-09-06

Fixed the station logo crashing into the playback-metrics divider
line right below it. The metrics row now gets a bit more clearance
when a logo is showing, so the logo has equal padding on its top,
right, and bottom sides — verified this time with a real rendered
screenshot instead of hand-computed measurements.

## [0.5.32] - 2026-09-06

Fixed unwanted empty space above the playback metadata that 0.5.31
introduced — growing the header to fit the bigger logo had pushed the
whole now-playing section down with it. The header stays its normal
compact height now; the logo (also made a bit bigger, 80px) overhangs
past it into its own space without displacing anything below.

## [0.5.31] - 2026-09-06

Made the station logo in the now-playing header much bigger (28px →
64px), and shortened the divider line under the header so it stops
before the logo's column instead of running behind it — the logo now
visibly overlaps into its own space below the line.

## [0.5.30] - 2026-09-06

Fixed both Venice Classic Radio stations (VCR Auditorium, VCR
Classica+) still showing no logo — the previous fix's fallback search
didn't try the part after the " | " separator, which is where the
real broadcaster name actually lives ("Venice Classic Radio", not the
"VCR Auditorium"/"VCR Classica+" prefix that only exists to tell the
two stations apart).

## [0.5.29] - 2026-09-06

Fixed several curated stations showing no logo icon even though a real
one exists — Radio-Browser's name search is exact-ish, so display
names like "VCR Auditorium | Venice Classic Radio Italia" or "Heart
70s (UK)" (built for readability, not for search) were missing real
indexed entries. The lookup now retries with the name progressively
simplified, with a safeguard against a short/generic word (like "VCR")
accidentally matching an unrelated station.

## [0.5.28] - 2026-09-06

Added ChatGPT to the AI providers settings page's description text —
it listed OpenCode, Ollama, and OpenAI-compatible endpoints but had
never been updated to mention ChatGPT since that provider shipped.
Fixed in all 13 languages plus README.md.

## [0.5.27] - 2026-09-06

Capitalized "OpenCode" consistently everywhere it's shown as a provider
name — the AI settings page, the player's provider dropdown (which was
showing lowercase "opencode"), and the docs. Literal binary/CLI/file
names (e.g. the `opencode` command, `bump-opencode.yml`) are left
lowercase since that's their real name.

## [0.5.26] - 2026-09-06

Fixed the AI settings page's status dots: opencode showed grey even
though it was actually enabled and working, because the dot was
derived from the (often-empty) text field instead of the real
configured state. All four dots now read from the same "enabled" data
the player's dropdown uses.

## [0.5.25] - 2026-09-06

Redesigned the AI providers settings page: each provider (ChatGPT,
opencode, Ollama, NIM) now sits in its own visually separated card with
a small status dot showing whether it's configured. Reordered the
cards — and the player's AI dropdown / automatic-fallback order — to
ChatGPT, opencode, Ollama, NIM, based on a real production comparison
across all four providers.

## [0.5.24] - 2026-09-06

Raised the ChatGPT/Codex provider's request timeout from 60s to 180s —
observed live response times of 23-70s (slower and more variable than
NIM/Ollama, since it's routed through OpenAI's subscription backend, not
a direct model endpoint), and a 60s ceiling risked silently dropping a
genuinely slow-but-successful response.

## [0.5.23] - 2026-09-06

Added ChatGPT/Codex subscription as a 4th AI provider — sign in with a
ChatGPT Plus, Pro, or Go subscription instead of an API key, from a new
"Connect with ChatGPT" button on the AI providers settings page. Uses
the same sign-in as the Codex CLI; unofficial and could stop working if
OpenAI changes it, but free to use if you already pay for ChatGPT. See
KB.md's "ChatGPT / Codex subscription" section for the full disclosure
before enabling.

## [0.5.22] - 2026-09-06

Fixed the listener map sometimes showing more dots than "Live now" —
the map previously always mixed live sessions with recent play history,
with no way to tell which was which. Added a second toggle (Live only /
Live + recent history) next to the Pins/Heatmap toggle, defaulting to
Live only so the map matches "Live now" out of the box. Also fixed the
map's history view being tied to whichever page the history table below
it happened to be scrolled to.

## [0.5.21] - 2026-09-06

Added Hip-Hop as a tenth curated genre, with 10 vetted stations (181.FM
- Old School HipHop/RnB, 181.FM - The Beat, 90s90s HipHop & Rap, 100 Hip
Hop and RNB FM, .977 Jamz, BBC Radio 1Xtra, All Underground Hip Hop
Radio, WEFUNK, Hot 108 Jamz, Top Urbano) — browsable under Genres like
every other category.

## [0.5.20] - 2026-09-06

Fixed Heart 70s (UK) in the default favorites lineup — it was set to
genre "other" instead of its correct "pop" (a mistake introduced in the
0.5.19 favorites reset). Fixed in the code (so future new accounts get
it right) and corrected live for the 6 accounts already migrated in
0.5.19, touching only that one field.

## [0.5.19] - 2026-09-06

One-time default-favorites reset: new accounts now start with a
refreshed 12-station lineup. Existing users' favorites were reset to
the same lineup via a standalone one-off script, run once — not a
recurring or automatic change.

## [0.5.18] - 2026-09-06

Station logos: the now-playing panel now shows the station's logo (when
one can be found via Radio-Browser) next to the station name. Resolved
logos are cached — including confirmed misses — so lookups only happen
once per station, and candidate favicon URLs are verified reachable
before being cached or shown.

## [0.5.17] - 2026-09-06

Pins mode on the listener map no longer scales marker size by session
count — it now uses a fixed-size marker matching the pulsing green dot
from the player's live-listener indicator. Size-based intensity now
lives only in Heatmap mode, where it belongs.

## [0.5.16] - 2026-09-06

Split the Analytics listener map's dual pin-size/heat-intensity encoding
into two dedicated views: a Pins mode (unchanged individual markers) and
a new Heatmap mode (via `leaflet.heat`), switchable with an instant
top-of-map toggle.

## [0.5.15] - 2026-09-06

Added Japanese as a thirteenth UI/AI-liner-notes language, alongside
English, Spanish, Italian, Portuguese, French, Russian, German, Greek,
Dutch, Danish, Swedish, and Norwegian (Bokmål) — switch instantly from
the top bar, same as the others.

## [0.5.14] - 2026-09-06

Added Norwegian Bokmål as a twelfth UI/AI-liner-notes language,
alongside English, Spanish, Italian, Portuguese, French, Russian,
German, Greek, Dutch, Danish, and Swedish — switch instantly from the
top bar, same as the others.

## [0.5.13] - 2026-09-06

Added Swedish as an eleventh UI/AI-liner-notes language, alongside
English, Spanish, Italian, Portuguese, French, Russian, German, Greek,
Dutch, and Danish — switch instantly from the top bar, same as the
others.

## [0.5.12] - 2026-09-06

Added Danish as a tenth UI/AI-liner-notes language, alongside English,
Spanish, Italian, Portuguese, French, Russian, German, Greek, and
Dutch — switch instantly from the top bar, same as the others.

## [0.5.11] - 2026-09-06

Added Dutch as a ninth UI/AI-liner-notes language, alongside English,
Spanish, Italian, Portuguese, French, Russian, German, and Greek —
switch instantly from the top bar, same as the others.

## [0.5.10] - 2026-09-06

Added Greek as an eighth UI/AI-liner-notes language, alongside
English, Spanish, Italian, Portuguese, French, Russian, and German —
switch instantly from the top bar, same as the others.

## [0.5.9] - 2026-09-06

Added German as a seventh UI/AI-liner-notes language, alongside
English, Spanish, Italian, Portuguese, French, and Russian — switch
instantly from the top bar, same as the others.

## [0.5.8] - 2026-09-06

Added Russian as a sixth UI/AI-liner-notes language, alongside English,
Spanish, Italian, Portuguese, and French — switch instantly from the
top bar, same as the others.

## [0.5.7] - 2026-09-06

Fixed the Analytics "Live now" table's status-dot column claiming a
large, fixed share of the table's width (a min-width rule meant for the
Users table's name column was leaking into every `.admin-table`,
including this one, where the first column is just a small dot) —
squeezing User/Station/Genre/Location/Elapsed into cramped, wrapping
columns. The dot column now sizes to its content; the other columns
get their space back.

## [0.5.6] - 2026-09-06

Replaced the "Add user" and "Edit profile" browser-native prompt
popups on the Users page with a proper in-page modal form. Same fields
as before (username/full name/email/temp password for Add user; full
name/email for Edit profile), now a real dialog with visible field
labels, a backdrop, Cancel/Save buttons, and Escape/backdrop-click to
close, instead of sequential `window.prompt()` dialogs.

## [0.5.5] - 2026-09-06

Fixed the PWA install prompt still offering the old app name after the
0.5.4 rebrand. 0.5.2's caching fix correctly stopped `index.html` from
being cached, but wrongly assumed every *other* static file was a
Vite-content-hashed, safe-forever asset — true for `/assets/*.js`/`*.css`,
but not for `manifest.webmanifest`, the favicon, or the PWA icons, which
Vite copies straight from `public/` under the same filename on every
build. Those were being cached for a full year, so a browser that had
already fetched the manifest kept quoting its old `name` field
indefinitely, even after uninstalling and trying to reinstall the app.
Only files actually under `/assets/` are cached immutably now; every
other static file (including `index.html`) always revalidates.

## [0.5.4] - 2026-09-06

Renamed the app's displayed brand text from "mradio" / "dial room" to
"mradio web" / "player" everywhere it appears — top bar, sign-in and
password screens, browser tab title, PWA/home-screen name. Styling
(serif brand mark, small mono subtitle) is unchanged, only the wording.

## [0.5.3] - 2026-09-06

Actually fixed the placeholder-text confusion this time — 0.5.1 only
changed the placeholder's *color*, not its wording, so the Email
settings page's Host field still showed a bare "smtp.gmail.com", which
happens to be the literal real value a Gmail user needs to type, making
an empty field look pre-filled no matter how it's colored. Placeholders
that could be mistaken for a real value now read "e.g. ..." (Email
settings' Host and Public URL fields, AI providers' Ollama Server URL
field).

## [0.5.2] - 2026-09-06

Fixed the previous release's placeholder-text fix appearing not to work
for some users — it genuinely was deployed correctly (verified directly
on the server), but `index.html` had no cache-control header, so a
browser that had already loaded the page before the update could keep
serving it from cache indefinitely, along with whatever CSS/JS it
referenced at the time. `index.html` now always revalidates
(`Cache-Control: no-cache`), while the actual hashed asset files
(`/assets/*.js`, `*.css`) — which get a new filename on every content
change — are now cached aggressively (`immutable, max-age=31536000`),
so future deploys are both guaranteed-fresh and faster to load.

## [0.5.1] - 2026-09-06

Two UX fixes to the new Email settings page, found via real use: (1)
clicking "Test" before "Save" now actually tests whatever is currently
typed into the form, matching how the AI providers page's test buttons
already work, instead of testing the last-saved (often empty)
configuration and giving a misleading "SMTP is not configured" error;
a genuinely-empty host now says "Enter a host and click Save before
testing" instead. (2) Placeholder text (e.g. the suggested
`smtp.gmail.com`) is now visibly greyed out and clearly distinguishable
from real typed values, instead of rendering close enough to normal
input text to look pre-filled.

## [0.5.0] - 2026-09-06

Added self-service "forgot password": from the sign-in screen, request
a reset link by email, click it, set a new password — no admin needed,
as long as outgoing email is configured and the account has an email
address set. New **Settings → Email (SMTP)** page (admin-only) lets the
admin configure any SMTP provider, with a first-class step-by-step
walkthrough for generating a Gmail App Password (not OAuth — a Google
"Sign in with Google"-style flow would need a restricted-scope security
review to send mail on someone's behalf, disproportionate for a
self-hosted app; an app password is Google's own recommended path for
this exact situation).

Reset links automatically point at whichever domain a listener actually
used to reach the app (via the request's forwarded-host header) — no
per-domain configuration needed if the app is reachable through more
than one address. An optional "Public URL" override exists as a
fallback. Reset tokens are single-use, expire after 1 hour, and the
forgot-password endpoint always returns the same response whether or
not the email is registered, so it can't be used to discover which
accounts exist.

## [0.4.2] - 2026-09-06

Fixed two layout bugs surfaced by longer display names with multiple
flag emoji (e.g. "Marco Dal Moro 🇮🇹🇺🇸"): the Users table's name column
had no minimum width and wrapped token-by-token; the top-bar user chip
had no size limit on the name and no explicit size on its chevron icon,
so a name that pushed the chip's line-height taller made the fully-round
pill balloon into a giant circle. Both now cap the name (ellipsis
overflow in the chip, natural wrap with a sane minimum width in the
table) and pin the chevron icon to a fixed size.

## [0.4.1] - 2026-09-06

Replaced the growing flat list of admin dropdown entries ("Users", "AI
providers", ...) with a single "Settings" entry that opens a hub page —
a card per section, each linking to the existing page. Users and AI
providers pages gained a "← Settings" breadcrumb to get back to the hub.
Groundwork for adding an "Email (SMTP)" section without the dropdown
growing indefinitely with every new admin feature.

## [0.4.0] - 2026-09-06

Added a `full_name` field to user accounts — a proper, emoji-capable
display name (e.g. "Marco 🎧") shown everywhere the raw login username
used to appear: the top-bar chip, and every identity column across
Analytics (Live now, Top listeners, Recent history). Falls back to the
username automatically when unset, so existing accounts are unaffected.
Also surfaced the existing-but-previously-unused `email` field in the
admin Users page. Both are admin-set for now, via the Users page's
create-user form and a new "Edit profile" action on each row.

Adding this field to `users` required extending this app's SQLite setup
for the first time to safely add a column to an already-shipped table
with real production rows — every prior schema change was either a
brand-new table or present since the very first commit. Verified
against a simulated pre-existing database (old schema, real rows) that
the migration applies cleanly, is idempotent on repeat runs, and
existing accounts/logins are undisturbed.

## [0.3.10] - 2026-09-06

Added French as a fifth UI/AI-liner-notes language, following the same
pattern as Italian and Portuguese: new `frontend/src/i18n/fr.ts`,
registered in `index.ts`'s `Language` type and `LANGUAGES` list, added
to `Config.language`'s union in `api/types.ts`, and to the backend's
`_VALID_LANGUAGES` (`routers/config.py`) and `_LANGUAGE_INSTRUCTIONS`
(`enricher.py`). README's language-support bullet updated to match.

Verified live: logged in, switched the top-bar language to Français,
and confirmed every screen (player, Analytics/Dashboard, admin user
menu) renders fully in French with no missing keys or English
fallback text.

## [0.3.9] - 2026-09-06

Follow-up to 0.3.8: the manifest covered Android/Chrome install, but
iOS Safari's "Add to Home Screen" doesn't fully honor the web app
manifest — it needs its own meta tags to launch as a standalone app
(instead of just opening Safari) and to show a clean name under the
icon. Added `apple-mobile-web-app-capable`,
`apple-mobile-web-app-status-bar-style`, and
`apple-mobile-web-app-title` to `index.html`. The 180×180
`apple-touch-icon.png` added in 0.3.8 was already the correct size for
this — no new icon assets needed.

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
