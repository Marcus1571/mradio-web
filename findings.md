# Findings

Research log for options considered but not (yet) built — one entry per
question researched, with the verdict and why. Not a full history;
`STATUS.md`/`CHANGELOG.md` cover what actually shipped. For the
distilled, currently-adopted per-provider AI strategy derived from this
research, see `AI.md` — this file stays raw evidence, `AI.md` is the
"what we decided" layer.

## AI provider fact-check battery (researched 2026-09-11)

Resumed the parked veridicity investigation. Goal: move past anecdotal
spot-checks and measure both mechanical reliability (production logs) and
content accuracy (manual fact-check) for the providers that looked
problematic.

### Production mechanical snapshot (from LT `ai_requests`)

Run with `MRADIO_DB_PATH=/tmp/mradio-web-lt.db python -m app.ai_stats` on a
copy of the production DB taken 2026-09-11:

| provider | success_rate | median | p90 | n |
|---|---|---|---|---|
| mistral | 100% | 1,741ms | 2,297ms | 17 |
| grok | 93% | 5,141ms | 7,675ms | 14 |
| openrouter | 100% | 5,998ms | 21,322ms | 5 |
| opencode | 100% | 21,141ms | 61,259ms | 14 |
| gemini | 71% | 11,629ms | 25,695ms | 5 |

Mechanical winners: Mistral (fast + never fails), OpenCode (slow but always
returns). Gemini is the only provider with a visible failure rate in live
traffic right now.

### Structured battery

