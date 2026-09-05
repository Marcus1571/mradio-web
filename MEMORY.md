# mradio-web — project memory

A current-state snapshot, not a rules file — read this once to pick up
where the project stands without reconstructing it from `git log`. Update
it when the state changes; it's meant to stay short enough to actually be
read, not a full history (that's what commit messages and `KB.md` are for).

## What this is

Full rewrite of [mradio](https://github.com/Marcus1571/mradio) (a terminal
radio player, Python stdlib + mpv) as a self-hosted, multi-user web app —
not a wrapper around the terminal app. Read `README.md` for the pitch,
`KB.md` for deployment. This file is "why is the code shaped this way."

## Status

- **v0.1.1 tagged and released, not pre-release.** `docker compose build
  && docker compose up` has now been run end-to-end for real (2026-09-05,
  on LT/UNRAID via Tailscale SSH) — the sandbox limitation that blocked
  this for v0.1.0 (couldn't reach Docker Hub's blob CDN) doesn't apply
  outside that sandbox. Deployed behind Nginx Proxy Manager at
  `mradioweb.legba.myddns.rocks`, logged in, played a stream, got AI
  liner notes via opencode — all confirmed working, not just built.
- Merged to `main` via PR #1. The `claude/hallmark-skills-package-81d0hb`
  branch it was built on is now just history — develop from `main` going
  forward.

## Local development

Confirmed working in-session (not theoretical) — this exact setup is how
the whole app was verified before Docker existed at all.

Backend:

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
MRADIO_DATA_DIR=./data uvicorn app.main:app --reload --port 8000
```

Bootstraps `admin`/`mradio` into `./data/mradio.db` on first run (or set
`MRADIO_ADMIN_USERNAME`/`MRADIO_ADMIN_PASSWORD` before that first run).

Frontend (separate terminal):

```bash
cd frontend
npm install
npm run dev
```

`vite.config.ts` already proxies `/api` (HTTP and WebSocket) to
`127.0.0.1:8000`, so open `http://localhost:5173` and it talks to the
backend above with no extra config. Session cookies are `Secure`, which
normally means HTTPS-only — `http://localhost` specifically gets a
same-origin exception in Chrome/Firefox, confirmed working via a real
Playwright run against this exact setup, so plain `npm run dev` logs in
fine. Anything other than `localhost` (a LAN IP, a different hostname)
won't get that exception and needs real HTTPS.

`npm run build`, `npx tsc -b`, and `npm run lint` (oxlint) are the checks
actually run during the build — zero errors as of the last commit. Lint
has a handful of benign warnings (`set-state-in-effect` on standard
fetch-on-mount hooks, a hook/component co-export in `useAuth.tsx`) that
were reviewed and left alone on purpose, not overlooked.

## Architecture decisions worth knowing (and why)

- **No self-update mechanism.** mradio's biggest chunk of complexity
  (background thread polling the GitHub releases feed, downloading and
  swapping its own script) is gone entirely. A container has no business
  self-modifying its own image; `git pull && docker compose build` is the
  update path. This also means **GitHub Releases are decorative here** —
  nothing in the app reads them, unlike mradio where every release had to
  exist or the self-update check would never see it.
- **No mpv, no server-side audio.** LT is headless. Playback moved to the
  browser's own `<audio>` element. ICY "now playing" metadata, which mpv
  used to hand over via its IPC socket, is now parsed directly out of the
  proxied stream bytes (`backend/app/icy.py`).
- **Every station goes through `GET /api/stream`, not just HTTP-only
  ones.** Browsers silently block HTTP audio from an HTTPS page; the fix
  is a uniform proxy so there's one code path, not per-station branching.
  It also carries an SSRF guard (`backend/app/routers/stream.py`) — the
  proxy will fetch any user-supplied URL, same as mradio's own "add a
  stream" feature, but this now runs server-side with LAN access, so it
  refuses private/loopback/link-local targets.
- **Multi-user is the fundamental fork from mradio.** mradio assumed one
  person, one machine, flat JSON files. This app has real accounts
  (SQLite, PBKDF2 password hashing, server-side sessions — not JWT,
  chosen specifically so a session can be revoked outright) and per-user
  JSON files for favorites/config, same shape mradio used, just one
  directory per user (`/data/users/<id>/`).
- **AI provider credentials are global (admin-managed); which provider is
  active is per-user.** Decided explicitly after backtracking once
  mid-build (an earlier turn briefly went with per-user credentials before
  the user corrected it) — nobody should need their own NIM key or Ollama
  URL, they just pick from what's configured. `backend/app/settings.py` +
  the admin-only `/api/settings/ai` endpoints.
- **The AI trivia cache is shared across all users, not per-user** —
  same track means same answer regardless of who asked first.
  `backend/app/cache.py`, keyed by `provider::raw_title`. The `raw_title`
  must be the *unparsed* ICY string (artist+track together) — that's how
  mradio itself avoids Mozart's and Beethoven's "Symphony No. 1"
  colliding; there's no separate artist field in the key.
- **opencode is bundled in the Docker image**, not left to the admin to
  install — verified it's a fully self-contained native binary (Bun-
  compiled, only needs glibc/libpthread/libdl/libm, all present in
  `python:3.11-slim`), so a `node:22-slim` build stage fetches it and only
  the ~180MB binary gets copied into the final image. Version is pinned
  via a Dockerfile `ARG`, not `@latest`, so builds stay reproducible;
  `.github/workflows/bump-opencode.yml` opens a PR (never auto-merges)
  when npm publishes a newer `opencode-ai`. Because the binary is always
  on `PATH` now, it auto-enables exactly the way it did in mradio itself
  (`oc_binary_present()` check) — zero config needed, though the admin can
  force it off by setting the `opencode` field to `0`.
