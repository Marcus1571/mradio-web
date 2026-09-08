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
  `BEHAVIOR.md` is still skipped — its main rule ("commit and push by
  default") is enforced one layer up by whatever harness/session is
  driving the work, not something the repo itself needs to restate.
  `findings.md` was originally skipped too (built for a different kind
  of work, vetting radio station candidates, that didn't exist in this
  project yet) but **adopted 2026-09-07** once a real matching use case
  showed up: researching additional free AI provider options without
  committing to building any of them yet. `KB.md`, `MEMORY.md`,
  `CHANGELOG.md`, and now `findings.md` are the pieces that map onto
  mradio-web's needs — re-evaluate this list per-project rather than
  assuming it's fixed forever.
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

**Missing-ChatGPT copy bug, caught by the user (0.5.28)**: the AI
settings page's two description strings (`aiDescription` on the
Settings hub, and `aiSettings.intro` on the page itself) were written
before ChatGPT/Codex existed as a provider and were never revisited
when it shipped in 0.5.23 — they still only listed OpenCode, Ollama,
and OpenAI-compatible endpoints. Same root cause as most i18n misses in
this project: a copy string lives in 13 files, and it's easy to add a
whole new feature/provider without grepping for every place the
provider list gets spelled out in prose (as opposed to the `PROVIDERS`
tuple, which is structurally exhaustive by definition). **Lesson**:
when adding a provider, explicitly grep `aiDescription\|aiSettings.*intro`
(or similar "here's the full list of providers, in prose" strings) as
its own checklist item, since these can't be caught by TypeScript,
build, or lint — only by a human reading the sentence.

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

## Language support (added 2026-09-05, 0.2.0 + 0.2.1 + 0.3.1; Portuguese + pattern cleanup 2026-09-06, 0.3.5; French 2026-09-06, 0.3.10; Russian 2026-09-06, 0.5.8; German 2026-09-06, 0.5.9; Greek 2026-09-06, 0.5.10; Dutch 2026-09-06, 0.5.11; Danish 2026-09-06, 0.5.12; Swedish 2026-09-06, 0.5.13; Norwegian Bokmål 2026-09-06, 0.5.14; Japanese 2026-09-06, 0.5.15; Turkish 2026-09-07, 1.0.3; Hebrew + RTL support 2026-09-07, 1.0.4) — fully done

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
Cyrillic, Greek, and CJK scripts alike. Turkish (`tr`, 1.0.3, 14th)
followed the identical 6-spot pattern with no surprises — dotted/
dotless I (İ/ı) and the other Turkish-specific diacritics (ş, ğ, ç)
render correctly with no special handling needed anywhere in the
stack, confirmed via a headless-Chrome screenshot of a throwaway
harness (`DevHarness.tsx`, same disposable-harness technique used for
the 1.0.1/1.0.2 no-ICY-message verification — mounted in place of
`App` in `main.tsx`, screenshotted, then fully reverted, nothing
committed) exercising both a normal playing-with-liner-notes state and
the no-ICY-support message from 1.0.1/1.0.2, both in Turkish. Not
re-verified live against the Analytics/Settings/Users pages this time
(no auth harness set up for those, unlike the Playwright passes used
for German/Russian/Japanese) — the i18n mechanism itself (TypeScript's
`Dict`-shape enforcement, the identical key structure across 14 now-
proven files) is what actually guards those pages, not per-language
manual checking, so this is a reasonable proportionality call, not a
skipped step.

**Hebrew (`he`, 1.0.4, 15th) — first RTL language, needed a real code
change beyond the usual 6-spot pattern.** Every prior language reused
the document's default `ltr` direction with zero layout changes; Hebrew
genuinely needs the whole page mirrored (text alignment, the volume
slider's fill direction, etc.) or it reads backwards. Added `rtl?: true`
to `LANGUAGES` entries in `i18n/index.ts` (only Hebrew's entry sets it)
and a new `applyDirection(lang)` helper there that sets
`document.documentElement.dir` — mirrors the exact existing pattern
`Dashboard.tsx` already used for `data-theme` (same file, same
`useEffect`/handler shape), not a new abstraction. Called from both
spots `language` state changes: the config-load effect (initial page
load/reload) and `setLanguage()` (live switch from the top bar) — both
needed it, confirmed by testing: only wiring one of the two would leave
a stale direction after a reload or after a live switch, respectively.
`index.html`'s `<html>` tag has no `dir` attribute of its own, so the
unset/default case (all 14 other languages, plus the pre-auth
`LoginScreen`/forced-`ChangePasswordScreen` which stay English-only per
the existing deliberate scope cut above) correctly stays `ltr` with no
extra code.

Verified via the same throwaway-harness technique as Turkish — this
time also asserting the actual DOM state (`--dump-dom`, not just a
screenshot) confirmed `<html lang="en" dir="rtl">` for Hebrew and
`dir="ltr"` for a same-harness English control render, so the fix is
confirmed at the attribute level, not just "the text looked
right-aligned in a screenshot." Screenshots themselves confirmed:
station name/track/artist/AI-provider chip all correctly right-aligned,
the volume slider's filled portion flips to the right side (matching
RTL convention), and — the trickiest case — the liner-notes trivia
paragraph mixes Hebrew with embedded Latin text ("Kind of Blue") and
Arabic numerals ("1959") and the browser's bidi algorithm orders it
correctly with zero special handling needed in this app's own code.
`tsc --noEmit`, `oxlint`, `vite build` all clean; English (and by
extension every other existing language) re-screenshotted as an
explicit before/after control to confirm zero regression to the
LTR default.

**Gap in the above verification, caught by the user immediately in
production (fixed 2026-09-07, 1.0.5)**: the harness used to verify
1.0.4 didn't render an actual station logo (`NowPlayingPanel`'s logo is
conditional on `useStationLogo()` resolving a real image, which needs
network access the harness didn't have), so the one absolutely-
positioned element on this panel never got exercised — and it was
wrong. `.station-logo` was pinned with a hardcoded `right:
var(--logo-inset)`, and `.panel-head-with-logo::after` (the shortened
divider segment behind it) hardcoded `right: calc(...)` too — both
stayed glued to the physical right edge in Hebrew while the rest of
the panel correctly mirrored, so the logo visually collided with the
now-right-flowing `.np-metrics` text. Fixed by switching both to the
CSS logical property `inset-inline-end`, which resolves to `right` in
LTR and `left` in RTL automatically — no `[dir="rtl"]` override needed,
same one-property fix pattern applies everywhere this class of bug can
occur. Audited the rest of `dashboard.css` for the same mistake while
fixing this one (grepped every `position: absolute`/`fixed` block for
asymmetric `left`/`right`) and found two more: `.user-dropdown` and
`.dropdown-menu` (the account menu and the language/provider dropdown
pickers) were both anchored `right: 0` to their trigger button, same
fix applied to both. `.panel-head::after` and `.live-dot::after` were
checked and are fine as-is — both set `left`/`right` symmetrically (or
use `inset` outright), so they were never side-specific to begin with.

**Lesson, worth remembering for any future RTL language**: a harness
without real backend/network data can validate text flow and typography
but will silently skip any element whose presence depends on that data
(here, a station logo) — a gap like this needs either a harness that
fakes the missing piece (what 1.0.5's fix verification did instead: a
harness rendering `.station-logo` directly with a data-URI placeholder
image, screenshotted in both directions) or a live check against the
real running app before calling RTL support "done." Re-verified 1.0.5's
fix this way, confirmed the logo/divider correctly move to the left in
Hebrew with the divider's shortened segment on the matching side, and
re-confirmed zero regression to the LTR English render alongside it.

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

## Station logos, cached (added 2026-09-06, 0.5.18; name-search retry 0.5.29; pipe-suffix fix 0.5.30; bigger + divider redesign 0.5.31; layout bug fixed 0.5.32; equal padding fixed with real screenshots 0.5.33; margin-vs-padding bug fixed 0.5.34; tokenized + rebalanced 0.5.35; shaved smaller for mobile 0.5.36; metadata centred + logo resized 0.5.37)

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

**Name-search retry + false-positive guard (0.5.29)**: user noticed most
curated stations had no logo and pushed back on "that's just missing
data" — right call. Root cause: Radio-Browser's `/stations/search` is
exact-ish, not fuzzy — confirmed live `name=VCR Auditorium` returns
nothing even though `"VCR | Venice Classic Radio Auditorium"` is a real
indexed entry with a working favicon. This app's own curated display
names regularly don't match verbatim, because they're written for
human readability (`" | subtitle"`, trailing `"(region)"` qualifiers)
not for a literal directory search. Fixed with a retry chain in
`_name_variants()`: strip `" | ..."`, strip a trailing `"(...)"`, then
try the bare first word — each tried in order until one search returns
a real, HEAD-verified favicon.

**The bare-first-word tier is genuinely dangerous and was caught before
shipping, not after**: confirmed live that searching `"VCR"` alone (the
first word of "VCR Auditorium") surfaces two entirely unrelated
stations sharing that same 3-letter token — one Congolese, one an
unrelated "VCR - 90.6 FM Stereo" — both with their own live, working
favicons, ranked *ahead* of the real Venice Classic Radio match in the
result list. A naive "first result with a working favicon" rule would
have confidently attached a wrong station's logo, which is worse than
showing no logo at all. Fixed two ways, stacked: (1) the bare-first-word
tier only fires when that word is longer than 4 characters or contains
a digit — filters out short call-sign-shaped acronyms (`VCR`, `WQXR`,
`KIX`, `BBC`...) while still allowing distinctive numeric brands
(`181.FM`, `.977`, `1.FM`); (2) even then, the candidate's own indexed
name must still share a real word with the *original* curated name
(`_distinguishing_words()`) before its favicon is trusted. Net result,
confirmed live against the real API for every previously-broken
station: Heart 70s and 181.FM Kickin'/True Blues now resolve to real
favicons; VCR Auditorium correctly still resolves to `None` (its only
path to a match is the disqualified bare-acronym tier) rather than a
wrong station's logo — no logo is the right outcome there until a
better signal exists, not a bug to keep chasing.

**One-time cache purge required after deploying**: `station_logos.json`
permanently caches a miss as `{"logo": None}` specifically so a
no-logo station never gets re-queried on every play — which means
every station this fix improves needs its stale `None` entry manually
cleared on LT once after deploying, or it'll keep serving the old
(wrong) answer from cache forever. This is a one-time data fix, not a
recurring task — same category as the Heart 70s genre fix and the
favorites reset, not a precedent for routinely editing production data.

**Both VCR stations still had no logo after 0.5.29 — user correctly
diagnosed why (0.5.30)**: user's own read was exactly right — "VCR
Auditorium"/"VCR Classica+" only exist to distinguish this app's own
two sibling stations from each other, while the real broadcaster name
lives after the pipe ("Venice Classic Radio Italia"). The 0.5.29 fix's
variant chain never tried the pipe *suffix* on its own, only the
pipe-stripped *prefix* — so it never got anywhere near the actual
broadcaster name. Fixed by adding the text after " | " as its own
variant, confirmed live it still doesn't match verbatim (Radio-Browser
doesn't index the trailing "Italia"), so it also retries with that
suffix's own last word dropped ("Venice Classic Radio Italia" →
"Venice Classic Radio") — one word shorter finds the real station with
a live, correctly-branded logo (`cropped-logo_VCR-MAIN...png`, the
actual current site logo, not a stale/dead one this time). Confirmed
live this resolves BOTH VCR stations at once, since they share the
identical pipe-suffix — same one-time cache-purge requirement as
0.5.29 applies again for these two entries specifically.

**Logo made bigger + divider redesign, first attempt had a real layout
bug (0.5.31, fixed 0.5.32)**: once logos actually started showing up,
user wanted them much bigger with the header's divider line stopping
short of the logo's column instead of running behind it — a "double
space" effect, sketched as a red box in a screenshot with the explicit
note the box itself wasn't to be drawn, only the layout it marked.

**0.5.31's mistake**: gave `.panel-head` extra `padding-bottom` sized
to the logo's overhang, reasoning (on paper, via hand-computed
geometry, since no screenshot tool was available) that this would let
a `top: 50%`-centered absolutely-positioned logo straddle a
correspondingly-repositioned divider. The arithmetic checked out, but
missed the actual consequence: `.panel-head`'s own box genuinely grew
by that padding, and `.np-body` (the metadata/track section) starts
immediately after `.panel-head` in normal flow — so all that extra
padding became real, visible dead space between the divider and the
now-playing content below it, confirmed by the user's own screenshot
with a second red box drawn around the empty gap. **Lesson**: computing
"does the geometry line up" isn't the same as checking "does growing
this box push something else I forgot about" — box model consequences
on sibling elements are exactly the kind of thing that's easy to miss
without actually rendering the page, and no amount of arithmetic
substitutes for that.

