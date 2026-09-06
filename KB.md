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

The app trusts `X-Forwarded-For`/`X-Forwarded-Proto` from its reverse
proxy (`uvicorn --proxy-headers`) so it sees each listener's real IP
instead of the proxy's own — this matters for the Analytics page's map
(§10). NPM sends these headers by default; no extra configuration needed
on the NPM side.

It also reads `X-Forwarded-Host` (falling back to the plain `Host`
header) to build the link in password-reset emails (§7) — so if you run
this app behind more than one domain pointing at the same instance, each
reset link correctly points back at whichever domain the listener
actually used. Also sent by NPM by default; nothing to configure.

## 4. First login

Default bootstrap account: **`admin` / `mradio`** (or whatever you set via
`MRADIO_ADMIN_USERNAME` / `MRADIO_ADMIN_PASSWORD` in `docker-compose.yml`
before the *first* run — these env vars are only read once, when no
accounts exist yet; changing them afterward does nothing).

You'll be forced to set your own password immediately — the account cannot
be used with the default password beyond that one screen.

**Forgot your password?** From the sign-in screen, click **Forgot
password?**, enter your account's email, and follow the link mradio-web
emails you (expires in 1 hour, single-use). Only works if the admin has
configured outgoing email (§7) and your account has an email address set
(§5) — if either is missing, ask your admin to reset it for you instead
(same "Reset password" action they'd use for anyone).

## 5. Managing accounts

No public sign-up. From the user menu (top right) → **Settings** → **Users**
(admin only):

- **Add user** — pick a username and a temporary password; they're forced
  to change it on their first sign-in, same as the bootstrap account. A
  full name (shown instead of the username everywhere in the UI — top
  bar, Analytics — once set; supports emoji) and email address (needed
  for the self-service "forgot password" flow above) are optional.
- **Make admin / Remove admin**, **Disable / Enable**, **Edit profile**
  (full name/email), **Reset password**, **Delete** — self-explanatory;
  you can't demote, disable, or delete your own account from here (avoids
  locking yourself out).

Each account gets its own favorites (12 slots) and its own active AI
provider choice — but see below, credentials are shared, not per-account.

## 6. Configuring AI providers

From the user menu → **Settings** → **AI providers** (admin only). This is
one shared set of credentials for the whole app — every account picks
which of these they want active, but nobody enters their own key. Matches
how mradio itself was configured (env vars / a single settings file), just
editable from the app instead of only at container start.

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
4. Paste it into mradio-web's **AI providers** page (user menu →
   Settings → AI providers, admin only) in the API key field, then
   **Save**.

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
   page (user menu → Settings → AI providers, admin only), then **Save**.

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

## 7. Configuring email (SMTP)

From the user menu → **Settings** → **Email (SMTP)** (admin only). This is
one shared outgoing-mail configuration for the whole app, used only to
send self-service "forgot password" reset links (§4) — nobody's inbox is
read, and there's no other use for it yet.

### Using Gmail

1. Turn on **2-Step Verification** on the Google account you want to send
   from (Google Account → Security) — this is required before Google
   will issue an app password, and is separate from your normal Gmail
   password.
2. Go to
   [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords),
   generate a new app password, and copy the 16-character value it
   shows you (only shown once).
3. On mradio-web's Email settings page: **Host** `smtp.gmail.com`,
   **Port** `587` (both already the defaults), **Username** your Gmail
   address, **Password** the app password from step 2 (not your real
   Gmail password), **From address** your Gmail address again, **Use
   STARTTLS** on (default). Save, then use the **Test** button to
   confirm — it sends a real test email to the currently signed-in
   admin's own account email (§5), so make sure that's set first.

This deliberately uses a plain SMTP app password rather than a "Sign in
with Google" OAuth flow — sending mail via Gmail's API needs a Google
"restricted scope" that requires a formal security review once an app
leaves testing mode, which is disproportionate for a self-hosted app
with a handful of accounts. An app password is Google's own recommended
path for exactly this situation, and avoids that review entirely.

Any other SMTP provider (a self-hosted mail server, another mailbox
provider, a transactional-email service's SMTP endpoint, etc.) works the
same way — just fill in that provider's own host/port/username/password.

**Fields:**

- **Host** / **Port** / **Username** / **Password**: your SMTP provider's
  connection details. Password is stored server side; the settings page
  only ever shows it redacted after saving.
- **From address**: the address reset emails appear to come from.
- **Use STARTTLS**: on by default — nearly every modern SMTP provider
  (including Gmail) expects this on port `587`.
- **Public URL** (optional): almost never needed. The link inside a reset
  email is normally built automatically from whichever domain the
  listener used to reach the app (§3) — correct even if you run more than
  one domain pointing at this instance. Only set this if that
  auto-detection is ever visibly wrong (e.g. an unusual proxy setup that
  doesn't forward the host header).

## 8. Data and backups

Everything persistent lives under the `/data` volume:

- `mradio.db` — SQLite: accounts, sessions, password-reset tokens, and
  play history (§10).
- `settings.json` — the AI provider credentials above.
- `smtp_settings.json` — the outgoing-email credentials above.
- `cache.json` — the shared AI liner-notes cache (author/track → trivia),
  shared across all accounts on purpose.
- `users/<id>/stations.json`, `config.json` — each account's favorites and
  personal settings (theme, volume, active provider).

Back up the whole `/data` directory (or the equivalent appdata folder on
your platform, same as any other container) — it's the entire state of
the app.

## 9. Updating

```bash
git pull
docker compose build
docker compose up -d
```

Rebuilds the image with the latest code and restarts the container. No
separate database migration step to run — schema changes (including
adding a column to an existing table) apply themselves automatically the
first time the new code starts up.
Rebuilding also refreshes the geolocation database used by Analytics
(§10) — there's no separate scheduled update for it, since it's just a
downloaded data file, not a version pin to review.

## 10. Analytics

Admin-only page (user menu → Analytics) — live sessions, a world map of
listeners, top stations/genres/listeners, and full play history. Nothing
to configure; it works automatically once the reverse-proxy header
trust from §3 is in place.

**The map needs real IPs to show anything.** Every play session records
the listener's IP and resolves it to an approximate city/country via a
local GeoLite2-City database (downloaded automatically at image build
time — no account or API key needed, nothing calls out to a third-party
geolocation service at runtime). Two cases correctly show no location,
not an error:

- Connections from your own LAN or over Tailscale — there's no
  meaningful public location for traffic that never left the local
  network, same as any self-hosted analytics/monitoring tool.
- If §3's proxy-header trust isn't set up correctly, every session will
  look like it's coming from the reverse proxy's own address instead of
  the real visitor — check `docker logs` for the IP recorded against a
  known remote session if the map looks empty when it shouldn't be.

Play history and stats have no such limitation — they work regardless of
where a listener connects from.