- **Design system**: custom OKLCH palette + Newsreader/Hanken Grotesk/IBM
  Plex Mono, picked via the Hallmark skill (`.hallmark/log.json` has the
  formal record) — deliberately not the cream+terracotta or
  near-black+neon looks that read as generic AI output. It's an app
  dashboard, not a marketing page, so it doesn't map onto any of
  Hallmark's landing-page macrostructures; the token/typography/motion
  discipline was carried over, the page shape wasn't forced to fit one.

## Deliberately not done (and why)

- **`CHANGELOG.md` adopted as of 0.1.1** (reversing the original decision
  below) — the user asked for it explicitly to follow their standard
  governance playbook across future projects too, so consistency across
  the user's projects won out over "commit messages already say this."
  `BEHAVIOR.md` / `findings.md` are still skipped: `BEHAVIOR.md`'s main
  rule ("commit and push by default") is enforced one layer up by
  whatever harness/session is driving the work, not something the repo
  itself needs to restate; `findings.md` was built for a different kind
  of work (vetting radio station candidates) that doesn't exist in this
  project. `KB.md`, `MEMORY.md`, and now `CHANGELOG.md` are the pieces
  that map onto mradio-web's needs.
- **No DB migration tooling yet.** The SQLite schema has only grown
  additively so far (`backend/app/db.py`); revisit if a column ever needs
  to change shape, not before.

## Gaps — not decisions, just not built yet

- **No committed test suite.** Everything was verified with ad-hoc
  scripts (fake ICY/OpenAI-compatible servers, direct FastAPI-app calls,
  a live Playwright browser run) during the build, none of which are
  checked into the repo. `pytest`, `vitest` — neither is set up; don't go
  looking for a test command that doesn't exist yet. Worth adding if this
  keeps growing, wasn't worth the scope during the initial build.
- **No `Makefile` / `install.sh`.** Unlike mradio's local setup, there's
  no single-command bootstrap — see "Local development" above for the
  actual two-terminal setup.

## Next steps (in order)

1. ~~`docker compose build && docker compose up` end-to-end~~ — done
   2026-09-05 on LT.
2. ~~Confirm working, drop pre-release~~ — done via the `0.1.1` release.
3. ~~Deploy per `KB.md`~~ — done: NPM proxy host at
   `mradioweb.legba.myddns.rocks`, port 8123 on LT (8000 was already
   taken by StirlingPDF), websockets + `proxy_buffering off` both set.
4. Configure AI providers beyond the bundled opencode from the admin page
   (NIM/Ollama), if desired — not yet done.
5. No committed test suite yet (see "Gaps" above) — still true, still not
   urgent at this scale.
6. Fixed 2026-09-05 (0.1.2): Wikipedia link `rel` attribute, NIM provider
   defaults not prefilled (now default to NVIDIA's hosted endpoint +
   `minimaxai/minimax-m3`, matching mradio's own reasoning for that model
   choice), genre-tag/station-name spacing in the favorites grid, and a
   missing stream-metadata row (bitrate/sample-rate/format/cache/elapsed)
   in the now-playing panel. Redeployed to LT same day.
