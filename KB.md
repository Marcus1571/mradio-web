# mradio-web — deployment & operations

This is the detailed reference. `README.md` stays a short intro on purpose —
this file covers building and running the container, first login, managing
accounts, and configuring AI providers.

## 1. Prerequisites

- Docker + the Docker Compose plugin on the host (`docker compose version`).
  On Unraid this is whatever ships with a recent Unraid release + the
  Docker service enabled — no Community Apps template needed, this is a
  manual `docker compose` deployment, same as any container you'd run
  outside the CA app store.
- A place for persistent data on the host, e.g. `/mnt/cache/appdata/mradio-web/data`
  on Unraid, or any other path on a plain Linux host.

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
file — change the host side if 8000 is already taken by something else on
your server). On a host that's already running other containers (common
on something like Unraid, which tends to accumulate a lot of them), check
for a conflict first (e.g. `docker ps` and look for a mapping already
using 8000) rather than assuming it's free.

If it's taken, keep the base `docker-compose.yml` unchanged and add a
`docker-compose.override.yml` next to it (untracked — host-specific,
don't commit it) remapping the host port and volume path, e.g.:

```yaml
services:
  mradio-web:
    ports: !override
      - "8123:8000"
    volumes:
      - /mnt/cache/appdata/mradio-web/data:/data
```

The `!override` YAML merge tag (Compose 2.24+) matters here: Compose
merges `ports:` lists by *appending*, not replacing, so without it,
Compose ends up trying to bind both the original and the new port, and
the container fails to start if the original one is already taken.

## 3. Reverse proxy (Nginx Proxy Manager)

One proxy host covers everything — the UI, the REST API, the stream proxy,
and the WebSocket all live on the same port, because the stream proxy is
just another route on the same FastAPI process, not a separate service.

In NPM, add a proxy host:

- **Domain**: whatever subdomain you want to use for this app, e.g.
  `radio.example.com`.
- **Forward Hostname/IP**: the server's LAN IP (e.g. `192.168.1.10`).
- **Forward Port**: `8000` (or whatever host port you mapped it to).
- **Websockets Support**: **on**. The now-playing/AI-liner-notes channel
  (`/api/ws`) is a real WebSocket; without this toggle NPM won't upgrade the
  connection and now-playing updates silently never arrive. The app sends
  a lightweight `{"type":"ping"}` keepalive over this socket every 30
  seconds, so most reverse proxies' idle-connection timeouts (e.g.
  nginx's default `proxy_read_timeout 60s`) never trigger — you shouldn't
  need to touch that setting for this. If you still see the socket dying
  periodically (visible as `mradio.ws INFO disconnected` in `docker
  logs`) behind an unusual proxy setup, raising `proxy_read_timeout`
  there in the Advanced tab is the fallback.
- **SSL**: a valid cert for that domain, force SSL on.
- **Advanced tab**, add:
  ```
  proxy_buffering off;
  ```
  This is the one non-default setting the stream proxy needs — without it,
  nginx buffers the live audio instead of streaming it through, so playback
  either stutters or never starts.

Sessions are cookie-based with `Secure` set, so the app **only works over
HTTPS** (i.e. through NPM) — not over plain `http://<server-ip>:8000`
directly, except `http://localhost` in a browser during local dev, which
gets a same-origin exception.

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
then `docker compose build` on the server to pick it up. It never
auto-merges or pushes a new image anywhere by itself.

### NVIDIA NIM (OpenAI-compatible)

**Getting an API key:**

1. Create an account at [build.nvidia.com](https://build.nvidia.com) (email
   + password).
2. Add and verify a phone number — required before NVIDIA will issue API
   keys.
3. Go to
   [build.nvidia.com/settings/api-keys](https://build.nvidia.com/settings/api-keys),
   click **Generate Key**, and copy the `nvapi-...` value.
4. Paste it into mradio-web's **AI providers** page (user menu → AI
   providers, admin only) in the API key field, then **Save**.

**Fields:**

- **API base URL**: defaults to `https://integrate.api.nvidia.com/v1` on a
  fresh install — NVIDIA's hosted NIM endpoint. Double-check the exact
  value on your build.nvidia.com API settings page if it's ever changed on
  their end, rather than trusting this blindly.
- **Model**: defaults to `minimaxai/minimax-m3` on a fresh install — the
  only free NIM model that reliably returns clean, strict JSON matching
  this app's liner-notes schema (same reasoning as the original mradio
  terminal app). The NIM catalogue changes often; other free models may
  appear or disappear, or you can point this at any other model you have
  access to.
- **API key**: paste the key from step 3 above. Stored server side; the
  settings page only ever shows it redacted after saving.

### Ollama

**Setting up Ollama:**

1. Install Ollama on the machine that will run it — see
   [ollama.com/download](https://ollama.com/download).
2. Pull a model to use for enrichment, e.g. `ollama pull gemma3:4b`.
3. Confirm it's reachable from wherever this app runs — Ollama listens on
   port `11434` by default.
4. If the app and Ollama run on different machines, make sure Ollama
   accepts connections from the network (not just `localhost`) and that
   any firewall allows the port.
5. Paste the server URL and model name into mradio-web's **AI providers**
   page (user menu → AI providers, admin only), then **Save**.

**Fields:**

- **Server URL**: e.g. `http://192.168.1.10:11434` for an Ollama instance
  running on your LAN, or `http://localhost:11434` if it's on the same
  host.
- **Model**: whatever you've pulled on that Ollama instance (mradio
  defaulted to `gemma3:4b` — keep that or change it).

Whether this points at an existing Ollama/NIM setup you already run for
other things, or a dedicated instance just for this app, is entirely up
to what you type in these two provider sections — nothing in the code
assumes either way.

## 7. Data and backups

Everything persistent lives under the `/data` volume:

- `mradio.db` — SQLite: accounts, sessions.
- `settings.json` — the AI provider credentials above.
- `cache.json` — the shared AI liner-notes cache (author/track → trivia),
  shared across all accounts on purpose.
- `users/<id>/stations.json`, `config.json` — each account's favorites and
  personal settings (theme, volume, active provider).

Back up the whole `/data` directory (or the equivalent appdata folder on
your platform, same as any other container) — it's the entire state of
the app.

## 8. Updating

```bash
git pull
docker compose build
docker compose up -d
```

Rebuilds the image with the latest code and restarts the container. No
database migration step exists yet — the schema is additive so far.
