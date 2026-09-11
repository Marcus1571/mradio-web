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
  in that same Custom Nginx Configuration box is the fallback.
- **SSL**: a valid cert for that domain, force SSL on.
- **Custom Nginx Configuration**, add:
  ```
  proxy_buffering off;
  ```
  This is the one non-default setting the stream proxy needs — without it,
  nginx buffers the live audio instead of streaming it through, so playback
  either stutters or never starts.

  In current Nginx Proxy Manager versions this box lives behind the
  **gear icon** at the right of the Edit Proxy Host tab strip (next to
  Details / Custom Locations / SSL), under the heading *Custom Nginx
  Configuration*. Older versions labelled the same tab **Advanced**.

Sessions are cookie-based with `Secure` set, so the app **only works over
HTTPS** (i.e. through NPM) — not over plain `http://<server-ip>:8000`
directly, except `http://localhost` in a browser during local dev, which
gets a same-origin exception.

The app trusts `X-Forwarded-For`/`X-Forwarded-Proto` from its reverse
proxy (`uvicorn --proxy-headers`) so it sees each listener's real IP
instead of the proxy's own — this matters for the Analytics page's map
(§11). NPM sends these headers by default; no extra configuration needed
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

- **Add user** — pick a username. If you give an email address, mradio-web
  generates a temporary password itself and emails the new user an invite
  link to set their own — you never see or type a password. Leave the
  email blank and you pick the temporary password yourself; they're then
  forced to change it on first sign-in, same as the bootstrap account. A
  full name (shown instead of the username everywhere in the UI — top
  bar, Analytics — once set; supports emoji) is optional either way.
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

**ChatGPT and Grok are admin-only to use, not just to configure.**
Every other provider (OpenCode, Ollama, NIM/OpenAI-compatible) is
available to every account once an admin sets it up, same as always.
ChatGPT and Grok are different: since both ultimately spend a real
personal subscription or paid API budget (Grok's API-key mode
included, since it's still billed to the admin's own xAI account),
non-admin accounts never see them as options in the player's AI
provider dropdown, can't select them even by calling the API directly,
and the app's automatic fallback chain (used when the currently-active
provider fails) will never silently fall through to one of these two
on a non-admin's behalf either — it skips straight to the next
available free/self-hosted provider instead.

### OpenCode

**Bundled in the image already — nothing to configure.** The Dockerfile
fetches the `opencode` CLI (a self-contained native binary, no separate
Node.js runtime needed at runtime) and bakes it in, so it's detected
automatically the same way mradio itself auto-enables OpenCode when the
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

### ChatGPT / Codex subscription

**⚠️ Unofficial mechanism — read before enabling.** This lets an admin
sign in with a personal ChatGPT Plus, Pro, or Go subscription instead of
an API key. It works by running the same sign-in as OpenAI's own Codex
CLI (`codex login --device-auth`) and then calling OpenAI's *internal*
Codex backend (`chatgpt.com/backend-api/codex/responses`) with the
resulting token — not the public, documented OpenAI API. This is the
same category of mechanism Anthropic shut off for the equivalent Claude
Code OAuth token in early 2026 (third-party use started billing as
overage, then stopped working). OpenAI hasn't done this as of writing,
but could at any time, without notice — if it breaks, liner notes for
that provider just stop working until you either wait it out or switch
to a different provider; nothing else in the app is affected. Use this
only if you're comfortable with that risk.

**Setting it up:**

1. Go to mradio-web's **AI providers** page (user menu → Settings → AI
   providers, admin only) and click **Connect with ChatGPT** in the
   "ChatGPT / Codex subscription" section.
2. The page shows a one-time code and a link. Open the link (or type it
   into a browser yourself), sign in to the ChatGPT account you want to
   use, and enter the code.
3. Once you complete that, the page automatically shows "Connected"
   along with your plan type (Plus/Pro/Go). No API key, no manual token
   entry.