7. Fixed 2026-09-05 (0.1.3), found immediately after deploying 0.1.2:
   stations could get stuck on "Connecting…" forever (audio played fine,
   only the metadata UI hung) — a pre-existing race between the audio
   stream connection and the now-playing WebSocket, where the first
   `station`/`title` event could be published before the WebSocket had
   subscribed and get silently dropped. `nowplaying.py` now caches and
   replays the latest `station`/`title` event per session on subscribe.
   Also added structured logging (`mradio.stream`/`mradio.nowplaying`/
   `mradio.ws` loggers, visible via `docker logs`) — there was previously
   zero application-level logging, only uvicorn's access log, which made
   this bug much harder to diagnose than it should have been.
8. Fixed 2026-09-05 (0.1.4): "Read on Wikipedia" link missing for
   non-classical tracks. Two stacked bugs, both in `enricher.py`: (a) the
   prompt only ever requested a `wiki` value for a classical "work" —
   for a plain song it was empty by design regardless of provider, now
   asks for the song's own article too; (b) even when a Wikipedia lookup
   *did* succeed, the code stored `wiki.resolve()`'s `{title, url}` dict
   directly instead of unwrapping it to the URL string the frontend's
   `EnrichmentItem.wiki: string` type expects — the link rendered but
   `href` resolved to `"[object Object]"`. Both fixed; the frontend
   itself needed no change since its type/JSX were already correct.
