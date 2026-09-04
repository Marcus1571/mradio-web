# mradio-web — deployment & operations

This is the detailed reference. `README.md` stays a short intro on purpose —
this file covers building and running the container, first login, managing
accounts, and configuring AI providers.

## 1. Prerequisites

- Docker + the Docker Compose plugin on the host (`docker compose version`).
  On Unraid/LT this is whatever ships with a recent Unraid + the Docker
  service enabled — no Community Apps template needed, this is a manual
  `docker compose` deployment like your other non-CA containers.
- A place for persistent data. Following your existing appdata convention:
  `/mnt/cache/appdata/mradio-web/data`.

## 2. Build and run

```bash
git clone https://github.com/Marcus1571/mradio-web.git
cd mradio-web
```

Edit `docker-compose.yml`:

- Change the volume line from `./data:/data` to your appdata path, e.g.
  `/mnt/cache/appdata/mradio-web/data:/data`.
- Optionally change `MRADIO_ADMIN_USERNAME` / `MRADIO_ADMIN_PASSWORD` —
  these only matter on the very first run (see below); leaving the
  defaults is fine since you're forced to change the password immediately.

Then:

```bash
docker compose build
docker compose up -d
```

`docker compose build` builds the image locally (multi-stage: builds the
React frontend, fetches the pinned `opencode` binary, installs the Python
backend, bundles all three into one image — see the `Dockerfile`). First
build takes a few minutes; nothing is pulled from a registry, everything is
built from this repo.

The container listens on port 8000 (`ports: - "8000:8000"` in the compose
file — change the host side if 8000 is already taken on LT).

## 3. Reverse proxy (Nginx Proxy Manager)

One proxy host covers everything — the UI, the REST API, the stream proxy,
and the WebSocket all live on the same port, because the stream proxy is
just another route on the same FastAPI process, not a separate service.

In NPM, add a proxy host:

- **Domain**: whatever subdomain you want, e.g. `radio.legba.myddns.rocks`
  (matching your existing `*.legba.myddns.rocks` / `*.legba.top` pattern).
- **Forward Hostname/IP**: LT's LAN IP (e.g. `192.168.88.8`).
- **Forward Port**: `8000` (or whatever host port you mapped it to).
- **Websockets Support**: **on**. The now-playing/AI-liner-notes channel
  (`/api/ws`) is a real WebSocket; without this toggle NPM won't upgrade the
  connection and now-playing updates silently never arrive.
- **SSL**: your existing wildcard cert, force SSL on.
- **Advanced tab**, add:
  ```
  proxy_buffering off;
  ```
  This is the one non-default setting the stream proxy needs — without it,
  nginx buffers the live audio instead of streaming it through, so playback
  either stutters or never starts.

Sessions are cookie-based with `Secure` set, so the app **only works over
HTTPS** (i.e. through NPM) — not over plain `http://LT-IP:8000` directly,
except `http://localhost` in a browser during local dev, which gets a
same-origin exception.

## 4. First login

Default bootstrap account: **`admin` / `mradio`** (or whatever you set via
`MRADIO_ADMIN_USERNAME` / `MRADIO_ADMIN_PASSWORD` in `docker-compose.yml`
before the *first* run — these env vars are only read once, when no
accounts exist yet; changing them afterward does nothing).

You'll be forced to set your own password immediately — the account cannot
be used with the default password beyond that one screen.

## 5. Managing accounts

No public sign-up. From the user menu (top right) → **Users** (admin only):

- **Add user** — pick a username and a temporary password; they're forced
  to change it on their first sign-in, same as the bootstrap account.
- **Make admin / Remove admin**, **Disable / Enable**, **Reset password**,
  **Delete** — self-explanatory; you can't demote, disable, or delete your
  own account from here (avoids locking yourself out).

Each account gets its own favorites (12 slots) and its own active AI
provider choice — but see below, credentials are shared, not per-account.

## 6. Configuring AI providers

From the user menu → **AI providers** (admin only). This is one shared set
of credentials for the whole app — every account picks which of these
they want active, but nobody enters their own key. Matches how mradio
itself was configured (env vars / a single settings file), just editable
from the app instead of only at container start.

### opencode

**Bundled in the image already — nothing to configure.** The Dockerfile
fetches the `opencode` CLI (a self-contained native binary, no separate
Node.js runtime needed at runtime) and bakes it in, so it's detected
automatically the same way mradio itself auto-enables opencode when the
binary happens to be on `PATH`. It'll just show up as "enabled" in the AI
providers list.

If you ever want to turn it off, set the **opencode** field to `0` — that
overrides the auto-detection.

Its own version is pinned in the `Dockerfile` (`ARG OPENCODE_VERSION`) so
builds stay reproducible. A scheduled GitHub Action
(`.github/workflows/bump-opencode.yml`) checks weekly for a newer
`opencode-ai` release and opens a PR bumping the pin — review and merge it,
then `docker compose build` on LT to pick it up. It never auto-merges or
pushes a new image anywhere by itself.

### NVIDIA NIM (OpenAI-compatible)

- **API base URL**: your NIM endpoint — typically
  `https://integrate.api.nvidia.com/v1`, but check the exact value on your
  build.nvidia.com API settings page rather than trusting that blindly.
- **Model**: the NIM model id you want (e.g. one of the Llama/Mixtral
  models NVIDIA hosts).
- **API key**: paste the key from `build.nvidia.com/settings/api-keys`
  (starts with `nvapi-`, same as mradio's own key format). Stored server
  side; the settings page only ever shows it redacted after saving.

### Ollama

- **Server URL**: `http://192.168.88.8:11434` for your LT setup.
- **Model**: whatever you've pulled on that Ollama instance (mradio
  defaulted to `gemma3:4b` — keep that or change it).

Whether this points at your existing Hermes-Agent Ollama/NIM stack or runs
independently is entirely up to what you type in these two provider
sections — nothing in the code assumes either way.

## 7. Data and backups

Everything persistent lives under the `/data` volume:

- `mradio.db` — SQLite: accounts, sessions.
- `settings.json` — the AI provider credentials above.
- `cache.json` — the shared AI liner-notes cache (author/track → trivia),
  shared across all accounts on purpose.
- `users/<id>/stations.json`, `config.json` — each account's favorites and
  personal settings (theme, volume, active provider).

Back up the whole `/data` directory (or just the appdata folder on LT, same
as your other containers) — it's the entire state of the app.

## 8. Updating

```bash
git pull
docker compose build
docker compose up -d
```

Rebuilds the image with the latest code and restarts the container. No
database migration step exists yet — the schema is additive so far.