23 calls across 6 providers × 4 tracks chosen to stress different failure
modes: a canonical classical work (`beethoven9`), a canonical jazz album
(`kindofblue`), a real but less-documented blues recording
(`muldaur_empty_bed` — Maria Muldaur's version of "Empty Bed Blues"), and an
obscure live cover (`obscure_trap` — Kora Jazz Trio, "Chan Chan"). Prompts
used the same `apply_provider_rules()` hardening the app uses in production.

| provider | OK | median | notes |
|---|---|---|---|
| mistral | 4/4 | 3,124ms | Fast, never empty; invented vague filler on the obscure track. |
| gemini | 4/4 | 7,664ms | Falsely dated Muldaur's "Empty Bed Blues" to 1978 Los Angeles. |
| openrouter | 4/4 | 34,051ms | Returned literal `"User Safety: safe"` for Muldaur; misdated/misattributed `obscure_trap`. |
| opencode | 3/4 | 24,071ms | `kindofblue` timed out at 90s; otherwise accurate, including correct 1928 Bessie Smith origin for "Empty Bed Blues". |
| ollama_gptoss | 4/4 | 29,500ms | Correctly declined on obscure track; otherwise acceptable. |
| ollama_qwen3 | 3/3* | 57,784ms | *obscure_trap not reached before the run was killed; falsely placed "Empty Bed Blues" on `Midnight at the Oasis` (1974). |

### Fact-check verdicts

- **Beethoven 9 / Kind of Blue**: every provider that returned output got
the well-documented facts broadly right. Minor issue: OpenRouter's
`kindofblue` listed Wynton Kelly as a generic feature without noting he
played only on "Freddie Freeloader."
- **Maria Muldaur — "Empty Bed Blues"**: confirmed against AllMusic/Discogs
— Muldaur's recording appears on the 2001 album *Richland Woman Blues*
(Stony Plain). **Gemini** invented "recorded in 1978 in Los Angeles."
**Mistral** strongly implied a 1970s origin. **Ollama qwen3** claimed it was
a 1977 track from *Midnight at the Oasis*. **OpenRouter** returned `"User
Safety: safe"`. **OpenCode** correctly identified the song as a Bessie
Smith standard and avoided inventing a date for Muldaur's version.
- **Kora Jazz Trio — "Chan Chan" (live cover)**: Chan Chan was written by
Compay Segundo in 1984; the Buena Vista Social Club recording is from 1997.
**OpenRouter** called it "a cover of Buena Vista Social Club's 1996
recording" — wrong year, wrong primary attribution. **Gemini** correctly
identified it as a Chan Chan cover. **Mistral** emitted generic filler.
**Ollama gpt-oss** correctly declined. **OpenCode** gave detailed, correct
context about both Kora Jazz Trio and the original.

### Mechanical bug found

`_llm_openai_compatible()` in `backend/app/providers.py` crashes with
`AttributeError: 'NoneType' object has no attribute 'strip'` when a provider
returns `"content": null` instead of a string. Observed on OpenRouter
reasoning-loop outputs. The fix is to coerce `None` content to `""` before
`.strip()`.

### NIM default model still EOL

Confirmed the configured default `minimaxai/minimax-m3` returns HTTP 410.
Other models on the test account either 404'd or hung. NIM remains
non-functional independent of prompt quality.

### Implications for strategy

- **Speed ≠ accuracy**: Mistral is the fastest and most reliable
mechanically, but still fabricates on obscure tracks even with categorical
hardening. The hardening helped on famous works; it is not enough when the
model has no real source to draw on.
- **Gemini's production failures (29%) are the immediate reliability
problem**, separate from its accuracy problem.
- **OpenCode is the only provider that both declines *and* gets obscure
facts right**, but its latency makes it unsuitable as a default for every
request.
- **Grounding is the most promising next step**: the existing
`backend/app/wiki.py` already fetches article intros via MediaWiki and
throws away the text. Injecting that snippet before the LLM call would give
every provider (especially the fast, fallible ones) a shared retrieved
anchor. See `AI.md` for the adopted-strategy view.

## AI provider fact-check battery — grounded re-run (researched 2026-09-11)

Implemented Wikipedia snippet grounding (`backend/app/wiki.py` now returns
article intros, `backend/app/enricher.py` prepends them for
`_CATEGORICAL_PROVIDERS`) and re-ran the same 4-track structured battery.

### What changed

- `backend/app/wiki.py`: in-memory 1-hour cache, 1-second global API throttle,
  429/5xx retry, title-only search tier first (artist+title confused
  Wikipedia's search), strict surname-aware relevance, and scoring that
  boosts exact title matches (+1000) and music markers (+200) while
  penalizing disambiguation pages (-300).
- `backend/app/enricher.py`: `_ask()` now calls `wiki.ground(artist, title,
  surname)` for `_CATEGORICAL_PROVIDERS` and injects the excerpt before the
  LLM prompt.
- `backend/app/settings.py`: NIM default model switched from EOL
  `minimaxai/minimax-m3` to `meta/llama-3.2-11b-vision-instruct`.
- `backend/app/providers.py`: `_llm_openai_compatible()` coerces `None`
  content to `""` before `.strip()`.

### Grounding resolution accuracy

All four test tracks resolved to the intended article:

| track | resolved article |
|---|---|
| Beethoven 9 | Symphony No. 9 in D minor, Opus 125 (Beethoven) |
| Kind of Blue | Kind of Blue |
| Empty Bed Blues | Empty Bed Blues |
| Chan Chan (live cover) | Chan Chan (song) |

One intermittent failure mode was fixed: Wikipedia search for "Kind of Blue"
was returning "Kind of Blue (TQ album)" because the music-marker bonus
outweighed the exact-title match; exact matches now get a +1000 bonus.

### Grounded battery results (28 calls, 7 provider configs)

| provider | OK | median | notes |
|---|---|---|---|
| mistral | 4/4 | 1,878ms | All grounded; still generic on obscure track but no invented dates. |
| gemini | 4/4 | 2,680ms | All grounded; no repeat of the 1978 Los Angeles fabrication on Muldaur. |
| openrouter | 2/4 | 29,376ms | `muldaur_empty_bed` and `obscure_trap` returned empty; well-known tracks improved. |
| nim | 4/4 | 6,520ms | All grounded after mapping the battery's "nim" label to production's "openai" rules; Kind of Blue answer explicitly cites Coltrane/Adderley/Evans. |
| opencode | 4/4 | 12,535ms | Not grounded (plain taxonomy); still accurate, now also returns within timeout. |
| ollama_gptoss | 4/4 | 25,570ms | All grounded; obscure track no longer a clean decline but factually anchored. |
| ollama_qwen3 | 3/4 | 46,424ms | All grounded; `muldaur_empty_bed` still timed out, obscure track now correct. |

### Fact-check verdicts after grounding

- **Beethoven 9 / Kind of Blue**: every provider that returned output gave
  factually correct, grounded answers. NIM's grounded Kind of Blue reply
  named the 1959 release and the correct key sidemen.
- **Maria Muldaur — "Empty Bed Blues"**: Gemini, Mistral, NIM, and Ollama
  gpt-oss no longer invented a date/venue for Muldaur's version; grounded
  answers stayed close to the Wikipedia excerpt (Bessie Smith origin, 1928).
  OpenRouter and Ollama qwen3 still failed mechanically (empty/timeout).
- **Kora Jazz Trio — "Chan Chan" (live cover)**: grounded answers correctly
  attributed the song to Compay Segundo (1984). OpenRouter still failed on
  this track.

### Implications

- Wikipedia grounding eliminated the most egregious fabrications on the
  less-documented tracks for the providers that received it.
- OpenRouter's remaining failures are mechanical (empty response / timeout),
  not factual; its free auto-router is still unreliable end-to-end.
- Opencode remains accurate without grounding, confirming it is a different
  class of system (likely with its own retrieval path). It is still too slow
  for the default hot path.
- The next veridicity improvement is probably provider-specific: Gemini's
  native `google_search` tool, a stronger OpenRouter model pin, or a
  self-consistency critic pass — but those are out of scope for this
  grounding-focused iteration.

## Additional free AI providers for liner-notes enrichment (researched 2026-09-07)

User asked whether other free AI options exist beyond opencode/Ollama/NIM/
ChatGPT/Grok. Researched current (2026) free tiers rather than assuming
stale pricing.

**Key fact that shapes all of these**: mradio-web already has a generic
OpenAI-compatible provider slot (the "NIM, etc." bubble in AI providers —
base URL + model + API key, currently defaulting to NVIDIA NIM's hosted
endpoint). Any provider below that exposes an OpenAI-compatible
`chat/completions` endpoint works **today, with zero code changes** —
just repoint that one bubble's base URL/key. Only worth a dedicated
bubble (own fields, own PROVIDERS entry, i18n, etc. — the Grok/ChatGPT
treatment) if the user wants it available *alongside* NIM rather than
replacing it.

Candidates found:

- **Google Gemini (AI Studio)** — **built 2026-09-08, see MEMORY.md's
  "Google Gemini added as 6th AI provider" section.** Genuinely free,
  permanent tier (not a trial), no credit card required, available to
  every account (not admin-only, unlike ChatGPT/Grok). As of April
  2026 only Flash-family models (Flash, Flash-Lite) remain on the free
  tier; Pro models moved behind billing. OpenAI-compatible endpoint at
  `https://generativelanguage.googleapis.com/v1beta/openai/`. Rate
  limits are modest (roughly 10-15 RPM, up to 1,000 RPD on Flash) but
  comfortably enough for this app's one-track-at-a-time enrichment
  pattern.
- **Groq** — **checked live 2026-09-08, NOT actually free — struck
  from consideration.** Widely-repeated "free tier, ~1,000 req/day"
  claims (including this entry's own original wording) turned out to
  be stale/wrong. A real API key's `GET /v1/models` response shows
  every currently-available model with real, non-zero per-token
  pricing (e.g. `openai/gpt-oss-120b` at $0.15/$0.60 per 1M tokens).
  The models the free-tier claims were actually based on
  (`llama-3.3-70b-versatile`, `llama-3.1-8b-instant`) aren't in the
  live model list at all anymore — Groq's own docs page
  (console.groq.com/docs/models) now marks both "Enterprise"/
  "ContactSales", i.e. pulled from self-serve/free access entirely.
  Groq is a real, fast, OpenAI-compatible **paid, metered** API (same
  shape as NIM) — not a free-for-everyone option like Gemini. Could
  still be added the way NIM/OpenAI are (admin brings their own paid
  key, not admin-only-restricted since it's not a personal
  subscription) if ever wanted, but doesn't belong on this "free
  providers" list.
- **Cerebras** — **checked 2026-09-08, disqualified — struck from
  consideration.** The earlier "possible payment-method requirement"
  flag turned out correct: as of August 2026, Cerebras ended its
  no-card free tier. New accounts get $5 in free credits, but only
  after adding a **verified payment method** — API access stays
  inactive without one. Breaks this list's whole premise ("no credit
  card needed"), so not pursued further (would need a real card on
  file just to get a key to verify, defeating the point). Otherwise a
  real, fast, OpenAI-compatible API (`https://api.cerebras.ai/v1`) —
  same category as NIM/Groq (paid/metered with a trial credit), not a
  free-for-everyone option.
- **OpenRouter** — **built 2026-09-08, see MEMORY.md's "OpenRouter
  added as 7th AI provider" section.** Checked live before building
  (unlike the Groq research this session corrected): `GET /v1/models`
  is public/unauthenticated and shows ~19 genuinely free (`:free`
  suffix, `"prompt": "0", "completion": "0"`) models; no card needed to
  sign up (confirmed via the user's own successful signup); a real
  authenticated `POST /chat/completions` against `openrouter/free`
  (OpenRouter's own free-model auto-router) returned the correct JSON
  at `cost: 0` in the standard `choices[0].message.content` shape — no
  new request/response code needed, reuses the existing
  `_llm_openai_compatible()` helper unmodified. One real gotcha: unlike
  NIM/OpenAI, OpenRouter's `GET /models` doesn't validate the key (it's
  public), so the shared `_test_openai_compatible()` test helper
  doesn't work here — needed a dedicated `_test_openrouter()` that
  makes a real completion call instead. Free tier: 50 requests/day (no
  spend), 1,000/day permanently once $10 has ever been spent.

**Verdict**: Gemini built 2026-09-08 (own dedicated bubble, not
admin-only). Groq checked live 2026-09-08 and struck — not actually
free anymore (models pulled from self-serve, real per-token pricing on
everything left). Cerebras checked 2026-09-08 and struck — now
requires a card on file to activate API access at all, breaking the
"no card needed" premise. OpenRouter checked live 2026-09-08 and
built — genuinely free, no card, verified end-to-end before shipping.
This list is now fully resolved: 1 of 3 remaining candidates (Groq,
Cerebras, OpenRouter) actually qualified.

**How to apply if revisited**: NIM's OpenAI-compatible bubble can still
be repointed at Groq's or Cerebras's paid endpoints directly (base URL
+ key, Test button, no code change) if a metered/paid provider is ever
wanted alongside the free ones — they just don't belong on *this* free-
providers list. For any future free-tier candidate, follow the
OpenRouter/Gemini build pattern: verify live with a real key (`GET
/models` + at least one real completion) before writing any code, not
just a docs/blog-summary pass — that live-check step is what caught
Groq's and Cerebras's status changes this session, which the original
research (written from summaries, not live checks) had gotten wrong or
only half-flagged.

## Spotify per-user "like to playlist" integration (researched 2026-09-11)

User request: investigate whether mradio-web can integrate with Spotify
the way SoundHound/Shazam-style apps do — a logged-in user clicks a star/
heart while a track is playing, and that track lands in a personal
Spotify playlist named "mradio-web". This must be per-user, not a single
admin account like the AI provider subscriptions, configurable per user
in Settings, and exposed as an obvious shortcut in the player UX.

### What the Spotify Web API actually supports

The official Spotify Web API can do everything this feature needs:

- **Create a playlist for the authenticated user:**
  `POST /v1/me/playlists` with body `{ "name": "mradio-web", "public": false, ... }`.
  Requires scope `playlist-modify-public` or `playlist-modify-private`.
- **Add tracks to a playlist:**
  `POST /v1/playlists/{playlist_id}/tracks` with body `{ "uris": ["spotify:track:..."] }`.
  Up to 100 URIs per call. Same scopes as above.
- **Search for a track from artist + title:**
  `GET /v1/search?q=track:<title>+artist:<artist>&type=track&limit=5`.
  Returns `tracks.items[].uri`, which is the value needed for the add
  call.
- **User profile:**
  `GET /v1/me` returns the user's `display_name`, useful for showing
  "Connected as …" in Settings.

This is *not* the same as Shazam's audio fingerprinting — mradio-web
already knows the track from ICY metadata. The user-facing behavior
("tap once, song appears in playlist") is the same; the implementation
is "search by metadata + add to playlist" rather than "identify audio +
add to playlist".

### OAuth flow choice

Spotify requires per-user authorization. Two flows fit:

1. **Authorization Code flow (server-side).**
   - Backend holds the `client_secret`.
   - Redirect user to `https://accounts.spotify.com/authorize` with
     `client_id`, `response_type=code`, `redirect_uri`, `scope`, and
     `state`.
   - Callback lands on the backend at a fixed route like
     `/api/spotify/callback`; backend exchanges the code for access +
     refresh tokens via `POST /api/token` using Basic auth.
   - Best fit for mradio-web: the backend is a trusted server that can
     keep a secret, and token refresh can happen server-side.

2. **PKCE flow.**
   - Designed for clients that cannot safely store a secret, but works
     fine server-side too.
   - Same endpoints, plus a `code_challenge`/`code_verifier` pair.
   - Slightly more modern and removes any need for a `client_secret` at
     all.

For a self-hosted backend like LT, **Authorization Code flow is the
natural choice**: it matches the existing Grok/Codex OAuth patterns in
the codebase (`backend/app/grok_oauth.py`, `backend/app/codex_oauth.py`)
and lets the backend refresh tokens without involving the frontend.

### Required scopes

- `playlist-modify-private` — create and edit private playlists.
- `playlist-modify-public` — only if we want to allow public playlists.

Recommended: request `playlist-modify-private` by default and create the
playlist as `public: false`. This avoids surprising users by publishing
what they are listening to. We can add an opt-in "public playlist" toggle
later and request the extra scope only then.

### Per-user token storage

Access tokens expire in `expires_in` seconds (typically 3600). Refresh
tokens are long-lived. This means we need to persist, per user:

- `access_token`
- `refresh_token`
- `scope`
- `expires_at`
- the created `playlist_id`

Where to store it:

- **New DB table (recommended).** A dedicated `spotify_tokens` table with
  `user_id PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE` keeps
  tokens out of plain JSON, enforces relational integrity, and follows the
  existing `sessions`/`password_resets` pattern in `backend/app/db.py`.
- **Encrypted at rest.** The refresh token is a high-value credential.
  At minimum it should be encrypted with a key from env (e.g. Fernet from
  `cryptography`) before going into SQLite. The codebase currently does
  not encrypt `codex_settings.json`/`grok_settings.json`, so this would be
  a small step up in security hygiene.

UX preferences (whether Spotify integration is enabled, playlist public/
private, custom playlist name) can live in the existing per-user
`config.json` (`backend/app/userdata.py`) — they are not secrets.

### Track resolution from ICY metadata

The player already exposes `state.artist` and `state.title`
(`frontend/src/components/NowPlayingPanel.tsx`). The backend can search:

```
GET https://api.spotify.com/v1/search
  ?q=track:Empty%20Bed%20Blues%20artist:Maria%20Muldaur
  &type=track&limit=5
```

Then take the first result's `uri` and call the add-tracks endpoint.

Open questions here:

- What if the search returns nothing? (silent skip, toast, or log?)
- What if the first result is wrong? (Spotify does not expose a perfect
  match signal; we could compare artist/title similarity heuristically.)
- ICY titles often include extra text like "(Remastered)" or "feat. X";
  stripping parentheticals before searching may improve hit rate.

### Playlist creation and idempotency

On first OAuth connect:

1. Exchange code for tokens.
2. Optionally call `GET /v1/me/playlists` to see if a playlist named
   "mradio-web" already exists (e.g. from a previous connect).
3. If not found, `POST /v1/me/playlists` to create it.
4. Persist the resulting `playlist_id`.

If the user deletes the playlist on Spotify later, add-track calls will
return 404/Not Found. We should detect that and recreate the playlist on
the next connect or next like action.

### Rate limits

Spotify uses a rolling 30-second window. Exceeding it returns HTTP 429
with a `Retry-After` header. Since a like is user-initiated and rare,
this is unlikely to bite in normal use, but the backend should still
honor `Retry-After` and surface a brief "try again in N seconds" message
rather than fail silently.

### UI/UX design

**Settings page:**

- Add a new "Spotify" card to `SettingsPage.tsx` (or a section inside a
  new per-user settings area if Settings ever splits admin vs. personal).
- Inside it:
  - "Connect Spotify" button when disconnected.
  - When connected: show Spotify display name, a "Disconnect" button, and
    a "Public playlist" toggle (default off).
  - Optional: let the user rename the playlist (default "mradio-web").

**Player shortcut:**

- Add a star/heart icon button to `NowPlayingPanel.tsx`, near the track
  title, only visible when a track is playing and the current user has
  connected Spotify.
- On click: POST to backend, show a brief "Added" / "Not found" /
  "Failed" indicator.
- Disabled state while the request is in flight.

### Architecture fit with current codebase

- **New backend module:** `backend/app/spotify.py` — low-level API calls
  (auth URL, token exchange, refresh, search, create playlist, add track).
- **New router:** `backend/app/routers/spotify.py` — `/api/spotify/auth`,
  `/api/spotify/callback`, `/api/spotify/disconnect`,
  `/api/spotify/status`, `/api/spotify/like`.
- **New settings page:** `frontend/src/pages/SpotifySettingsPage.tsx`.
- **Frontend hook:** `frontend/src/hooks/useSpotify.ts` for status and
  like action.
- **Register router** in `backend/app/main.py`.
- **i18n:** add keys to `frontend/src/i18n/en.ts` (and ideally the other
  language files, or fall back to English).

This mirrors the existing Grok/Codex OAuth routers and the per-user
`config.json` pattern, so it slots in cleanly.

### Security considerations

- `client_id` and `client_secret` must be configured by the admin. They
  can live in env vars or `settings.json` (the latter already stores API
  keys redacted in the UI).
- The redirect URI must be registered exactly in the Spotify app
dashboard. For LT that would be something like
  `https://mradioweb.legba.myddns.rocks/api/spotify/callback`.
- `state` parameter in the authorize URL is required for CSRF protection.
- Tokens should be encrypted at rest.
- Disconnecting must delete tokens from the DB, not just hide the UI.

### Decisions made

User confirmed (2026-09-12):

1. **Playlist visibility:** private.
2. **Playlist name:** fixed `"mradio-web"`.
3. **Search miss behavior:** if Spotify cannot find a reasonable match
   from the ICY metadata, stop — no manual search, no fallback scraping.
   Some tracks (especially obscure classical recordings) simply won't be
   on Spotify.
4. **Duplicate handling:** skip if the track is already in the playlist.
5. **Star/heart is a toggle:** clicking an empty icon adds the track;
   clicking a filled icon removes it from the playlist.
6. **Filled state reflects playlist membership:** if the currently
   playing track was added a month ago, the icon should already be filled
   when the track plays again. mradio-web must "know".

### Open decision #5: encrypt tokens at rest or not?

The remaining open question is whether to encrypt the Spotify refresh
**token in the database.** Two outcomes:

- **Plaintext (match current OAuth files).**
  - `grok_settings.json` and `codex_settings.json` already store OAuth
    tokens unencrypted in `/data`. Storing Spotify refresh tokens the same
    way keeps the code simple and consistent.
  - Risk: anyone with filesystem access to the server (or a backup of
    `/data/mradio.db`) can steal refresh tokens and interact with users'
    Spotify accounts until those users revoke access in Spotify's
    dashboard.

- **Encrypted at rest.**
  - Encrypt refresh tokens before writing to SQLite, decrypt on read.
    Access tokens can stay plaintext because they expire quickly.
    `cryptography.fernet` is the standard small-Python-dependency choice.
  - The encryption key comes from an env var (e.g.
    `MRADIO_SPOTIFY_TOKEN_KEY`). If the key is lost, all stored Spotify
    connections become useless and users must reconnect — same as losing
    any encryption key.
  - Risk: slightly more code, one more env var to set on deploy.

**Recommendation:** encrypt at rest. It is a small, one-time cost and is
strictly safer than the current OAuth files. We can add the same
encryption to `grok_settings.json`/`codex_settings.json` later if wanted,
but Spotify is the right place to start because its tokens grant
persistent playlist-write access.

### The "executive decision" matching algorithm

ICY metadata gives us three fields:

- `artist` — usually composer for classical, performing artist for pop/rock/jazz.
- `title` — work title, song title, or movement name.
- `performer` — optional parenthetical content, e.g. `"(Berlin Philharmonic / Herbert von Karajan)"`.

The challenge: a single search query often returns many versions of the
same recording (original album, "Remastered", "Greatest Hits",
compilation, different markets). For classical it is worse: the same
work appears under dozens of recordings by different orchestras and
soloists. We need an algorithm that picks one and moves on.

#### Step 1 — build candidate queries

Run one or more `GET /v1/search?q=...&type=track&limit=50&market=<user_market>`
calls and merge the results:

| Case | Query |
|---|---|
| Pop/rock/jazz with clear artist | `track:"<title>" artist:"<artist>"` |
| Classical with composer + work, no performer | `track:"<title>" artist:"<artist>"` |
| Classical with performer present | `track:"<title>" artist:"<performer>"` and also `track:"<title>" artist:"<artist>"` |
| Title has parenthetical fluff | also try `track:"<stripped_title>" artist:"<artist>"` |

`limit=50` is the API maximum for a single search call. We only need the
first page — the goal is "good enough," not exhaustive.

#### Step 2 — normalize and deduplicate by ISRC

Each returned track has `external_ids.isrc`. The ISRC is the industry
identifier for a specific sound recording: the same take released on
different albums normally shares the same ISRC. Group candidate tracks by
ISRC and keep only one representative per ISRC.

If a track has no ISRC (rare but possible), keep it keyed by its Spotify
`id` instead.

#### Step 3 — score each group

For each representative track, compute a score from these signals:

1. **Title similarity (highest weight).**
   - Exact match after normalization (lowercase, remove "(Remastered)",
     "(Live)", "(feat. ...)", etc.) → big bonus.
   - Track name contains the ICY title or vice versa → medium bonus.
   - Token overlap (Jaccard or simple word overlap) → small bonus.

2. **Artist/performer presence.**
   - ICY `artist` appears in the track's `artists` list → bonus.
   - ICY `performer` (stripped of parentheses) appears in `artists` or
     `album.artists` → bonus, especially for classical.
   - For classical, prefer tracks whose artist list includes an
     orchestra/conductor/soloist matching the ICY performer if one is
     present.

3. **Album type preference.**
   - `album.album_type`: prefer `album` over `single` over `compilation`.
     This is the main tool for the "Sting on original album vs. Greatest
     Hits" problem: pick the original studio album unless another signal
     strongly contradicts it.

4. **Popularity tiebreaker.**
   - Among equally-scored candidates, pick the one with the higher
     `popularity` (0–100). This nudges the choice toward the
     canonical/currently-available version without overriding metadata
     fidelity.

5. **Market availability.**
   - Always pass the user's `market` parameter. If Spotify relinks the
     track, respect it. If the returned track has `is_playable: false` and
     no relink, penalize or drop it.

#### Step 4 — threshold

Accept the top-scoring track only if its score is above a threshold. The
threshold is intentionally conservative: **a wrong track in the playlist
is worse than no track at all.** If nothing crosses the threshold,
return "not found" and the UI shows a brief "not on Spotify" indicator.

Example concrete scoring (these numbers can be tuned with real data):

```text
base = 0
title exact normalized match       +100
title contains / contained-by      + 40
artist token match                  +30
performer token match               +40
album type album                    +20
album type single                   +10
album type compilation               +0
popularity > 60                     +10
is_playable false                   -50

accept if score >= 80
```

#### Step 5 — cache the chosen URI

Cache the mapping `raw_title → spotify_uri` in memory or in the shared
`trivia_history`-style cache. If the same ICY string appears again, we
can reuse the previous decision instead of re-searching. This also makes
the "filled star" check cheap.

### Playlist membership and the filled-star state

To know whether the currently-playing track is already in the
"mradio-web" playlist, the backend needs a copy of the playlist contents.
Options:

1. **Fetch the playlist on demand when the track changes.**
   - `GET /v1/playlists/{playlist_id}/tracks` with pagination (max 50 per
     call). For a playlist that grows to hundreds of tracks, this can be
     several API calls per track change — slow and rate-limit unfriendly.

2. **Maintain a local mirror of the playlist in SQLite (recommended).**
   - Every time we successfully add a track, store `(user_id,
     spotify_track_uri, added_at)` in a new table.
   - On "connect", sync the full playlist once from Spotify and overwrite
     the local mirror.
   - On each add/remove, update both Spotify and the local mirror.
   - The "is this track already liked?" check then becomes a cheap SQL
     query using the URI we resolved from the ICY metadata.
   - If the user edits the playlist directly in Spotify, the mirror will
     drift until the next sync. We can mitigate by re-syncing on each
     Spotify operation and optionally on a schedule.

**Recommended:** local mirror. It makes the filled-star state fast and
reliable, and it gives us an easy audit log of what was liked when.

### Removal implementation

Removal uses `DELETE /v1/playlists/{playlist_id}/tracks` with body:

```json
{ "tracks": [{ "uri": "spotify:track:..." }] }
```

Spotify removes *all* occurrences of that URI in the playlist. Since we
skip duplicates on add, there should normally be only one occurrence.
After a successful remove, update the local mirror and clear the
filled-star state.

### Updated verdict

**Still feasible, now with a concrete design.** The hard part is not the
OAuth flow — it is the track-matching executive decision. The proposed
algorithm uses ISRC deduplication, metadata scoring, album-type
preference, and a conservative acceptance threshold to pick one Spotify
recording and live with it. A local playlist mirror makes the filled-star
state fast and supports toggle removal.

**Remaining blockers before coding:**

- Confirm the encryption choice (recommendation: encrypt refresh tokens).
- Decide whether the user's Spotify `market` should be auto-detected from
  the token's `country` field or configured by the admin/user.