9. Fixed 2026-09-05 (0.1.5): now-playing WebSocket died silently and
   never recovered (audio fine, metadata stuck until manual reconnect/
   reload) — near-certainly Nginx Proxy Manager's idle timeout, since
   neither side sent any keepalive traffic. `ws.py` now has a third
   `pump_ping()` task sending `{"type":"ping"}` every 30s (verified live:
   pings arrive at exactly 30s/60s over a real WebSocket connection);
   `usePlayer.ts`'s WS effect was rewritten into a self-contained
   reconnect loop with exponential backoff, gated by a `wantsConnectionRef`
   so a deliberate Stop doesn't get silently fought by its own keepalive
   logic. Same session also replaced Pause with a real Stop:
   `togglePause()` only ever called native `audio.pause()`, which doesn't
   touch `audio.src` — the backend kept proxying the live station forever
   while "paused," and resuming played back stale buffered audio rather
   than reconnecting to what's actually airing. `PlayerState.playing:
   boolean` became `status: 'stopped' | 'playing'`; `stop()` clears
   `audio.src` and reloads (the same abort mechanism `reconnect()`
   already used), which the backend correctly detects as a disconnect
   and cleans up via `stream.py`'s existing `finally` block — verified
   live via `docker logs` showing `mradio.stream INFO disconnected`
   firing exactly when Stop was clicked. No pause-with-a-timeout
   compromise was built — decided with the user that a live stream only
   has Play and Stop, nothing in between ("live is live").
10. Fixed 2026-09-05 (0.1.6): 0.1.5 only fixed the WebSocket's recovery —
    the actual audio stream had zero error/stall handling, so a dead
    connection just went silent with nothing watching for it (confirmed
    live: killed the backend mid-stream, no reconnect happened until this
    fix). `usePlayer.ts`'s audio element now listens for `error`/`stalled`
    and auto-reconnects (reusing the existing `reconnect()`), gated by the
    same `wantsConnectionRef` so Stop still wins. Verified live —
    killing/restarting the backend produced automatic reconnect attempts
    ~2s apart until the connection came back. Also fixed a regression
    from 0.1.5: native `pause` (which fires for both an intentional Stop
    *and* the browser giving up on a dead stream) was setting `status`,
    so an unintentional drop could get misclassified as a real Stop —
    only `stop()` itself sets it now. Also added the app version to the
    top bar, sourced from `frontend/package.json` at build time via a
    Vite `define` (`__APP_VERSION__`), so it can't drift from an actual
    release.
11. 2026-09-05 (0.1.7): tightened vertical spacing in the now-playing
    panel (metrics row, performer line, trivia actions, transport bar)
    and changed liner notes to default expanded instead of clamped —
    purely cosmetic, no behavior change.

**Separately noticed while investigating (not a code bug):** the
Ollama provider is failing on every call in production
(`POST http://192.168.88.8:11434/api/generate` → 404) — direct testing
confirms the configured model `gemma3:4b` isn't pulled on that Ollama
instance at all (`gemma3:4b` was mradio-web's stale default, copied from
the original terminal app's docs). Models actually available there:
`gemma4:e4b-it-qat`, `qwen3.5:9b`, `phi4-reasoning:plus`,
`phi4-mini:latest`, `translategemma:12b`. This silently falls back to
opencode every time (visible in logs as the `127.0.0.1:4096` opencode
calls right after each failed Ollama call) — not broken, just wasteful.
Fix is a one-line change in the AI providers settings page (pick one of
the models actually pulled), not a code change.

## Language support (added 2026-09-05, 0.2.0 + 0.2.1) — fully done

UI language (English/Spanish, top-bar dropdown, 0.2.0) —
`frontend/src/i18n/` (hand-rolled `en.ts`/`es.ts`/`index.ts`, no library,
`Dict` type widening so Spanish only has to match English's key shape,
not its exact text). `Dashboard.tsx` owns `language` state exactly like
`theme`, passes a bound `t()` down as a prop to every consumer — no
React Context, matching this codebase's existing "no abstraction until
needed" style. Persists via `PATCH /api/config`'s `language` field.

**Deliberate scope cut**: `LoginScreen.tsx` and the *forced* first-login
`ChangePasswordScreen` (rendered pre-auth in `App.tsx`, as siblings of
`Dashboard` — not children) stay English-only. There is no account
identity yet at that point to look up a saved preference for, and
(explicit decision, not an oversight) no `localStorage` fallback either
— keeping it simple. `ChangePasswordScreen` reached *voluntarily* from
the Dashboard's user menu is a normal translated page; only the pre-auth
render path is the exception.

AI liner notes follow the UI language too (0.2.1) — `Enricher.language`
mirrors `self.provider`'s pattern (set once in `start()` from
`load_cfg()`, pushed live by `PATCH /api/config` into the running
instance, not re-read from disk per-call). `_PROMPT_TEMPLATE` gained a
`{language_instruction}` slot (English stays fully implicit — zero
prompt-text cost — Spanish adds one line asking for the trivia field in
Spanish while explicitly protecting `"wiki"`, which must stay the
English Wikipedia article title for `wiki.resolve()`'s lookup).
`cache.py`'s key gained a language dimension
(`provider::language::raw_title`) so two accounts in different
languages don't collide on one cached blurb for the same track — old
2-part keys just age out via the existing eviction cap, no migration.
Switching language auto-triggers the existing `reenrich` WS message
(same one the manual "Re-ask AI" button already used) so the
currently-playing track's notes update immediately, not on the next
track — `Dashboard.tsx`'s `setLanguage` awaits the config PATCH before
calling `reenrich()` to avoid a race where the re-ask could beat the
language update to the Enricher.

Verified locally end-to-end except the actual LLM output quality/
language-following behavior itself, which needs a real provider
credential this session didn't have — every other link in the chain
(prompt construction, cache isolation, config persistence, live
Enricher sync, WS re-ask trigger) was confirmed working via direct
tests and a live Playwright run against the real backend.

## Known unknowns

- NIM's exact API base URL is asserted in `KB.md` as "typically
  `https://integrate.api.nvidia.com/v1`" — that's not independently
  verified against current NVIDIA docs, just noted as a starting point to
  check on build.nvidia.com rather than trust blindly.
- Whether AI enrichment should point at the user's existing Hermes-Agent
  Ollama/NIM stack or run independently was flagged as an open question
  in the original project plan — it's now purely a value in the AI
  Providers admin page, not a code decision, so it never needed resolving
  in the build itself.

## Where things live

- `backend/app/` — one module per concern: `auth.py`/`users.py`/`db.py`
  (accounts), `userdata.py` (favorites/config), `cache.py` (shared AI
  cache), `icy.py`/`nowplaying.py`/`routers/stream.py` (the proxy),
  `providers.py`/`enricher.py`/`enrichers.py`/`settings.py` (AI
  enrichment), `stations.py` (curated list + genre logic, stateless),
  `routers/` (one file per REST/WS surface).
- `frontend/src/` — `api/` (types + fetch client), `hooks/` (one per
  concern: `usePlayer` is the biggest, wires `<audio>` + the stream proxy
  + the WebSocket together), `components/` + `pages/` (UI), `styles/`
  (plain CSS, the design tokens from `.hallmark/log.json`).
- `KB.md` — deployment reference (Compose, reverse proxy, first login,
  account/provider config). `README.md` — what/why overview.