4. Use **Disconnect** at any time to sign this app out — the stored
   token is deleted and the provider goes back to "not configured" for
   everyone.

**Hit your usage limit?** ChatGPT/Codex subscriptions have their own
usage quota, separate from the ChatGPT app/website's own usage graph —
the Test button shows the exact reset date when this happens. Rather
than disconnecting (which loses the sign-in and means redoing the OAuth
flow later), use the **"Show in the player's AI menu"** toggle in this
same section to hide the provider from everyone's dropdown while
keeping the connection intact, then switch it back on once the quota
resets. Grok, Gemini, and OpenRouter's sections all have the same
toggle for the same reason — every provider with a real usage quota
gets one.

**Auto-hide on failure**: ChatGPT, Grok, Gemini, and OpenRouter also
hide themselves from the dropdown automatically, without any manual
action — if a real enrichment request through one of them fails (bad
key, expired token, quota hit, network error), it drops out of
everyone's dropdown right away. A background check retries it every 30
minutes; if that retest succeeds, it reappears on its own — no admin
action needed either way. While hidden this way, its section on the AI
providers page shows a note: "Temporarily hidden from the dropdown
after a recent failure — retrying automatically in the background." —
distinct from the manual toggle above, which stays exactly as you left
it. Ollama and the generic OpenAI-compatible (NIM) bubble don't get
this: a failure there is almost always a config mistake (wrong URL/
key) that won't fix itself on a timer, so hiding it automatically would
just mask something that needs a person to go fix it.

This provider is bundled the same way `opencode` is (§ above): the real
`codex` CLI binary ships inside the Docker image (`Dockerfile`'s
`codex-build` stage, `ARG CODEX_VERSION`), used only to perform the
sign-in itself — plain HTTP login attempts are blocked by a Cloudflare
bot/TLS-fingerprint check on OpenAI's side, confirmed during
development, which the real CLI passes because it's a genuine trusted
client. A scheduled GitHub Action
(`.github/workflows/bump-codex.yml`) keeps that version pinned and
up to date the same way `bump-opencode.yml` does.

### Grok (xAI)

Two ways to use xAI's Grok models, chosen with a radio toggle in the
Grok section of the **AI providers** page — mutually exclusive, pick
one.

**Option A — API key (metered, pay per token):**