**0.5.32's fix**: `.panel-head` goes back to its original compact
height (no extra padding at all) — the divider is still shortened via
`.panel-head:has(.station-logo)::after`, but the logo itself is
positioned with a fixed `top: var(--space-xs)` (flush with the
header's own top padding, same as the station-name text) instead of
being vertically centered across an artificially-taller box. At 80px
tall (bumped up from 64px once the layout bug no longer made it look
smaller than it was), the logo now genuinely overhangs past
`.panel-head`'s real bottom edge into `.np-body`'s space — but because
`.panel-head` itself never grew, `.np-body` starts exactly where it
always did, so there's no dead space. The overhang overlaps
`.np-body`'s own top-right corner rather than displacing its content
downward, which is the correct implementation of "double space" the
user actually wanted: the logo visually intrudes into the section
below, not the section below being pushed away from the logo.
Accepted, not fixed: a very long track title wrapping to multiple
lines could theoretically run under the logo's corner on a narrow
panel — a rare cosmetic edge case, not treated as worth adding
complexity (e.g. shape-avoidance CSS) to prevent, consistent with this
project's "don't engineer for hypotheticals" convention.

**Still crashing into the metrics divider — switched to real Playwright
screenshots instead of more hand arithmetic (0.5.33)**: user's own
screenshot (two more red arrows) showed the logo's bottom edge still
overlapping `.np-metrics`'s divider line, and the right-side padding
visibly tighter than the top. Two straight rounds of "compute the pixel
math by hand, ship it, it's wrong" was the signal to stop guessing.
This session had no MCP screenshot tool, but **Chrome + `npx playwright`
were both available locally** — used them directly: built a tiny
static HTML fixture referencing the real `index.css`/`dashboard.css`
source files with realistic content, screenshotted it with a headless
Playwright script, and iterated against the actual rendered image
instead of arithmetic. Immediately visible: the logo (a child of
`.panel-head`) was still being positioned relative to `.panel-head`
despite `.panel` also being `position: relative` — CSS always resolves
to the *nearest* positioned ancestor, not just any ancestor up the
tree, so giving `.panel` its own `position: relative` had no effect on
an element still nested inside a *different* positioned box.

**Fix, done properly this time**: moved the `<img class="station-logo">`
out of `.panel-head` in the JSX to be a direct sibling of it, both
still inside `section.panel` (which is now the actual positioning
context) — this makes the logo's `top`/`right` genuinely independent
of `.panel-head`'s own height, so `.panel-head` never needs any special
sizing at all regardless of the logo's size. Added a `showLogo` boolean
and a `panel-head-with-logo` class (via `.panel:has(.station-logo)` in
CSS, or the JSX conditional class directly) purely to shorten the
divider above the logo's column. Used Playwright's `boundingBox()` to
read exact pixel gaps (not eyeballed): confirmed top=25px, right=25px
before touching `.np-metrics` at all — then added `margin-top: 27px`
to `.panel:has(.station-logo) .np-metrics` (pushing its divider down,
rather than shrinking the logo back to fit an artificially tight gap)
until bottom=26px too, all three within a rounding pixel of each
other. Re-screenshotted the no-logo case and a very-long-station-name
case afterward to confirm no regressions (compact header stays
unchanged without a logo; a long name still truncates via the
existing `text-overflow: ellipsis` and never runs under the logo's
column). **Lesson for this project generally**: when a local browser +
`npx playwright` are available, prefer an actual rendered screenshot
loop over computing CSS box-model interactions by hand — two prior
attempts at this exact feature shipped visible bugs from arithmetic
that was individually correct but missed real interactions (padding
consequences on `.np-body`, then a positioning-context mistake) that
only became obvious once actually rendered.

**Third bug in this same feature: margin vs. padding (0.5.34)**: even
with the screenshot loop set up in 0.5.33, the very next fix still
shipped visibly wrong — user's screenshot showed a much bigger gap
above the metrics text than below it, with an explicit side-by-side
"this one's wrong, this one (no-logo case) is right" comparison. Root
cause: 0.5.33's fix added `margin-top: 27px` to `.np-metrics` when a
logo is present, to push its divider down far enough to clear the
logo — but `margin-top` moves the *entire box*, text included, not
just the divider at its bottom. That shoved the "128 kbps..." text
itself down by 27px, creating the exact oversized gap the user flagged,
while the *bottom* gap (between the text and the divider) stayed
unchanged at its normal small amount. Fixed by using `padding-bottom`
instead of `margin-top`: this keeps `.np-metrics`'s top edge (and
therefore its text) exactly where it always was, flush under the
header like the no-logo case, and only grows the space *inside* the
box between the text and its own bottom border/divider. Re-tuned the
pixel value from 27px to 38px since padding-bottom compounds
differently against the existing `padding: 0 0 var(--space-xs)` than
margin-top did — confirmed via the same `boundingBox()` measurement
loop from 0.5.33, this time re-verifying all three gaps (top/right/
bottom around the logo, 25px each) AND the header-to-metrics-text gap
specifically (16px, matching the no-logo case) since that was the
exact dimension that broke last time. **Lesson stacked onto 0.5.33's**:
having a screenshot loop available doesn't prevent every mistake by
itself — CSS's margin/padding distinction (margin moves the box as a
whole including its content start point; padding only grows space
*inside* the box, after the content) is a classic, specific trap for
"push this element's edge down without moving its content" style
fixes, worth remembering by name next time similar spacing logic comes
up in this codebase.

**User caught the actual root cause behind all this drift: hardcoded
pixels instead of relative tokens (0.5.35)**: after 0.5.34, the bottom
gap around the logo was still visibly bigger than the top/right gaps —
but this time the user didn't just report the symptom, they correctly
diagnosed the mechanism: "adapt the padding... I say this in case you
coded the padding in absolute pixels instead of relative sizes." Right
call — `.station-logo`'s `height: 72px` and `.np-metrics`'s
`padding-bottom: 38px` were both bare pixel numbers with no declared
relationship to each other or to this app's `--space-*` token scale,
which is exactly why three straight tuning passes needed a fresh
guess-and-recheck cycle each time rather than one value driving the
other. Fixed properly: `--logo-size: 4.5rem` is now a single custom
property defined once on `.panel` (visible to descendants), consumed
directly by `.station-logo`'s `height` AND by `.np-metrics`'s
`padding-bottom` via `calc(var(--logo-size) - var(--logo-offset))` — a
genuine shared source of truth instead of two independently-guessed
numbers that happened to work together by luck. `--logo-offset`
(2.5rem) is the one number still calibrated by eye/measurement rather
than derived — that's fine and expected, since it encodes "how much
tighter this row's natural rhythm is than the logo's footprint," not
an arbitrary duplicate of the logo's own size. Re-verified the actual
gap numbers via the same Playwright `boundingBox()` loop, this time
deliberately undershooting the "technically equal" 25px from 0.5.34 in
favor of a visibly tighter ~19px, since the user's ask was explicitly
"reduce," not "make it exactly symmetrical again" — a case where the
measured-equal answer and the visually-good answer aren't quite the
same thing, and the user's eye is the actual spec here, not the
numbers. **Lesson, stacked on 0.5.33/0.5.34's**: three consecutive
tuning misses on the same feature is a strong signal to ask "is there
an underlying reason this keeps needing correction," not just "what's
the next number to try" — in this case the user spotted it before I
did, and the fix (a shared token) is also what makes any *future*
resize of the logo automatically keep its own padding in proportion,
which none of the previous three fixes would have done.

**Shaved further for mobile fit (0.5.36)**: user was "almost happy" but
wanted everything shaved down more, explicitly citing phones/small
screens as the reason. Because 0.5.35's `--logo-size` token already
drove both `.station-logo`'s height and `.np-metrics`'s calculated
padding-bottom, shrinking the whole feature was mostly one number —
`--logo-size` went from 4.5rem to 3rem, `.station-logo`'s `top`/`right`
switched from `--space-md` to the smaller `--space-sm` token, and the
divider-shortening rule (`.panel-head-with-logo::after`) was itself
finally converted from a hardcoded `88px` to
`calc(var(--space-sm) + var(--logo-size) + var(--space-sm))` — closing
the one remaining magic-number gap from earlier passes. Re-tuning
`--logo-offset` (2.5rem → 3rem, with the padding-bottom calc wrapped
in `max(0px, ...)` since the new offset is now allowed to meet or
exceed the logo size) brought top/right/bottom down to a tight, even
~17-19px. **Added an actual mobile check this time** (390px viewport,
via the same Playwright loop, not assumed): confirmed the fixed-size
logo was eating too much of the header row's width at phone size,
visibly truncating the station name more than necessary — added a
`@media (max-width: 480px)` override dropping `--logo-size` to
2.25rem specifically for narrow screens, which (because everything
else derives from that one variable) automatically shrunk the
divider-shortening and padding-bottom to match with no further
manual tuning — the clearest payoff yet of 0.5.35's tokenization work
paying for itself on the very next request.

**Metadata centred, logo resized — and the insight that ended the
tuning loop (0.5.37)**: user asked for two things at once (metadata
halfway between the two dividers instead of hugging the lower one; a
bigger logo with evenly-reduced margins) and mentioned switching models
because the previous approach was "running in circles" — fair, five
straight releases had gone into nudging the same numbers. What broke
the loop was measuring the *boxes* rather than the gaps:
`getComputedStyle` on `.np-metrics` showed the carefully-derived
`min-height` calc was resolving to **4px** — it had never once been the
binding constraint. The band's height was always just its natural
content (text + padding), so several rounds of tuning had been spent on
a value that did nothing. Two consequences: (a) the off-centre metadata
was never a padding problem at all, it was `.np-metrics` having no
vertical alignment — a single `align-content: center` fixed it, and all
the accumulated `padding-bottom`/`min-height` machinery got deleted
rather than re-tuned; (b) with the band's height set by its content,
the logo's bottom margin can only be closed by *growing the logo* —
which is why the user's two requests were really one. 4.4rem lands the
logo exactly `--logo-inset` above the lower divider: 13/13/12.6px on
all three sides.

Mobile needed the opposite call, worth recording: below 480px the
metrics text wraps to two lines, so that band becomes *taller* than any
sane logo and "even margins all round" stops being achievable —
chasing it would need an absurdly large logo, the opposite of what a
phone wants. Shrank the logo there instead (2.75rem) and accepted the
looser gap below it as ordinary breathing room. **Lesson**: when
several rounds of tuning a value give disappointing results, confirm
the value is actually taking effect (`getComputedStyle`) before tuning
it again — and when a target can't be met at one breakpoint, say so and
choose a different goal there rather than distorting the design to
force it.

**Logo quality: three distinct bugs behind "no logo" (0.5.38)**: user
listed stations still missing logos or showing blurry ones. Running
`find_logo()` against the real catalogue separated three causes that
all presented identically:

1. **Non-image URLs passing validation.** Radio-Browser lists Radio
   Paradise's favicon as bare `https://radioparadise.com` — a
   homepage. It answers 200 to a HEAD request, so the existing check
   accepted and cached it, and it rendered as nothing. Fixed by also
   requiring `content-type: image/*`. This immediately caught a second
   case too: 181.FM's indexed `181.FM.jpg` is really a 404 HTML page.
   **Status code alone is not validation** — check the type as well.
2. **Favicons winning over real logos.** Several stations are indexed
   with both a 16×16 `favicon.ico` and a proper logo; the picker
   returned whichever came first, so 181.FM/KJazz got the blurry one
   upscaled into the panel. `_first_working_favicon()` now scans all
   candidates and only falls back to a `.ico` if nothing better
   verifies.
3. **Genuinely absent from the directory.** A small hand-checked
   override map keyed by curated *name* (KUSC — its stream host is a
   shared CDN, so keying the host would mislabel every other station
   on it). Overrides are HEAD-verified like any other candidate.

**The real fix, found only because the user pushed back (0.5.38,
second pass)**: told the 181.FM logo was still crappy, with "just put
181.fm into search and look at the website." I had checked the two
URLs the directory listed and the homepage's declared
`<link rel="icon">` — but never the image the site actually *shows*.
Fetching the homepage with a browser User-Agent (it serves a stub to
plain clients) revealed **`og:image`**: `og181fmlogo.jpg`, 1200x630,
86KB, the exact logo the user screenshotted, versus the 4KB favicon we
were serving. This is a general convention, not a one-off — it also
found 1.FM's real logo (`radio.1cloud.fm/og_image.png`), letting the
hardcoded imgur override be deleted entirely. **Lesson: when a site
"has no usable logo", check `og:image` before concluding that — it's
the image a site publishes to represent itself, and it beats both
`favicon.ico` and directory metadata.**

Two performance traps this introduced, both caught by measuring:
- **Deprioritising apple-touch-icons was wrong.** Treating them as
  low-quality forced a homepage fetch even when a fine ~180px icon was
  already in hand. Only `.ico`/favicons are genuinely blurry at the
  panel's render size; the rule now covers just those.
