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
12. Fixed 2026-09-05 (0.2.2): three bugs from a review pass — (a) the
    theme toggle icon showed the destination theme instead of the current
    one, inverted back; (b) the AI providers page had no way to verify a
    saved credential actually works short of waiting for a real track to
    fail — see "AI provider connection test" below; (c) KB.md's Ollama
    section never got the same setup walkthrough NIM's had, despite being
    asked before — added, see same section below.

**Fixed 2026-09-05 (production data, not a code change):** the Ollama
provider was failing on every call in production
(`POST http://192.168.88.8:11434/api/generate` → 404) because the
configured model `gemma3:4b` was never pulled on that Ollama instance
(stale default, copied from the original terminal app's docs) — silently
falling back to opencode every time (visible in logs as the
`127.0.0.1:4096` opencode calls right after each failed Ollama call).
Caught by the new Test-connection feature (0.2.2+): "Server reachable,
but model \"gemma3:4b\" is not pulled there." Confirmed available models
on that instance: `gemma4:e4b-it-qat`, `qwen3.5:9b`, `phi4-reasoning:plus`,
`phi4-mini:latest`, `translategemma:12b`. Verified `gemma4:e4b-it-qat`
(closest match to the stale default's size/family) returns clean,
unwrapped JSON for this app's exact prompt shape, then updated the saved
`ollama_model` setting to it via `settings.save()` directly (same
function the admin API itself calls) — not a code default change, since
`_DEFAULTS["ollama_model"]` in `settings.py` only seeds brand-new
installs and wouldn't have touched the already-persisted `settings.json`
on LT. Test-connection now reports Ollama as `True, "Connected."`.
`_DEFAULTS` itself is left as `gemma3:4b` deliberately — that's still
correct as a generic fresh-install default; it just needs pulling before
use, same as any Ollama model does.

## ChatGPT/Codex subscription as a 4th AI provider (2026-09-06, 0.5.23; timeout fixed 0.5.24; 4-way comparison + settings redesign 0.5.25)

**Real-production timing data, first day**: user tested two real liner
notes live on LT after connecting their own ChatGPT Go account. Log
timestamps (title-detected → `httpx` POST completion) showed 23s and
69s — both noticeably slower and more variable than NIM/Ollama's usual
5-20s, consistent with this call being routed through OpenAI's own
subscription-tier backend/load balancer rather than a direct model
endpoint (the response headers include `x-codex-safety-buffering-enabled`
and similar internal routing hints, seen during dev testing). The 69s
outlier came within seconds of `llm_codex()`'s original hardcoded 60s
`httpx` timeout — a genuinely bad near-miss, since a timeout there fails
silently (returns `None`, falls through to no-liner-notes or a fallback
provider) rather than erroring visibly. Fixed by raising it to 180s
(`_CODEX_TIMEOUT`), matching opencode's existing 180s ceiling rather
than picking a new arbitrary number — same "this mediates through
something heavier than a plain API call" reasoning already established
for that provider. Both real liner notes were independently assessed as
high quality (correct movement/whole-work distinction, accurate
historical detail, no hallucination spotted) — the timing variance is a
real, worth-tracking trade-off of the mechanism, not a quality problem.

User's idea: another app ("Hermes") lets you sign in with a ChatGPT
subscription instead of an API key, via a browser OAuth redirect +
consent screen. Initial research said this was impossible (OpenAI's
public API and ChatGPT subscriptions are billed as fully separate
products) — user pushed back with real screenshots proving Hermes's flow
was genuine, not scraping. Correct: it's OpenAI's own **Codex CLI
device-code flow** (RFC 8628, the same one `codex login` runs in a
terminal). Two implementation attempts were needed to get this right —
both failures and the reasoning behind the pivot are the load-bearing
part of this entry, not just the final shape.

**Attempt 1 (failed, kept as documented history, not reverted silently)**:
reimplemented the OAuth device-code flow as raw `httpx` calls against
`auth.openai.com/oauth/device/code` and `/oauth/token` (client_id and
endpoints confirmed via a reference open-source project,
`icebear0828/codex-proxy`, which does the same thing at production
scale). **Confirmed live this is blocked**: `auth.openai.com` sits
behind Cloudflare, which returns `cf-mitigated: challenge` (a JS/TLS
fingerprint check) to any plain HTTP client — verified with raw `curl`
too, not just Python, and confirmed no header/User-Agent combination
fixes it. The reference project works around this with custom native
TLS-fingerprinting code (mimicking a browser/Rust `reqwest` handshake) —
real infrastructure this app has no reason to reimplement.

**Attempt 2 (shipped)**: this app already bundles the real `opencode`
CLI binary in the Docker image for an analogous reason (a trusted real
client instead of reimplementing undocumented internals) — `codex` gets
the identical treatment. `backend/app/codex_oauth.py` spawns
`codex login --device-auth` as a subprocess (`CODEX_HOME` pointed at
`DATA_DIR/codex_home`, confirmed live this directory must pre-exist or
the CLI errors out, and confirmed it must NOT be under `/tmp` — the CLI
refuses to create helper binaries there), parses its stdout for the
device code + verification URL, and once the subprocess exits 0, reads
the CLI's own `$CODEX_HOME/auth.json` for `tokens.access_token`/
`refresh_token`/`account_id` rather than parsing any HTTP response
itself. **Two real bugs caught only by testing against a real login,
not just reading docs**: (1) the CLI's stdout contains ANSI color escape
codes (`\x1b[94m...\x1b[0m`) which silently broke the code/URL regex
matches — fixed by stripping ANSI codes before matching; (2) passing a
fully-replaced `env={"CODEX_HOME": ..., "HOME": ...}` to
`asyncio.create_subprocess_exec` wiped `PATH` entirely, so the
subprocess couldn't even find the `codex` binary — fixed by spreading
`{**os.environ, "CODEX_HOME": ...}` instead of replacing the environment.

**The important, non-obvious finding**: only the device-code *initiation*
endpoint needed this workaround. Confirmed live, separately, that both
token refresh (`grant_type=refresh_token` against the same
`/oauth/token` endpoint) and the actual liner-notes call
(`chatgpt.com/backend-api/codex/responses`) work completely fine as
plain `httpx` requests once a real token is in hand — no Cloudflare
block on either. So `providers.py`'s `llm_codex()` and
`codex_oauth.py`'s `refresh()`/`ensure_fresh_token()` stayed as direct
HTTP calls; only login itself goes through the bundled binary. This
matters for anyone maintaining this later: don't assume the whole
provider needs subprocess mediation just because login did.

**Confirmed end-to-end with the user's real ChatGPT Go account**,
through the actual running app (not a standalone script): connect
button → real device code shown → user completes browser flow → status
flips to `connected: true` with `chatgpt_plan_type: "go"` → Test button
reports "Connected (go)." → selecting it as the active provider and
playing a real station produced a genuine, well-formed AI liner note
about Gershwin's *Rhapsody in Blue* end-to-end through the player UI.
Correct model id (`gpt-5.6-terra` at the time of writing, confirmed by
running `codex exec` for real and reading its own startup banner — an
earlier guess, `gpt-5.1-codex`, was wrong and returned a 400) — **this
will go stale as OpenAI ships new models; there is no way to query it
generically, re-derive it the same way if liner notes start failing**.

**Dockerfile**: new `codex-build` stage (`node:22-slim`, `ARG
CODEX_VERSION`, `npm install --global @openai/codex@${CODEX_VERSION}`) —
confirmed the npm package resolves the correct platform-specific binary
automatically via `optionalDependencies` aliasing (not a separate
package per platform, just version-tagged installs of the same
`@openai/codex` package, e.g. `@openai/codex@<version>-linux-x64`).
Final image copies `node` + the `@openai/codex` module tree and
recreates npm's own symlink (`ln -s .../codex/bin/codex.js
/usr/local/bin/codex`) rather than hand-rolling a wrapper script (a
first draft did this with a shell script; simplified after confirming
npm's own approach works and is simpler). **Verified with a real
Docker build**, both natively (arm64, this dev machine) and cross-built
for `linux/amd64` (LT's actual architecture) via `docker build
--platform linux/amd64` — confirmed `codex --version` and a real device
login attempt both work inside the actual final image on the actual
target architecture before deploying, not assumed. `python:3.11-slim`
(this app's base image) already ships CA certificates, unlike bare
`node:22-slim` — relevant because Codex's Rust binary fails silently
with a generic "error sending request" if certs are missing, which
looked like a network problem before it was diagnosed as a missing
`ca-certificates` package in a throwaway test image (not in the actual
production base image, which is fine).

New provider `"codex"` threaded through the existing generic
provider-tuple machinery: `PROVIDERS` tuple, `provider_enabled()`,
`ai_configured()`, `run_provider_test()` in `providers.py`; the if/elif
dispatch in `enricher.py`'s `_llm()`. **The player-side "only selectable
when configured" gating the user separately asked about was already
fully implemented before this feature** (`NowPlayingPanel.tsx`'s
provider dropdown already disables + labels unconfigured providers
generically by name) — confirmed by reading the existing code, not
assumed, and zero changes were needed there beyond adding `codex:
'ChatGPT'` to `_PROVIDER_LABEL`.

New provider card in `AISettingsPage.tsx` (4th `settings-group`, not a
radio button inside the existing generic-OpenAI card — kept each
provider's settings self-contained) with a `useCodexStatus` polling hook
(`frontend/src/hooks/useCodexStatus.ts`, 3s interval while `pending`,
modeled on `AnalyticsPage.tsx`'s only prior polling precedent in this
frontend). New backend router `routers/codex.py`
(`GET /api/settings/codex`, `GET .../status`, `POST .../connect`,
`POST .../disconnect`, `POST .../test`) mirrors `routers/smtp.py`'s
shape. New `codex_settings.py` (token/plan-type JSON store, mirrors
`settings.py`/`smtp_settings.py`'s `_DEFAULTS`/`_SECRET_FIELDS`/
`load`/`save`/`redacted` shape exactly).

**On the hardcoded `CLIENT_ID`**: `app_EMoamEEZ73f0CkXaXp7hrann` is
OpenAI's own public client identifier for the Codex CLI itself — not a
secret, not tied to any account, the same value baked into OpenAI's own
open-source CLI. User asked directly whether this bakes in anyone's
personal authorization; it does not — every install gets its own empty
`codex_settings.json`/`codex_home/`, and only becomes "connected" if
that install's own admin completes their own OAuth login with their own
account. Worth remembering this question will likely come up again from
other users/reviewers of this code; the answer belongs here, not just
in a chat transcript.

**4-way real-production comparison (0.5.25)**: user's explicit bar —
"I accept the OpenAI dependency risk only if it delivers a substantial
improvement over the other three free providers." Ran a one-off
diagnostic script directly on LT (cleaned up after, no trace left in
app state) firing the same 6 real tracks through opencode/ollama/openai
(NIM)/codex and comparing timing + quality. Findings: **NIM failed on
every single call** ("no response") — a real, separate, still-unfixed
problem, not investigated further since the user moved straight to the
settings redesign request without confirming it as a task. ChatGPT was
often faster than opencode (which had two 100+ second outliers) but was
NOT substantially better in quality than opencode/ollama — verdict
given to the user: does not clear the stated bar, but remains a
roughly-equal fourth option worth keeping. Ollama had one genuine
factual error (wrong date for a Myaskovsky symphony) in this sample.
Based on this data, user picked a preference order — ChatGPT, opencode,
Ollama, NIM — for both the settings-page card order and the player's
dropdown/fallback order.

**Settings-page redesign (0.5.25)**: reordering the fallback/dropdown
order needed exactly one change — `providers.py`'s `PROVIDERS` tuple —
since `routers/enrich.py`'s `list_providers()` and `enricher.py`'s
fallback logic both already iterate that same tuple generically; no
other backend logic needed touching. `AISettingsPage.tsx`'s four
provider blocks were reordered to match and each wrapped in a new
`.provider-bubbles` container; `.settings-group` (previously a bare
flex column with no visual separation) gained a `--paper-3` background,
`--line` border, and rounded corners so each provider reads as a
distinct card, plus a small `.provider-status-dot` next to each
heading (grey when unconfigured, `--live` green when configured) —
"configured" is derived client-side straight from already-loaded state
(`codexStatus?.connected`, `settings.opencode`, `settings.ollama_url`,
`settings.api_key`) rather than fetching `/api/enrich/providers`
separately, since that data was already in hand. Verified end-to-end
locally: spun up the real backend against a throwaway `MRADIO_DATA_DIR`
+ venv (exact setup this file's own "Local development" section
documents) and the real Vite dev server, confirmed via `curl` that
`/api/enrich/providers` really does return `codex, opencode, ollama,
openai` in that order post-change — **no screenshot/browser tool was
available in that session, so the actual pixel-level "bubble" look was
not visually confirmed before shipping**, only the DOM/CSS pairing and
data-flow correctness; flagged this gap to the user rather than
claiming a visual check that didn't happen, consistent with
[[feedback_verify_ui_visually]]'s spirit even when the ideal tool isn't
on hand.

**Display casing fixed (0.5.27)**: "opencode" was shown lowercase
everywhere in the UI (settings page, docs) except one spot that had it
worse — `NowPlayingPanel.tsx`'s `_PROVIDER_LABEL` map had BOTH
`opencode: 'opencode'` and `ollama: 'ollama'` lowercase, meaning the
player's own AI-provider dropdown/label had been showing lowercase
provider names in production the whole time, not just the settings
page. Fixed to `'OpenCode'`/`'Ollama'` there, plus every i18n string
across all 13 languages (`aiDescription`, the shared-credentials intro
line, `opencodeGroup`) and KB.md's `### opencode` heading → `### OpenCode`
(README.md too). Left every literal binary/CLI/package/filename
reference lowercase (`` `opencode` `` the binary, `bump-opencode.yml`,
`opencode-ai` the npm package) since that's genuinely the correct,
real-world name for those — only the *product name as prose/UI label*
needed the capital. Ollama's own display strings were already correct
before this pass; only opencode's were wrong.

**Status-dot bug, caught by the user immediately after shipping
(0.5.26)**: opencode's dot showed grey with the "Enable" field left
empty, even though opencode was genuinely enabled and working in
production. Root cause: `oc_port()` in `providers.py` treats an empty
`opencode` field as "enabled" too, as long as the `opencode` binary is
present on the host (`oc_binary_present()`) — true in this Docker image
since it's bundled, so opencode is enabled *by default* with no field
set at all. The frontend dot didn't know this and used the raw
`settings.opencode` text field as its proxy for "configured," which is
wrong specifically for opencode (right for the other three, where the
field really is the source of truth). Fixed by using the same
already-existing `useProviders()` hook (`/api/enrich/providers`) the
player's dropdown itself relies on, instead of re-deriving "configured"
client-side from raw settings fields — one source of truth instead of
two independent guesses at the same fact. **Lesson**: when a status
indicator needs to answer "is this the same as elsewhere in the app,"
prefer reusing the endpoint/hook that other UI already trusts for that
exact fact, rather than re-implementing the derivation logic a second
time from raw fields — the raw fields don't always tell the whole
story (as here, where a binary-present fallback exists that no field
value reveals).

## Hip-Hop genre added (2026-09-06, 0.5.21)

Tenth curated genre, following the exact pattern of every prior genre
addition. `backend/app/stations.py` needed 5 spots, not the usual
frontend-facing ones — this app's genre system is entirely
backend-driven (labels come from `GENRE_LABELS` via `/api/stations/genres`,
no frontend hardcoding or i18n keys per genre): `GENRES` tuple,
`GENRE_LABELS` dict (`"Hip-Hop"`), `_GENRE_KEYWORDS["hiphop"]` (`hip hop`,
`hip-hop`, `hiphop`, `rap`, `urban`, `jamz` — for auto-classifying
user-added custom stream URLs via `genre_of()`), the 10 new
`DEFAULT_STATIONS` entries, and two easy-to-miss hardcoded genre-list
tuples that duplicate `GENRES` for historical reasons and needed the
same addition: `genre_of()`'s classification-priority order and
`genre_stations_for()`'s "does this genre pull from the curated catalogue
too, or favorites-only" allow-list (only `"other"` is meant to stay
favorites-only — a new real genre needs adding to both spots or it
silently behaves like "other" even though it has curated stations).
Only frontend change: `Genre` type in `api/types.ts` (type safety only,
still no UI text hardcoded per genre).

**Station selection method**: no single authoritative "best hip-hop
stations" list exists, so sourced via Radio-Browser (same directory used
for station-logo lookups, see [[station_logos]]) queried by tag, filtered
out obvious click-farm/mistagged EDM "club charts" results that show up
in raw tag searches, then verified every candidate's stream actually
responds (`curl -A "VLC/3.0"` — a few needed a real player user-agent to
avoid a 400/empty response, e.g. `stream.radiojar.com` and
`radio.dominiserver.com`, both fine once curled properly) before adding
any of them. Final 10: 181.FM - Old School HipHop/RnB, 181.FM - The Beat
(HipHop/R&B), 90s90s HipHop & Rap, 100 Hip Hop and RNB FM, .977 Jamz, BBC
Radio 1Xtra, All Underground Hip Hop Radio, WEFUNK, Hot 108 Jamz, Top
Urbano — mixing 1.FM/181.FM-network entries (matching stations already
curated elsewhere in this list), a national broadcaster (BBC 1Xtra, same
non-UK HLS URL pattern already proven working for BBC Radio 3), and
recognizable long-running independent stations (WEFUNK, Hot 108 Jamz),
plus one Latin/reggaeton-adjacent pick (Top Urbano) for genre breadth.
BBC 1Xtra reuses the exact `nonuk` HLS URL structure already validated
by BBC Radio 3's entry — confirmed via `curl` that the equivalent
1Xtra path resolves the same way. Verified live via Playwright: genre
tab shows "Hip-Hop 10", all 10 stations list correctly with clean
favorite-star/URL rows, and one (WEFUNK) actually streams end-to-end
through this app's own proxy with real ICY metadata coming through
("hit-boy feat. alchemist - slipping into darkness") — not just a UI
listing check. Total curated station count: 104 (was 94).