1. Create an account at [console.x.ai](https://console.x.ai) and
   generate an API key.
2. Select **API key** in the Grok section's radio toggle.
3. Fields:
   - **API base URL**: defaults to `https://api.x.ai/v1` on a fresh
     install — xAI's own documented API.
   - **Model**: defaults to `grok-4.3` on a fresh install. Check
     [console.x.ai](https://console.x.ai) for xAI's current model
     lineup and pricing if you want a different one.
   - **API key**: paste the key from step 1. Stored server side; the
     settings page only ever shows it redacted after saving.
4. **Save**.

**Option B — SuperGrok / X Premium+ subscription (no per-token
billing):**

1. Select **Subscription** in the Grok section's radio toggle, then
   click **Connect with Grok**.
2. The page shows a one-time code and a link. Open the link (or type
   it into a browser yourself), sign in to the xAI/X account you want
   to use, and enter the code.
3. Once you complete that, the page automatically shows "Connected."
4. Use **Disconnect** at any time to sign this app out.

This works via xAI's own standard OAuth device-code flow
(`auth.x.ai`) — confirmed during development that, unlike OpenAI's
equivalent for ChatGPT/Codex above, this endpoint is genuinely
reachable by a plain HTTP client with no bot/TLS-fingerprint block, and
the resulting token is used against `api.x.ai`, the same public
documented API Option A also calls, not an undocumented internal
route. No CLI binary is bundled for this — it's plain HTTP calls, same
as everything else in this app. Still worth the same disclosure as
ChatGPT/Codex above: this authenticates the same way third-party CLI
tools do, not through a first-party integration xAI has explicitly
blessed, and xAI could change or restrict what an OAuth token is
entitled to at any time. If it breaks, switch to Option A or another
provider; nothing else in the app is affected.

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
- **Model**: defaults to `mistralai/mistral-nemotron` on a fresh install
  (changed 2026-09-09 — the previous default, `minimaxai/minimax-m3`,
  was retired by NVIDIA and started returning `410 Gone`; confirmed
  live). NVIDIA's `/v1/models` catalogue is a poor guide to what
  actually works: a live probe of all ~80 models it lists for a real
  account found only ~9 genuinely invokable, and most of those are
  reasoning/safety-classifier/embedding models unsuited to this app's
  strict single-JSON-object task. If this default ever breaks again,
  re-probe the account's real model access rather than trusting the
  public catalogue or picking a plausible-sounding name — most 404 with
  "Function not found for account".
- **API key**: paste the key from step 3 above. Stored server side; the
  settings page only ever shows it redacted after saving.

### Google Gemini

Not admin-only — unlike ChatGPT and Grok, this isn't tied to anyone's
personal paid subscription, so once configured every account can use
it, same as OpenCode/Ollama/NIM.

**Getting an API key:**

1. Go to [aistudio.google.com/api-keys](https://aistudio.google.com/api-keys)
   and sign in with a Google account.
2. Click **Create API key** — no credit card or billing account needed
   for the free tier.
3. Copy the key and paste it into mradio-web's **AI providers** page
   (user menu → Settings → AI providers, admin only), in the Gemini
   section's API key field, then **Save**.

**Fields:**

- **Model**: defaults to `gemini-3.5-flash-lite` on a fresh install —
  deliberately a "Lite" model, not the newest `gemini-3.8-flash`. Confirmed
  via a real account's AI Studio rate-limit dashboard
  (`aistudio.google.com/rate-limit`): every non-Lite free-tier Flash
  model (2.5/3/3.5/3.6/3.7/3.8) shares a **20 requests-per-day** cap —
  trivially exhausted by a couple of liner-notes requests, and it only
  resets at midnight Pacific, not on a rolling basis. The Lite variants
  (`gemini-3.1-flash-lite`, `gemini-3.5-flash-lite`) get **500/day**
  instead, on the same free tier, same account. Google's model lineup
  changes fairly often — check
  [ai.google.dev/gemini-api/docs/models](https://ai.google.dev/gemini-api/docs/models)
  or your own AI Studio rate-limit dashboard for current numbers before
  switching to a non-Lite model.
- **API key**: paste the key from step 2 above. Stored server side; the
  settings page only ever shows it redacted after saving.

**Under the hood:** talks to Google's Interactions API
(`v1beta/interactions`), not the older OpenAI-compatibility shim —
confirmed live that the compat shim's own model listing didn't include
`gemini-3.8-flash` even though the model works fine directly, which
produced a false "model not found" Test failure early on. The
Interactions endpoint isn't user-configurable (no base URL field),
since there's only the one real endpoint to point at.

### OpenRouter

**Admin-only** — unlike Gemini, which is free for everyone once
configured. OpenRouter's free tier is a single *shared* daily quota
(50 requests/day, see below) across every account using the one saved
key, not a per-user allowance — with several accounts able to pick it,
that shared quota could be exhausted quickly. One API key routes to
whichever model you name, across many underlying providers.

**Getting an API key:**

1. Go to [openrouter.ai/keys](https://openrouter.ai/keys) and sign up
   with email or GitHub — no credit card needed.
2. Create an API key and copy it.
3. Paste it into mradio-web's **AI providers** page (user menu →
   Settings → AI providers, admin only), in the OpenRouter section's
   API key field, then **Save**.

**Fields:**

- **Model**: defaults to `openrouter/free` — OpenRouter's own router
  that auto-picks among whichever models are currently free, rather
  than one pinned model ID. Deliberate choice: OpenRouter's free-model
  lineup rotates over time (confirmed live via `GET /v1/models`: ~19
  models tagged `:free` with genuinely zero-cost pricing at the time of
  writing), so pinning to a specific one (e.g.
  `nvidia/nemotron-3-super-120b-a12b:free`) risks it later being pulled
  from the free tier. To pin a specific free model instead, use its
  exact `:free`-suffixed ID from
  [openrouter.ai/models](https://openrouter.ai/models) (filter by
  "Free").
- **API key**: paste the key from step 1 above. Stored server side; the
  settings page only ever shows it redacted after saving.

**Free-tier limits**: confirmed live — 50 requests/day if you've never
added credit to the account, rising to 1,000/day (permanently) the
first time you ever spend $10, whether or not you use paid models
day-to-day. Both figures reset daily.

**Reliability note** (2026-09-09): a live provider-comparison found
several of OpenRouter's genuinely free models are reasoning models
whose chain-of-thought is billed against the same `max_tokens` budget
as the actual reply — at this app's original 1200-token budget, some
would exhaust the whole budget reasoning and return empty content,
never reaching real JSON. Fixed by bumping OpenRouter's `max_tokens` to
3000 and its timeout to 90s (`providers.py`'s `llm_openrouter()`,
`settings.py`), plus applying the same anti-hallucination prompt
hardening Mistral/NIM/Gemini get (`textutil.py`'s
`_CATEGORICAL_PROVIDERS`) — its shorter-answer structure also reduces
how much a model needs to reason through, which helped completion
times as much as the bigger token budget did in testing. Even with
these fixes, response times on the free auto-router can vary widely
(observed 3-84 seconds for different tracks) since it's genuinely
unpredictable which underlying model you'll land on each call.

**Under the hood:** standard OpenAI-compatible
`chat/completions` shape (confirmed live) — reuses the same shared
request/response code NIM and the generic OpenAI-compatible bubble
already use. One real gotcha found during setup: `GET /v1/models` is
public and unauthenticated (returns 200 even with an invalid or no
key), so unlike NIM's Test button, OpenRouter's Test makes a real
`chat/completions` call to actually verify the key — a bad key only
ever surfaces as a `401` on that call, never on the models listing.

### Mistral

**Admin-only** (as of 2026-09-09, by explicit request — not a
quota-driven restriction like OpenRouter's shared daily cap, just kept
for admins for now). Uses Mistral AI's free "Experiment" plan on La
Plateforme (their developer API console, distinct from their consumer
"Vibe" chat app).

**Getting an API key:**

1. Go to [console.mistral.ai](https://console.mistral.ai) and sign up —
   no credit card needed, but a one-time phone number verification is
   required.
2. In the console, switch to **Docs & API** (not "Vibe" or "Studio")
   and generate an API key.
3. Paste it into mradio-web's **AI providers** page (user menu →
   Settings → AI providers, admin only), in the Mistral section's API
   key field, then **Save**.

**Fields:**

- **Model**: defaults to `open-mistral-nemo` (12B), not Mistral's
  flagship `mistral-small-latest` — confirmed live (2026-09-09) that
  Mistral Small is rate-limited to **0 requests/minute** on the free
  Experiment tier, even with a valid key. `open-mistral-nemo` and the
  Ministral family (`ministral-3b-latest`, `ministral-8b-latest`) all
  get real free-tier quota instead (see below). To try a different free
  model, check current availability via a real `chat/completions` call
  first — a `GET /v1/models` listing succeeding doesn't mean the free
  tier actually allows requests against that model.
- **API key**: paste the key from step 2 above. Stored server side; the
  settings page only ever shows it redacted after saving.

**Free-tier limits**: confirmed live per-model, not shared account-wide
— `open-mistral-nemo` and `ministral-8b-latest`: 625,000 tokens/min,
188 requests/min. `ministral-3b-latest`: 1,300,000 tokens/min, 750
requests/min. Very generous compared to Gemini's or OpenRouter's daily
caps, on smaller models.

**Accuracy note**: a live spot-check found `open-mistral-nemo` invented
plausible-sounding but incorrect details (wrong dedicatee, an invented
"three weeks" composition claim) on a well-documented classical work —
this provider gets the same anti-hallucination prompt hardening as the
NIM provider (see `textutil.py`'s `apply_provider_rules()`), but expect
more hallucination risk than Gemini/OpenRouter's larger free models on
niche facts.

**Under the hood:** standard OpenAI-compatible `chat/completions` shape
at `api.mistral.ai/v1` (confirmed live) — reuses the same shared
request/response code as NIM and OpenRouter. Unlike OpenRouter, `GET
/v1/models` *does* validate the key (401 on an invalid one), but that
alone doesn't confirm the configured model has any free-tier quota —
same as OpenRouter, the Test button makes a real `chat/completions`
call rather than trusting the models listing.

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
5. Paste the server URL into mradio-web's **AI providers** page (user
   menu → Settings → AI providers, admin only), then click away from
   the field (or **Save**) — the page probes that URL's `/api/tags`
   and turns the **Model** field into a dropdown of whatever's
   actually installed there, instead of a name you'd otherwise have to
   type by hand.

**Fields:**

- **Server URL**: e.g. `http://192.168.1.10:11434` for an Ollama instance
  running on your LAN, or `http://localhost:11434` if it's on the same
  host.
- **Model**: a dropdown once the server above is reachable, listing
  every installed model with its size, largest first (with a "largest
  installed" label on that one) — sizes and this label are informational
  only, not a quality recommendation. A bigger model isn't necessarily a
  more accurate one for this app's liner-notes task; use the **Test**
  button to actually compare before committing to one. If the server
  isn't reachable yet (or hasn't been saved), this falls back to a plain
  text field showing whatever model name was last saved.

Whether this points at an existing Ollama/NIM setup you already run for
other things, or a dedicated instance just for this app, is entirely up
to what you type in these two provider sections — nothing in the code
assumes either way.

## 7. Configuring email (SMTP)

From the user menu → **Settings** → **Email (SMTP)** (admin only). This is
one shared outgoing-mail configuration for the whole app — nobody's
inbox is read, only sent from. Two flows use it:

- **Forgot password** (§4): a self-service reset link, sent to whatever
  address is already on the account. This email also always states the
  account's username, so it doubles as a "forgot my username" recovery
  — click the link only to learn the username, then go back to the
  still-open login page and sign in with the password you actually
  remembered; the unused reset link simply expires untouched, it
  doesn't block a normal login.
- **New-account invite**: when an admin creates a user *with* an email
  address filled in at creation time, that person gets a "you've been
  invited" email with their username and a link to set their own
  password — the same one-time-link mechanism as the reset email, just
  with a 7-day window instead of 1 hour. Adding an email to an
  *existing* account later (via profile edit) does **not** trigger this
  — only having one at the moment of creation does, so an admin
  backfilling emails for old accounts doesn't accidentally spam
  everyone with invite links. If the send fails (bad SMTP credentials,
  provider outage, etc.) the account is still created — check the
  server log (`mradio.users`) for `invite email FAILED for user_id=…`,
  or just use **Resend invite** (next to each user with an email, on
  the Users admin page) to try again once SMTP is fixed. The same
  button is also the way to get an invite out after changing a user's
  email address on the Users page, since that edit itself never sends
  anything on its own.

Both emails share the same branded HTML template (light theme, the
app's own logo mark, teal accent) — see `backend/app/email_templates.py`.
The set-password page itself (reached from either link) also shows
"Signing in as &lt;username&gt;" before the form, via a read-only token
lookup (`GET /api/auth/reset-password-info`) that doesn't consume the
link.

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

## 8. Station logos (optional: SearXNG)

Station logos are found automatically — no configuration needed. The app
tries, in order: the Radio-Browser directory, then the station's own
website (its `og:image`), then Wikipedia. Whatever it finds is verified
to be a real image and cached in `station_logos.json`, including
confirmed misses, so a station is never looked up twice.

That covers most stations. For the remainder, the app can optionally use
a **self-hosted [SearXNG](https://docs.searxng.org/)** as a last resort:

```yaml
environment:
  - MRADIO_SEARXNG_URL=http://192.168.1.10:7777
```

Leave it unset if you don't run one — that tier is skipped and everything
else works as before. It's deliberately last: it only runs for stations
that would otherwise show no logo at all.

Your SearXNG needs its JSON API enabled, which is off by default. In its
`settings.yml`:

```yaml
search:
  formats:
    - html
    - json
```

Then restart the SearXNG container. Results are filtered to skip icon
libraries and stock-photo sites, and a result is only accepted if its
title or URL still matches the station name — a wrong logo is worse than
none, so an unverifiable match is discarded.

No hosted search engine works here: Google and DuckDuckGo both refuse
server-side requests, and Brave requires a paid API key. A SearXNG you
already run has none of those constraints.

## 9. Data and backups

Everything persistent lives under the `/data` volume:

- `mradio.db` — SQLite: accounts, sessions, password-reset tokens, and
  play history (§11).
- `settings.json` — the AI provider credentials above.
- `smtp_settings.json` — the outgoing-email credentials above.
- `cache.json` — the shared AI liner-notes cache (author/track → trivia),
  shared across all accounts on purpose.
- `users/<id>/stations.json`, `config.json` — each account's favorites and
  personal settings (theme, volume, active provider).

Back up the whole `/data` directory (or the equivalent appdata folder on
your platform, same as any other container) — it's the entire state of
the app.

## 10. Updating

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
(§11) — there's no separate scheduled update for it, since it's just a
downloaded data file, not a version pin to review.

## 11. Analytics

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

## 12. Spotify playlist integration (optional)

Each listener can connect their own Spotify account and save tracks to a
private "mradio-web" playlist straight from the player. Configuration is
split: the Spotify **app credentials** live in mradio-web's Settings UI, but
the **redirect URI** and **token-encryption key** are environment variables
on the server because they're infrastructure-level values that shouldn't be
editable from the UI.

### 12.1 Create a Spotify app

1. Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
   and create an app.
2. Add the redirect URI:
   ```
   https://<your-domain>/api/spotify/callback
   ```
   Use the same domain listeners reach the app on (e.g. `https://radio.example.com`).
3. Note the **Client ID** and **Client Secret**.

### 12.2 Configure the server

Add these environment variables in `docker-compose.yml` (or an override):

```yaml
environment:
  - MRADIO_SPOTIFY_REDIRECT_URI=https://<your-domain>/api/spotify/callback
  - MRADIO_SPOTIFY_TOKEN_KEY=<a 32-byte Fernet key>
```

- `MRADIO_SPOTIFY_REDIRECT_URI` must match exactly what you entered in the
  Spotify app settings, including `https://`.
- `MRADIO_SPOTIFY_TOKEN_KEY` encrypts refresh tokens at rest. Generate one
  with:
  ```bash
  python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```
  If unset, refresh tokens are still stored but only obfuscated as
  `plain:<token>` — fine for local development, not for production.

Restart the container after changing env vars:

```bash
docker compose up -d
```

### 12.3 Enter app credentials in mradio-web

From the user menu → **Settings** → **Spotify** (admin only):

- Paste the **Client ID** and **Client Secret** from the Spotify app.
- Save.

Once this is done, every user sees a star icon next to the currently-playing
track. A hollow star means the track isn't in their playlist yet; a filled
star means it is. Clicking it connects Spotify if needed, then adds or
removes the track.

### 12.4 How tracks are matched

The app searches Spotify using the ICY metadata (artist and title parsed from
the stream), deduplicates by ISRC, and picks the best candidate with a
conservative score combining title similarity, artist/performer presence,
album type (album preferred over single over compilation), and popularity.
If no good match is found, the star action reports that the track wasn't
found. The playlist contents are mirrored locally so the filled-star state
is instant.