- **Per-request timeouts don't bound a multi-request lookup.** One
  lookup makes a search per name variant, a HEAD per candidate, then
  possibly homepage fetches — each under `_TIMEOUT` while the total
  ran to 90s+ for VCR. Fixed twice over: og:image is now tried once
  after the directory is exhausted (not inside every variant's result
  set), and `find_logo()` wraps everything in an overall
  `_TOTAL_TIMEOUT` deadline. Full-catalogue run went 47s → 18s.

Result: 94/104 curated stations resolve a logo. The remaining 10 have
nothing usable anywhere (KCSM's own site 404s its favicon) and
correctly show blank. Verified no regressions by re-resolving every
station in production's cache: the only "loss" was Radio ROKS Ballads,
which had been showing *Radio Białystok's* favicon — a Polish station's
logo on a Ukrainian one — so blank is strictly better.

**Wikipedia as a last tier, and why not Google Images (0.5.40)**: user
asked for a Google Images fallback filtered to transparent PNGs.
Checked rather than assumed: a server-side fetch of Google Images
returns a **JavaScript shell with zero image URLs** — scraping it would
need a headless browser in the container and breaches Google's terms.
Wikipedia's API is the sound equivalent: free, no key, content licensed
for reuse. It runs only when everything else found nothing, so it costs
one request on the rare blank.

**Its search always returns *something*, which is the whole danger**,
and two live near-misses forced the guard to be tightened twice:
- `TSF Jazz` matched a different French station called `Jazz Radio` —
  the word-overlap check passed because both contain "jazz". Added
  `_GENERIC_STATION_WORDS` (radio/jazz/blues/rock/country/…) which are
  excluded from identity matching; overlap on those alone proves
  nothing.
- `WSM 650 AM` then matched `WSM-FM` — same call sign, *different
  station* — and would have shown the FM logo. Fixed by requiring the
  article title to contain **every** specific word, not merely one.
  Notably the correct `WSM (AM)` article has no image at all, so
  showing nothing is the genuinely right answer there.

Net effect: Wikipedia fires for exactly one station (TSF Jazz, 95/104
total). That low hit rate is the design working — the alternative to a
strict guard isn't more logos, it's confidently-wrong ones, which this
feature has now produced twice (VCR→Congolese station, Radio
ROKS→Radio Białystok) and which is always worse than a blank space.

**Brave Search evaluated and rejected; transparency (0.5.41)**: user
asked about Brave Search as a Google Images substitute. Checked:
its API returns 422 without a key (needs signup *and a credit card*,
$5/1000 requests beyond free credits), and its HTML endpoint is
CAPTCHA-gated. So it's not unusable like Google — it's a real option —
but it means asking the user to obtain and configure a key with card
details on file, for a fallback that would fire on <10 stations. Not
worth it unless they ask again; noted here so it isn't re-researched.

**Content-type headers are not sufficient to validate an image.**
Hunting a transparent 181.FM logo turned up
`/images/181_logo_300.webp` (referenced only inside the site's JS
bundle — not in og:image, not in any `<link rel="icon">`, not in the
manifest), a genuine alpha-channel WebP. Their server sends it with
**no content-type header at all**, so 0.5.38's header-only check
rejected it. `_is_usable_image()` now sniffs magic bytes (PNG/JPEG/
GIF/ICO/WebP/SVG) when the header is *absent* — but still trusts the
header when present, so the earlier "homepage returns 200" and
"404 page pretending to be a .jpg" cases stay rejected (re-verified
explicitly).

**On transparency generally**: there's no reliable signal for finding
a transparent logo. Checked manifests, `<link rel="icon">`, og:image —
all either absent or flattened. 181.FM's per-channel
`/images/station-thumbnails/*_300.webp` files exist but are
photographic album art, not logos, and read as mush at 70px. So the
transparent file is a host-keyed override (one entry covers every
181.FM channel), not a general mechanism. Transparency also can't
become a *filter*: it would reject correct opaque logos like TSF
Jazz's. If white boxes keep bothering the user, the better fix is
ours — rounding the logo's corners or blending it into the panel —
rather than narrowing what counts as a valid logo.

**White backgrounds solved in CSS, not by hunting files (0.5.42)**:
user flagged France Musique's logo as another white box and asked for
an automatic detector plus a DuckDuckGo fallback. Findings:

- **DuckDuckGo is not usable server-side.** Its image endpoint needs a
  `vqd` token scraped from the HTML page; supplying a valid one still
  returns 403 from a datacentre IP without session cookies. Same
  category as Google. **Brave** (checked the round before) *is* real
  but needs an API key with a credit card on file. So: no search engine
  is a viable fallback without the user provisioning a paid key.
- **A white-background detector is easy** — sampling the four corner
  pixels correctly classified all four test logos (France Musique
  opaque-light, 181.FM/1.FM transparent, TSF Jazz dark). But acting on
  it server-side means adding Pillow, downloading and decoding every
  image, re-hosting rewritten files, and owning a new cache. Large
  feature for a cosmetic issue.
- **`mix-blend-mode: multiply` does it for free**, because white
  multiplied by the background *is* the background. Zero dependencies,
  no per-station work, and it self-selects: transparent and dark logos
  are unaffected.

Two things only a real render revealed:
- **Dark mode must be excluded.** multiply against a dark panel crushes
  a light logo to near-black. Scoped to light mode using index.css's
  own `[data-theme]` + `prefers-color-scheme` pair, so the manual theme
  toggle is honoured too, not just the OS setting.
- **multiply alone left a faint grey patch**, because France Musique's
  background is 250,250,250 against a warmer panel — close to white
  isn't white. `filter: brightness(1.06)` lifts it the last step so it
  cancels exactly. Verified at 2x scale; the box disappears completely.

**Lesson**: when a defect appears per-item (a white box on this
station, then that one), check whether it's a *rendering* problem
before treating it as a *data* problem — the CSS fix covers every
station at once, including ones not yet reported, while the per-station
hunt would never end.

**Self-hosted SearXNG closes the search-engine gap (0.5.43)**: after
Google/DDG/Brave were each ruled out, user pointed out they *run
SearXNG on LT* — which invalidates every objection at once: no API
key, no CAPTCHA, no third-party terms, and it aggregates Bing/Brave/
DDG results anyway. Correct call, and a reminder to ask what's already
on the box before concluding a capability is unavailable.

Setup: its JSON API is **off by default**. Added to
`/mnt/user/appdata/searxng/settings.yml` (backed up first, asked before
touching another service):
```yaml
search:
  formats: [html, json]
```
then `docker restart SearXNG` (container is named `SearXNG`, not
`searxng`). Verified `?format=json` went 403 → 200.

Wired in as `MRADIO_SEARXNG_URL`, **optional and unset by default** —
nobody else running this app has a SearXNG, and the tier is simply
skipped when empty (verified). On LT it lives in the untracked
`docker-compose.override.yml`, keeping the LAN IP out of the repo.
Compose *appends* `environment:` lists, so the base file's admin vars
survive.

Results went 95 → **103/104**. It found logos nothing else could
(KCSM, Chilltrax, WSM's correct *AM* logo) and its top hit for 181.FM
was the same transparent WebP that previously had to be hardcoded.

Two filters were essential, both learned from earlier tiers: results
are padded with icon libraries and stock-photo archives (lucide,
artic.edu, shutterstock…) that match on generic words, so
`_IMAGE_SEARCH_NOISE_HOSTS` drops those, and the same
`_GENERIC_STATION_WORDS` guard from the Wikipedia tier still applies.
Also sorts PNG/WebP/SVG ahead of JPEG, since only the former can carry
transparency. Placed *after* Wikipedia but *before* falling back to a
blurry favicon — a real logo beats a 16x16 icon.

**Scan depth matters more than result count (0.5.44)**: WSM 650 AM
still had no logo despite the SearXNG tier. Not a matching bug — the
guard was fine. SearXNG returned **921 results** for that query and the
code only examined `results[:20]`, which were almost entirely lucide/
devicon icon-library entries; the correct logo sat just past that
window. Widened to `[:120]`. Safe because the filtering (noise hosts,
specific-word match) is pure string work — only the few survivors are
ever fetched, so lookup time was unchanged (29s for the full
catalogue). Coverage 102 → **103/104**.

Worth remembering: when an aggregating search backend returns
hundreds of results, "take the first N" is the wrong instinct — the
head of the list is where the generic filler lives, and the useful
result is often ranked below it.

**Station curation**: user asked to replace "Country Radio (CZ)", the
one Czech station among nine American ones in the country genre.
Picked **America's Country** (`ais-sa2.cdnstream1.com/1976_128.mp3`)
via Radio-Browser sorted by clickcount — deliberately not another
181.FM/1.FM channel, since four and two of those respectively already
sit in that genre. Verified before committing: 200, 128k, `icy-metaint`
present, and a real `StreamTitle` observed on the wire ("Tim McGraw -
7500 OBO") — **checking a stream plays is not enough; confirm it sends
track titles, or liner notes silently never appear**.

**A separate lesson about stale cache entries**: user reported
"1.FM Hot Country" blank, which isn't in `stations.py` at all — it's
the *ICY name* broadcast by `1.FM Absolute Country Hits`. Its cache
entry was `None` from a transient failure during a warm run, while
sibling channels on the same host had resolved fine. When a station
looks inconsistent with its siblings, suspect a cached miss before
suspecting the lookup logic; re-running just the misses recovered
three stations without rebuilding the whole cache.

**Audio quality**: probed `icy-br` across all 104 streams in parallel
(sequential took >6min and timed out; `xargs -0 -P 20` with a NUL
delimiter is the pattern — station names contain spaces, so plain
`xargs` silently mangles them and probes only a handful). Radio
Paradise was the one real upgrade available: swapped
`stream-uk1.radioparadise.com/mp3-128` → `stream.radioparadise.com/mp3-320`.
Their FLAC feed (1441k) exists but sends no `icy-metaint`, which would
silently kill liner notes — **when changing a stream URL, check ICY
metadata survives, not just that it plays**. Everything else at/below
128k is broadcasting at its real ceiling (KCSM 96k, WSM 64k is an AM
station); their "better" alternatives were dead or lower quality.

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

## 1.0.0 (2026-09-07)

Moved from 0.5.47 to **1.0.0** at the user's call — the app had been
running in production continuously since 0.1.1 across 78 tags, with
every feature in daily use. No code change accompanied the bump; it's
a statement about maturity, not a release gate.

**Corrected a factual error from the same session**: I told the user
the repo had *no* LICENSE, based on `gh repo view` returning
`licenseInfo: null`. Wrong — a valid, complete MIT LICENSE is present
and git-tracked; GitHub's detector simply hadn't indexed it. That
error mattered, because I'd used "no license" as an argument against
publishing a Docker image (see below). The image decision still holds
on its other grounds, but not that one. **Check the file, not just the
API.**

Also added a "Before you install" section to README.md covering the
three things most likely to trip up a stranger: HTTPS is mandatory
(Secure cookies mean plain HTTP silently fails at login), the ChatGPT
provider is an unofficial mechanism, and the app is household-scale by
design rather than multi-tenant. All three were already documented in
KB.md, but buried where a hurried installer wouldn't look until
already stuck.

## Deployment stays a source build, no published image (decided 2026-09-07)

Asked why the project never produces a Docker image and whether it
should publish one. Reviewed and **deliberately declined** — worth
recording so it isn't reopened without new reasons.

Why there's no image today (it follows from the setup, not oversight):
- Deploys are `git pull && docker compose build` on LT, ~30-60s. A
  registry saves no meaningful time for a single operator.
- Host-specific config (port 8123, appdata path, `MRADIO_SEARXNG_URL`)
  lives in an untracked `docker-compose.override.yml`. Nothing about
  that needs a registry.
- Both GitHub workflows are version-bump PR openers by design ("never
  publishes or auto-merges anything"). No job has ever built the image.

Two constraints publishing would expose, worth knowing before anyone
revisits this:
- The image bakes in **GeoLite2-City.mmdb** at build time. Shipping it
  in a public image means redistributing CC-BY-SA data, with
  attribution obligations the project doesn't currently carry.
- It bundles the **Codex CLI** for the unofficial ChatGPT auth path
  that KB.md already flags as risky. Publishing invites strangers into
  that, a different posture from "the admin, on their own box,
  knowingly."
- ~~The repo is public with no LICENSE.~~ **Wrong — corrected the same
  day.** `gh repo view` returned `licenseInfo: null`, but a valid MIT
  LICENSE is present and tracked; GitHub just hadn't indexed it. This
  argument does not hold. The two points above still do.

**The strongest argument was never speed — it was CI.** With no build
job, a broken Dockerfile surfaces mid-deploy on LT rather than on
push; several Dockerfile edits (the `codex-build` stage, the GeoLite2
fetch) could have failed there. If this is revisited, **start with a
build-only CI job and leave publishing out of it** — that captures
most of the value with none of the licensing/redistribution questions.
User's call was to leave it as is, which is reasonable: it has held
across 47 releases.

## Stale metadata on quick station switches + honest "no ICY support" state (fixed 2026-09-07, 1.0.1)

User reported the now-playing panel stuck on "Connecting…" on a station
(SomaFM Groove Salad) suspected of not sending ICY titles at all, then —
mid-investigation — reported something worse: switching between several
*other* stations that normally do show titles left them all stuck too,
and a full page reload fixed it. That second report changed the
diagnosis; investigated the race properly before touching any UI copy.

**Root cause**: `usePlayer.ts` reuses one `sid` (`crypto.randomUUID()` in
a `useRef`) for the entire player session, across every station switch —
not one per stream connection. `play(station)` reassigns `audio.src`,
which aborts the old `/api/stream` fetch client-side, but the server only
learns of that asynchronously (a `GeneratorExit` the old request's
`finally` handles in a shielded background task, see `stream.py`'s
existing comment on why that shielding exists). That leaves a real
window where the old station's proxy connection is still alive and can
emit one more `title`/`station` event — with nothing in `nowplaying.py`
to tell it apart from the new connection sharing the same `sid`. A
reload mints a fresh `sid`, which is why that "fixed" it.

**Fix**: `nowplaying.py` gained `begin_generation(sid)`/
`is_current_generation(sid, gen)` — a UUID token per `/api/stream`
connection. `stream.py` mints one at connection start (before publishing
its own `station` event, so it invalidates any earlier connection for
the same `sid` still draining) and gates the `title` publish on still
being current; a straggler from an abandoned connection is dropped
instead of corrupting the live one's state. `_generation` is cleared
alongside `_last_station`/`_last_title` in `unsubscribe()`'s existing
full-cleanup path.

**Separately, the originally-reported issue was real too**: when
`icy-metaint` is genuinely absent (`parse_metaint()` returns `None`),
`IcyDemuxer` is never constructed and no `title` event is ever sent — the
frontend had no way to distinguish "still connecting" from "this station
will never send a title," so it sat on "Connecting…" forever. Fixed by
adding `has_icy: metaint is not None` to the `station` WS event;
`PlayerState.hasIcy: boolean | null` (`null` = not yet known, distinct
from a confirmed `false`) drives a new message
(`nowPlaying.noIcySupport`) in `NowPlayingPanel.tsx`, shown only once
`hasIcy === false` — `null`/`true` both still show "Connecting…", since
neither has ruled out a title still arriving. Reset to `null` on both
`play()` and `reconnect()`.

Also added a **Reload app** button in the top bar (reusing the existing
`RefreshIcon`) as a cheap safety net for any future stuck state — not a
fix for this bug specifically (the generation-token fix is), just
good insurance given how bad "stuck until you know to reload" is as a
user experience.

All 13 locales updated for both new strings (`nowPlaying.noIcySupport`,
`topbar.reloadApp`). Verified via a temporary throwaway harness
(`DevHarness.tsx`, mounted in place of `App` in `main.tsx`, screenshotted
via headless Chrome, then fully reverted — nothing committed) that all
three `hasIcy` states (`null`, `true`, `false`) render the correct copy.
`tsc --noEmit`, `oxlint`, and `vite build` all pass clean. No committed
test suite exists for the backend generation-token logic (see "Gaps"
above) — verified by hand via a throwaway script confirming
`begin_generation`/`is_current_generation` invalidate correctly on a
second call for the same `sid`.

## Empty-StreamTitle stations still stuck on "Connecting…" after 1.0.1 (fixed 2026-09-07, 1.0.2)

User caught this live on production immediately after the 1.0.1 deploy: TSF
Jazz still showed "Connecting…" forever, not the new no-metadata message.
1.0.1's `has_icy` flag is derived purely from whether `icy-metaint` is
present in the upstream headers — true for TSF Jazz — so the new message
never triggered; the panel just fell back to its old default.

**Investigated properly instead of guessing**: pulled the live container
logs (`docker logs mradio-web`) and found `metaint=16000` for TSF Jazz,
confirming it really does send ICY framing, and zero `title` log lines for
it ever, across two separate connection attempts (18s and counting).
Bypassed the app entirely and `curl`'d the origin
(`tsfjazz.ice.infomaniak.ch`) directly with `Icy-MetaData: 1`, then
hand-parsed the raw ICY metadata blocks in a throwaway script: **every
single block, sampled over ~25s / 20 metadata checks, contains
`StreamTitle='';`** — an empty but present title field, not a missing
one. `icy.py`'s `extract_title()` already correctly treats an empty
capture group as "no title" (falsy check), so nothing there was wrong —
the gap was that `stream.py`/`nowplaying.py` had no way to tell "haven't
gotten a title yet, might still come" apart from "this station's title
field is confirmed to always be empty."

**Fix**: `icy.py` gained `has_stream_title_field()` (true if a
`StreamTitle=` field exists in the block at all, even empty) and
`IcyDemuxer.feed()`'s return signature grew a third element,
`saw_metadata_field: bool`, true whenever a metadata block completed
during that call regardless of whether it yielded a usable title.
`stream.py` tracks a per-connection `no_title_reported` flag and
publishes a new one-shot `{"type": "no_title"}` event (once per
connection, gated by the same generation-token check the `title` publish
already uses) the first time it sees a metadata field with no usable
title. `nowplaying.py` caches this like `station`/`title` for
subscribe-time replay (`_last_no_title`, cleared whenever a `station` or
real `title` event for the same sid supersedes it, and on full
unsubscribe cleanup) — same reasoning as the original replay-on-subscribe
fix from 0.1.3, since this is genuinely "latest value wins" state, not a
one-off toast. `ws.py` forwards it to the frontend verbatim.

Frontend: `usePlayer.ts`'s WS handler sets `hasIcy: false` on a `no_title`
message — collapsing this case onto the exact same UI state/message as
"no ICY support at all" (`nowPlaying.noIcySupport`), per explicit user
decision (asked directly rather than assumed): the distinction between
"header missing" and "header present but always empty" doesn't matter to
a listener, both mean "no track info, ever," so one message covers both.
Guarded with `s.rawTitle ? s : ...` so an already-showing real title is
never downgraded by a stale/reordered `no_title` event.

**Verified against real production data, not synthetic**: captured TSF
Jazz's actual ICY bytes via `curl` from this dev machine, fed them through
the real `IcyDemuxer` in a throwaway script (temporary venv, since this
machine has no backend venv set up — see "Local development" above),
confirmed it fires exactly one `no_title` and zero `title` events,
matching production. Separately fed a synthetic real-title stream through
the same demuxer to confirm normal stations are unaffected (one `title`
event, zero `no_title` events) — a zero-length metadata block (the
common "no change this cycle" case on a healthy station) correctly has no
`StreamTitle` field at all and doesn't count as `saw_metadata_field`.
`tsc --noEmit`, `oxlint`, `vite build` all clean.

**Lesson**: "the header is present" and "the header carries a real value"
are different facts, and a station can satisfy the first while never
satisfying the second, indefinitely — worth remembering for any future
ICY-adjacent work, not just this one station. Confirmed live in
production (not just build/lint) before calling this done, consistent
with [[feedback_verify_ui_visually]]'s standing rule, even though the
actual defect here was backend logic rather than CSS/rendering — the
verification method (real logs, real upstream bytes, a real demuxer run)
was the equivalent rigor for a backend-shaped bug.

## Language/provider switch ignored an existing cached AI answer (fixed 2026-09-07, 1.0.6)

User reported building a liner note in Hebrew, switching to English
(rebuilt), then switching back to Hebrew — instead of instantly
reusing the Hebrew answer already sitting in `cache.json`, the panel
sat on "Asking the AI provider…" and a real network call fired again.
Reported as happening with any language, not just Hebrew.

**Investigated against real production data, not assumption**: pulled
`cache.json` from LT (`docker exec mradio-web python3 -c "..."`) and
found the exact Hebrew entry for the exact track already cached, valid,
non-`fail`, under the correct `codex::he::<raw_title>` key — so the
cache write path and key format were both already correct (as they
should be, unchanged from the design docstring in `cache.py`). The bug
had to be in when/whether the read path was even consulted.

**Root cause**: two call sites — the WS `reenrich` handler (fired by
every language switch, via `Dashboard.tsx`'s `setLanguage()` calling
`player.reenrich()`, and separately by the "Re-ask AI" button) and
`routers/enrich.py`'s `activate_provider()` (fired by every AI-provider
switch) — both called `Enricher.invalidate()`, which went straight to
`submit()`. `submit()` does check the cache, but only to silently
`return` early and skip re-queuing a background LLM call — it never
notifies anyone a cache hit happened. Contrast with `pump_nowplaying()`'s
handling of a genuinely new track (`title` WS event): that path
explicitly calls `enricher.blurb()` *first* and sends an `enrichment`
message immediately on a hit, only falling through to `submit()` on a
miss. `invalidate()` never had that first check, so on a cache hit the
frontend's optimistic `enriching: true` (set by `usePlayer.ts`'s
`reenrich()` before the WS message is even sent) was never cleared by
anything — the panel was stuck on the placeholder with zero network
call ever happening, not literally "re-searching," but indistinguishable
from it to the user, and confirmed by the logs showing a genuine
`POST https://chatgpt.com/backend-api/codex/responses` firing around
the same time (a real, separate 429-rate-limit issue that made the
*next* switch look even more like "still searching").

**The subtlety that shaped the fix**: `invalidate()` has two genuinely
different callers with opposite intent. A language/provider switch
should prefer an existing cached answer for the *new* language/provider
if one exists — asking again would just reproduce the same cached
result at the cost of a real API call and a long wait. The "Re-ask AI"
button, which routes through the exact same WS `reenrich` message and
therefore the exact same `invalidate()` call, has the opposite intent:
it exists specifically to force a fresh answer even when one is
cached — that's the whole point of the button, and a naive "always
check cache first" fix would have silently broken it (clicking Re-ask
would just re-show the same cached blurb forever).

**Fix**: `invalidate()` gained a `force: bool = False` parameter.
`force=False` (the default — both `ws.py`'s automatic-switch path and
`enrich.py`'s provider-switch path use it) checks the cache first via
the same `cache_store.get_cached()` call `blurb()`/`submit()` already
use, and on a hit delivers it straight through `self.on_result` — the
identical callback `_finish()` already uses to push a fresh LLM answer
to the WS, so both paths converge on one delivery mechanism rather than
duplicating it — then returns without touching the offline cooldown or
enqueueing anything. `force=True` (routed only from the "Re-ask AI"
button, via a new `force` field on the frontend's `{type: "reenrich"}`
WS message, plumbed through `usePlayer.ts`'s `reenrich(force = false)`
and `NowPlayingPanel.tsx`'s button calling `reenrich(true)`) skips the
cache check entirely and always enqueues a fresh ask, bypassing even
`submit()`'s own redundant internal cache check (which would otherwise
still block a forced re-ask that happens to match what's cached).

**Verified with a real functional test, not just reading the code**: a
throwaway script (temporary venv + `MRADIO_DATA_DIR`, same technique
used for the 1.0.2 ICY-demuxer verification) seeded a fake
`codex::he::...` cache entry, then called `invalidate(force=False)` and
confirmed it delivered the cached item via `on_result` with **zero**
items enqueued to the worker queue, then called `invalidate(force=True)`
on the same already-cached track and confirmed the opposite — nothing
delivered via the shortcut, one item correctly enqueued for a real LLM
call. `tsc --noEmit`, `oxlint`, `vite build`, and a Python `ast.parse`
syntax check on all three touched backend files all clean.

**Lesson**: a cache-hit check that silently `return`s without notifying
its caller is a trap specifically when the caller's job is to *report*
a result somewhere (a WS push, a UI state update) — it's easy to reason
"the cache check prevents wasted work" and stop there, missing that
"prevents wasted work" and "produces the result the caller was waiting
for" are two different guarantees, and only the first one was actually
implemented. Worth checking for the same pattern anywhere else a
success path and a "already have it" path are expected to converge on
the same delivery mechanism, not just here.

## Stop→Play left metadata permanently stuck on "Connecting…" — only a page reload fixed it (fixed 2026-09-07, 1.0.7)

User reported this as a major bug, explicitly refusing "just reload the
page" as an acceptable answer. Investigated against real production
logs on LT, not assumption — pulled 600+ lines around the actual
reported sequence (Heart 70s (UK), Stop, Play again) and found the
concrete evidence for two separate, real bugs, both fixed together.

**Root cause (the actual reported symptom)**: `usePlayer.ts`'s
WebSocket carries every piece of now-playing metadata (`station`,
`now_playing`, `enrichment`) completely independently of the audio
`<audio>` element, which talks to `/api/stream` over its own plain HTTP
request. `stop()` sets `wantsConnectionRef.current = false` — by
design, so the WS's own `onclose` handler's reconnect-with-backoff loop
doesn't fight a deliberate Stop. But if the WebSocket happens to close
for any *unrelated* reason (reverse-proxy idle timeout, a laptop
sleep/wake cycle, a brief network blip) while the player is sitting in
the stopped state, that same guard means **nothing ever reconnects
it** — the passive backoff loop only fires in response to a *future*
close event, not one that already happened. Confirmed live in the
logs: at 18:03:15 a fresh `/api/stream` connection for the same `sid`
delivered a perfectly good `station`/`title` sequence, all correctly
cached by `nowplaying.py` for replay — but the WebSocket itself didn't
accept until 300ms later (`WebSocket /api/ws?sid=... [accepted]` at
18:03:15.665), meaning it had to reconnect from scratch just to
receive that replay. `play()` never checked or touched the WS at
all — it only reset local React state and restarted the `<audio>`
element, so if the socket was already dead at the moment Play was
clicked, audio would come back (a fully independent connection) while
metadata stayed silently broken forever, exactly matching what was
reported. A page reload "fixed" it only because it constructs a brand
new `usePlayer()` instance with a brand new socket from scratch.

**Fix**: added `ensureWsConnected()` — checks the WS's actual
`readyState`, and if it's not `CONNECTING`/`OPEN`, clears any pending
backoff timer, resets the backoff counter, and calls the same
`connectWs()` the mount-time effect already uses (hoisted into a ref,
`connectWsRef`, so it's callable from outside that effect — mirrors
the existing `audioReconnectRef` pattern used for the audio-stall
recovery). `connectWs()` itself gained a re-entrancy guard (no-op if a
socket is already `CONNECTING`/`OPEN`) so calling it from
`ensureWsConnected()` can never orphan an in-flight handshake. Called
from both `play()` and `reconnect()` — the two moments the user is
explicitly asking for a live connection, which is exactly when a dead
socket needs to be actively revived rather than passively waited on.

**Second, related bug found investigating the same logs**: Heart 70s
(UK) sends a real title once, then — a few milliseconds later, well
within the same connection — an empty `StreamTitle='';` on the very
next metadata block (some encoder buffering/cycling quirk, not a
station with genuinely no metadata support). `stream.py`'s
`no_title_reported` flag only prevented *duplicate* `no_title`
publishes; it never checked whether a real title had *already* been
seen on that same connection, so this immediately-following empty
block still fired a `no_title` event right after a perfectly good
`title` event. `nowplaying.py` caches both for replay (title in
`_last_title`, no_title in `_last_no_title`) since the `title` branch's
existing `_last_no_title.pop()` only fires when a *later* title
supersedes an *earlier* no_title, not the reverse ordering seen here —
so both ended up cached simultaneously, and a WS reconnect (exactly
the scenario `ensureWsConnected()` above now triggers more often, by
design) could replay them in a way that left `hasIcy` incorrectly
downgraded to `false` for a station that actually does support
metadata. Fixed with a `saw_real_title` flag in `stream.py`'s `body()`:
once a real title has been seen on a connection, `no_title` can never
fire again for the rest of that connection's life, full stop.

**Verified with real functional tests against the actual reproduced
pattern, not just reading the code**: a throwaway script (temporary
venv, same technique as 1.0.2's ICY-demuxer verification) fed the real
`IcyDemuxer` a synthetic byte stream reproducing Heart 70s's exact
title-then-empty-block pattern and confirmed `no_title` correctly never
fires once a real title has landed; a second test confirmed a
genuinely-always-empty station (TSF Jazz's pattern) still correctly
fires `no_title` exactly once, so the original 1.0.2 fix wasn't
regressed. `tsc --noEmit`, `oxlint`, `vite build`, and a Python
`ast.parse` syntax check on `stream.py` all clean.

**Not otherwise fixed, and deliberately left alone**: the same log
window showed Heart 70s (UK)'s `/api/stream` connection itself
reconnecting roughly every 1-2 seconds for a stretch (34 reconnects
inside one ~90-second window) — the existing audio `error`/`stalled`
auto-reconnect (added 0.1.6) firing repeatedly, most likely because
this specific station's stream (`media-ssl.musicradio.com/Heart70sMP3`)
genuinely stalls often from this network path, or the browser's
`<audio>` element gives up on it quickly for its own reasons. This is
a separate reliability concern about one station's stream quality, not
the "stuck after Stop→Play" bug that was reported and fixed here —
left untouched rather than risking a change to retry cadence/backoff
that wasn't asked for and isn't the reported symptom.

## Grok (xAI) added as 5th AI provider, with a real sign-in choice (added 2026-09-07, 1.1.0)

User asked for Grok "similar to what we did with ChatGPT." Investigated
before assuming the same shape applied, and it doesn't — Grok has two
genuinely different, both-legitimate integration paths, unlike ChatGPT
which only had one viable route:

1. A real, documented, OpenAI-compatible metered API (`api.x.ai`) — the
   same shape the existing NIM/OpenAI-compatible provider already
   covers generically.
2. An unofficial-but-technically-clean subscription OAuth flow
   (SuperGrok/X Premium+), mirroring ChatGPT's shape but — crucially,
   confirmed live, not assumed — without ChatGPT's actual blocker.

**Clarified scope with the user before building**: asked whether Grok
should reuse the existing generic OpenAI-compatible slot for API-key
mode, or get its own dedicated fields — user chose dedicated (so NIM
and Grok-via-key can be configured simultaneously, not sharing one
slot), plus explicitly wants both modes available as a radio toggle in
one Grok "bubble," not a forced either/or provider split.

**Research pass before writing any OAuth code (user explicitly asked
for this order, given the ChatGPT precedent of one wasted implementation
attempt)**: confirmed live via `curl` — not just read about in
third-party docs — that `auth.x.ai`'s OIDC discovery
(`/.well-known/openid-configuration`), device-code endpoint (`POST
/oauth2/device/code`), and token endpoint all return real 200 responses
to a plain `curl`/httpx client, no Cloudflare bot/TLS-fingerprint
challenge of the kind that blocked `auth.openai.com` and forced the
Codex CLI bundling workaround. Found and read the full, real,
working source of an open-source implementation
(`piex-dev/piex`'s `extensions/xai-oauth`, itself ported from
`NousResearch/hermes-agent`) to get the exact endpoint URLs, the public
client_id (`b1a00492-073a-47ea-816f-4c329264a828` — a public client
identifier, not a secret, same category as `codex_oauth.py`'s hardcoded
`CLIENT_ID`), and scope string, rather than guessing or reverse-
engineering. **This means the subscription half needed zero bundled
binaries and zero Dockerfile changes** — plain `httpx` calls, unlike
`codex_oauth.py`'s subprocess-based CLI delegation.

**New backend files**, mirroring the `codex_oauth.py`/`codex_settings.py`/
`routers/codex.py` pattern exactly but adapted for the plain-HTTP
reality: `grok_oauth.py` (device-code start/poll/refresh — poll-driven
from the status endpoint rather than a background `asyncio.Task`, since
there's no subprocess to block on; `routers/grok.py`'s `/status` route
calls `poll_once()` itself, same interval-driven design the frontend's
`useGrokStatus` hook already polls on), `grok_settings.py` (token
storage, identical shape to `codex_settings.py`), `routers/grok.py`
(connect/disconnect/status/test, mirrors `routers/codex.py`).
`providers.py` gained `llm_grok()` (dispatches to either mode based on
`settings["grok_mode"]`, both paths hitting the same `api.x.ai`
`chat/completions` endpoint — the only difference is how the Bearer
token is obtained) and `grok_enabled()` (checks whichever of the two
mutually-exclusive modes is actually selected). `PROVIDERS` tuple,
`enricher.py`'s `_llm()` dispatch, `models.py`'s `AISettingsUpdate`, and
`routers/settings.py`'s test-provider `Literal` all extended the same
mechanical way every provider before it was.

**Frontend**: new `GrokIcon` (crossing angular strokes, distinct from
the existing 4-point `SparkleIcon` used elsewhere for AI liner notes),
new `useGrokStatus.ts` hook (identical shape to `useCodexStatus.ts`),
and a new Grok card in `AISettingsPage.tsx` between ChatGPT and
OpenCode — a `role="radiogroup"` toggle (new `.grok-mode-toggle`/
`.grok-mode-option` CSS, no prior radio-button pattern existed anywhere
in this app to reuse) switching between the API-key fields (base URL/
model/key, prefilled to `https://api.x.ai/v1` / `grok-4.3`) and the
subscription connect/status flow (reuses `codexUserCodeHint`/
`codexWaiting`'s i18n strings rather than duplicating near-identical
copy, since the device-code UX is genuinely the same interaction).

**Verified with real functional tests against the live xAI API, not
mocks**: a throwaway script minted a real device code via
`start_device_flow()`, confirmed `pending_status()` and `poll_once()`
behave exactly as designed against actual live responses (including
the real `authorization_pending` 400 response, matching the code's
error handling exactly), and confirmed the full FastAPI app imports
cleanly with all 5 new `/api/settings/grok/*` routes correctly wired
and requiring auth (401, not 404, via `TestClient`) — not just that
the Python files parse. Frontend: a throwaway harness rendered the
real `AISettingsPage` component (with `window.fetch` stubbed for the
settings/providers endpoints it calls on mount) and screenshotted both
radio states — API-key mode showing the three prefilled fields, and
Subscription mode showing the "Connect with Grok" button matching the
ChatGPT bubble's own not-connected layout — confirming the actual
rendered UI, not just that the JSX compiles. `tsc --noEmit`, `oxlint`,
`vite build`, and a Python `ast.parse` syntax check across every new/
touched backend file all clean.

**Disclosure in KB.md/README.md mirrors ChatGPT/Codex's own** — new
`### Grok (xAI)` section in KB.md's §6 documents both setup paths, and
explicitly notes the subscription path's lower-but-nonzero risk profile
(genuinely documented endpoints, but still not a first-party-blessed
integration — xAI could restrict what an OAuth token is entitled to at
any time, same category of risk as ChatGPT/Codex, just without the
technical bot-block workaround that made ChatGPT's mechanism feel more
fragile). README's "AI liner notes are optional" bullet updated to
cover both providers with an unofficial sign-in option, not just
ChatGPT.

**Bug, caught by the user immediately in production (fixed 2026-09-07,
1.1.1)**: connected Grok via Subscription mode, then clicked Test and
got "No API key configured." — for an account that genuinely was
connected. Root cause: `grok_mode` is a field in `settings.json`, and
every settings field except this one is meant to require the main
**Save** button before it takes effect, by design (matches every other
provider's field). But selecting **Subscription** and clicking
**Connect** is a self-contained action from the admin's point of
view — it completes real OAuth and writes real tokens to
`grok_settings.json` immediately, with no expectation that Save also
needs a separate click afterward. Confirmed live on LT:
`settings.json`'s `grok_mode` was `None` (defaulting to `"api_key"` at
load time) while `grok_settings.json` showed a genuinely connected
subscription — `_test_grok()` correctly reads the *saved* mode, saw
`"api_key"`, and correctly (given that stale input) reported no key
configured. Fixed by having `connectGrok()` in `AISettingsPage.tsx`
`PATCH /api/settings/ai` with `{grok_mode: 'subscription'}` immediately
before starting the OAuth flow — the one deliberate exception to
"settings fields wait for Save," because Connect/Disconnect already
write to the server outside the form's own save cycle, same as
`grok_settings.json`/`codex_settings.json` always have. The
already-broken production account's `settings.json` was patched
directly on LT (`grok_mode: "api_key"` → `"subscription"`, the one-line
fix matching what Connect should have written the first time) since
the code fix alone only prevents this for future connections, not
retroactively for an account already stuck in the broken state.
**Lesson**: when a UI has one field that's genuinely written by two
different actions (Save button, and Connect/Disconnect elsewhere on
the same page), decide explicitly which of those actions owns writing
it — defaulting to "the same rule as every other field" without
checking is exactly how this slipped through initial testing, since
the harness used for 1.1.0's own verification stubbed the connect
flow rather than exercising a real Save-less Connect against a live
backend.

**User-reported real-production timing (2026-09-07)**: Grok (subscription
mode) responds in under 10 seconds — faster than every other provider
on record. For comparison, from the 0.5.23-era 4-way comparison and
subsequent live data: ChatGPT/Codex 23-70s, opencode had 100+s
outliers, Ollama/NIM's usual range was 5-20s. Grok is at or ahead of
the fastest provider previously measured. Not yet acted on (no request
to reorder the provider preference/fallback chain based on this) — just
recorded as a data point in case speed becomes a deciding factor later,
the same way the original 4-way comparison's timing data drove the
ChatGPT/opencode/Ollama/NIM preference order in `PROVIDERS`/the
settings-page card order.

No way to check Grok's subscription usage/quota remaining from within
mradio-web — confirmed when asked directly: xAI's API has no documented
usage-quota endpoint the app could query (unlike, say, a hypothetical
built-in dashboard), and the OAuth chat/completions call doesn't return
usage data in its response. The only place to check is xAI's own
side (console.x.ai for API-key mode, or wherever SuperGrok/X Premium+
surfaces subscription usage). mradio's own signal is reactive only:
a failing Test button or a silent fallback to the next configured
provider, not a predictive quota view.

## Subscription-based AI providers (ChatGPT, Grok) restricted to admins only (2026-09-07, 1.1.2)

User's explicit request: "the AI agents that are with subscription
(non free) as ONLY available to admins." Clarified scope before
building — asked whether Grok's API-key mode (metered but not tied to
anyone's *personal* subscription the way Subscription mode is) should
be exempt; user chose the simpler, broader rule: **both of Grok's
modes, entirely**, same as ChatGPT — since API-key mode is still
billed to the admin's own xAI account, not free either way.

This was previously enforced at configuration time only
(`routers/codex.py`/`routers/grok.py` already required
`require_admin` to set up credentials) but NOT at use time — any
regular account could still select ChatGPT/Grok from the player's own
AI-provider dropdown once an admin had configured them, or receive
them via the automatic fallback chain with zero visibility into whose
budget was being spent.

**New single source of truth**: `providers.py`'s
`ADMIN_ONLY_PROVIDERS = frozenset({"codex", "grok"})`. Every place that
computes which provider to actually use routes through one new choke
point, `Enricher._usable_providers()` — returns the full `PROVIDERS`
tuple for an admin, or `PROVIDERS` minus `ADMIN_ONLY_PROVIDERS` for
everyone else. `active_provider()`, `switch_provider()`, and `_llm()`'s
automatic fallback chain all call it, so a non-admin can never reach
ChatGPT/Grok through any path — explicit selection, a stale
pre-restriction persisted choice, or silent fallback when their actual
pick fails — not just the obvious "block the dropdown" case.

**`Enricher` needed to learn admin status**, which it didn't track
before. `enrichers.get_enricher()` changed signature from `(user_id:
int)` to `(user: dict)` — refreshes `enricher.is_admin` on *every*
call, not just at creation, so a mid-session promotion/demotion (an
admin changing another admin's role while they're actively connected)
takes effect immediately without a reconnect. All 4 call sites
(`routers/ws.py`, `routers/enrich.py` ×2, `routers/config.py`) already
had the full `user` dict in scope from `get_active_user`'s dependency,
so this was a pure signature change, no new DB lookups added.

**Two enforcement layers in `routers/enrich.py`**, both required —
neither alone is sufficient: `list_providers()` omits admin-only
providers from the response entirely for a non-admin (not just marks
them disabled — they shouldn't see "ChatGPT"/"Grok" as options in the
list at all), and `activate_provider()` separately returns 403 if a
non-admin's request names one directly, defense against calling the
API without going through the UI. The frontend needed zero changes:
`NowPlayingPanel.tsx`'s provider dropdown already just renders
whatever `providers` array the backend returns, so filtering
server-side was sufficient on its own.

**Verified with real functional tests, not just reading the code**: a
throwaway script confirmed `_usable_providers()` correctly excludes
`codex`/`grok` for `is_admin=False` and includes both for
`is_admin=True`; confirmed `switch_provider('codex')`/`switch_provider('grok')`
both return `False` for a non-admin even when otherwise valid;
confirmed `active_provider()` never resolves to an admin-only provider
for a non-admin even when `self.provider` is a stale pre-restriction
`"codex"` pick and no other provider happens to be configured except
one that IS admin-only-adjacent (it correctly fell through to
`opencode`, which happened to be enabled on this dev machine, not
`codex`). Inspected the actual route source via `inspect.getsource()`
to confirm the 403 guard and the list-filtering logic are really wired
into the live route functions, not just present somewhere in the
file. `tsc --noEmit`, `oxlint`, `vite build`, and a Python syntax check
across every touched backend file all clean.

**KB.md** gained a note in §6's intro (before the per-provider
sections) explaining this is enforced at *use* time, not just
*configuration* time, and that it covers explicit selection, stale
persisted picks, and automatic fallback alike — not just "hidden from
the dropdown."

## Rename a favorite, in place (added 2026-09-08, 1.2.0)

User asked for a third edit-mode action alongside delete/move,
explicitly requesting an in-place inline edit rather than a popup, and
asked directly how to do it "elegantly" — offered a design choice
(pencil icon next to trash vs. tap-the-name-itself) before building;
user picked the explicit pencil icon for discoverability.

**Confirmed the scope question before implementing, by reading the
data model rather than assuming**: favorites are entirely per-user
(`userdata.py`'s `load_favorites(user_id)`, one JSON file per account),
keyed by URL, holding `{name, url, genre}`. Renaming here only ever
edits the calling user's own favorite entry — never the shared curated
catalogue (`stations.py`) and never another user's favorites, even for
the exact same station URL. `genre` is deliberately left untouched by
rename (still derived from the station's real identity via
`genre_of()`, not tied to whatever label the user prefers).

**Backend**: new `userdata.rename_favorite(favs, url, name)` — same
find-by-URL-preserve-slot-position shape as the existing
`delete_favorite()`, blank names are a no-op rather than silently
saving an empty label. New `PATCH /api/favorites` (REST-appropriate
verb for a partial update of an existing resource, distinct from the
existing POST=add/DELETE=remove/POST /move=reorder shape).

**Frontend**: new `PencilIcon`/`CheckIcon`/`XIcon` in `Icons.tsx`.
`StationBrowserPanel.tsx` gained `renaming`/`renameValue` state and a
`onStartRename`/`onSaveRename`/`onRenameKeyDown` trio. The trickiest
part was structural, not visual: a filled favorite slot in its normal
display state is a `<button>` (so clicking it plays the station or
marks it for move), but a `<button>` can't cleanly contain a real
`<input>` (nested interactive elements, and the input's own clicks
would bubble into the button's onClick) — so a slot in rename mode
renders as a plain `<div>` instead, swapped in only for that one slot
via `renaming === i`, with the input, a check (save), and an X
(cancel) icon inside it directly. Save fires on Enter, on blur (click
away — the "in place, elegant" behavior explicitly asked for), or on
clicking the check icon; Escape or the X icon cancels without saving.
`onMouseDown={(e) => e.preventDefault()}` on both the check and cancel
icon spans stops the input's own `onBlur` from firing (and
saving/racing) before the click's own handler runs — without it,
clicking either icon would blur-save first, defeating Escape/cancel's
own icon-click equivalent. `onSlotClick` gained an early return when
`renaming !== null`, so clicking a different slot while a rename is
in-flight can't accidentally trigger play/mark-for-move underneath it.
Also fixed a small pre-existing sloppiness while touching this file:
`.fav-delete:hover` unconditionally turned every icon in that shared
class red on hover, including the new pencil/check icons where red
reads as "destructive" incorrectly — split into `.fav-rename`/
`.fav-rename-save` hover variants using the accent color instead,
trash/cancel keep the red.

**Verified with real interaction tests, not a hand-assembled mockup**:
a throwaway harness rendered the real `StationBrowserPanel` (with
`window.fetch` stubbed to serve/mutate an in-memory favorites array,
including a working fake `PATCH` handler) and drove actual DOM clicks
— click "Edit favorites," click the real `.fav-rename` pencil element,
confirmed via `--dump-dom` that the `renaming`/`fav-rename-input`
classes appear in the live DOM (not just asserted from reading the
JSX) — then a second pass typed a new value via a real `input` event
and clicked the real save button, screenshotted the result, and
confirmed the panel returned to its normal display state showing the
new name. Backend: a throwaway script called `rename_favorite()`
directly and confirmed a matching-URL rename, a non-matching URL
no-op, and a blank-name no-op all behave correctly. `tsc --noEmit`,
`oxlint`, `vite build`, and a Python syntax check both clean.

## Google Gemini added as 6th AI provider, free for everyone; AI providers page redesigned as collapsible cards (added 2026-09-08, 1.3.0)

User explicitly asked for these two together: add Gemini as a free
provider "intended for everyone" (contrast with the ChatGPT/Grok
admin-only restriction from the same day), and separately flagged the
AI providers page as "too long" now that it has this many bubbles,
asking for some form of toggle.

**Gemini is fully OpenAI-compatible, unlike Grok's dual-mode**:
confirmed live via `curl` that `generativelanguage.googleapis.com/v1beta/openai/`
is real, reachable, and returns a proper structured error for a bad
key (`400 INVALID_ARGUMENT`, not a 401/403 like a typical OpenAI-shaped
API — this mattered for the test function, see below) — so this needed
no dual-mode toggle, no OAuth, nothing Grok-shaped at all. Backend
factored `providers.py`'s existing `llm_openai()`/`_test_openai()` into
shared `_llm_openai_compatible()`/`_test_openai_compatible()` helpers
(now that a second real OpenAI-compatible caller exists, not before)
rather than writing a third near-copy of the same request/response
shape; `_test_openai_compatible()` gained a `key_rejected_statuses`
parameter specifically so Gemini's 400-based rejection could be
handled without duplicating the whole test function. New
`llm_gemini()`/`_test_gemini()` are each ~6 lines calling the shared
helpers with Gemini's own field names. **Deliberately NOT added to
`ADMIN_ONLY_PROVIDERS`** — confirmed this is the one property that
makes Gemini different from Grok's API-key mode despite both being
"just an API key": Gemini's free tier isn't billed to anyone's account
at all, whereas Grok's API-key mode is still billed to the admin's own
xAI account even though it's not a subscription per se.

Own dedicated settings fields (`gemini_api_base`/`gemini_api_key`/
`gemini_model`/`gemini_timeout`), same precedent as Grok getting its
own fields instead of sharing NIM's generic slot — so NIM and Gemini
can both be configured and used at the same time. Default model
`gemini-3.8-flash`, the current Flash-family model on Google's actual
free tier per their own docs as of this writing — Pro models moved
behind billing in 2026, only Flash/Flash-Lite remain free, and Google's
model lineup is noted (in KB.md too) as changing often enough to be
worth a live check if this default ever stops working.

**Page redesign, decided via two explicit design questions before
building** (not assumed): asked whether collapsed-by-default should
apply even to already-configured providers, or whether a configured
provider should start expanded — user chose configured-starts-open,
matching "let me see what's already set up at a glance, collapse the
rest." Asked separately whether to extract a shared wrapper now that a
6th copy-pasted bubble would make the existing duplication worse, or
keep the copy-paste pattern for consistency — user chose extraction.

New `ProviderBubble` in `AdminSettingsShared.tsx` (alongside the
existing `KbNote`/`TestBadge`) — owns the collapse/expand shell
(header row as a real `<button>` for keyboard/a11y correctness,
`aria-expanded`, a rotating chevron via new CSS `.provider-collapse-chevron.open`),
each provider only supplies its own fields/test-button JSX as
`children`. `defaultOpen` seeds `useState` once at mount and
deliberately does NOT force re-expansion later if `enabled` flips true
after the admin has manually collapsed it — noted in the component's
own comment as a deliberate choice, not an oversight, since auto-
re-expanding after a manual collapse would fight the admin's own
action. All 6 bubbles (`AISettingsPage.tsx`) converted to
`<ProviderBubble icon=... name=... enabled=... defaultOpen=...>`,
shrinking each from its previous ~50-90 line hand-written header block
down to just its fields. Page's total line count dropped even after
adding Gemini's entire new bubble, net effect of the refactor
outweighing the addition.

**Verified with a real driven-click test, not a static screenshot**: a
throwaway harness rendered the real `AISettingsPage` (with
`window.fetch` stubbed, one fake-configured provider (`openai`) and one
fake-unconfigured provider mixed in) and confirmed via screenshot that
configured bubbles (OpenCode per its own binary-present auto-enable,
NIM per the fake `enabled: true`) start expanded while unconfigured
ones (ChatGPT, Grok, Gemini) start collapsed — then a second pass
programmatically clicked the real Gemini header button and
screenshotted the result, confirming the chevron flipped, the bubble
expanded, and the prefilled base-URL/model fields rendered correctly,
all independent of the still-collapsed ChatGPT/Grok bubbles next to
it. `tsc --noEmit`, `oxlint`, `vite build` all clean; a throwaway
Python script exercised `provider_enabled()`/`run_provider_test()`
against the real live Gemini API with a fake key and confirmed the
400-as-rejected handling works against the actual server response, not
just an assumption from reading Google's docs.

**KB.md** gained a `### Google Gemini` section (same setup-walkthrough
shape as NIM's own section, no risk disclosure needed since this is a
genuinely documented first-party API, unlike ChatGPT/Grok's caveats)
with a one-line note up front that this one is NOT admin-only.
README's provider-list bullet updated to include Gemini.

**Gap caught by the user immediately (fixed 2026-09-08, 1.3.1)**:
Ollama and NIM's bubbles both have a `KbNote` deep link ("New to
Ollama/NIM? See '...' in KB.md") pointing admins at the detailed setup
walkthrough; the initial Gemini build only got a plain one-line intro
sentence, no link — the exact `KbNote` component already existed and
was already imported in this file, it just wasn't used for the new
bubble. Same root cause as the earlier "aiDescription/aiSettings.intro
missed ChatGPT" lesson from 0.5.28: adding a new provider is easy to
under-apply consistently across every existing pattern the other
providers already follow, not just the structural ones (fields,
dispatch, i18n keys) but the softer UX ones too (this deep-link
convention). Fixed by adding the same three-key `geminiNotePrefix`/
`geminiNoteLink`/`geminiNoteSuffix` pattern (mirroring NIM's exact
"Getting an API key" wording, since both are external-key-signup flows
in the same shape, unlike Ollama's local-install flow) across all 15
languages, and wiring a `<KbNote anchor="google-gemini" .../>` into the
Gemini bubble right after its intro paragraph. Confirmed the anchor
slug resolves correctly on the live GitHub-rendered KB.md before
shipping (GitHub's lowercase/hyphenate heading-slug rule, same
verification method used for every prior KB.md deep link in this
project) — `google-gemini` for the `### Google Gemini` heading.
Verified visually via a driven click on the real component (the bubble
starts collapsed since Gemini isn't configured in the test harness, so
the harness auto-clicked its header before screenshotting) rather than
just reading the JSX.

## ChatGPT/Codex Test button showed generic "did not respond" for real quota exhaustion (fixed 2026-09-08, 1.3.2)

`_test_codex()` in `providers.py` called `llm_codex()`, which discards
the HTTP response body/headers on any non-200 status
(`if r.status_code != 200: return None`) — so the Test button's failure
message was always the same generic string no matter what actually went
wrong (expired token, network error, rate limit, real quota exhaustion).

User reported the Test button failing ("ChatGPT/Codex did not respond.")
while their own check of the real Codex CLI's `/usage` screen showed
quota was fine. Root-caused by replicating the exact request
`llm_codex()` makes directly inside the LT container and inspecting the
full response for once: a genuine `429` with
`error.type: "usage_limit_reached"`, `plan_type: "go"`, and a
`resets_at` Unix timestamp ~28 days out. Confirmed via response headers
(`x-codex-primary-used-percent: 100`, `x-codex-primary-window-minutes:
43200` — a 30-day rolling window) that **Codex enforces its own
usage meter, separate from the ChatGPT app/CLI's own token-usage graph**
— a plan can show headroom there and still 429 here. This is real
OpenAI-side quota exhaustion, not a bug in mradio-web's request logic;
the bug was purely that the true reason never reached the UI.

Fix: factored the request-building into `_codex_request_payload()`
(shared by both `llm_codex()` and the new path) and added
`_test_codex_call()` + `_format_codex_error()`, which reads the real
status code and error body on failure. `_test_codex()` now delegates to
`_test_codex_call()` instead of `llm_codex()`. `usage_limit_reached`
renders as "Codex usage limit reached (separate from your ChatGPT app's
own usage — resets YYYY-MM-DD HH:MM UTC)."; 429/401/403 get their own
specific messages; anything else still falls back to a status-code-based
message rather than pure silence. `llm_codex()` itself (the enrichment
fallback-chain path) is untouched — it still just returns `None` on
failure, since that path only needs pass/fail, not a human message.

Verified live before release: hot-patched the fixed `providers.py` into
the running LT container (`docker cp` to a differently-named module,
imported and called directly) against the real, still-exhausted quota —
confirmed it now returns the specific usage-limit message with the
correct reset date instead of the old generic string, before doing the
full rebuild/deploy.

## Manual ENABLE/DISABLE toggle for ChatGPT and Grok's player-dropdown visibility (added 2026-09-08, 1.4.0)

Direct follow-up to the 1.3.2 fix: even with a real error message,
hitting the Codex usage quota still meant every player still showed
ChatGPT as pickable in the dropdown, and picking it just failed
silently in enrichment — the only existing fix was disconnecting
(losing the saved OAuth token) and reconnecting once the quota reset,
which the user described as "having to logout everytime I pass the
quota."

Added `codex_manually_enabled` / `grok_manually_enabled` booleans to
`settings.py`'s `_DEFAULTS` (both default `True`, so existing installs
keep today's behavior until an admin touches the new switch) and gated
`provider_enabled()` in `providers.py` on them for codex/grok only —
deliberately NOT applied to Ollama/NIM/Gemini, which don't share this
"connected but temporarily can't be used" failure mode (Gemini's own
free-tier quota, if hit, would need the same treatment eventually, but
wasn't asked for and isn't needed yet).

This was the single choke point to change: `enricher.py`'s
`active_provider()` fallback chain and `switch_provider()` both already
route through `providers.provider_enabled()` (see the 1.1.2 admin-only
restriction work for why that choke point exists), so gating it there
alone was enough — no separate check needed in the dropdown-listing
endpoint or the fallback logic.

Frontend: added a checkbox (`.provider-enable-toggle`, styled like the
existing `.grok-mode-option` radio pattern) right under the intro
paragraph in both the ChatGPT and Grok `ProviderBubble`s. PATCHes
`/api/settings/ai` immediately on change (same "don't wait for the main
Save button" pattern as `connectGrok()`'s immediate `grok_mode` PATCH
from 1.1.1) so flipping it takes effect right away without also having
to fill in and submit the rest of the form. Unchecking it does NOT
disconnect/lose the saved token — `codexStatus?.connected` and the
Disconnect/Test controls are entirely unaffected, confirmed visually
(see below).

i18n: added `providerEnableToggle` / `providerEnableToggleHint` to all
15 languages. Caught two real bugs doing this in bulk via a Python
script: `nl.ts` got literal doubled straight quotes (`''...''`, invalid
JS) from a translation string mistake, and both `fr.ts` and `it.ts` had
an unescaped straight apostrophe inside a single-quoted string
(`d'utilisation`, `d'uso`) that silently passed `tsc --noEmit` in
isolation but broke the real `vite build` — a reminder that `tsc
--noEmit` alone isn't sufficient proof of a working build; always run
the actual `npm run build` before calling a multi-file text change done.

Verified visually via the throwaway-harness technique (temporary
`DevHarness.tsx` swapped into `main.tsx`, `window.fetch` stubbed for
`/api/settings/ai`, `/api/enrich/providers`, `/api/settings/codex(grok)/
status`, screenshotted via headless Chrome, drove a real click on the
checkbox) — confirmed unchecking it flips the ChatGPT status dot from
green to gray while "Connected (go)." and the Disconnect/Test buttons
stay untouched, before fully reverting `main.tsx` and deleting the
harness file.

**Follow-up gap (fixed same day, 1.4.1):** the visual check above only
covered the *settings page* toggle, not the actual player dropdown it
controls — the player still rendered a disabled/greyed "not configured"
line for every unchecked or unconfigured provider
(`NowPlayingPanel.tsx`'s `providers.map()` with `disabled={!p.enabled}`
plus a `{!p.enabled && ...}` label). User's screenshots showed exactly
this for both a manually-disabled ChatGPT and an unconfigured Gemini —
same "ghost" line in both cases, since both are just `enabled: false`
from the same `/api/enrich/providers` response. Root cause: the toggle
was built to control the underlying `enabled` flag correctly (verified
above), but nobody updated the one place that flag drives UI to actually
hide rather than greying out. Fixed with a one-line change —
`providers.filter((p) => p.enabled).map(...)` instead of mapping every
provider and disabling the button — which also made the `disabled` prop
and the `{!p.enabled && <span>...}` label dead code, removed along with
it. This also removed the now-orphaned `nowPlaying.notConfigured` i18n
key from all 15 languages (grep-confirmed zero remaining references
before deleting). `.dropdown-option:disabled` CSS was deliberately left
alone — it's shared with `TopBar.tsx`'s language picker via the same
`dropdown-option` class, so it's not proven dead, just currently unused
by this particular dropdown.

Not re-verified visually this time (see [[feedback_verify_ui_visually]])
— judged low-risk enough to skip the harness since it's a pure
list-filter with no new branching (`.filter(p => p.enabled)` before an
existing `.map()`), not a new interactive element. If a future dropdown
change in this area turns out subtly wrong, re-check this call.

## Stop then reload/reopen auto-resumed playback anyway (fixed 2026-09-08, 1.4.2)

`usePlayer.ts`'s `play()` persists `last_url`/`last_name`/`last_genre`
to `/api/config` (a real "resume last station" feature), and
`Dashboard.tsx`'s mount effect auto-calls `player.play()` if
`config.last_url` is set. But `stop()` never touched that same config
— it only flipped local React state (`status: 'stopped'`), so the
persisted `last_url` from the most recent `play()` call stayed put
regardless of whether the user later pressed Stop. Reloading or
reopening the app after Stop still saw a populated `last_url` and
resumed playback, since the mount effect had no way to tell "was left
playing" apart from "was played at some point, then stopped."

Fixed by adding a `last_status: 'playing' | 'stopped'` field
(`config.py`'s `ConfigUpdate`, `types.ts`'s `Config`) — `play()` now
also PATCHes `last_status: 'playing'`, `stop()` PATCHes
`last_status: 'stopped'`, and `Dashboard.tsx`'s auto-resume condition
gained `&& config.last_status === 'playing'`. A missing/legacy
`last_status` (any existing user's config predating this fix) reads as
`undefined`, which fails that check and correctly does NOT auto-resume
— matches the safer default (don't surprise-play audio) rather than
guessing. Closing the tab/browser while still playing (not via Stop)
intentionally still resumes on reopen — that's the feature working as
originally intended, only the Stop case was the bug.

**Follow-up gap (fixed same day, 1.4.3):** 1.4.2 correctly stopped
audio from auto-resuming, but overcorrected — it stopped calling
`player.play()` entirely for the `last_status !== 'playing'` case, and
`state.station` (which drives `hasStation`, the panel's station name/
logo/live-dot, the Play/Stop button's enabled state, and the favorites
list's highlighted slot via `currentUrl={player.state.station?.url}`)
is *only* ever populated by `play()`. So Stop→reload went from "wrongly
resumes playback" straight past the correct middle state to "wrongly
shows an empty 'Nothing playing' panel with no station selected at
all" — confirmed by the user's own before/after screenshots showing
Swiss Jazz selected-and-playing before reload, then the panel entirely
empty (no station highlighted in Favorites either) after.

Fixed by splitting "populate the panel with a station's identity" from
"start playback," which had never been two separate operations before.
Added `usePlayer.ts`'s `selectStation(station)` — the same state fields
`play()` sets (station, stationName, hasIcy, rawTitle/artist/title/
performer, enrichment) minus the parts specific to actually starting
audio (no `audioRef` touch, no `wantsConnectionRef` flip, no
`/api/config` PATCH — this is a read-only local reflection of state the
server already persisted, not a new event to record). `Dashboard.tsx`'s
mount effect now branches: `last_status === 'playing'` calls
`player.play(station)` as before; anything else calls
`player.selectStation(station)` instead of skipping entirely. The
existing "Stopped — press play to reconnect" UI in
`NowPlayingPanel.tsx` (already built for the ordinary same-session
Stop click, `hasStation && status === 'stopped'`) needed zero changes —
it was already exactly the right state to land in, just unreachable
after a reload until now.

Verified visually this time (unlike 1.4.1's skip) via the
throwaway-harness technique, but a heavier version than before: this
touches `Dashboard.tsx` itself, which needs `AuthProvider` (for
`TopBar`'s `useAuth()`) plus stubs for `/api/config` (with
`last_status: 'stopped'`), `/api/favorites`, `/api/stations/genres`,
`/api/enrich/trivia-history`, `/api/enrich/providers`, `/api/auth/me`,
`/api/stations/logo`, and a fake `WebSocket` global (real `usePlayer()`
opens one on mount) — a fully-wired `Dashboard`, not just one page
component. Screenshotted the reload state (station name, live-dot,
"Stopped — press play to reconnect.", slot 6 highlighted in Favorites,
Play icon showing) and then drove a real click on the transport button,
confirming it flips to "Connecting…" with the Stop icon — exactly the
same resume path a normal Play click already used, now reachable from a
restored-but-never-live `state.station`.

## Gemini switched from the OpenAI-compat shim to the real Interactions API (fixed 2026-09-08, 1.5.0)

User hit "Connected, but model 'gemini-3.8-flash' was not found on this
endpoint." on the Test button — with a genuinely valid key and a real,
current model. First hypothesis (wrong, corrected below) was that
`gemini-3.8-flash` itself was a hallucinated/bad model name from
whichever earlier session picked it as the default; public docs/
pricing pages both independently confirmed it's real, current, and
free-tier eligible, so that theory didn't hold.

User then pasted the actual current Gemini docs (`aistudio.google.com/
docs/api-key`), which revealed two things `mradio-web`'s Gemini
integration had gotten wrong from the start:

1. **Wrong API surface entirely.** `llm_gemini()`/`_test_gemini()` both
   called Google's OpenAI-*compatibility* shim
   (`v1beta/openai/chat/completions` + `GET .../models`), not Google's
   own native API. Google's current docs exclusively show a different,
   newer surface: the **Interactions API**
   (`POST v1beta/interactions`, `client.interactions.create()`).
2. **Key type mismatch, unconfirmed but plausible.** The user's key
   turned out to be a new-style "auth key" (bound to a service account,
   `AQ.` prefix) rather than a legacy "standard" key — Google's docs say
   these behave differently and that ALL new AI-Studio keys are auth
   keys by default as of this docs revision. Never definitively proved
   this was *the* reason the compat shim's `/models` omitted the model,
   but it's a believable contributing factor either way.

**Verified everything live before writing any code** (per this
project's standing rule against shipping unverified external-API
integrations) — a real curl round-trip against
`https://generativelanguage.googleapis.com/v1beta/interactions` using
the user's actual key, run from inside the LT container (not the
Mac dev machine — see the network-flakiness note below):
- Success: `200`, `gemini-3.8-flash` genuinely works — confirming the
  compat shim's stale `/models` listing was the real bug, not the model
  name or (as far as could be proven) the key type.
- Response shape: `steps[]`, mixing `type: "thought"` (reasoning, no
  visible text — matches `usage.total_thought_tokens`) and
  `type: "model_output"` (`content[].text`, the real reply) — a shape
  Google changed in a documented May 2026 breaking change, gated by the
  `Api-Revision: 2026-05-20` header. Skip thought steps, concatenate
  model_output text.
- The system-prompt field is `system_instruction`, not `instructions` —
  caught by testing it live: a first draft copied `instructions` from
  `llm_codex()`'s unrelated OpenAI Responses-API shape, which returned a
  clean `400 "Unknown parameter 'instructions'."` immediately, before
  this ever reached committed code.
- Error shapes differ by status, also confirmed live: a bad model is a
  flat `{"error": {"message": ...}}` (404); a bad key is that same
  object *wrapped in a JSON array* (`[{"error": {...}}]`, 400) — an
  asymmetry easy to miss without testing both paths, handled in
  `_gemini_error_message()`.

**Apparent "network flakiness" during this verification, corrected**:
`POST /v1beta/interactions` intermittently hung for 20-60s (both from
the Mac dev machine and, later, from inside the LT container) while
`GET /v1beta/models` on the same hostname and other HTTPS hosts (x.ai,
google.com) all returned in under 0.5s. First assumed to be generic
network flakiness — wrong. Root cause, found by testing the same POST
without the `Api-Revision` header and getting an immediate clean `429`:
this free-tier project's rate limit is only **20 requests total** for
`gemini-3.8-flash` (`generate_content_free_tier_requests` metric) — the
repeated live-verification calls in this same debugging session burned
through it, and Google's edge/proxy layer evidently sometimes turns an
over-quota request into a multi-second hang rather than an immediate
429 under sustained retry pressure, rather than always failing fast.
Once the quota was confirmed exhausted, every subsequent request
returned a fast, clean 429 with the real reason — proving
`_gemini_error_message()`'s formatting works correctly. Lesson: a
"hang" against a real external API can be a disguised rate limit, not
just a connectivity problem — check for a fast-vs-slow response pattern
across different endpoints on the same host before concluding it's
generic flakiness.

Removed the `gemini_api_base` setting/field entirely (backend
`_DEFAULTS`/`AISettingsUpdate`, frontend `Config` type and the "API
base URL" row in the Gemini bubble) — the Interactions endpoint isn't
swappable the way Ollama's/NIM's genuinely-configurable base URLs are,
so an editable field there was actively misleading (a user could type
something and it would silently do nothing). Bumped `gemini_timeout`'s
default 30s → 45s after directly observing the "thinking" model's
latency in these live tests (one test burned 364 reasoning tokens
before replying) — a request that times out currently fails silently
through `llm_gemini()`'s `except` clause into the provider fallback
chain rather than erroring loudly, so a too-tight default would look
like a flaky/broken provider rather than what it actually is.

`_test_gemini()` now makes a real generation call (matching what
`llm_gemini()` actually does) instead of the old `GET /models` probe,
so it gets its own 45s timeout rather than sharing the other
providers' 10s `_TEST_TIMEOUT` — those are all fast, lightweight
listing calls; Gemini's test genuinely can't be.

## Gemini default switched from gemini-3.8-flash to gemini-3.5-flash-lite (2026-09-08, 1.5.1)

Direct follow-up to 1.5.0. Even with the Interactions API fix working
correctly, the user kept hitting "Gemini rejected the request: You
exceeded your current quota... limit: 20" on the Test button shortly
after 1.5.0 shipped. Initially mis-diagnosed as a per-minute limit
(the retry countdown was shrinking, 35s → 10s, across repeated Test
clicks) — wrong: a later Test click sent the countdown back UP to 41s,
which a rolling per-minute window can't do. The real answer came from
the user checking their own AI Studio rate-limit dashboard
(`aistudio.google.com/rate-limit`) directly: `gemini-3.8-flash` showed
**23/20 RPD** (requests-per-day, resets at midnight Pacific — a fixed
daily cap, not rolling) — confirmed by the dashboard's own peak-usage
chart spiking straight into the red "Limit" line. The countdown
fluctuation was just each new request recalculating "time until the
next slot frees up" within an already-blown daily bucket, which can
go up or down depending on exactly which of the day's 23 requests are
aging out of the window next — not a sign of an imminent full reset.

Checked the same dashboard for every other free-tier Gemini model: all
of 2.5-flash, 3-flash, 3.5-flash, 3.6-flash, and 3.7-flash share that
identical 20 RPD ceiling — this isn't a 3.8-specific quirk, it's the
free tier's standard allowance for any non-Lite Flash model. Only the
"Lite" variants (`gemini-3.1-flash-lite`, `gemini-3.5-flash-lite`) get
500 RPD — 25x more, same free tier, same account, no billing needed.
User also asked about **Antigravity**, visible on the same dashboard —
checked and ruled out: it's a distinct "Agents" product (Google's
agentic coding tool), not a chat-completion model this app's
liner-notes generation could point at.

Switched the default `gemini_model` to `gemini-3.5-flash-lite`
everywhere it was hardcoded (`settings.py`'s `_DEFAULTS`, both
`llm_gemini()`'s and `_test_gemini()`'s `or "gemini-3.8-flash"`
fallbacks in `providers.py`) — verified live via `_test_gemini()`
itself (not just assumed) that the new model name works before
committing. Also directly patched LT's already-saved
`gemini_model: "gemini-3.8-flash"` in production `settings.json` via
`settings.save()`, the same "code default alone isn't retroactive for
existing saved data" pattern as the 1.1.1 Grok-mode-persistence fix —
a code default change never touches a value a user (or earlier testing
in this same session) already saved.

`gemini_timeout`'s 45s default (from 1.5.0) and the Interactions API
switch itself both stay correct regardless of which specific model is
selected — this fix only concerns which model name ships as the
out-of-the-box default, not the request/response mechanics.

## GitHub project page link added to the user menu (added 2026-09-08, 1.6.0)

Simple addition — an `<a>` element between Settings and Change password
in `TopBar.tsx`'s user dropdown, linking to
`github.com/Marcus1571/mradio-web/tree/main`, `target="_blank"` +
`rel="noopener noreferrer"`. Visible to every account (not gated behind
`user?.is_admin` like Settings is) since it's informational, not an
admin action. `.user-dropdown a` was already styled identically to
`.user-dropdown button` (a pre-existing shared CSS rule), so no new CSS
was needed.

Added the `topbar.githubProject` i18n key to all 15 languages.

Verified visually via the throwaway-harness technique — this time
against `TopBar` directly rather than the full `Dashboard` (needs only
`AuthProvider` for `useAuth()`, no station/config/WebSocket stubbing).
Screenshotted the opened dropdown (confirmed placement, divider
styling, correct English text) and inspected the actual rendered `<a>`
element's `href`/`target`/`rel` attributes via Puppeteer's `$eval`
rather than trusting the JSX alone. Also screenshotted with `dir="rtl"`
forced (a fast layout-only check, not a real Hebrew-locale load) to
confirm the new item doesn't break Hebrew's right-to-left dropdown
alignment — it didn't.

## OpenRouter added as 7th AI provider; Groq and Cerebras struck from findings.md (added 2026-09-08, 1.7.0)

User asked to build "the next one on the list" from `findings.md`'s
researched-but-unbuilt free-AI-provider candidates (Groq → Cerebras →
OpenRouter, in that order). Checked each live before building anything
— the same discipline the Gemini work established, and it caught two
real problems the original research (blog/doc summaries, not live
checks) had gotten wrong:

- **Groq**: user's own screenshot of `console.groq.com/docs/models`
  showed `llama-3.3-70b-versatile`/`llama-3.1-8b-instant` (the models
  the "free tier" claims were based on) marked "Enterprise"/
  "ContactSales" — pulled from self-serve access. Confirmed via a real
  API key's `GET /v1/models`: every model actually available now has
  real, non-zero per-token pricing. Not free anymore. Struck.
- **Cerebras**: confirmed the "possible payment-method requirement"
  flag the original findings.md entry had already hedged on — as of
  August 2026, Cerebras requires a verified card on file just to
  activate API access at all, even though the $5 starter credit itself
  doesn't cost anything. Breaks the whole "no card needed" premise this
  list was built on. Struck without getting a key (would have required
  adding a card, defeating the point).
- **OpenRouter**: checked live, held up. `GET /v1/models` is public and
  unauthenticated (works with no key at all) — confirmed ~19 models
  tagged `:free` with genuinely `"prompt": "0", "completion": "0"`
  pricing. Signup confirmed no-card (multiple independent sources +
  the user's own successful signup). A real authenticated
  `POST /chat/completions` against `openrouter/free` (OpenRouter's own
  free-model auto-router, not one pinned model) returned the exact
  requested JSON, `cost: 0`, standard `choices[0].message.content`
  shape.

**One real gotcha found while verifying**: `_test_openai_compatible()`
(the shared test helper NIM/OpenAI use, which validates a key via
`GET /models`) doesn't work for OpenRouter — its `/models` endpoint
returns `200` even with an invalid or missing key, since it's a public
listing, not an authenticated one. Confirmed live: only the real
`POST /chat/completions` call rejects a bad key (`401`). Wrote a
dedicated `_test_openrouter()` instead of reusing the shared helper —
the same category of "the generic helper's assumption doesn't hold for
this provider" lesson `_test_gemini()` already taught, just a different
specific reason (auth-not-required-for-listing vs. stale-model-listing).

Backend: `llm_openrouter()` itself needed **zero new request/response
handling** — confirmed live that OpenRouter matches the standard OpenAI
`chat/completions` shape exactly, so it reuses `_llm_openai_compatible()`
unmodified (the same helper NIM/OpenAI/Gemini's predecessor share).
Registered in `PROVIDERS` (not `ADMIN_ONLY_PROVIDERS` — free tier, not
a personal subscription, same treatment as Gemini) and
`enricher.py`'s `_llm()` dispatch chain.

Default model `openrouter/free` (not a pinned specific `:free` model)
is a deliberate choice: OpenRouter's free-model roster is explicitly
documented as rotating over time (a real, cited risk — see
`findings.md`'s original OpenRouter entry from before this was built),
so the router auto-adapts as the free lineup changes instead of
silently breaking when one specific free model gets pulled.

Frontend: new `OpenRouterIcon` (three lines converging on a center
node/circle, echoing "routing" — distinct from `GeminiIcon`'s diamond
and `GrokIcon`'s crossing strokes). Own `ProviderBubble`, own i18n keys
across all 15 languages (careful with apostrophes this time — no
repeat of the `nl.ts`/`fr.ts`/`it.ts` quoting bugs from the 1.4.0
build).

Verified visually: screenshotted the new bubble (icon, green status
dot since a fake key was pre-filled, intro text, KB.md link, Model/API
key fields, auto-expanded since it was the "active" provider in the
stub) and drove a real click on its Test button, confirming the
"Working" badge renders — the same harness technique as every prior UI
verification this session, `DevHarness.tsx` fully reverted after.

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