## One-time default-favorites reset (2026-09-06, 0.5.19; Heart 70s genre bug fixed 2026-09-06, 0.5.20)

User explicitly requested a one-time-only change: reset the default
12-station favorites lineup to a new specific selection (screenshot
provided), applied to **every existing user's actual favorites** as a
single irreversible pass, AND make it the seed for all future new
accounts — with an explicit instruction that after this one time,
favorites are never touched by us again going forward.

Two separate mechanisms, deliberately kept separate:

1. **Future new users**: `backend/app/stations.py`'s `DEFAULT_STATIONS`
   first 12 entries were reordered to the new lineup (VCR Auditorium, VCR
   Classica+, Radio Swiss Classic, 181.FM Kickin' Country, 1.FM Absolute
   Country Hits, Swiss Jazz, Radio Paradise, Jazz Radio Blues, Heart 70s
   (UK), 181.FM True Blues, Jazz Lounge, Funkstar Radio) — this is the
   exact list `userdata.py`'s `_load_favorites_sync()` already reads via
   `DEFAULT_STATIONS[:MAX_FAV]` on a brand-new account's first load, so
   this one edit is sufficient for all future accounts with zero other
   code changes. The 6 displaced stations (Naim Classical, WQXR, Classic
   FM, radio klassik Stephansdom, NPO Klassiek, France Musique) were kept
   in the file, just moved further down — still fully browsable under
   Genres, just no longer in the default favorites. Total station count
   unchanged (94), confirmed no duplicate (name, url) pairs after the
   reorder.
2. **Existing users** (the one-time, non-repeating part): new standalone
   script `backend/scripts/reset_favorites_once.py`, run once by hand
   (`--dry-run` first, then for real), NOT part of app startup or any
   migration path — it will not run again on future deploys. Overwrites
   every existing user's `favorites` via the same `userdata.save_favorites()`
   used everywhere else; explicitly does NOT touch `config.json`
   (theme/volume/provider/language). Verified end-to-end against scratch
   users with genuinely different pre-existing favorites and a custom
   config — confirmed the script correctly rewrites favorites, leaves
   config byte-for-byte untouched, and dry-run mode writes nothing.

