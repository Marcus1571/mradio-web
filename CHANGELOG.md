# Changelog

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