**Correction (2026-09-06, 0.5.20)**: originally assumed "Heart 70s (UK)"
showing genre "other" in the user's screenshot was itself the deliberate,
correct value to preserve (see the reasoning this replaces, kept below
struck through for the lesson). It was not — the user confirmed it "used
to be" `pop` and called this a bug introduced during the 0.5.19 reset.
**Lesson**: a screenshot showing a value doesn't mean that value is
intentional or correct — it can just as easily be evidence the thing
you're about to copy is already wrong. When a migration's source data
(a live screenshot, an existing DB row, etc.) conflicts with what the
codebase's own classification logic says, that conflict is worth
surfacing as a question before baking it into a "this is deliberate"
migration decision, not resolving it silently in either direction.
Fixed in `stations.py` (`Heart 70s (UK)` → `"pop"`) and corrected live
for all 6 already-migrated accounts via a surgical one-field patch
(only that one entry's `genre`, not a full favorites re-write) — see
[[mradio_web_status]] for the exact verification steps.

~~"Heart 70s (UK)" is stored as genre `"other"`, not `"pop"` — this is
deliberate, not a bug: the user's screenshot showed it under "Other" in
the UI (meaning their actual saved favorite already diverged from
stations.py's "pop" classification at some point), so the new default
lineup matches the screenshot's genre exactly rather than "correcting"
it to the current curated-list value — preserves what the user actually
asked for over what the source-of-truth catalogue says.~~ (superseded
above — this reasoning was wrong.)

**No new code path was added that could ever re-push this (or any
future) favorites change to existing users automatically** — per the
user's explicit instruction that this is a one-time-only operation.

## Language support (added 2026-09-05, 0.2.0 + 0.2.1 + 0.3.1; Portuguese + pattern cleanup 2026-09-06, 0.3.5; French 2026-09-06, 0.3.10; Russian 2026-09-06, 0.5.8; German 2026-09-06, 0.5.9; Greek 2026-09-06, 0.5.10; Dutch 2026-09-06, 0.5.11; Danish 2026-09-06, 0.5.12; Swedish 2026-09-06, 0.5.13; Norwegian Bokmål 2026-09-06, 0.5.14; Japanese 2026-09-06, 0.5.15) — fully done

UI language (English/Spanish/Italian/Portuguese/French/Russian/German/
Greek/Dutch/Danish/Swedish/Norwegian Bokmål/Japanese, top-bar dropdown,
0.2.0 + Italian in 0.3.1 + Portuguese in 0.3.5 + French in 0.3.10 +
Russian in 0.5.8 + German in 0.5.9 + Greek in 0.5.10 + Dutch in 0.5.11
+ Danish in 0.5.12 + Swedish in 0.5.13 + Norwegian Bokmål in 0.5.14 +
Japanese in 0.5.15) — `frontend/src/i18n/` (hand-rolled `en.ts`/
`es.ts`/`it.ts`/`pt.ts`/`fr.ts`/`ru.ts`/`de.ts`/`el.ts`/`nl.ts`/
`da.ts`/`sv.ts`/`nb.ts`/`ja.ts`/`index.ts`, no library, `Dict` type
widening so non-English files only have to match English's key shape,
not its exact text). Adding a language is now a proven 6-spot pattern
(confirmed for Italian in 0.3.1, Portuguese in 0.3.5, French in
0.3.10, Russian in 0.5.8, German in 0.5.9, Greek in 0.5.10, Dutch in
0.5.11, Danish in 0.5.12, Swedish in 0.5.13, Norwegian Bokmål in
0.5.14, Japanese in 0.5.15 — see [[feedback_i18n_and_readme_kb_links]]
for the durable checklist): new `<lang>.ts` file, add its code to
`Language` + `LANGUAGES` in `index.ts`, add the code to
`Config.language`'s union in `api/types.ts`, and the backend's two
spots (`routers/config.py`'s `_VALID_LANGUAGES`, `enricher.py`'s
`_LANGUAGE_INSTRUCTIONS`), plus the README's language-list bullet.
Russian's Cyrillic text needed no special handling anywhere in the
stack (same as CJK/emoji before it) — confirmed via a live Playwright
pass across the player, Analytics, and Settings/Users pages with no
layout breakage or truncation; German verified the same way and needed
nothing special either, despite running noticeably longer strings than
English in places (e.g. "Administrationseinstellungen, nach Bereich
gruppiert."). Greek used the ISO code `el` (not `gr`, a common but
incorrect guess) since that's the actual ISO 639-1 code. Dutch (`nl`)
needed nothing special either. Danish used the ISO code `da` (not
`dk`, the *country* code). Swedish used the ISO code `sv` (not `se`,
again the *country* code, same pitfall as Greek/Danish). Norwegian
Bokmål used the ISO code `nb` — the user explicitly asked for "the
modern one, something like Bokmål, not the Nynorsk," and `nb` is the
correct ISO 639-1 code for Bokmål specifically (`nn` is Nynorsk, `no`
is the generic macrolanguage code covering both). Confirmed via a live
Playwright pass (one cosmetic false alarm: the 🇳🇴 flag glyph rendered
as the wrong flag in headless Chromium screenshots due to missing
emoji font coverage in that scratch environment — verified via DOM
codepoint inspection (U+1F1F3 U+1F1F4, the genuine Norway
regional-indicator pair) that the actual data/markup is correct; a
real browser with normal emoji font support renders it fine). Japanese
used the ISO code `ja` — first CJK/non-Latin-adjacent script added
(fully double-byte, no romanization), verified via a live Playwright
pass across the player, Analytics, Settings hub, and Users pages: all
render correctly with no mojibake, no missing glyphs, and no layout
breakage; the Users table's "ステータス" (Status) column header wraps
to two lines in its narrow column, which is a natural wrap (harmless,
consistent with how German's longer strings were judged acceptable
in 0.5.9), not a truncation or missing-translation bug — thirteenth
language added, this pattern is now well-proven across Latin,
Cyrillic, Greek, and CJK scripts alike.
`Dashboard.tsx`'s config-load fallback chain (previously an `===`
chain naming each language code, needing an edit per new language) was
**simplified in 0.3.5** to validate against `LANGUAGES` generically
(`LANGUAGES.some((l) => l.code === config.language)`) — this spot
should no longer need touching for future languages. `Dashboard.tsx`
owns `language` state exactly like `theme`, passes a bound `t()` down
as a prop to every consumer — no React Context, matching this
codebase's existing "no abstraction until needed" style. Persists via
`PATCH /api/config`'s `language` field.

**Deliberate scope cut**: `LoginScreen.tsx` and the *forced* first-login
`ChangePasswordScreen` (rendered pre-auth in `App.tsx`, as siblings of
`Dashboard` — not children) stay English-only. There is no account
identity yet at that point to look up a saved preference for, and
(explicit decision, not an oversight) no `localStorage` fallback either
— keeping it simple. `ChangePasswordScreen` reached *voluntarily* from
the Dashboard's user menu is a normal translated page; only the pre-auth
render path is the exception.

AI liner notes follow the UI language too (0.2.1, Italian added 0.3.1,
Portuguese added 0.3.5, French added 0.3.10, Russian added 0.5.8,
German added 0.5.9, Greek added 0.5.10, Dutch added 0.5.11, Danish
added 0.5.12, Swedish added 0.5.13, Norwegian Bokmål added 0.5.14,
Japanese added 0.5.15) — `Enricher.language` mirrors `self.provider`'s
pattern (set once in `start()` from `load_cfg()`, pushed live by
`PATCH /api/config` into the running instance, not re-read from disk
per-call). `_PROMPT_TEMPLATE` gained a `{language_instruction}` slot
(English stays fully implicit — zero prompt-text cost — Spanish/
Italian/Portuguese/French/Russian/German/Greek/Dutch/Danish/Swedish/
Norwegian Bokmål/Japanese each add one line asking for the trivia
field in that language while explicitly protecting
`"wiki"`, which must stay the English Wikipedia article title for
`wiki.resolve()`'s lookup).
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

## AI provider connection test (added 2026-09-05, 0.2.2)

`POST /api/settings/ai/test?provider=<ollama|openai|opencode>` — new
endpoint in `routers/settings.py`, takes an `AISettingsUpdate`-shaped body
(reused as-is, no new request model), merges it on top of the
currently-saved settings server-side, and dispatches to
`providers.run_provider_test()`. This solves the redacted-API-key problem
cleanly: the frontend only sends `api_key` when the admin actually
retyped it this session (`apiKeyInput` non-empty), otherwise the merge
falls back to the real saved key that only the backend ever holds.

Three provider-specific test functions in `providers.py`
(`_test_ollama`/`_test_openai`/`_test_opencode`), all with a fixed 10s
timeout independent of the configured production timeouts (a test should
fail fast, not hang for the real 75s/30s/180s enrichment budget):
- Ollama: `GET /api/tags`, then checks the configured model is actually
  in the returned list — a reachable server with the wrong model pulled
  is reported as a failure, not a pass, since that's what actually
  matters for enrichment to work.
- OpenAI-compatible (NIM): `GET /v1/models` (checks connectivity + the
  key is accepted, matching Ollama's `/api/tags` approach), and if the
  endpoint returns a model list, confirms the configured model is on it.
  **Originally did a real chat-completion call instead** ("exercise the
  real code path"), but confirmed against the real production NIM key
  that NVIDIA's free-tier `minimaxai/minimax-m3` genuinely takes longer
  than any sane test timeout to respond (20s+ observed) — an
  `httpx.ReadTimeout`, which stringifies to `''`, so the failure pill
  showed "Could not reach ...:" with nothing after the colon. `/v1/models`
  responds in ~150ms and proves the same thing (valid key, right base
  URL) without paying for a slow real inference call on every click.
  `_exc_reason()` helper added so any future exception with an empty
  `str()` falls back to showing its class name instead of a blank
  message.
- opencode: reuses the app's one shared `enricher._opencode`
  `OpencodeSession` instance (imported lazily inside the function to
  avoid a circular import — `enricher.py` already imports `providers` at
  module level) rather than spawning a second subprocess.

Frontend: one Test button + result pill per provider group in
`AISettingsPage.tsx`, reusing the existing `.pill`/`.pill.admin`
(success)/`.pill.disabled` (failure) classes already in `admin.css` —
deliberately not a new color/badge system. Testing is independent of
Save: it never persists anything, and uses whatever's currently typed in
the form.

**Fixed in 0.2.3**: the Test *buttons themselves* shipped in 0.2.2 with
no visible button styling — they'd reused `.row-actions button`, which is
deliberately plain-text-styled for the Users table's inline action links
("Make admin", "Disable", etc.), wrong for a primary action in a settings
form. This shipped without ever clicking Test in a real browser first —
the pill/JSON logic was verified, the actual rendered look wasn't. Added
`.test-btn`/`.test-actions` (bordered button matching the settings form's
visual language) and verified live end-to-end this time: ran the backend
+ Vite dev server locally, logged in via Playwright, clicked all three
Test buttons, and confirmed both the failure pill (red, "No server URL
configured." / "No API key configured.") and a genuine success pill
(green "Working", via this dev machine's real Homebrew-installed
opencode binary) render correctly. **Lesson: for any UI change, actually
look at the rendered page before calling it done — a green build/lint is
necessary but not sufficient.**

**Fixed in 0.2.4**, found testing 0.2.3 against the real production NIM
key (not just the empty-field failure paths tested for 0.2.2/0.2.3):
(a) the NIM test's `httpx.ReadTimeout` bug above — see the "OpenAI-
compatible (NIM)" bullet above for the fix; (b) the "New to NIM/Ollama?"
notes said "the project's KB.md" as plain text, not an actual link.
`AISettingsPage.tsx` gained a small `KbNote` component rendering a real
`<a href="https://github.com/Marcus1571/mradio-web/blob/main/KB.md#<anchor>">`
(GitHub's own heading-slug anchors — `#ollama`, `#nvidia-nim-openai-compatible`
— verified live to actually scroll to the right section), styled via new
`.admin-note a` CSS. **Second lesson stacked on the first: testing only
the "field is empty" failure path isn't enough for a feature whose whole
point is validating real credentials — test it against a real,
already-configured value too**, which is what surfaced the NIM timeout
bug in the first place.

## Admin analytics dashboard (added 2026-09-05, 0.3.0)

Loosely inspired by Tracearr (a Plex/Jellyfin/Emby monitoring tool) but
deliberately scoped down — took the *idea* (live sessions, map, stats,
history), none of the stack (no TimescaleDB/Redis/Fastify, no React
Native, no account-sharing detection — that solves a different problem
this app doesn't have).

**New `play_history` SQLite table** (`db.py`'s `SCHEMA`, same
`CREATE TABLE IF NOT EXISTS` pattern as everything else, no migration
framework) — one row per stream connection: user, station, genre,
start/end time, IP, and resolved city/country/lat/lon. Written by
`routers/stream.py` at the exact same two points it already logs
connect/disconnect — no new hook points needed.

**Real bug found via a live Playwright test, not code review**: the
history-end write (an `await` inside the stream proxy's `body()`
generator's `finally` block) could silently get cut short on an abrupt
client disconnect. Root cause: an async generator's `finally` block
isn't guaranteed to run its `await`s to completion once the generator is
being closed via cancellation/`GeneratorExit` — a well-documented Python
asyncio gotcha, confirmed by testing the exact disconnect path
(clean Stop-button click vs. abrupt browser-context close) 6+ times each
and finding `ended_at` left `NULL` specifically on abrupt disconnects.
Fixed by wrapping the whole cleanup sequence (`history.end_session`,
`nowplaying.session_ended`, the pre-existing `upstream.aclose()`/
`client.aclose()`) in `asyncio.shield(asyncio.create_task(cleanup()))` —
the standard fix for exactly this pattern. This also silently fixes a
lower-stakes version of the same bug that predates this feature (the
httpx client cleanup could theoretically get cut short the same way).

**Real bug found via manual verification, not assumption**: genre was
being re-guessed from the station's *name* via the existing
`stations.genre_of()` heuristic on every single play — checked this
against the full 94-station curated list and found a **35% mismatch
rate** (e.g. "WQXR" → guessed "other", real genre "classical", since the
name has no genre keyword). The frontend already knows every curated/
favorite station's real genre; it just wasn't sending it. Fixed by
threading `station.genre` through as a new `?genre=` query param on
`/api/stream` (backend validates it's a real `stations.GENRES` value,
falling back to the name heuristic only when absent — the actual
fallback path for arbitrary custom stream URLs, which have no assigned
genre otherwise). Also fixed the same hardcoded `'other'` in
`Dashboard.tsx`'s page-reload auto-resume path — `config.last_genre` is
now a real persisted field, following the exact same pattern as the
pre-existing `last_url`/`last_name`.

**Geolocation** (`backend/app/geoip.py`, new): a local GeoLite2-City
`.mmdb` file (downloaded at Docker build time from a redistribution
mirror — `github.com/P3TERX/GeoLite.mmdb`, MIT-licensed repackaging of
MaxMind's CC-BY-SA data, no MaxMind account/API key needed — refreshed
whenever the image is rebuilt, no separate scheduled workflow for v1).
Private/loopback/link-local IPs correctly resolve to no location. One
gap caught independently (not incidental): Python's `ipaddress` module
does **not** flag Tailscale's CGNAT range (`100.64.0.0/10`, RFC 6598) as
private — without an explicit check it would silently fall through to a
real GeoLite2 lookup that happens to return nothing today, but for the
wrong reason. This app is reached over Tailscale (see
[[infra_landscape]]), so this is a realistic path, not a hypothetical —
`geoip.py` explicitly excludes this range now.

**Prerequisite fix, easy to miss**: the app runs behind Nginx Proxy
Manager, and `uvicorn` was started with no `--proxy-headers` flag — so
`request.client.host` reflected NPM's internal Docker IP for literally
every visitor, not their real IP. Without this fix the whole map feature
would have shipped silently broken (every session showing NPM's own
address, or nothing, depending on whether that IP happens to be
private). Fixed by adding `--proxy-headers --forwarded-allow-ips=*` to
the Dockerfile's `CMD` — safe here since NPM and the app share the same
Docker host per `KB.md`'s documented deployment, not behind an untrusted
public load balancer.

Frontend: new `AnalyticsPage.tsx`, following `UsersPage.tsx`'s exact
conventions (`{ t }` prop, `admin.css` classes, `.pill` reuse). Map via
`leaflet` + `react-leaflet` (the one deliberate exception to this app's
zero-UI-dependency posture so far — no reasonable hand-rolled substitute
for an actual map). Stats charts are hand-rolled inline SVG (bar lists +
a sparkline polyline) — no charting library, keeping that exception
narrow and intentional. New `Page` union member `'analytics'` — the
page itself is still called "Analytics" internally (its own `<h1>` and
`analytics.*` i18n block are unchanged), but how it's reached from the
UI changed in 0.3.7: originally a "Analytics" entry in the user
dropdown menu next to "AI providers," moved 2026-09-06 to a standalone
top-bar **Dashboard** button (between the theme toggle and the account
chip, still `user?.is_admin`-gated, still navigates to the same
`'analytics'` page) — the dropdown entry was removed, not duplicated.
The now-unused `topbar.analytics` i18n key was renamed to
`topbar.dashboard` across all four languages rather than left as a
dead key.

Verified live end-to-end via Playwright in both themes and both
languages (not just build/lint) per the standing lesson from 0.2.2/0.2.3
— screenshotted the actual rendered map (real pins for New York/
Amsterdam/Zurich/London from seeded test data), stats bars, sparkline,
and paginated history table, in dark, light, English, and Spanish.

## Trivia history (added 2026-09-05, 0.3.2; made per-user + persisted 2026-09-06, 0.3.3)

"Recently played" — the last 10 AI trivia blurbs (author, title,
station, trivia, wiki link), re-readable while a different track plays.
**0.3.2 shipped this as session-only/in-memory; 0.3.3 replaced that
with per-user persistence** after the user asked for it explicitly
("per user not per session... together with the trivia/info, the
author and title must be kept too" — the author/title part was already
true in 0.3.2's shape, carried forward unchanged).

Current (0.3.3) architecture: new `trivia_history` SQLite table
(`db.py`, same `CREATE TABLE IF NOT EXISTS` pattern as `play_history`) —
one row per `(user_id, raw_title)`, `backend/app/trivia_history.py`
mirrors `history.py`'s plain-async-functions-over-`db.tx()` style.
`record()` deletes any existing row for that `(user_id, raw_title)`
first (so a re-ask moves the entry to newest instead of duplicating —
same dedupe behavior 0.3.2 had in a JS array, now enforced in SQL),
inserts, then trims to the 10 most recent per user. Wired into
`routers/ws.py`'s `push_enrichment()` — the single choke point every
successful enrichment already passes through — and the cached-hit
branch in `pump_nowplaying()` (a track whose trivia is already cached
still needs to land in *this user's* persisted history even though no
fresh LLM call happened). `state` in that same handler gained
`station_name`/`artist`/`title`/`performer` tracking (previously only
`raw_title`) to have everything `record()` needs.

New `GET /api/enrich/trivia-history` (behind `get_active_user`, not
admin-only — personal data). Frontend: `usePlayer.ts` dropped the
in-memory array entirely, replaced with a `triviaHistoryVersion`
counter bumped on every fresh (non-fail) `'enrichment'` message;
`NowPlayingPanel.tsx`'s `TriviaHistoryStrip` fetches the endpoint in a
`useEffect` keyed on that version instead of receiving history as a
prop. All the 0.3.2 UI (filmstrip chips, expand-in-place reusing
`.trivia`/`.trivia-actions`/wiki-link, clamp-at-280 "show more",
one-expanded-at-a-time) is unchanged — only the data source moved from
client state to a server fetch. Verified live: played a track to a
real trivia result, reloaded the page, logged back in — the chip was
still there, proving persistence (this is the concrete thing 0.3.2
could never do).

**Two real AI bugs found and fixed in the same 0.3.3 round** (from
production logs + a direct user report: "sometimes AI won't give
anything and re-requesting fails, and if I change AI provider yields
nothing — I need to reload the page"):

1. `providers.py`'s `_offline_until` is a single **global, cross-user,
   cross-provider** cooldown (120s) — `enricher.py`'s `_worker()` sets
   it via `mark_offline()` on ANY failed attempt and checks it via
   `is_offline()` before even trying again, so one failure from one
   user on one provider silently no-ops every enrichment attempt from
   *everyone*, on *every* provider, for two minutes — including a
   deliberate "Re-ask AI" click. That's "re-requesting fails." Fixed:
   `Enricher.invalidate()` (what both "Re-ask AI" and a provider switch
   call) now calls `providers.clear_offline()` first — a human
   explicitly asking again is exactly the case the cooldown shouldn't
   block; it exists to stop *automatic* background retries from
   hammering a genuinely down provider, not to veto a deliberate one.
2. `routers/enrich.py`'s `activate_provider()` (`POST
   /api/enrich/providers/activate`, what the provider dropdown calls)
   updated `enricher.provider` but never re-asked about the
   currently-playing track — the panel kept showing the previous
   (often failed/empty) result until a separate manual re-ask, which
   itself could still be blocked by bug #1. That's "change AI provider
   yields nothing." Fixed: it now calls `enricher.invalidate(...)`
   immediately after a successful switch, using new `Enricher.last_key`/
   `last_artist`/`last_title`/`last_performer` fields (set in `submit()`
   alongside the existing `last_key`) so the router doesn't need
   `routers/ws.py` to thread that state through separately.
   `is_offline()` global cooldown itself was deliberately left as a
   single flag (not made per-provider) — that's a bigger, riskier
   change to the fallback-chain logic for a problem the two fixes above
   already solve for the reported symptom; noted as a known remaining
   limitation, not silently dropped.

**Root cause of "reload fixes it"**: purely coincidental — by the time
a frustrated user gives up and reloads, the 120s cooldown has usually
already expired on its own. Reloading itself does nothing special.

Verified live end-to-end via Playwright: forced a real failure (pointed
`ollama_url` at an unreachable port, confirmed "No liner notes" via a
real `llm_ollama()` connection-refused path — not simulated), then
switched to opencode via the dropdown with zero manual re-ask, and
confirmed a fresh, successful enrichment landed ~30s later — the exact
reported bug sequence, now fixed, confirmed via `docker logs`-style
request tracing (`POST .../activate` immediately followed by a real
opencode health-check + session-create, not silence).

**Confirmed, not assumed**: the shared AI trivia cache (`cache.py`,
`provider::language::raw_title` key, added in 0.2.1) already handles
a third language with zero code changes — the key was never hardcoded
to a fixed set of two languages, so switching en → it on the same track
correctly misses the cache and triggers a fresh request in the new
language, exactly as the user asked to confirm before this feature was
built.

## Named-provider status message (added 2026-09-06, 0.3.4)

"Asking the AI provider…" now says which one — "Asking opencode…",
"Asking NIM…", "Asking ollama…" — via a new `nowPlaying.askingNamedProvider`
i18n key (`{provider}` placeholder) rendered when `useProviders()`'s
`active` is non-empty, generic message kept as the fallback.

**Real bug found and fixed while building this, not assumed**: the
provider name the frontend shows (top-right pill, and now this status
line) came from `GET /api/enrich/providers`'s `active` field, which
returned raw `enricher.provider` — the user's own *explicitly saved*
preference, empty by default. A fresh account that never explicitly
picked a provider showed "none" in the pill even while enrichment was
correctly succeeding via opencode's automatic fallback (confirmed live:
real trivia arrived, pill said "none" the whole time). `enricher.py`
already had `active_provider()` (the fallback-resolved provider,
already used internally by `_llm()`'s ordering logic) — `list_providers()`
in `routers/enrich.py` just wasn't using it. Fixed to call
`await enricher.active_provider()` instead. `activate_provider()`'s own
returned `active` is deliberately left as raw `enricher.provider` —
right after an explicit switch, that value IS the user's real choice,
not a fallback.

**Deliberately not built**: staged phase progress (asking → LLM
responded → Wikipedia lookup → composing), which the user asked about
directly and was talked out of after checking real timing — the LLM
call is 10-90+ seconds of a track's enrichment time, Wikipedia
resolution (`wiki.py`) is under a second total across all its sub-calls
even in the slow fallback path (`_search()`'s up-to-8-request chain, see
"AI provider connection test" section above). A phase indicator would
show "asking" almost the entire wait and then flash through the rest
in under a second, which reads as a stall-then-flicker, not real
progress — not worth the new WS message types and instrumentation
across `enricher.py`/`wiki.py` it would require.

## README ↔ KB.md cross-linking (fixed 2026-09-06, 0.3.5)

User pointed at the original terminal-app project's own README
(`~/src/mradio/README.md`) as the reference: it links to `KB.md`
repeatedly and deliberately — a top nav line, an early "full detail
lives in KB.md" pointer, deep links to *specific* sections next to the
feature they explain, a closing call-to-action link. mradio-web's
README had exactly one bare `[KB.md](KB.md)` link before this. Fixed to
match: top nav line, early pointer paragraph, deep links
(`KB.md#N-section-slug`) next to each relevant "What it does" bullet, a
full section-by-section link list under "Getting started," and a
closing "→ Open the Knowledge Base ←" link. See
[[feedback_i18n_and_readme_kb_links]] for the standing rule: any new
feature that gets its own KB.md section should also get a matching
README link, going forward.

## Saved volume ignored on reload (fixed 2026-09-06, 0.3.6)

Reported directly by the user: volume always reset to 70% on page
reload, even though the actual set level (e.g. 27%) was genuinely
persisted server-side — confirmed via a direct `GET /api/config` check
before reproducing anything in the UI.

Root cause, found by reading `Dashboard.tsx`/`usePlayer.ts` together,
not guessed: `Dashboard.tsx` calls `usePlayer(config?.volume)`, and
`usePlayer`'s `useState({...INITIAL_STATE, volume: initialVolume ?? 70})`
only ever reads that constructor argument on the component's *first*
render. `useInitialConfig()` fetches `/api/config` inside a `useEffect`
(async, after mount) — so on that critical first render, `config` is
still `null`, `config?.volume` is `undefined`, and `70` gets locked in
permanently. When the real config later arrives, nothing re-applies
it — `theme`/`language`/`mute`/`last_url` are all explicitly re-synced
once config loads (in `Dashboard.tsx`'s `useEffect(() => {...}, [config])`),
volume was the one field that wasn't.

Fixed with a new `usePlayer.ts` function, `applySavedVolume(volume)` —
deliberately separate from the existing user-facing `setVolume()`
(which always re-PATCHes `{volume, mute: false}`, and would have
wrongly cleared a saved mute if reused here for the initial sync).
`applySavedVolume` only sets `audio.volume`/`state.volume`, no network
call, no mute side effect. Called from the same config-loaded effect
in `Dashboard.tsx` right alongside the existing theme/mute/language
syncs.

**Investigation footnote, not a real bug**: while verifying this fix
live, a mute-persistence test against the Vite *dev server*
(`npm run dev`) briefly appeared to also break — mute would show as set
right after clicking, then silently clear itself on reload. Traced to
React 19's `StrictMode` (enabled in `main.tsx`) intentionally
double-invoking effects with no cleanup function in development —
`Dashboard.tsx`'s config-loaded effect calls `player.toggleMute()`
directly (a non-idempotent toggle) with no cleanup, so StrictMode's dev
double-invoke cancels it right back out. Confirmed via a real
production build (`npm run build && npm run preview`, which doesn't
double-invoke) that mute persistence is fine in what actually ships —
this was purely a dev-server-only artifact of how the verification was
done, not a shipped bug. Worth noting as a latent code-quality
observation (an effect calling a non-idempotent toggle function is
fragile against StrictMode/concurrent-rendering assumptions) but not
worth "fixing" on its own since production behavior is already correct.

## "Install as web app" showed a generic icon, not mradio's own (fixed 2026-09-06, 0.3.8)

Reported by the user: Edge's "Install as web app" / "Create a
shortcut" used a generic placeholder icon instead of mradio's own
lightning-bolt favicon, even though the favicon itself renders fine in
the browser tab. User's own hunch (confirmed correct): a favicon alone
isn't enough — installed-app icons are a separate system.

Root cause: `index.html` only had `<link rel="icon" type="image/svg+xml"
href="/favicon.svg">`, which controls the browser tab only.
"Install as web app"/"Add to home screen" flows read a completely
separate `manifest.webmanifest` file with **raster PNG** icons (SVG in
a manifest's `icons` array isn't reliably supported by
Chromium/Edge's install flow) — no manifest existed, so the browser
fell back to a generic icon. iOS Safari ignores the manifest entirely
and needs its own `<link rel="apple-touch-icon">` tag, which also
didn't exist.

Fix: generated `manifest.webmanifest` plus `icon-192.png`,
`icon-512.png`, `icon-maskable-512.png` (extra padding/safe-zone for
Android's adaptive-icon masking), and `apple-touch-icon.png`, all in
`frontend/public/`. Icons were rasterized from the *existing* favicon
mark (not redrawn) via `rsvg-convert`, centered on a square tile filled
with the app's own dark background color rather than plain white/
transparent — computed as `#111419` by manually converting the CSS
custom property `--paper: oklch(19% 0.012 260)` to sRGB (OKLab
intermediate space, matrix multiply; no existing tool/dependency in
the project does this conversion). Added the matching
`<link rel="apple-touch-icon">`, `<link rel="manifest">`, and
`<meta name="theme-color" content="#111419">` tags to `index.html`,
right below the existing favicon link.

Verified with more than a JSON eyeball-check: used Playwright + Chrome
DevTools Protocol's `Page.getAppManifest` — the same manifest parser
Edge/Chrome's actual install flow uses — confirming `errors: []` and
correct resolution of all three icon sizes/purposes, `display:
standalone`, and both colors.

**Follow-up, iOS (fixed 2026-09-06, 0.3.9)**: 0.3.8's manifest fixed
Android/Chrome install, but the user specifically asked to confirm
iOS was covered too — it wasn't, fully. iOS Safari doesn't rely on the
manifest the way Chrome does: it needs its own
`apple-mobile-web-app-capable` meta tag to launch standalone (without
it, "Add to Home Screen" creates an icon that just opens Safari
instead of running full-screen), `apple-mobile-web-app-status-bar-style`
for the status bar, and `apple-mobile-web-app-title` for a clean name
under the icon (otherwise iOS uses the `<title>` tag verbatim, em-dash
and all). The `apple-touch-icon.png` already shipped in 0.3.8 was
already the correct 180×180 size Apple expects — confirmed via `file`/
`sips`, no new icon needed, only the three meta tags in `index.html`.

## User display names + email in admin UI (added 2026-09-06, 0.4.0)

First half of a two-part user-account request (second part — SMTP/
self-service forgot-password — not built yet, see Next steps). The
admin dashboard showed raw `username` as the only identity everywhere;
user wanted a proper, emoji-capable display name (screenshot reference:
Tracearr's leaderboard, names + flag emoji per person) shown instead.

**The one genuinely novel piece**: adding a `full_name TEXT` column to
`users`, a table that already has real rows in production. Every prior
schema change in this codebase (`play_history`, `trivia_history`, the
`must_change_password` column) was either a brand-new table or a column
present since the very first commit — there was no working precedent
for "add a column to an already-shipped table with live data." SQLite
has no `ALTER TABLE ADD COLUMN IF NOT EXISTS`, so `db.py` gained a
small idempotent helper, `_ensure_column(db, table, column, coltype)` —
checks `PRAGMA table_info()` first, only runs `ALTER TABLE` if the
column is actually missing — called from `init_db()` right after
`executescript(SCHEMA)`. Written generically so it's the reusable
pattern for the *next* additive column too, not a one-off. No default
value: `NULL` for pre-existing rows is exactly the "unset, fall back to
username" state the UI already needed.

Verified this specifically and rigorously (not just "it worked on a
fresh DB"): built a throwaway `mradio.db` by hand with the *old* schema
(no `full_name` column) plus two real user rows, ran the new `init_db()`
against it directly — confirmed the column gets added, existing rows
survive untouched (`full_name = NULL`), and running `init_db()` a
second time against the now-migrated file doesn't error (no duplicate-
column crash). Also confirmed a from-scratch DB still gets the column
via the same code path — deliberately kept as one path, not two that
could drift (the column is *not* added directly to `SCHEMA`'s `CREATE
TABLE users`, precisely so every DB, fresh or existing, goes through
`_ensure_column`).

`full_name` threads through every place `username` was previously shown
as identity: TopBar chip/initials, and all three Analytics identity
columns (Live now, Top listeners bar list, Recent history table) — via
`backend/app/history.py`'s SQL joins gaining `u.full_name` alongside
`u.username`, and a new shared frontend helper,
`frontend/src/utils/format.ts`'s `displayName(u)`, which is the single
source of the "show full_name if set and non-blank, else username"
fallback rule (avoids 5+ inline `?? .trim() ||` repetitions). `username`
itself is *never* removed from any model/type — it stays as the
fallback key and the login credential, exactly as before.

**Decision: admin-only for now, not self-service.** Set via the Users
page's create-user form (gained Full name + Email inputs) and a new
"Edit profile" row action (two sequential `window.prompt`s, matching
the page's existing no-modal-library pattern already used by
`resetPassword`) — no new "my profile" page for users to self-edit.
Matches this account model's existing philosophy (admin-managed, no
public signup) and avoids inventing new self-service infrastructure for
a first version of a cosmetic field; easy to add later without
touching `update_profile()` at all if ever wanted.

Verified live end-to-end via Playwright: created a user with an actual
emoji in `full_name` ("Marco 🎧"), confirmed it round-trips with zero
mangling through create → SQLite → GET → TopBar chip → all three
Analytics tables; then cleared `full_name` via "Edit profile" and
confirmed the Users table and TopBar correctly fall back to showing the
bare username again.

**Follow-up bug, found by user testing a real longer name (fixed
2026-09-06, 0.4.2)**: "Marco 🎧" alone didn't surface it, but a longer
name with two flag emoji ("Marco Dal Moro 🇮🇹🇺🇸") broke two layouts —
(1) the Users table's first column had no `min-width`, so the name
wrapped token-by-token across 3-4 lines, crushing the row; (2) the
TopBar's `.user-chip` is a fully-round pill (`border-radius: 999px`,
sized off its own content height) with no size cap on `.user-name` and
no explicit size on the adjacent `ChevronDownIcon` `<svg>` (which had
no default size rule anywhere, previously "getting away with it" only
because flexbox was silently shrinking it) — a taller line-height from
some browsers' flag-emoji rendering made the chevron balloon to fill
available space, and the whole round chip ballooned into a giant circle
to match. Fixed with `.admin-table td:first-child { min-width: 12rem }`
(table cell), and on the chip: `.user-name` gained a plain `max-width`
+ `white-space: nowrap` + `text-overflow: ellipsis` (not `flex: 1 1
auto`, which was tried first and made it worse — a growable flex-basis
inside a shape-locked round pill has nothing to constrain it against),
and `.user-chip svg` gained an explicit `14px` size. Verified against
the exact reported case plus a synthetic worse one (very long name, 3
flags) to confirm the ellipsis path actually engages, not just the
common case.

**Not yet done**: self-service "forgot password" via emailed reset
link, and admin-configurable SMTP settings (the second half of the
original request) — deliberately shipped separately since it's a much
higher-risk change (new unauthenticated endpoints, anti-enumeration
correctness, an outbound network dependency). Also found and *not yet
fixed* while investigating: this SPA has no client-side router at all
(`App.tsx` picks screens by auth-state `useState` only), so a future
`/reset-password?token=...` emailed link would 404 against the current
`StaticFiles(html=True)` mount — confirmed via Starlette's own source,
which only serves `index.html` for the root path, not arbitrary
unmatched paths. Needs one small explicit backend route before that
mount when the forgot-password feature is built.

## Settings hub — admin dropdown consolidated (added 2026-09-06, 0.4.1)

User noticed while asking "where do SMTP settings for forgot-password
live?" that the admin dropdown was just accumulating flat entries
("Users", "AI providers", soon "Email") with no ceiling — asked to add
a proper Settings landing page with sections instead, where e.g. the
Users section opens the already-existing Users page.

Replaced the two direct dropdown entries with one "Settings" entry →
new `frontend/src/pages/SettingsPage.tsx`, a simple card grid (`.settings-
grid`/`.settings-card` in `admin.css`) driven by a plain array of
`{page, title, description}` — adding a future section (Email, and
whatever comes after) is one array entry, not a `TopBar.tsx` edit.
Clicking a card calls the same `onNavigate(page)` prop `Dashboard.tsx`
already threads everywhere else (plain `useState<Page>` routing, no
new abstraction). `UsersPage.tsx`/`AISettingsPage.tsx` gained an optional
`onBack` prop rendering a small "← Settings" breadcrumb (`.admin-breadcrumb`)
above their existing header — added specifically because these two pages
are now one level deeper than before (dropdown → Settings → page, vs.
dropdown → page), so a way back to the hub specifically (not all the way
to the player, which "Back to player" already covered) mattered enough
to add, per explicit ask rather than assumption.

Verified live: dropdown now shows only "Settings" for admins (confirmed
the old "Users"/"AI providers" entries are gone), the hub renders both
cards correctly, and clicking a card → breadcrumb → back to hub → other
card all work as a real click-through, not just code review.

The now-planned `EmailSettingsPage` (SMTP + forgot-password, see the
entry above — still not built) will be a third card here, not a new
dropdown entry — this was designed with that in mind, not just for the
two sections that exist today.

## SMTP settings + self-service forgot-password (added 2026-09-06, 0.5.0)

Second half of the account-management request that started with
full_name/email (0.4.0). User explicitly asked about a Gmail OAuth
wizard for this — discussed and decided against it: sending mail via
Gmail's API needs the `gmail.send` scope, a Google "restricted scope"
requiring a formal security review once an app leaves testing mode
(weeks, possibly a paid CASA audit) — wildly disproportionate for a
self-hosted app with a handful of accounts. A Gmail **App Password**
achieves the identical practical outcome (authenticate as "this app,
sending as my address") with a password field instead of an OAuth
consent flow, zero review risk, and is literally Google's own
documented recommended path for small/personal SMTP use cases — not a
compromise. `EmailSettingsPage.tsx` gives Gmail a first-class walkthrough
(2FA prerequisite, direct link to `myaccount.google.com/apppasswords`)
while still accepting any other SMTP provider generically.

**Reset-link base URL — the multi-domain decision.** User specifically
asked about running this behind two domains (existing DDNS + a possible
Cloudflare Tunnel domain) and whether a reset email would "know" which
one to link back to. Deliberately did *not* hardcode a single admin-set
public URL for this (an earlier draft plan from a sub-agent proposed
exactly that, reasoned from `KB.md` only documenting `X-Forwarded-For`/
`-Proto` as trusted headers — overridden after this conversation).
Instead, `routers/auth.py`'s `_base_url()` prefers the *request's own*
`X-Forwarded-Host`/`Host` header, falling back to an optional admin
`public_url` override only if that's ever missing — so whichever domain
a listener actually used to reach the app is automatically the one that
comes back in their reset email, correct for any number of domains
pointing at the same box with zero per-domain config. `KB.md` §3 updated
to note the app now also relies on `X-Forwarded-Host` (NPM forwards it
by default already, same as the other two headers — nothing to
configure).

**The one genuinely new piece of frontend infrastructure**: this SPA
has no client-side router at all (`App.tsx` picks screens via plain
auth-state `useState`). A `/reset-password?token=...` emailed link would
have 404'd against the existing `StaticFiles(html=True)` mount, which
(confirmed by reading Starlette's own source) only serves `index.html`
for the root path, not arbitrary unmatched paths. Fixed with one
explicit `@app.get("/reset-password")` route in `main.py` returning
`FileResponse(index.html)`, registered before the static mount — no
router library added. `App.tsx` then checks
`window.location.pathname === '/reset-password'` before the auth gate
(must work even with a stale session cookie present) and renders the
new `ResetPasswordScreen`.

**Security properties, built in from the start, not bolted on**:
- `password_resets` table + `password_reset.py` reuse `auth.py`'s exact
  session-token pattern (`secrets.token_urlsafe(32)`, SHA-256 hash at
  rest via the shared `_token_hash()` helper, never the raw token
  stored) — no new crypto invented. 1-hour TTL (vs. sessions' 30 days),
  and single-use via a `used_at` timestamp column.
- `POST /api/auth/forgot-password` returns the **exact same** `{"ok":
  true}` whether the email exists, is disabled, sending failed, or SMTP
  isn't configured at all — verified live via Playwright by comparing
  the full rendered response text byte-for-byte between a real and a
  fake email, not just spot-checking.
- Verified end-to-end with a real (if throwaway) SMTP target — a local
  `aiosmtpd` debug server (installed only in a scratch venv, never added
  to `requirements.txt`) — including a full round trip: request reset →
  confirm zero `password_resets` rows for a non-existent email vs. one
  real row for a registered one → consume the token via the actual
  running `/reset-password` page (not just calling the function
  directly, to also prove the routing fix above works) → confirm login
  with the new password succeeds → confirm reusing the same token a
  second time is correctly rejected.
- `EmailSettingsPage.tsx` reuses `AISettingsPage.tsx`'s exact
  secret-field pattern (separate `passwordInput` state, empty by
  default, placeholder shows the redacted saved value, only sent if
  non-empty) — extracted `KbNote`/`TestBadge`/`TestState` into a new
  shared `components/AdminSettingsShared.tsx` so both settings pages
  import the same implementation instead of duplicating it.

Ships as the third card on the Settings hub (see entry above) — exactly
where that feature was designed to accommodate it.

**Follow-up UX fixes from real use (fixed 2026-09-06, 0.5.1):**
- **"Test" before "Save" gave a misleading error.** `POST /api/settings/
  smtp/test` originally only ever read the *persisted* settings
  (`smtp_settings.load()`), so clicking Test right after filling the
  form but before Save tested the old/empty saved config, not what was
  visibly typed — producing "SMTP is not configured" even though the
  form looked filled in. Root cause was an inconsistency with
  `AISettingsPage.tsx`'s own test buttons, which already test
  in-progress form values via an `overrides` param — the SMTP test
  endpoint just hadn't been given the same capability. Fixed by
  threading `overrides: SmtpSettingsUpdate` through `POST .../test` and
  `email_sender.send_email()` (merged onto the saved config, same
  `{**saved, **overrides}` pattern the AI test endpoint already uses),
  and having `EmailSettingsPage.tsx`'s `sendTest()` pass the current
  form state — same care as the AI page's password-field handling: only
  include `password` in the override if `passwordInput` is non-empty,
  so testing doesn't accidentally overwrite/blank out an already-saved
  password for the test call. Also reworded the genuinely-empty-host
  case from "SMTP is not configured." to "Enter a host and click Save
  before testing." — actionable, not just descriptive.
- **Placeholder text looked pre-filled.** No `::placeholder` style
  existed anywhere in `admin.css` — placeholders (e.g. Host's suggested
  `smtp.gmail.com`) rendered close enough to real input text to read as
  already configured at a glance, which is exactly what confused this
  into thinking Save wasn't needed. Fixed with an explicit
  `.settings-row input::placeholder { color: var(--ink-3) }` (paired
  with `color: var(--ink)` on real values) — reuses the same ink-scale
  tokens already used everywhere else in this app for primary vs. muted
  text, so it's consistent, not a one-off color. Benefits the AI
  Providers page's fields too, not just Email settings, since they share
  the same CSS rule.

**Real follow-up (fixed 2026-09-06, 0.5.2)**: the placeholder fix above
appeared "not to work" for the user even after the 0.5.1 deploy —
investigated thoroughly rather than assuming user error: confirmed via
direct `curl` against the live LT container that the deployed CSS bundle
genuinely contained the fix, and via a fresh Playwright render + pixel
sampling (darkest pixel in the placeholder text vs. real text: `rgb(118,
123, 130)` vs `rgb(24, 29, 38)` — a large, real, correctly-applied
contrast gap) that the fix works correctly when actually loaded. Root
cause was somewhere else entirely: `backend/app/main.py`'s static file
serving set **no `Cache-Control` header at all** on any file, including
`index.html` — the one unhashed file that tells the browser which
hashed `/assets/*.js`/`*.css` filenames to load. A browser that had
already loaded the app before a deploy could keep serving `index.html`
from its own heuristic cache indefinitely, silently pinning that browser
to whichever old JS/CSS bundle `index.html` referenced at load time —
explaining exactly this "the fix isn't visible even though it's
deployed" symptom, and explaining why a full test suite passing
end-to-end (this session verified the actual 0.5.1 fix worked, correctly)
still didn't catch it: the bug was in cache *policy*, not in the fixed
code itself. Fixed with a small `_CacheAwareStaticFiles(StaticFiles)`
subclass overriding `file_response()`: `index.html` (and the `/reset-
password` route, which also serves it) gets `Cache-Control: no-cache`
(always revalidated), while genuinely content-hashed asset files get
`public, max-age=31536000, immutable` (safe to cache forever, since any
content change produces a new filename) — the standard, correct caching
strategy for Vite-style hashed-asset builds, and one this app should
have had from its very first release rather than leaving cache behavior
to browser heuristics. Verified via `curl -sI` against both a hashed
asset and `index.html`/`/reset-password` directly, confirming the
expected header on each.

**The 0.5.2 fix itself had the same bug it was fixing, for a different
file (fixed 2026-09-06, 0.5.5)**: `_CacheAwareStaticFiles`'s rule was
"cache everything immutably except `index.html`" — true for `/assets/
*.js`/`*.css` (genuinely Vite-content-hashed), false for every other
file this app serves from `public/` verbatim with a **stable**
filename: `manifest.webmanifest`, `favicon.svg`, `apple-touch-icon.png`,
`icon-*.png`. Surfaced when the user renamed the app (0.5.4,
"mradio" → "mradio web") and the OS install prompt kept quoting the old
name even after uninstalling and retrying — confirmed the server was
serving the correct new manifest content the whole time
(`curl` against LT showed `"name": "mradio web"`), so the only
explanation left was the browser never re-fetching the manifest at
all, which a 1-year `immutable` `Cache-Control` on it fully explains.
Fixed by checking for `/assets/` in the path explicitly (verified via
`find dist -maxdepth 1` that this is genuinely the only hashed
directory Vite produces) rather than the previous "not index.html"
exclusion-based logic — every other static file, `index.html` included,
now gets `no-cache`. **Pattern worth remembering**: a cache-header fix
scoped as "trust everything except this one known-bad file" is fragile
by construction — the safer default is "trust nothing except this
narrowly-identified known-safe location," which is what this second
pass landed on.

**Genuine miss, corrected 2026-09-06, 0.5.3**: the user's original
0.5.0-era instruction was "replace the placeholder text `smtp.gmail.com`
with `e.g. smtp.gmail.com`" — i.e. change the *wording*. 0.5.1 instead
only changed the placeholder's *color* (`.settings-row input::placeholder
{ color: var(--ink-3) }`), leaving the bare, unprefixed text unchanged.
This looked plausible from a code-review distance (a real, measurable
contrast difference genuinely exists — verified via pixel sampling
in that entry) but missed the actual, specifically-requested fix,
and wasted a full round of the user re-explaining and re-screenshotting
before it was caught. The color fix alone was never going to be enough:
`smtp.gmail.com` is not a hypothetical example for someone using
Gmail, it's the literal, exact value they're supposed to type — no
amount of color/contrast styling changes the fact that an empty field
showing the real answer looks pre-filled. Fixed for real this time by
changing the placeholder strings themselves to `"e.g. smtp.gmail.com"`
and `"e.g. https://radio.example.com"` (`EmailSettingsPage.tsx`), plus
`AISettingsPage.tsx`'s Ollama Server URL placeholder for the same
reason even though its example IP is less likely to collide with a
real value. **Lesson**: when a user gives a specific instruction
("change X to Y"), verify the literal instruction was executed, not
just that the underlying complaint (visual confusion) seems addressed
by some plausible-sounding related change — these are not always the
same fix, and only the actual diff proves which one happened.

## Brand text renamed: "mradio / dial room" → "mradio web / player" (2026-09-06, 0.5.4)

User disliked the original "mradio — Dial Room" branding — wanted the
top-bar brand mark to read "mradio web" (serif, unchanged styling) with
"player" as the small subtitle (unchanged mono styling), and the
browser tab/PWA name to be just "mradio web", not "mradio — Dial Room".
Pure text swap, no CSS/component changes — `.brand-mark`/`.brand-sub`
already used the right fonts (`--font-display` serif / `--font-mono`),
this was never a styling complaint. Touched every occurrence: the
`<span className="brand-mark">`/`<span className="brand-sub">` pair
appears in 5 files (`TopBar.tsx`, `LoginScreen.tsx`,
`ChangePasswordScreen.tsx`, `ForgotPasswordScreen.tsx`,
`ResetPasswordScreen.tsx` — the last two new in 0.5.0's forgot-password
work, easy to miss if not grepped for explicitly), plus
`index.html`'s `<title>` and `apple-mobile-web-app-title` meta tag, plus
`manifest.webmanifest`'s `name`/`short_name`. Grepped for the literal
strings across the whole frontend before editing, specifically to avoid
another repeat of the previous entry's lesson (partial fixes that miss
some of the actual occurrences).

## "Add user" / "Edit profile" moved off window.prompt (added 2026-09-06, 0.5.6)

User asked for a "proper page" instead of the ephemeral `window.prompt`
popups for these two actions. Chose an in-page modal over a full
separate page (explicit choice, not a default) — this app has no
routing library and no modal precedent yet, but a modal is the lighter
addition for a handful of fields versus a full navigate-away page, and
keeps the Users table visible underneath.

New `frontend/src/components/Modal.tsx` — thin wrapper around the
native `<dialog>` element (`showModal()`/`close()` driven by an `open`
prop), not a hand-rolled overlay: gets ESC-to-close, backdrop, and
focus trapping for free from the browser, matching this codebase's
"reuse the platform, minimal abstraction" style rather than pulling in
a modal library. New `frontend/src/styles/modal.css` styled with the
same design tokens (`--paper-2`, `--radius-lg`, etc.) already used
everywhere else — no new visual language introduced.

`UsersPage.tsx`'s inline create-user form (which was already a real
form, just awkwardly living at the bottom of the table) and the
`editProfile()` `window.prompt` chain were both replaced with the same
`Modal` component, each with its own open/busy/error state. Reused
existing `common.cancel`/`common.save` i18n keys rather than adding new
ones. `resetPassword()`/`deleteUser()` deliberately *not* touched —
user only asked about "Add user"/"Edit profile" specifically, and a
single confirm/prompt for a one-field action is a much smaller UX
complaint than a two-prompt chain for a two-field edit; left as a
possible future ask rather than assumed in scope.

Verified live: modal opens/closes correctly (including ESC and
backdrop-click, both confirmed via Playwright), create and edit both
round-trip correctly through the existing API endpoints unchanged
(no backend changes needed for this — pure frontend UI swap), and the
modal renders correctly in both dark and light themes.

## Station logos, cached (added 2026-09-06, 0.5.18)

The now-playing panel's station row had visible empty space next to the
station name — the user asked whether a logo could be shown there, and
whether it should be cached.

**No universal "radio station logo" API exists.** Scraping the stream
URL's own domain doesn't generalize: tested live with VCR Classica+,
whose curated stream URL (`uk2.streamingpulse.com`) is a third-party UK
CDN entirely unrelated to the real broadcaster's branding
(`veniceclassicradio.eu`). **Radio-Browser** (`api.radio-browser.info`, a
free, open, community-maintained internet radio directory) is the right
source — confirmed live it already indexes this exact stream URL via
`/stations/byurl?url=...` and returns the real station's own favicon, not
the CDN's. Confirmed this is best-effort, not guaranteed: WQXR's curated
URL isn't indexed by exact match at all, but resolves via a name-search
fallback (`/stations/search?name=...`); some stations return no favicon
either way. Lookup order in `backend/app/radio_browser.py`: exact
stream-URL match first, name search second, `None` if both miss —
mirrors `wiki.py`'s existing best-effort posture (every failure mode
degrades silently, never raises).

**Caching (new `backend/app/station_logos.py`)**: user was asked whether
this belongs in SQLite (their original suggestion) or as a JSON file
mirroring the existing AI trivia cache (`cache.py`) — chose the JSON
file, since station identity is global/stateless, matching this app's
existing convention that SQLite is reserved for per-user/relational data
(users, sessions, play history) while global lookup caches use
`jsonstore.py`. **Cache misses are stored explicitly as `{"logo": None}`,
not merely omitted** — this is the detail that actually matters: without
it, a station with no findable logo would re-query Radio-Browser on every
single play, defeating the point of caching. Confirmed live: repeat
lookups for both a real hit and a confirmed miss both serve from cache in
single-digit milliseconds vs. 300-650ms for the first (network) lookup.

**Real-world data-quality bug caught during verification, not
hypothetical**: VCR Classica+'s Radio-Browser-listed favicon
(`veniceclassicradio.eu/player/new/image/l.png`) actually 404s today —
the site reorganized its paths since Radio-Browser last indexed it. Community-maintained
directories go stale; a naive "cache whatever favicon field is present"
implementation would have permanently cached a dead image link for this
station. Fixed by adding a `HEAD` request (`client.head(favicon,
follow_redirects=True)`, checking for `200`) before accepting a favicon
candidate, in `radio_browser.py`'s `_first_working_favicon()` — same
verify-before-trust pattern `wiki.py` already uses for article URLs
(`client.head(url)` before returning a Wikipedia link). This is a
network-request cost paid once per station (amortized away by the
success/miss cache either way), not per play. Frontend also has a
belt-and-suspenders `onError` handler on the `<img>` (`NowPlayingPanel.tsx`)
that hides a logo that still somehow fails to load client-side (e.g. a
site that works for a HEAD probe but blocks hotlinked image loads) —
degrades to "no logo shown," never a broken-image icon.

Frontend: `frontend/src/hooks/useStationLogo.ts` (new hook, `useProviders.ts`/
`useGenres.ts` shape) fetches `GET /api/stations/logo?url=...&name=...`
keyed on the station's URL/name changing, not on every render.
`NowPlayingPanel.tsx` renders the `<img class="station-logo">` as a
sibling of `.station-strip` inside `.panel-head` (already `flex;
justify-content: space-between`) — lands on the right side of the same
row as the dot + name with zero other layout change, matching the user's
explicit placement request. `.station-logo` is height-constrained (28px)
with `max-width: 120px` and `object-fit: contain`, since real logos vary
wildly in aspect ratio (square favicons vs. wide wordmarks — confirmed
both shapes live: WNYC's square vs. VCR's wide wordmark before it was
rejected as stale). Renders nothing (not a placeholder box) when no logo
is found — most stations, especially user-added custom stream URLs,
won't have one, and an empty row reads better than a broken-image icon.

## Pins mode kept the old size-by-count encoding after the heatmap split (fixed 2026-09-06, 0.5.17)

Right after [[mradio_web_status]]'s 0.5.16 pins/heatmap split shipped, the
user noticed Pins mode was *still* using `radius={6 + count}` — the split
correctly gave heat-intensity its own dedicated view, but nobody had
actually removed the same encoding from the pins view it was split out of,
so pins were still silently double-jobbing. Fixed by switching from
`CircleMarker` (a Leaflet vector shape with a numeric radius prop) to a
plain `Marker` using a custom `L.divIcon` — the icon's `html` is literally
`<span class="live-dot" />`, i.e. it reuses the *exact* pulsing green dot
markup/CSS/keyframe animation from the player's live-listener indicator
(`.live-dot` + `.live-dot::after` + `@keyframes pulse-ring` in
`dashboard.css`), per the user's own suggestion ("why don't you use that
strange blinking green dot"), rather than inventing a new fixed-size
marker style from scratch. Required explicitly importing `dashboard.css`
into `AnalyticsPage.tsx` too (previously only `admin.css`/`analytics.css`)
— technically already present in the single Vite bundle by the time this
page is reachable (only navigable from within `Dashboard.tsx`'s own tree),
but importing it directly here documents the actual dependency instead of
relying on incidental load order from an unrelated page. New
`.map-live-dot-icon { background: none; border: none }` rule strips
Leaflet's default `.leaflet-div-icon` white-box-with-border styling, which
would otherwise show behind the transparent dot. `count` is no longer used
for anything in Pins mode — it still exists on the `Pin` type and still
drives Heatmap mode's intensity normalization, which is exactly where that
signal belongs now. Verified live via Playwright: seeded 5 geographically
distinct history rows, confirmed every rendered marker measures exactly
8×8px regardless of underlying session count, and that the tooltip
(location label) still works on hover.

## Listener map showing a different count than "Live now" (fixed 2026-09-06, 0.5.22)

User noticed (via screenshot) "Live now" showed 1 listener while the map
showed 2 pins, and reasonably assumed this was a bug. It wasn't a data
bug — `AnalyticsMap`'s `buildPins()` had always deliberately unioned live
sessions AND the (paginated) recent-history table's current page into
one pin set, while "Live now" is strictly real-time (`nowplaying.live_snapshot()`,
only actual open WebSocket connections). Two legitimately different,
both-correct signals that looked inconsistent side by side with no
labeling to explain why. Also found a second, more subtle latent bug
while fixing this: the map's "history" pins were literally whatever page
of the *history table* happened to be loaded (`historyOffset` state),
not a stable "recent N sessions" — paging the table at the bottom of the
page would silently change what the map above it showed, with zero
visual connection between the two.

Fixed via a second, independent toggle (**Live only** / **Live + recent
history**) next to the existing Pins/Heatmap toggle, separated by a
`.map-picker-sep` divider so they read as two separate controls, not one
row of four equal options. **Defaults to "Live only"**, so out of the
box the map always matches "Live now" exactly — no more surprise
mismatch for anyone who doesn't know to look for the toggle. Fixed the
page-dependent-history bug simultaneously: the map's history fetch is
now a dedicated `GET /api/analytics/history?limit=25&offset=0` call,
triggered only when scope is `'live+history'`, entirely independent of
the history table's own `historyOffset`-driven pagination fetch — same
endpoint, deliberately separate state so one doesn't leak into the
other. `buildPins(sessions, scope === 'live+history' ? mapHistory : [])`
is the one-line mechanism switching between the two views. Verified live
with a real local playback session (which correctly resolves to 0 map
pins in "Live only" mode when tested from localhost — loopback IPs have
no GeoLite2 location by design, see the geoip exclusion noted elsewhere
in this file — production traffic through the real reverse proxy would
resolve normally) plus 2 seeded historical rows that appeared exactly
when switching to "Live + recent history" and disappeared switching
back, confirmed via screenshot both ways.

## Listener map pins/heatmap toggle (added 2026-09-06, 0.5.16)

The original listener map (`AnalyticsMap` in `AnalyticsPage.tsx`) drew one
`CircleMarker` per unique city with `radius={6 + count}` — the user pointed
out (via a Tracearr screenshot comparison) this was quietly doing two jobs
at once: a location pin map AND a crude heat-intensity encoding (bigger
circle = more sessions), which muddies both readings compared to having
each as its own dedicated view. Fixed by adding a `MapMode = 'pins' |
'heatmap'` toggle (two buttons reusing the existing `.since-btn` style
already used by the stats since-picker — kept UI patterns consistent
rather than inventing a new switch component) plus a real heat layer via
the `leaflet.heat` plugin (new dependency + `@types/leaflet.heat`, the
only addition to this app's near-zero-dependency stance besides
`leaflet`/`react-leaflet` themselves — no reasonable hand-rolled
substitute for either). `HeatLayer` is a small function component that
calls `useMap()` (from `react-leaflet`) and imperatively adds/removes an
`L.heatLayer(...)` in a `useEffect`, since `leaflet.heat` has no React
wrapper of its own — this is the standard integration pattern for
non-React Leaflet plugins inside react-leaflet. Heat point intensity is
`count / max(counts)`, i.e. normalized against the busiest location in
the current pin set, not an absolute scale — matches how `CircleMarker`
radius already worked. **`minOpacity: 0.4`** was necessary — without it,
low-count outlier locations (e.g. a single session from Tokyo, against a
6-session European cluster) rendered essentially invisible at default
opacity, defeating the point of a map showing *where* listeners are, not
just *where the most* are. Gradient customized away from the plugin's
default blue→cyan→lime→yellow→red to a warm amber→orange→red-orange scale
(`{0.2: '#fde68a', 0.5: '#fb923c', 0.8: '#ea580c', 1: '#c2410c'}`) to
visually match the Tracearr reference screenshot's heat-map look, which is
what the user was pointing to as the desired outcome. Pins mode is the
default on page load (unchanged from before this feature — no surprise
behavior change for existing users). Verified live via Playwright with
seeded `play_history` rows (a 6-point European cluster + 3 geographically
isolated points in New York/Sydney/Tokyo) to produce a visually
meaningful heat blob and confirm outlier visibility — confirmed clean
layer teardown when switching modes back and forth (no stale canvas or
duplicate markers), toggle active-state styling, and i18n keys
(`analytics.mapPins`/`analytics.mapHeatmap`) across all 13 languages.

## Analytics live table's status-dot column crowding the rest (fixed 2026-09-06, 0.5.7)

Direct fallout from the earlier "long display name" table fix (0.4.2's
`.admin-table td:first-child { min-width: 12rem }`, added for the
Users table's name column) — every table sharing the generic
`.admin-table` class inherited that rule, including the Analytics
"Live now" table, whose *first* column is just a small pulsing status
dot with no text at all. That dot column was being forced to 12rem
wide, visibly starving User/Station/Genre/Location/Elapsed of space
and causing them to wrap awkwardly — exactly the kind of layout bug a
generic class-based rule can introduce in a table it wasn't written
for. Fixed by scoping the min-width rule to a new `.admin-table-users`
class applied only to `UsersPage.tsx`'s table, and giving the
Analytics dot column its own `.admin-table-status-col` (`width: 1%` —
the standard CSS trick for "shrink this table cell to its content's
intrinsic width" in table layout) applied to both the dot `<th>` and
`<td>`. **Lesson, same shape as the placeholder-text miss earlier this
session**: a fix scoped to a shared class can silently regress an
unrelated user of that class — worth checking every place a modified
shared class is actually used, not just the one page the fix was
written for.

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
- `providers.py`'s offline cooldown (`_offline_until`) is still a single
  global flag, not per-provider, even after 0.3.3's fixes (see "Trivia
  history" section above) — a genuinely-down provider still blocks
  *automatic* retries for every other provider/user for up to 120s. The
  two 0.3.3 fixes cover every *deliberate* user-initiated retry path
  (manual re-ask, provider switch), which is what the actual reported
  bug needed; making the cooldown per-provider is a real but
  lower-priority follow-up, deliberately deferred as riskier (touches
  the fallback-chain ordering in `active_provider()`/`_llm()` too) for a
  problem already solved for the reported symptom.

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
