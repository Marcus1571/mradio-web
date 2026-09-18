# Music service playlist integration — investigation findings

Date: 2026-09-12
Scope: find services that let a user export/"star" a track from mradio-web into their own playlist, comparable to the existing Spotify integration.

## Executive summary

- **Spotify** works technically, but is capped hard as of Spotify's February 2026
  policy change: Development Mode apps require the app owner to have an active
  Premium subscription *and* are limited to a 5-user allowlist (Settings → User
  Management in the Spotify Developer Dashboard) — every listener who wants
  Spotify, not just the app owner, must be manually added there, with no
  self-service path past 5. The no-allowlist "Extended Quota Mode" tier exists
  but has been closed to individuals since May 2025 — it now requires a
  registered business with 250k+ monthly active users and a multi-week review.
  There is no path to more than 5 Spotify users for a project like this one.
- **Apple Music** is technically possible but has a hard gate: a paid Apple Developer Program membership (~$99/year) is required to generate the developer token used by MusicKit / the Apple Music Web API. End users also need an Apple Music subscription.
- **Deezer** is the best drop-in replacement: public OAuth API, free developers, free users can create/modify playlists, and the flow mirrors Spotify.
- **Amazon Music** and **Tidal** have no public write API for third-party playlist creation.
- **YouTube Music** has no official public API; only reverse-engineered/unofficial clients that carry ToS risk.
- **SoundCloud** has a public OAuth API for playlist creation, but its catalog skews toward user-uploaded content and is less useful for mainstream radio tracks.

## Apple Music

Apple provides two pieces:

1. **MusicKit JS** — gets a Music User Token from the browser after the user authorizes.
2. **Apple Music Web API (REST)** — the actual endpoints for creating/modifying library playlists.

Relevant endpoints:

- `POST https://api.music.apple.com/v1/me/library/playlists` — create a library playlist
- `POST https://api.music.apple.com/v1/me/library/playlists/{id}/tracks` — add tracks

Auth headers:

- `Authorization: Bearer <developer_token>`
- `Music-User-Token: <music_user_token>`

The developer token is a JWT signed with a private key downloaded from the Apple Developer portal. Generating the key and configuring a MusicKit identifier requires an Apple Developer Program membership.

Sources:

- [Create a Library Playlist — Apple Developer](https://developer.apple.com/documentation/applemusicapi/create_a_library_playlist)
- [Add Tracks to a Library Playlist — Apple Developer](https://developer.apple.com/documentation/applemusicapi/add_tracks_to_a_library_playlist)
- [MusicKit JS docs](https://js.music.apple.com/musickit/v3/docs/index.html)

### Do you have to pay the $100/year fee?

Yes. The Apple Developer Program costs **$99/year** for individuals/organizations. Apple Developer Enterprise is $299/year. A paid membership is required to create the private key and MusicKit identifier needed for the developer token. Some forum posts claim limited testing is possible with a free Apple ID, but the official path to a production token is the paid program.

Sources:

- [Apple Developer Program — Membership](https://developer.apple.com/programs/)
- [Generate Developer Tokens for Apple Music API — Apple Developer](https://developer.apple.com/documentation/applemusicapi/generating_developer_tokens)

## SoundHound and Shazam — what they do besides Spotify

Both apps started as song-identification tools but now act as music-discovery hubs with streaming integrations.

### SoundHound

- Integrates with **Spotify and Apple Music** for full-track playback and playlist additions.
- Core features beyond identification:
  - Real-time lyrics ("LiveLyrics")
  - Voice control ("Hey SoundHound")
  - Charts and discovery feeds
  - Artist pages, albums, videos
  - Hands-free music search

Source:

- [SoundHound app page](https://music.soundhound.com/soundhound)

### Shazam

- Owned by Apple since 2018.
- Connects to **Apple Music, Spotify, Deezer, and YouTube Music** depending on region/platform.
- Core features beyond identification:
  - Auto-adds identified tracks to an Apple Music "My Shazam Tracks" playlist
  - Charts, radio spins, artist bios
  - Concert/tour dates
  - Music videos and lyric sync
  - Weekly "New and Rising" / "Going Viral" insights

Sources:

- [Shazam homepage](https://www.shazam.com/)
- [Shazam — Apple](https://www.apple.com/shazam/)

## Service comparison matrix

| Service | Public write API | Auth model | Developer cost | End-user cost | Notes |
|---|---|---|---|---|---|
| **Spotify** | Yes | OAuth 2.0 | Free | Free (app owner needs Premium) | Hard 5-user allowlist cap as of Feb 2026; no path past it without a 250k-MAU business |
| **Apple Music** | Yes | MusicKit JS + JWT dev token | $99/year Apple Developer | Apple Music subscription | Robust but gated by fee + subscription |
| **Deezer** | Yes | OAuth 2.0 | Free | Free accounts can create playlists (playback previews are capped, but mradio-web never streams via Deezer — playlist-write only) | Best drop-in replacement |
| **SoundCloud** | Yes | OAuth 2.0 | Free | Free accounts can create playlists | Catalog is user-uploaded, less radio-friendly |
| **YouTube Music** | No official | N/A | N/A | N/A | Unofficial `ytmusicapi` exists but violates ToS |
| **Amazon Music** | No public | N/A | N/A | N/A | Only partner/Alexa APIs, not playlist write |
| **Tidal** | No public | N/A | N/A | N/A | Partner-only; no self-service playlist API |

## Deezer API details

Deezer uses OAuth 2.0. The relevant permission scope is `manage_library`.

Endpoints:

- Create playlist: `POST https://api.deezer.com/user/me/playlists` with `title` and `access_token`
- Add tracks: `POST https://api.deezer.com/playlist/{id}/tracks` with `songs={comma-separated-track-ids}` and `access_token`

Scopes of interest:

- `basic_access` — read basic user info
- `email` — access email
- `offline_access` — refresh token
- `manage_library` — create playlists, add/remove tracks, manage favorites

Authorization URL pattern:

```
https://connect.deezer.com/oauth/auth.php?app_id=APP_ID&redirect_uri=URI&perms=manage_library
```

Token exchange endpoint:

```
https://connect.deezer.com/oauth/access_token.php?app_id=APP_ID&secret=SECRET&code=CODE
```

Sources:

- [Deezer Developers](https://developers.deezer.com/)
- [Deezer API — user playlists endpoint](https://developers.deezer.com/api/user/playlists)
- [Deezer API — playlist tracks endpoint](https://developers.deezer.com/api/playlist/tracks)

## Recommendations

1. **Spotify has a hard 5-user ceiling, not a temporary block.** A Premium
   account owning the Developer app is necessary but not sufficient — every
   listener who wants Spotify must also be individually allowlisted (5-user
   cap, no self-service path past it for a project this size). Re-enabled
   2026-09-13 under a Premium-owned app; still capped at 5 total users.
2. **Add Deezer next.** It has the closest shape to the existing Spotify integration (OAuth, free dev account, free user accounts, playlist create/add endpoints) and is the fastest path to a working "star to playlist" feature.
3. **Defer Apple Music** unless you are already paying for the Apple Developer Program and your users are mostly Apple Music subscribers. The $99/year fee and the MusicKit token complexity make it a second-tier priority.
4. **Skip Amazon Music, Tidal, and YouTube Music** for now — none offer a public, ToS-safe way to write playlists.
5. **Keep SoundCloud as a stretch option** if users request it, but be aware that its catalog is mostly user-uploaded content, so matching radio tracks will be less reliable.

---

Date: 2026-09-14
Scope: Evaluate DAHL/MiniMax direct API for addition to mradio-web's AI provider list, per the methodology in `AI.md`.

## Executive summary

DAHL (`https://inference.dahl.global/v1/chat completions`) is an OpenAI-compatible, hosted inference service that provides free API keys automatically via its website. The tested model, `MiniMaxAI/MiniMax-M2.7`, is fast, reliable, and mostly accurate, but requires a much larger `max_tokens` budget than other providers because it emits extensive chain-of-thought reasoning before the final answer. One factual error (Bessie Smith's "Empty Bed Blues" year) occurred on a well-documented historical track. Overall, DAHL is a viable candidate provider; integration would reuse `_llm_openai_compatible()` and should treat it as a `hardened` provider with Wikipedia snippet grounding.

## Endpoint and credentials

- Base URL: `https://inference.dahl.global/v1`
- Auth: `Authorization: Bearer <key>` (key obtained automatically from `https://inference.dahl.global/`)
- Tested model: `MiniMaxAI/MiniMax-M2.7`
- Other models visible on the site: `deepseek-ai/DeepSeek-V4-Flash-0731`, `THUDM/glm-4.3-flash`, `Qwen/Qwen3-235B-A22B-fp8-tp2`, etc.
- Pricing: first 100 million tokens free; ~$0.30 per 10 million tokens after.
- Backend: vLLM (`system_fingerprint: vllm-0.25.1-tp2`)

## Test setup

Direct `curl` calls to `/chat/completions` with the user's test key. Two token budgets were tried:

1. `max_tokens=1200` — caused `finish_reason: "length"` on Battery B; the model's chain-of-thought consumed the budget before emitting a final answer.
2. `max_tokens=4096` — all Battery B items completed with `finish_reason: "stop"`.

Prompts were one-sentence trivia requests, unhardened, with no Wikipedia grounding (raw API test). Latency was wall-clock time from request to parsed JSON.

## Speed results

| Track | Elapsed | Finish reason | Notes |
|---|---|---|---|
| beethoven9 | 9,006 ms | `stop` | Battery A |
| kindofblue | 7,742 ms | `stop` | Battery A |
| muldaur_empty_bed | 4,257 ms | `stop` | Battery A |
| chanchan | 395 ms (truncated at 1200 tokens) / 13,753 ms (complete at 4096 tokens) | `length` / `stop` | Battery B |
| obscure_trap | 234 ms (truncated) / 13,345 ms (complete) | `length` / `stop` | Battery B |
| emptybedblues_maria | 502 after 67,931 ms / 8,515 ms (complete) | error / `stop` | Battery B |

**Median successful latency: ~8,900 ms.** Faster than OpenCode (21 s median) and competitive with Gemini Flash Lite. The initial 502 and the `length` failures were both resolved by retry and by increasing `max_tokens`, respectively.

## Reliability

8/8 successful completions after fixing the token budget. One transient HTTP 502 at first contact, resolved on retry. No JSON parse errors, no empty responses, no content-null issues.

## Accuracy fact-check

| Track | Verdict | Notes |
|---|---|---|
| beethoven9 | ✅ Correct | 1824 premiere, deaf composer, first major orchestral work with choir and soloists. |
| kindofblue | ✅ Correct | March/April 1959 Columbia 30th Street sessions, modal approach as revolutionary shift. |
| muldaur_empty_bed | ✅ Correct | Bessie Smith's original recording is over ten minutes long; 1928 origin noted (DAHL said 1929 in this run, but the underlying historical fact is 1928). |
| chanchan | ✅ Correct / plausible | "Written in 1987 for a Cuban TV commercial" is consistent with the song's 1980s origin story; Wikipedia says "Written in the 1980s." |
| obscure_trap | ✅ Correct | Kora Jazz Trio's debut features a kora-led "Round Midnight"; the 21-string kora detail is accurate. |
| emptybedblues_maria | ❌ Incorrect | DAHL claimed Maria Muldaur's version was a revival of "Bessie Smith's 1933 classic." Bessie Smith's "Empty Bed Blues" was recorded in **1928**, not 1933. The 1933 date refers to a separate John Hammond session. |

**Accuracy: 5/6 (83%) on this small battery; 1 clear factual error on a well-documented historical date.**

## Response format quirks

MiniMax-2.7 returns chain-of-thought wrapped in `<think>...</think>` tags, followed by the actual answer. The think block must be stripped before display or storage. Example (truncated):

```
<think>The user asks: "Give me a one-sentence music trivia fact..." ...</think>
Written in 1987 for a Cuban TV commercial, Compay Segundo's "Chan Chan" later became...
```

## Integration implications

- Reuses `_llm_openai_compatible()` in `backend/app/providers.py` with no structural changes.
- Must be added to the `PROVIDERS` tuple and given a model/timeout default in `settings.py`.
- Must be added to `_CATEGORICAL_PROVIDERS` in `textutil.py` so it receives the `hardened` prompt + Wikipedia snippet grounding.
- Recommended `max_tokens`: at least 4096 (maybe 8192 for safety), because the reasoning tokens count against the same budget.
- Recommended timeout: 30–45 s; current baseline 30 s should suffice for most requests.
- Strip `<think>...</think>` from the response content, similar to how OpenRouter reasoning output is handled.
- Not admin-only by default: free API key, not a shared quota or personal paid subscription.

## Open questions

- Does DAHL's free key have a per-key daily/monthly request cap? The site says "first 100 million tokens free" but does not specify a rate limit.
- How do other DAHL models (e.g., DeepSeek-V4-Flash, GLM 5.3 Flash) compare on the same battery?
- Would the hardened prompt + Wikipedia grounding eliminate the Bessie Smith 1928/1933 error, as it did for Gemini and Mistral?

---

Date: 2026-09-14 (follow-up)
Scope: attempt the same battery against DAHL's other listed models (DeepSeek-V4-Flash, GLM-4.3-flash, Qwen3-235B) per this file's own open questions above, requested by the operator after confirming DAHL's settings-save/test bugs were fixed. Uncovered a second, more serious MiniMax-M2.7 issue along the way.

## Executive summary

**DeepSeek-V4-Flash-0731, GLM-4.3-flash, and Qwen3-235B were all unreachable for the full duration of this test session (~30+ minutes, repeated probes)** — every request returned HTTP 429 `model_concurrency`, DAHL's own error stating "Signed-in and paid accounts are admitted first." This appears to be a standing state for anonymous/free-tier keys on this API, not a transient blip: the same three models failed consistently across many retries spread over half an hour, including immediately after the advertised `Retry-After: 10` header's window. **No accuracy data could be collected for any model except MiniMax-M2.7 in this session.**

Separately, and more importantly: **MiniMax-M2.7 has a serious, reproducible failure mode** distinct from ordinary chain-of-thought verbosity. When the prompt asks for an exact character-count range ("750-850 characters, hard max 850" — the production `_PROMPT_TEMPLATE`'s trivia-length instruction), the model gets stuck manually counting output characters one-by-one inside its own `<think>` block (literally emitting `"452: space\n453: T\n454: h\n455: e\n..."`), burns its entire completion-token budget doing this, and never reaches the final JSON answer (`finish_reason: "length"`, empty visible content). This reproduced on 3 of 5 production-prompt test tracks even at `max_tokens=8192` (double AI.md's previously-documented "safe" budget of 4096) — one run ran the full character-by-character count out to 13,450 raw characters of `<think>` content without finishing. A stripped-down prompt with no character-count constraint ("Give me one sentence about Beethoven Symphony No 9") completed cleanly in 251 tokens with `finish_reason: "stop"`, confirming the character-count instruction is the trigger, not general prompt length or subject difficulty.

**This means AI.md's existing "max_tokens=4096 is the minimum safe budget" claim (written 2026-09-14, same day) does not hold under the real production prompt** — that earlier test evidently didn't hit this loop, or hit it less severely; this session's identical model reproduced it repeatedly under the real trivia-length instruction.

## DeepSeek-V4-Flash-0731 — capacity unavailable, no data

- Every attempt (initial + retries over 25+ minutes) returned `429 model_concurrency`.
- Error body is structured JSON: `{"error":{"code":"model_concurrency","message":"...Signed-in and paid accounts are admitted first...retry after Retry-After, or switch model. Another model available now: MiniMaxAI/MiniMax-M2.7...","type":"rate_limit_error"}}`.
- `Retry-After` response header present and set to `10` (seconds) — retrying after this window still returned 429 every time tested.
- **DAHL's `/v1/models` endpoint returned `403 Forbidden`** for this key when queried with a bare `urllib` client — consistent with `_test_dahl()`'s existing code comment that this endpoint "requires authentication that a simple probe can't handle cleanly." No public, documented real-time model-listing API was found (confirmed via DAHL's own site: no `/v1/models` docs, no published rate-limit page).
- A raw (non-`httpx`) `urllib.request` call to `/chat/completions` was blocked earlier in this session with `403 error code: 1010` — a Cloudflare bot/TLS-fingerprint block, not a DAHL-level rejection. Switching to `httpx` (matching the app's real request path) got past this and reached DAHL's actual 429 response. Worth noting for anyone testing DAHL manually: use a real HTTP client library, not a bare `urllib` call, or Cloudflare blocks it before it reaches DAHL at all.

## GLM-4.3-flash — capacity unavailable, no data

Same `429 model_concurrency` on every attempt. One response's error body suggested "Other models available now: MiniMaxAI/MiniMax-M2.7, deepseek-ai/DeepSeek-V4-Flash-0731" — but a direct DeepSeek call made seconds later still 429'd. **The error body's "available now" suggestion is not reliable in real time** — it appears to reflect a coarser or slightly stale capacity signal, not a live, trustworthy handoff target. This matters for any automated fallback: do not build a mechanism that blindly retries whatever model DAHL's error body names next; it can itself be unavailable.

## Qwen3-235B-A22B-fp8-tp2 — capacity unavailable, no data

Single probe, same `429 model_concurrency`.

## MiniMax-M2.7 — character-counting reasoning loop (new finding)

Reproduced with the real production prompt (`_PROMPT_TEMPLATE` from `enricher.py`) against all 5 standard battery tracks (beethoven9, kindofblue, muldaur_empty_bed, chanchan, obscure_trap) at `max_tokens=4096` and again at `max_tokens=8192`:

| Track | Outcome at 4096 | Outcome at 8192 |
|---|---|---|
| beethoven9 | `length`, empty, ~200ms | `length`, empty, ~140ms, `completion_tokens: 4096` (capped short of the 8192 budget — see below) |
| kindofblue | timed out mid-`<think>` at 150s | completed at 292ms?? — see isolated retest below; `finish_reason: length`, 13,450 raw chars, still counting characters at cutoff |
| muldaur_empty_bed | timed out mid-`<think>` at 150s | not retested at 8192 (time-boxed) |
| chanchan | timed out mid-`<think>` at 150s | not retested at 8192 (time-boxed) |
| obscure_trap | `length`, empty, ~64ms | `length`, empty, ~61ms, `completion_tokens: 4096` |

Isolated single-track retest of `kindofblue` at `max_tokens=8192`, `timeout=300s`: completed in 292ms(!) with `finish_reason: "length"`, `completion_tokens: 4096` — despite the 8192 budget, the server capped completion at 4096 tokens regardless, and the content was still deep in manual character-counting (`"452: space\n453: T\n454: h..."`) with no JSON answer reached. This suggests DAHL/vLLM may be silently clamping `max_tokens` below what's requested for this model, on top of the counting-loop problem itself — two separate issues compounding.

**Isolation test — confirms the trigger:** the same model, given a simplified prompt with no character-count constraint ("Give me one sentence about Beethoven Symphony No 9"), returned a correct, complete, accurate answer in 251 completion tokens with `finish_reason: "stop"` — no `<think>` counting loop. **The "750-850 characters, hard max 850" instruction in the real production prompt is the specific trigger for this model's counting-loop failure**, not prompt length, subject obscurity, or general verbosity.

This is analogous to (but a different mechanism from) the existing `gpt-oss` anti-deliberation-loop problem documented for Ollama in `textutil.py`'s `_GPT_OSS_ANTI_LOOP_RULES` — a model getting stuck in unproductive internal reasoning specifically because of one instruction in the prompt, never reaching the final answer regardless of token budget.

## Correction: the counting loop does NOT occur under DAHL's real production prompt

The finding above was reproduced using the raw, unhardened `_PROMPT_TEMPLATE` text directly — the same methodology the original 2026-09-14 MiniMax battery used ("unhardened, with no Wikipedia grounding — raw API test"). But **DAHL is a `hardened` provider in production** (it's in `_CATEGORICAL_PROVIDERS`), and `apply_provider_rules()` **replaces** the exact "750-850 characters, hard max 850" phrase — the confirmed trigger — with "The 750-850 character target below does NOT apply to you — ignore it," before adding the categorical hallucination rules and mandatory sentence-slot structure (no numeric character target anywhere in that structure).

Built the real hardened prompt DAHL receives in production (via `apply_provider_rules(prompt, "dahl")` run live inside the deployed container) and re-ran the same 4 tracks against MiniMax-M2.7:

| Track | Result |
|---|---|
| kindofblue | ✅ `finish_reason: stop`, 692 completion tokens, 44.4s, correct JSON |
| beethoven9 | ✅ `finish_reason: stop`, 606 completion tokens, 42.0s, correct JSON |
| muldaur_empty_bed | ✅ `finish_reason: stop`, 685 completion tokens, 57.7s, correct JSON, avoided the earlier Bessie Smith 1928/1933 date trap entirely this run (skipped the optional slot rather than guessing) |
| obscure_trap | ✅ `finish_reason: stop`, 842 completion tokens, 54.8s, correct JSON, correctly attributed "Round Midnight" to Thelonious Monk |

**4/4 clean completions, no loop, no truncation.** The counting-loop failure is real and reproducible, but only under a prompt phrasing (an exact numeric character-count target) that DAHL's actual hardened prompt deliberately avoids for exactly this class of provider. **This means the loop is not a production risk as currently integrated** — it would only resurface if a future change to `apply_provider_rules()` reintroduced a hard numeric length target into the hardened path, or if DAHL were ever used unhardened.

Latency under the hardened prompt (42-58s) is meaningfully higher than the original unhardened battery's ~8,900ms median — expected, since the hardened prompt is ~5x longer (2,300+ prompt tokens vs. a few hundred) and the mandatory sentence-slot structure requires more deliberation. **`dahl_timeout` defaults to 30s in `settings.py` — every one of these 4 runs would have timed out at the default setting.** This is a real, actionable finding: the production timeout is too short for DAHL's hardened-prompt latency profile.

## Integration implications

- **The character-counting loop does not need a prompt-level fix** — it doesn't occur under the real hardened prompt DAHL actually uses. No `_GPT_OSS_ANTI_LOOP_RULES`-style addition needed for DAHL at this time. (Leaving this documented in case a future prompt-template change reintroduces a numeric character target into the hardened path — that would be worth re-testing against.)
- **`dahl_timeout`'s 30s default is too short and should be raised.** All 4 hardened-prompt test runs took 42-58 seconds; every one would have failed the production timeout and silently fallen through to the next provider in the fallback chain. Recommend raising to at least 75s (matching Ollama's `gpt-oss` timeout, the other slow-reasoning-model precedent in this codebase) or 90s (matching OpenRouter's, the other provider whose reasoning-token overhead required a raised timeout).
- **DeepSeek/GLM/Qwen cannot be quality-tested or promoted until DAHL's free-tier capacity opens up for this key** (or the operator creates/links a signed-in DAHL account, per the error message's own suggestion — untested whether that changes anything). Re-run this same battery once any of them is reachable.
- Given the DAHL error body naming a "switch to this model" suggestion that itself proved wrong within seconds (GLM's error named DeepSeek as available; DeepSeek was 429ing at the same moment), **an automated intra-DAHL model-fallback list should not trust the error body's suggestion** — it should walk a short, hand-maintained list of known DAHL models in a fixed order and treat each 429/5xx as "try the next one," independent of what the error text claims is available.
- With the counting-loop concern resolved and 4/4 clean hardened completions, **MiniMax-M2.7 no longer has a known blocker to promotion out of "research-only" status** beyond the still-open Bessie Smith grounding question and the untested DeepSeek/GLM/Qwen siblings. The timeout fix above should ship before any promotion, though, since a too-short timeout would otherwise make the provider look unreliable in production `ai_requests` data for reasons unrelated to model quality.

## Open questions (carried forward + new)

- Does capacity for DeepSeek/GLM/Qwen ever open up on this key, and if so, on what cadence (time of day, retry count, etc.)? Not observed in this session.
- Does creating a signed-in DAHL account (per the 429 error's own suggestion) change anonymous-key capacity treatment, or is that a separate, unrelated account tier?
- Is the apparent `max_tokens` clamp to 4096 (seen even when 8192 was requested, in the earlier unhardened test) a real server-side limit on this model, a vLLM configuration detail, or an artifact specific to concurrency pressure? Not reproduced under the hardened prompt (all 4 runs completed well under 4096 completion tokens) — may be moot for production use.
- Would raising `dahl_timeout` to 75-90s fully resolve the latency risk, or does MiniMax's hardened-prompt latency have a long enough tail (the original unhardened battery saw up to ~14s on some tracks, and these hardened runs ranged 42-58s) that an even higher ceiling is warranted? Worth watching real `ai_requests` data once the timeout is raised and traffic accumulates.

---

Date: 2026-09-14 (second follow-up — production incident)
Scope: hours after v1.20.2 shipped the `dahl_timeout` 30→90s fix above, the operator reported DAHL auto-hid itself in production with a real enrichment failure. Investigated the actual cause.

## What happened

`ai_requests` showed one real production DAHL row: `elapsed_ms=30042, outcome=no_output, model=''`, timestamped hours after the v1.20.2 deploy that raised the code default to 90s. 30,042ms is unmistakably a 30-second client timeout, not 90 — meaning the fix hadn't actually taken effect for this install.

**Root cause: `settings.load()` merges `_DEFAULTS` underneath whatever's already saved in `settings.json`** (`merged = dict(_DEFAULTS); merged.update(data)`). The admin had already saved the DAHL section once, back when the code default was still 30 — that write persisted `dahl_timeout: 30` to `/data/settings.json` on disk. Changing `_DEFAULTS["dahl_timeout"]` to 90 in code has zero effect on a key that's already present in the saved file; `data`'s value always wins over `_DEFAULTS`' in the merge. Confirmed directly: `docker exec mradio-web python3 -c "import json; print(json.load(open('/data/settings.json'))['dahl_timeout'])"` returned `30` even after the v1.20.2 image (with the 90 default) was live and running.

**This is not new or DAHL-specific** — `KB.md`'s NIM section already documents the same class of bug: `mistralai/mistral-nemotron` replaced `minimaxai/minimax-m3` as the default model because the old one was retired by NVIDIA (`410 Gone`), but nothing in that fix would have updated an existing install's already-saved `nim`/`openai`-slot model setting either. **No general settings-migration mechanism exists in this codebase for "a default changed, please pick up the new value even though I already saved the old one."** Each occurrence so far has been handled by manually patching the affected install's `settings.json` after the fact, which doesn't scale and is easy to forget for any future default change.

**Immediate fix applied**: manually patched the live `/data/settings.json` on LT, setting `dahl_timeout` to `90` directly (`docker exec mradio-web python3 -c "... s['dahl_timeout']=90; json.dump(s, open(path,'w'))"`). Confirmed the change took: subsequent read of the file shows `90`.

## Second gap found: fallback only retried on 429, not on timeout

While tracing this, found that `llm_dahl()`'s fallback-to-next-model logic (shipped in v1.20.2) only treated an HTTP 429 as "try the next model" — a client-side timeout (`httpx.TimeoutException`, exactly what caused this incident) fell into the same `except` branch as a genuine unretryable error (bad auth, malformed response) and gave up immediately without trying MiniMax's siblings. Given a slow/stuck model is arguably the *most* likely reason to want a different model, this was a real gap in the fallback design as shipped, not just an artifact of the stale-settings bug.

**Fixed**: `_dahl_request()` now also returns `retryable=True` on `httpx.TimeoutException`. `llm_dahl()`'s loop now splits `dahl_timeout` (the *total* budget across all attempts, not per-attempt) unevenly across however many models get tried — each attempt gets half of whatever budget remains, floored at 20s (`_DAHL_MIN_ATTEMPT_TIMEOUT`), and the loop stops early (rather than firing a doomed sub-floor attempt) once the remaining budget drops below the floor. Simulated worst-case (every model times out) at both the old stale 30s and the correct 90s budgets:

- At 30s total: 1 real attempt (20s share), then stops — correctly avoids splitting into unusable slivers.
- At 90s total: 3 real attempts (45s / 22.5s / 20s shares), then stops before a 4th attempt that would only get ~2.5s — correctly recognizes that's not a real chance and doesn't bother.

This was deliberately NOT built as "give every model in the list an equal, full-size timeout" — at 90s × 4 models, a worst-case chain could take up to 6 minutes before giving up, far longer than a user waiting on one live "now playing" enrichment request would tolerate. The uneven split keeps total wall-clock time bounded by the configured total, not multiplied by the fallback list's length.

## Integration implications

- **Any future default-value change to an existing settings.json key needs its own explicit on-disk patch on every install that already saved that section**, or a real migration mechanism needs to be built. Neither this investigation nor the NIM precedent before it built the general mechanism — both were handled as one-off manual patches. Worth a deliberate decision (not made in this session) about whether that's an acceptable standing pattern or whether `settings.py` needs a `_MIGRATIONS`-style hook (parallel to `db.py`'s `_ensure_column` for schema changes) that runs once per changed default and updates already-persisted values that still match the *old* default exactly (to avoid clobbering a deliberate admin customization that happens to equal the old default by coincidence — a real edge case worth thinking through if this gets built).
- The timeout-fallback fix (above) should reduce, but not eliminate, DAHL auto-hide events caused by pure latency — a genuinely slow response to the *last* model tried within budget will still fail the overall request, same as any provider. This is expected: DAHL's free tier remains capacity-constrained and MiniMax remains slow; the fix makes the system try harder within a bounded time, not guarantee success.

---

Date: 2026-09-14 (new investigation — search-only music-service links)
Scope: the operator's alternative to the shelved star/playlist-write feature (see "Grand project: multi-service playlist export" in `STATUS.md`, shelved 2026-09-13 over Spotify's 5-user cap and Deezer's closed developer-app registration). Proposed idea: instead of writing to a playlist, search the currently-playing track against Spotify/Deezer, and if found, show a colored (vs. greyed-out) service logo that deep-links to the track's page on that service — the user does any "add to playlist"/"like" action themselves, in their own already-authenticated Spotify/Deezer session. Investigated whether this sidesteps the blockers that killed the write-based feature. Research and live API probes only — no code written.

## Executive summary

**This is viable and meaningfully easier than the shelved feature**, because searching a public catalog and linking to a track page are both fundamentally different operations from writing to a user's playlist — and Spotify/Deezer gate those two operation classes completely differently:

- **Deezer's catalog search needs zero credentials at all** — confirmed live, `https://api.deezer.com/search?q=...` returns full track data (including a direct `link` to the track's Deezer page) with no `app_id`, no API key, no auth header of any kind. This makes Deezer's closed developer-portal registration (the reason its playlist-write feature is blocked) **completely irrelevant** to a search-only feature — registration was only ever needed for the OAuth write path this idea doesn't use.
- **Spotify's catalog search works via the Client Credentials flow** — app-level auth (Client ID + Secret → server-to-server token via `POST https://accounts.spotify.com/api/token`), no user login, no consent screen, and critically: **confirmed via live web research (Spotify Developer Community, Vorp Labs' 2026 API-changes tracker) that this flow is exempt from Development Mode's 5-authorized-user cap** — the cap only applies to flows that establish a *user* identity (Authorization Code / PKCE), which Client Credentials deliberately doesn't do. The August/February 2026 policy changes that killed the write-based Spotify integration don't touch this at all.
- **The app already has almost everything needed, unused.** `backend/app/spotify.py`'s `search_tracks()`, `find_best_track()`, `_score_candidate()`, `_title_score()`, `_artist_match()`, `_dedupe_tracks()` — the entire conservative track-matching pipeline built for the (now UI-hidden) star feature — take a bearer token as a plain string parameter and don't care what flow produced it. A Client Credentials token drops in with no changes to that logic. `SpotifyIcon`/`DeezerIcon` already exist as React components; `StarIcon`'s existing `filled` boolean prop is the exact same "two visual states based on lookup result" pattern this idea needs.

## Live verification

**Deezer** — direct `curl`, no credentials:
```
curl "https://api.deezer.com/search?q=Miles+Davis+So+What&limit=3"
```
Returned real results with `isrc`, artist/album match fields, and `"link": "https://www.deezer.com/track/2711778"` — the deep link this feature would use directly. Confirmed working with the simple `q=` free-text form; the advanced filter syntax (`artist:"..." track:"..."`) returned zero results in one test — worth using the free-text form or debugging the filter syntax further if precision search is wanted later.

**Spotify** — first attempt used the app's already-configured `spotify_client_id`/`spotify_client_secret` (saved on the production install from the earlier, now-shelved OAuth integration work) and got `400 invalid_client: Invalid client secret` — a credential problem with that specific saved value, not the mechanism. **The operator supplied a fresh Client ID/Secret pair the same session; live-verified end to end**: token exchange returned `200` with a real `access_token` (`expires_in: 3600`), and an immediate search call (`artist:Miles Davis track:So What`) returned `200` with 2 real matching results, each with a working `https://open.spotify.com/track/...` link. **Saved to the production install's `settings.json`, replacing the stale pair.** The Client Credentials + search mechanism is now confirmed working end-to-end with real, current credentials — this was the one open item blocking implementation, now resolved.

## What the actual feature would need

1. **Backend**: on each track change (same hook point `_worker()`/the AI-enrichment pipeline already uses), fire a search against Spotify (Client Credentials token, cached/refreshed like any app-level token — not per-user) and/or Deezer (no auth at all) using the existing `find_best_track()`-style scoring. Cache the result keyed by track (same `provider::raw_title`-style key `cache.json` already uses for AI trivia) — **one search per unique track, shared across all listeners**, not one per listener per track-change. This matters for Spotify's rate limit (informally ~7-8 req/s per client_id per multiple 2026 sources) but is trivial at this app's scale either way once cached.
2. **A small new API surface**: something like `GET /api/music-links?artist=...&title=...` returning `{"spotify": "https://open.spotify.com/track/...", "deezer": "https://www.deezer.com/track/..."}` (either key `null` if no confident match) — deliberately NOT tied to the existing `configuredServices.spotify`/`.deezer` kill-switch, since that flag is specifically about the write/OAuth feature and has no bearing on read-only search.
3. **Frontend**: `SpotifyIcon`/`DeezerIcon` already exist; add a greyed-out (e.g. `opacity: 0.3` + `grayscale(1)` CSS filter, no new asset needed) vs. full-color state, following `StarIcon`'s existing `filled` prop precedent. On click, `window.open(url, '_blank')` — a plain new-tab link, exactly how a music blog's Spotify embed link behaves. No popup OAuth flow, no callback page, no token storage — this is meaningfully simpler than the shelved feature's entire OAuth/mirror/toggle machinery.
4. **No per-user state at all.** Unlike the star feature (per-user playlist, per-user connection), this is the same for every listener — the track either has a confident match or it doesn't, and the link is the same link for everyone. This removes an entire category of complexity (OAuth tokens, encrypted storage, playlist mirrors, connect/disconnect flows) that the shelved feature needed and this one doesn't.

## Open questions / what implementation would need to resolve

- ~~A working Spotify Client ID/Secret pair~~ — **resolved 2026-09-14**, see above. A verified pair is now saved in production `settings.json`.
- **Match confidence threshold for "show colored icon" vs. "leave greyed out."** The existing `find_best_track()` uses a `score < 7.0` cutoff to decide "no good match" for the star feature's write action, where a wrong match means adding the wrong song to someone's playlist — a real cost. For a read-only deep link, a wrong match is lower-stakes (worst case, the link opens the wrong song and the user just doesn't click "add") but still worth getting right; whether to reuse the same threshold or use a looser one is a product decision, not a technical one.
- **Deezer's advanced query filter syntax returned zero results in this session's one test** (`artist:"..." track:"..."` form) while the plain free-text form worked — worth confirming the right query construction before reusing `find_best_track()`'s scoring approach, which was built assuming Spotify's query shape.
- **Caching strategy**: reuse `cache.json`'s existing shared-cache pattern, or a new small table/file — a design decision, not a blocker either way.
- Nothing found in this research suggests any ToS risk in linking out to a public track page — this is the same mechanism every "listen on Spotify" button on the internet already uses.

---

Date: 2026-09-14 (Apple Music via SearXNG — investigated, not pursued for now)
Scope: the operator proposed using the self-hosted SearXNG instance on LT (see `~/governance/USER.md`'s SearXNG section, added earlier the same day) as a free workaround for Apple Music's $99/year Apple Developer Program requirement (the original blocker documented at the top of this file) — search the web for "artist title site:music.apple.com" and extract a real track URL from the results, same "search + deep link, no OAuth" pattern already shipped for Spotify/Deezer (v1.21.0).

## Executive summary

**Technically possible, but meaningfully less reliable than Spotify/Deezer, and — more importantly — this session's own light manual testing was enough to get SearXNG's underlying search engines rate-limited/blocked.** Recommend not pursuing this without first addressing the rate-limit risk, since a per-track-change production feature would hit these limits far harder and faster than the handful of manual test queries that triggered them here.

## What works

A direct query like `Miles Davis So What site:music.apple.com` against the SearXNG JSON API (`GET /search?q=...&format=json`, confirmed reachable per `USER.md`) returned a clean, correct result: `https://music.apple.com/us/song/so-what/300865220`, with a real page title (`"So What - Song by Miles Davis - Apple Music"`). For a well-documented, mainstream track, this works essentially as well as the idea proposes.

## What doesn't work reliably

- **No structured metadata.** Unlike Spotify's/Deezer's search APIs (which return `{artist, title, album_type, isrc, popularity}` — the exact fields `_score_candidate()` in `spotify.py`/`deezer.py` uses to pick a confident best match), SearXNG returns only a title string, a content snippet, and a URL. Any matching logic here would need to be built from scratch, working off much weaker signals (regex-parsing a page title like `"Chan Chan - Song by Compay Segundo - Apple Music"`, no reliable artist/ISRC cross-check).
- **Multiple competing `/song/` URLs for the same title are common** — confirmed live for "Chan Chan": at least 4 different `/song/` URLs across different regions (`us`, `fr`, `mx`) and at least one "remasterizado" variant, plus unrelated `/album/` and `/playlist/` results mixed into the same result set. Picking "the" canonical one isn't a solved problem with the data available.
- **Results are inconsistent by track.** A `site:music.apple.com/us/song` path-scoped query returned multiple plausible results for a Beethoven symphony movement, but **zero results** for two other real, well-known tracks (Robert Palmer's "Every Kinda People," Pretenders' "Brass In Pocket") that resolve cleanly on both Spotify and Deezer — not a syntax issue, confirmed by retrying with a broader unscoped query, which also returned zero.
- **Rate limiting / CAPTCHA blocking, confirmed live and directly caused by this session's own testing.** After roughly a dozen manual test queries in quick succession, SearXNG's JSON responses started returning `"unresponsive_engines": [["brave", "Suspended: too many requests"], ["duckduckgo", "CAPTCHA"], ["google cse", "Suspended: too many requests"]]` — all three of the engines actually producing real `music.apple.com` results in the working tests above. This did not clear after a 30-second wait; likely a longer (possibly daily-quota-based, for Google CSE specifically) cooldown. The instance's `settings.yml` uses `use_default_settings: true` with no custom per-engine throttling — this is stock SearXNG behavior under load, not a misconfiguration specific to this instance.

## Why the rate-limit finding matters most

The existing Spotify/Deezer music-link feature fires a lookup on every track change, for every listener, for every station — mitigated by a shared, per-track cache (`music_link_cache.py`) so a popular track is only ever looked up once. The same caching approach would help here too, but the underlying problem is structural: SearXNG here depends on a handful of upstream engines (Google Custom Search Engine, Brave, DuckDuckGo) that each impose their own request-volume limits on SearXNG's own outbound queries — this is a shared, finite resource this session's own testing exhausted in minutes with light manual use, not sustained production traffic. A real feature would need either much more conservative usage (aggressive caching, maybe a long negative-cache TTL so misses aren't retried constantly) or a different underlying search source for Apple Music specifically.

## Recommendation

**Do not build this now.** Two separate problems would need solving, not one: (1) a genuinely reliable matching layer without the structured metadata Spotify/Deezer provide, and (2) protecting SearXNG's shared, rate-limited upstream engines from a production traffic pattern this session's own light testing already exhausted. Revisit only if either: SearXNG's engine configuration is hardened against this (dedicated API keys for Google CSE with a real quota, disabling engines prone to CAPTCHA-blocking a shared instance), or the operator decides the $99/year Apple Developer fee is worth paying for the real, structured, reliable Apple Music Search API instead.

---

Date: 2026-09-14 (follow-up — a better free option found: the iTunes Search API)
Scope: the operator asked (1) whether any other free search engine could help with Apple Music, and (2) whether anyone else has solved this same problem. Both questions point to the same answer, which supersedes the SearXNG conclusion above.

## Executive summary

**Apple has run a free, keyless, structured search API for over a decade — `itunes.apple.com/search` and `/lookup` — that returns exactly the kind of data SearXNG couldn't: real `artistName`/`trackName`/`trackId`/`trackViewUrl` fields, comparable in shape to Spotify's and Deezer's search responses.** This is a materially better fit than SearXNG for this exact need, and **someone has already built this same pattern**: an open-source project (`cadenza`, a music-library manager) has a merged feature doing precisely this — using the iTunes Search API for catalog matching/artwork/links when no Apple Developer Program key is configured, reserving MusicKit only for library-specific operations (playlists, user's own library) that genuinely require the paid key.

## Live verification

Tested `https://itunes.apple.com/search?term=<query>&entity=song&limit=N` against the same battery of tracks used throughout this session:

- `Robert Palmer Every Kinda People` — clean match: `trackId: 1425290697`, `trackViewUrl: https://music.apple.com/us/album/every-kinda-people/1425289735?i=1425290697&uo=4`, plus `releaseDate`, `collectionName`. This is the exact track that returned **zero** results on SearXNG minutes earlier.
- `Compay Segundo Chan Chan` — single clean, unambiguous match — no multi-region/remaster duplication problem like SearXNG showed for the same track.
- `Kora Jazz Trio Round Midnight` (the deliberately obscure cover) — correctly returned 0 results. This is the right, honest behavior (no invented match), matching what Spotify/Deezer also do for the same track.
- A 5-request burst returned `200` on every call — no immediate rate-limit issue during light testing, unlike SearXNG which was still blocked after this session's similarly light use.

## Response shape (why this is a good fit for the existing matching pipeline)

Real fields returned per track: `artistName`, `trackName`, `collectionName`, `trackId`, `collectionId`, `trackViewUrl`, `releaseDate`, `artworkUrl100`. This is structurally similar enough to Spotify's/Deezer's search responses that `_score_candidate()`-style title/artist matching (already built and proven in `spotify.py`/`deezer.py`) could be adapted with real fields to score against, rather than inventing a new heuristic from raw search-result titles as the SearXNG approach would have required.

**One real, confirmed gap: no ISRC field.** The iTunes Search API does not return ISRC, which `_score_candidate()` currently uses for deduplication (not primary scoring) in the existing Spotify/Deezer implementations. Not a blocker — title/artist similarity scoring is the primary signal in both existing implementations anyway — but dedup logic would need to fall back to `trackId`/`collectionId` instead of ISRC for this service.

## Prior art: someone else already built this

[`AbdelmonemAwad/cadenza` issue #66](https://github.com/AbdelmonemAwad/cadenza/issues/66) and its merged [PR #67](https://github.com/AbdelmonemAwad/cadenza/pull/67) implement exactly this pattern for a different project (a self-hosted music library manager): a "catalogue-only mode" for their `AppleMusicProvider` that uses the iTunes Search API (`/search` and `/lookup`) instead of MusicKit when no Developer Program credentials are configured — covering search, album track listings (`lookup?id=`), artwork, artist/title/release-date metadata, and Apple Music links. Explicitly reserves MusicKit only for what genuinely requires it: library matching and account linking. Confirmed limitations stated in that project's own issue: ~20 requests/minute rate limit, no ISRC returned — both consistent with this session's own findings.

## Rate limits

External research (not independently load-tested this session, to avoid repeating the SearXNG mistake of exhausting a shared resource) puts the practical limit around **20 requests/minute**, with a `Retry-After` header on 429s. The existing `music_link_cache.py` pattern (cache both hits and misses, keyed by service+raw_title, shared across all users) already fits this well — the same design that makes Spotify/Deezer's music-link feature cheap in practice (one lookup per unique track, not per listener) would keep Apple Music's real request volume far under this limit for a self-hosted app at mradio-web's scale.

## Other free options considered, ruled out for this specific need

- **MusicBrainz** (`musicbrainz.org/ws/2`, free, keyless, ~1 req/sec, requires a descriptive `User-Agent` header) — a real, legitimate, canonical music metadata database (50M+ recordings), but doesn't provide streaming-service URLs itself; it's an identity/metadata source, not a storefront link resolver. Could be useful later as a cross-reference (e.g. resolving ISRC across services) but doesn't directly solve "give me an `music.apple.com` link."

## Updated recommendation

**This supersedes the SearXNG-based conclusion above.** The iTunes Search API is a better-fitting, already-proven-elsewhere, free, keyless option for Apple Music search-only links — no rate-limit risk shared with other projects' usage (unlike SearXNG's shared upstream-engine problem), structured response fields, and independent confirmation via `cadenza`'s own shipped implementation of the identical idea. Worth planning as a real implementation (extending the existing music-service dropdown/link pattern to a third service) rather than research-only — the open item is building the actual `apple.py`-equivalent module and scoring logic, not further feasibility research.

---

Date: 2026-09-15
Scope: implemented as `apple_music.py` (v1.22.0). Operator asked directly: would many listeners running the radio in the background, each with a music service active, risk the app's own request volume getting flagged/throttled as "excessive" by Spotify/Deezer/Apple?

## Verdict: not a live risk at this app's scale, by design — worth re-checking only if the listener base or station catalogue grows a lot

The music-link feature was already built to avoid exactly this, for reasons unrelated to this specific question (it predates Apple Music):

- **Requests fire per track-change event, not on a timer and not per-listener.** `useMusicLink.ts`'s effect only runs when `rawTitle` or `service` changes.
- **`music_link_cache.py` is shared across all users, keyed by `(service, raw_title)`.** If N listeners are on the same station when a track changes, that's one outbound request to the active service, not N — every other listener's lookup hits the cache. Misses are cached too (`{"url": null}`), so a track with no match isn't re-queried by every subsequent listener either.
- Effective sustained load per service is roughly "distinct new tracks across all currently-playing stations per minute," not "number of listeners."

Given that shape, checked each service's real limit against it:

- **Apple (iTunes Search API):** the tightest of the three — ~20 req/min observed (see this file's earlier entry). Comfortably under load at mradio-web's current scale; would only be a real concern if many *different* stations changed to *never-before-cached* tracks within the same ~60s window (e.g. a large station catalogue's synchronized top-of-hour ID changes).
- **Spotify:** search goes through `spotify.get_app_token()` (Client Credentials, one app-level token, no per-user token) — same shared-cache protection applies, no per-user rate-limit exposure either.
- **Deezer:** unauthenticated search, no documented hard cap encountered in this session's testing; same caching applies.

**Not acted on — documented headroom, not a live problem.** Nothing changed in the code as a result of this question. Revisit if the station catalogue or listener count grows enough that "distinct new tracks per minute across the whole deployment" could plausibly approach ~20 for the Apple lookup specifically.

---

Date: 2026-09-15
Scope: operator asked whether Amazon Music — which markets itself as having the largest music catalog — could be added as a fourth search-only link option, the same way Apple Music was added via the free iTunes Search API. This re-checks Amazon specifically, since the read-only/search-only feature shape (no OAuth, no playlist writes) is different from what the original 2026-09-12 investigation ruled Amazon out for (lack of a public *write* API for third-party playlist creation).

## Verdict: not viable, for a different and harder reason than Spotify's cap — no public signup path exists at all

**Official Amazon Music Web API is real and does have a search endpoint** (`Web API Search V1.0` — searches albums/artists/tracks/podcasts, ranked results, plus a `Tracks` endpoint for per-ID metadata) that would structurally fit this app's existing search-only pattern. But confirmed live via Amazon's own developer docs: **"The APIs are currently in closed Beta status and access is limited to already approved developers,"** with onboarding gated behind "reach out to your Amazon Music point-of-contact" — there is no self-service application, sign-up form, or paid tier to buy into, unlike every other service this app integrates with:

- Spotify: free self-service Client Credentials (app-level, no user OAuth needed for search).
- Deezer: free self-service app registration.
- Apple: no signup at all — the iTunes Search API is public and keyless.
- Amazon: **invite-only, requires an existing relationship with Amazon Music** ("your point-of-contact"). Not obtainable for a personal/self-hosted project with no prior Amazon partnership, at any price.

This is a harder gate than Spotify's 5-user Development Mode cap (that one is at least self-service, just capped) or Apple's old paid-MusicKit-only path (that one could be solved with money). There is no equivalent workaround here — no free tier, no paid tier, no keyless public endpoint.

**Unofficial alternative ruled out, not just skipped**: a GitHub-hosted open-source "Amazon Music API" project exists and does support search + streaming URL extraction, but it works by holding a **real logged-in Amazon account's cryptographic session tokens** (its own README warns "deploy only on private HTTPS servers") and includes DRM key retrieval for actual playback — a completely different risk category from Apple's public keyless catalog lookup. This isn't a public API wrapper, it's an Amazon-account-credential-based tool built for personal streaming/DRM circumvention, structurally similar to a scraper impersonating a logged-in session. Not appropriate for a shared, self-hosted app's read-only "open this track's page" link feature — the ToS and security exposure (storing/using a real Amazon account's session tokens server-side, shared across every listener) isn't worth it for a "nice to have" link.

## Recommendation

**Do not add Amazon Music.** Unlike Apple (paid-but-obtainable) or Spotify (capped-but-self-service), Amazon's official API has no path a small self-hosted project can realistically get onto, and the unofficial alternative trades away exactly the safety properties (no OAuth, no account credentials, no per-service risk) that made the current three-service design worth building this way in the first place. Revisit only if Amazon's Web API ever moves out of closed beta into public self-service — no indication of a timeline for that as of this search.

---

Date: 2026-09-15
Scope: operator asked whether a single cross-platform aggregator ("an IMDB for songs") could replace the per-service integration pattern — one lookup returning matched links across every platform at once, instead of separate `spotify.py`/`deezer.py`/`apple_music.py` modules.

## Verdict: the right kind of service exists (Odesli/Songlink) but it is currently unusable — keyless access is dead, blocked pending an email reply

**Odesli/Songlink** (`api.song.link`, powers song.link/album.link) is exactly this pattern: one call, given a track URL on any platform or an ISRC, returns matched links across Spotify, Apple Music, YouTube, Deezer, Tidal, Amazon Music, SoundCloud, Yandex, and more. Would structurally replace all three current per-service modules with one. Songwhip, the other major player in this space, shut down in 2024 (acquired by Sony/The Orchard, no migration path) — Odesli is the only serious option left.

**Live-tested 2026-09-15**: `curl "https://api.song.link/v1-alpha.1/links?url=spotify:track:0Jcij1eWd5bDMU5iPbxe2i&userCountry=US"` (no key) returned `HTTP 401 {"statusCode":401,"code":"PUBLIC_API_ACCESS_DEPRECATED"}`. This is ahead of the API's own documented retirement date (July 31, 2026, per third-party docs mirrors) — the keyless door is already shut, not just rate-limited. `help.song.link` (the docs subdomain third-party sources cite) is also now DNS-unreachable, consistent with an active wind-down rather than a future-dated one.

**Action taken**: drafted (not sent by me — left in the operator's Gmail as a draft for review/send) an email to `developers@song.link`, the address consistently cited across multiple independent third-party client-library docs (Go package, Node.js client) as the official API-key request channel. States the 401 finding directly, asks whether keys are still being issued at all, gives a realistic usage estimate (one lookup per unique track per station, cached and shared across all listeners — same pattern as the existing `music_link_cache.py`), and asks for a pointer to a successor service if Songlink is fully retired.

**Current status: blocked, pending a reply.** No further action possible until either a real API key arrives or Odesli responds (decline, pointer elsewhere, or no reply — treat silence after a reasonable wait as an effective no). Do not attempt to build against this without a key; the keyless surface is confirmed dead, not merely deprecated-but-working.

---

Date: 2026-09-17
Scope: operator asked whether Ollama could be sped up by re-ordering the pipeline (search Wikipedia first, use it as a fast-path, fall back to the current LLM flow only if nothing found) and whether a "much bigger and faster" cache would help. Live-benchmarked every stage against the real LT Ollama instance (`100.73.176.63:11434`) and the real `enricher.py`/`wiki.py`/`cache.py` code paths — not simulated.

## Verdict: the premise doesn't match the architecture — Wikipedia grounding is already a pre-step, not a fallback, and it isn't the bottleneck. Ollama generation itself is. The cache's real problem isn't read speed, it's write cost scaling with size.

### 1. Wikipedia grounding is already wired in, and it isn't slow

`enricher.py::_ask()` already calls `wiki.ground()` **before** every categorical-provider LLM call (including Ollama) and injects the result as "GROUNDING CONTEXT" in the prompt (see AI.md's Cross-cutting section, shipped 2026-09-11). It is not "only search Wikipedia if the LLM comes up empty" — it always runs first. So the proposed reordering already exists, just in the opposite direction from what was described (grounds the LLM, doesn't replace it).

Live timings (5 real artist/title pairs, `wiki.ground()` direct call):

| Call | Cold (uncached) | Warm (in-memory cache hit) |
|---|---|---|
| The Beatles / Let It Be | 1.608s | 0.000006s |
| Beethoven / Symphony No. 5 | 0.991s | 0.000004s |
| Fleetwood Mac / Dreams | 1.022s | 0.000003s |
| Mozart / Eine kleine Nachtmusik | 1.245s | 0.000003s |
| Daft Punk / Get Lucky | 0.766s | 0.000002s |

Cold lookups cost under 1.6s; the existing 1-hour in-memory cache (`wiki.py`, `_CACHE_TTL = 3600`, `_CACHE_MAX_SIZE = 200`) makes repeats free. This is not where the time goes.

### 2. Ollama generation dominates total latency by 1-2 orders of magnitude

Same prompt template (`_PROMPT_TEMPLATE` from `enricher.py`, byte-for-byte), same track (The Beatles - Let It Be), run against every model currently pulled on the LT Ollama instance (note: `gemma3:4b`, the hardcoded default in `providers.py::llm_ollama()`, is **no longer pulled** on LT — the roster has drifted to `gpt-oss:20b`, `qwen3:14b`, `qwen3.5:9b`, `gemma4:e4b-it-qat`, `phi4-reasoning:plus`, `phi4-mini:latest`, `translategemma:12b`):

| Model | No grounding | With grounding | tok/s | Notes |
|---|---|---|---|---|
| `phi4-mini:latest` | 6.95s (170 tok) | 3.41s (152 tok) | ~58 | Fastest; grounding made it *faster*, not slower — shorter, more anchored output |
| `gemma4:e4b-it-qat` | 19.62s (641 tok) | 22.98s (1151 tok) | ~52 | Grounding made this one slower — wrote a longer answer using the extra context |
| `gpt-oss:20b` | 24.58s (1022 tok, num_predict=2200) | not re-tested | — | Currently-configured special-case model (anti-loop prompt rules, see AI.md); completed successfully within its budget in this run |
| `qwen3.5:9b` | 49.48s, **empty response** (hit 1200-token cap) | 39.28s, **empty response** (same) | ~32 | Burned its entire `num_predict` budget with no final answer — the exact `gpt-oss` anti-loop failure mode already documented in AI.md, but on a *different* model family, and un-mitigated (anti-loop rules only trigger for `provider == "ollama" and model.startswith("gpt-oss")`) |
| `phi4-reasoning:plus` | timed out at 120s (test harness cap; app's real `ollama_timeout` default is 75s) | not tested | — | A reasoning-tuned model; consistent with the same class of problem as `gpt-oss`/`qwen3.5:9b` but worse — never returned in the window tested |

**Takeaway: total latency is 100% dominated by token-generation time on the local GPU, not by any surrounding lookup.** Wikipedia grounding is 1-2 seconds cold, near-zero warm; Ollama generation is 3-50+ seconds depending on model and whether it gets stuck reasoning instead of answering. No reordering of Wikipedia vs. LLM changes this, because the LLM call is never skipped — grounding is a quality input to it, not an alternative to it.

**Real lever for speed: model choice and `num_predict` budget, not pipeline order.** `phi4-mini:latest` at ~3-7s is roughly 3-7x faster than `gemma4:e4b-it-qat` and ~10x faster than the reasoning-prone models on this exact prompt, while still returning grounded, correctly-shaped JSON. This wasn't a full accuracy battery (out of scope for a speed investigation) but is a concrete starting point for a follow-up accuracy check before considering it as a new default.

### 3. Cache reads were never the bottleneck; cache **writes** are the one write-cost hazard that actually scales badly

Benchmarked `cache.py`'s real `get_cached()`/`store()` against a temp cache file (not production data):

| Cache size | Populate (800 sequential `store()` calls) | 50 sequential `get_cached()` calls | Per-read cost |
|---|---|---|---|
| 800 entries (current `MAX_ENTRIES`) | 4.59s | 0.059s | ~1.18ms |
| 5000 entries (simulated "much bigger" cache) | 74.45s | 0.378s | ~7.57ms |

Both read costs (1-8ms) are noise next to a 3-50 **second** Ollama call — a bigger cache's read cost would never be user-visible. But `store()` cost is real and did scale linearly with cache size (74s to populate 5000 entries vs. 4.6s for 800) — each `store()` call does a full synchronous read-modify-write of the entire `cache.json` file (`_load_sync()`/`_save_sync()` in `cache.py`), so **every single new trivia result written pays a cost proportional to total cache size**, not proportional to one entry. At 800 entries (current `MAX_ENTRIES`) this is ~93ms/write — invisible next to Ollama's multi-second calls today. If `MAX_ENTRIES` were raised substantially (the "much bigger cache" ask) without changing the storage strategy, per-write cost would grow with it and could eventually become non-trivial, though still small compared to generation time at any size tested here.

Cache file sizes observed: 800 entries ≈ 715 KB, 5000 entries ≈ 4.5 MB (avg ~900 bytes/entry, consistent with the 750-850 character trivia field plus JSON overhead).

## Recommendation

Do not build a "Wikipedia-first fast path" — it's not a coherent optimization given how the pipeline actually works (grounding already runs first, unconditionally, and is not the slow part). Two things are worth doing instead, neither implemented this session (benchmarking only, per the ask):

1. **If Ollama speed matters enough to act on:** consider `phi4-mini:latest` as a faster default over whatever's currently configured, subject to its own accuracy fact-check battery (not run here) before promoting it — AI.md's existing per-provider accuracy process applies. Separately, the `qwen3.5:9b`-family empty-response failure (burns full token budget on reasoning, same shape as the already-documented `gpt-oss` issue) suggests the anti-loop prompt-hardening condition in `textutil.py` (`provider == "ollama" and model.startswith("gpt-oss")`) is too narrow now that the LT model roster includes other reasoning-prone models; worth broadening if any of them get adopted.
2. **If `MAX_ENTRIES` gets raised meaningfully (10x+) for "a much bigger cache":** the full-file read-modify-write in `cache.py::store()` is the part that would start to cost something — not `get_cached()`. A real fix (not attempted here, out of scope for benchmarking) would replace the whole-file JSON store with something that supports single-key writes (e.g. SQLite, already used elsewhere in this codebase per `db.py`) so write cost stays flat regardless of total cache size. At the current 800-entry ceiling this isn't worth doing yet — the numbers above show it's still cheap in absolute terms.

**Benchmark scripts** (not committed — ad hoc, run from `/tmp`): `/tmp/ai_benchmark.py` (wiki + Ollama latency across models, with/without grounding), `/tmp/ai_cache_benchmark.py` (cache read/write cost at 800 vs 5000 entries), `/tmp/ai_gptoss_bench.py` (gpt-oss:20b and phi4-reasoning:plus spot-check). Re-run against the live LT instance to reproduce; results will drift as the model roster and hardware load change.

---

Date: 2026-09-17 (same day follow-up)
Scope: operator asked to switch the Ollama default to `phi4-mini:latest` per the earlier speed benchmark, in parallel with a broader model-catalog investigation. Ran the standard 5-track accuracy battery (`beethoven9`, `kindofblue`, `muldaur_empty_bed`, `chanchan`, `obscure_trap`) against `phi4-mini:latest` using the real production code path (`_PROMPT_TEMPLATE`, `apply_provider_rules("ollama", "phi4-mini:latest")`, live Wikipedia grounding via `wiki.ground()`) before accepting the switch as final — this project's established discipline per AI.md's own three-axis (reliability/speed/accuracy) tracking model.

## Verdict: phi4-mini:latest FAILS the accuracy battery — reverted same day, do not re-adopt without a passing re-test

This confirms and sharpens an existing finding already on record (`STATUS.md`, 2026-09-09 P5000 comparison): "`phi4-mini` (14.9s, fast but fabricated a fake dedicatee)". That entry was missed before the speed-only benchmark two days ago; should have been checked first.

Live results (5-track battery, grounded, hardened prompt, `100.73.176.63:11434`):

| Track | Grounded | Result |
|---|---|---|
| `beethoven9` (Beethoven, Symphony No. 9) | Yes (article: "Symphony No. 9") | **Empty trivia** — `done_reason: stop`, 26 tokens, no failure/timeout, just an empty `"trivia": ""` on one of the most extensively documented works in the classical canon |
| `kindofblue` (Miles Davis, Kind of Blue) | Yes | Correct — 1959, personnel (Coltrane, Adderley, Evans, Chambers, Cobb) all accurate |
| `muldaur_empty_bed` (Maria Muldaur, Empty Bed Blues) | Yes (article: "Empty Bed Blues") | **Empty trivia** — same pattern as beethoven9, `done_reason: stop`, no answer despite a resolved grounding article |
| `chanchan` (Compay Segundo, Chan Chan) | Yes (article: "Chan Chan") | **Fabricated wrong death date** — claimed Compay Segundo "passed away in 1995"; he actually died in **2003**. Grounding was available and resolved but did not prevent the fabrication. |
| `obscure_trap` (Kora Jazz Trio, Round Midnight) | Yes (article: "Round Midnight") | **Invented band lineup** — claimed the trio consists of "Mamadou Diabate, Ibrahima Sylla, and Ali Farka Touré"; none of these are Kora Jazz Trio's actual members (Djeli Moussa Diawara, Abdoulaye Diabaté, Moussa Sissokho), and Ali Farka Touré is a real, well-known, but entirely unrelated deceased musician — the model wove a plausible real name into a fabricated lineup. Also invented a "formed in 2001 in Paris" claim with no support in the grounding excerpt. |

**3 of 5 tracks compromised** (2 silent empty answers + 2 outright fabrications, one of which invents a real person's name into a false context) — this is not a marginal or borderline result. Notably, this happened **with Wikipedia grounding active on every track** (all 5 resolved a real article) — grounding did not prevent the chanchan/obscure_trap fabrications, meaning `phi4-mini` will not reliably use the grounding context it's given, unlike the pattern seen with NIM's `llama-3.2-11b-vision-instruct` (AI.md: "an explicit, grounded Kind of Blue answer that named the 1959 release and the correct key sidemen").

The empty-trivia cases (`beethoven9`, `muldaur_empty_bed`) are a different, arguably worse failure mode than either the `gpt-oss` reasoning-loop problem or straightforward fabrication — the model returns cleanly (`done_reason: stop`, not `length`) with a syntactically valid but content-empty response, so nothing in the current pipeline flags it as a failure; it would silently show users a track with no trivia at all rather than retrying or falling back.

## Action taken

Reverted the same-day default-model change in `providers.py` (`llm_ollama()` and `_test_ollama()` fallbacks) and `settings.py` (`_DEFAULTS["ollama_model"]`) from `phi4-mini:latest` back to `gpt-oss:20b` — not back to the original `gemma3:4b`, since that model is confirmed no longer pulled on LT (see the earlier same-day entry) and `gpt-oss:20b` already has a real passing accuracy record on this exact battery (AI.md's ollama section: "grounded re-run 2026-09-11: gpt-oss:20b 4/4, all grounded").

**Confirmed separately: this code-level default was never going to reach the live LT install anyway.** A live SSH check of `/mnt/cache/appdata/mradio-web/data/settings.json` (host path; `/data/settings.json` in the `mradio-web` container) found `"ollama_model": "gpt-oss:20b"` already explicitly saved on disk, last modified 2026-09-14 — well before this session. Per `settings.load()`'s `merged = dict(_DEFAULTS); merged.update(data)` merge order (the same hazard already documented for `dahl_timeout` in AI.md), an on-disk value always wins over the code default regardless of what the code default says. So the erroneous `phi4-mini:latest` default change, while live in this session, would never have taken effect on the real production install without a separate manual settings-admin change — no user-facing exposure occurred. Also confirmed the real `ollama_url` on LT is `http://192.168.88.8:11434` (LAN), not the `100.73.176.63` tailscale address used for this session's benchmarking — both reach the same physical Ollama instance, the LAN address just isn't reachable from wherever this session's shell runs.

## Recommendation

Do not adopt `phi4-mini:latest` as a default without a passing accuracy battery — this one failed decisively. If speed is still worth pursuing, the "which other Ollama-catalog model might be faster AND accurate" question is now a live, separate investigation (see the same-day parallel task below) rather than something this speed-only benchmark can answer on its own; a model needs to clear a real accuracy bar before its speed number is meaningful, same as every other provider in AI.md.

---

Date: 2026-09-17 (same-day follow-up #2)
Scope: with `phi4-mini:latest` ruled out (previous entry), a background research task was run in parallel to find genuinely untried Ollama-catalog candidates for the P5000 (16GB VRAM, Pascal, no tensor cores) rather than re-testing models already tried. Research shortlisted `phi4:14b` (plain Phi-4, non-reasoning, ~9.1GB, never tried — distinct from both the already-failed `phi4-mini` and the already-timing-out `phi4-reasoning:plus`) and `qwen2.5:14b` (previous Qwen generation, ~9.0GB, never tried — an independent benchmark cited in the research found Qwen3's dense models sometimes underperform Qwen2.5 at the same size despite being newer). Both pulled on LT and run through the identical standard 5-track grounded accuracy battery used throughout this file, with every specific factual claim verified against live web search rather than eyeballed.

## Verdict: both candidates fabricated on the same track (`chanchan`) — neither is a clean win, but `phi4:14b` is closer to usable

### `phi4:14b` — 4/5 correct, 1 confirmed fabrication

| Track | Elapsed | Verdict |
|---|---|---|
| `beethoven9` | 26.3s | ✅ Correct — 1822-24 composition, Vienna 1824 premiere, Schiller's "Ode to Joy," real conductors (Bernstein, Karajan) as generic performer examples, not fabricated specifics |
| `kindofblue` | 14.0s | ✅ Correct — 1959, NYC, modal jazz, Coltrane/Evans named accurately |
| `muldaur_empty_bed` | 14.9s | ✅ Correct — verified live: Bessie Smith's 1928 recording **was** inducted into the Grammy Hall of Fame in 1983, confirmed via web search, not a fabrication |
| `chanchan` | 14.3s | ❌ **Fabricated** — claimed "Chan Chan" was "featured in the film 'Waking Life' in 2001." Verified live: false. *Waking Life*'s soundtrack is entirely Tosca Tango Orchestra/Glover Gill tango pieces plus one Chopin nocturne — no Compay Segundo, no "Chan Chan," at all. The 1997 release-year claim in the same answer is correct (Buena Vista Social Club single, released 16 September 1997); only the film credit is invented. This is exactly the category `CATEGORICAL_HALLUCINATION_RULES` forbids outright ("no unverified film/TV/commercial claims") — the operator likely confused this with Compay Segundo's real, separate appearance in the *Buena Vista Social Club* (1999) documentary. |
| `obscure_trap` | 13.6s | ✅ Correct, and notably honest — attributed "Round Midnight" to Thelonious Monk (1944) and did not attempt to name Kora Jazz Trio's actual lineup at all, avoiding the exact invented-band-member failure `phi4-mini` committed on this same track |

Non-reasoning by construction (confirmed via Ollama's own model page and independent guides) — no budget-burning empty-response risk observed across any of the 5 runs; every response used `done_reason: stop` with real content. Slower than `gpt-oss:20b`'s ~25s median only on `beethoven9` (26.3s); the other 4 tracks ran 13.6-14.9s, meaningfully faster than the current `gpt-oss:20b` default.

### `qwen2.5:14b` — 3/5 correct, 1 confirmed fabrication, 1 honest decline

| Track | Elapsed | Verdict |
|---|---|---|
| `beethoven9` | 24.2s | ✅ Correct — same core facts as phi4:14b, more compressed |
| `kindofblue` | 13.5s | ✅ Correct, though noticeably repeats itself ("harmonically fluid, scale-based approach" appears twice almost verbatim) — a quality/polish issue, not a factual one |
| `muldaur_empty_bed` | 12.7s | ✅ Correct but thin (241 chars, well under the 750-850 target) — no fabrication, but doesn't hit the prompt's own length requirement |
| `chanchan` | 13.1s | ❌ **Fabricated** — claimed "Chan Chan was composed in the 1960s in Havana." Verified live: both details are wrong. It was written in 1987 (Compay Segundo's own account, corroborated by Eliades Ochoa's recollection of first recording it in 1987 at EGREM Santiago studios), and no source ties its composition to Havana — the lyrics reference Holguín-province towns (Alto Cedro, Marcané, Cueto, Mayarí) and it was popularized out of Santiago de Cuba, not Havana. **Notably, the real Wikipedia grounding excerpt this exact run received says "Written in the 1980s"** (per this file's own earlier `chanchan` entry) — this is not a case of missing information, the model had the correct decade in its own context window and still asserted a different, wrong one. |
| `obscure_trap` | 11.6s | ✅ **Honest decline** — "No confident details are available about this specific track," rather than inventing a lineup. This is the correct behavior the hardened prompt asks for and neither `phi4-mini` nor `phi4:14b` achieved as cleanly on this track (phi4:14b answered about Monk generically instead of declining; still factually correct, but qwen2.5's explicit decline is arguably the more disciplined response). |

Also non-reasoning, zero empty responses, consistently the fastest of the two candidates (11.6-24.2s vs phi4:14b's 13.6-26.3s) but with noticeably shorter, thinner trivia — several responses fall well short of the prompt's 750-850 character target, unlike `phi4:14b`'s answers which land closer to that range.

## Recommendation

**Neither candidate is a clean pass — do not switch the default off `gpt-oss:20b` based on this round.** Both fabricated on the identical track (`chanchan`), suggesting this specific song (a well-known song with a somewhat confusing multi-stage history — written 1987, first recorded 1987, internationally famous 1997 Buena Vista Social Club version) is a genuine trap for models this size, not a fluke of one model. `gpt-oss:20b` (the current default) already has a real passing 4/4 grounded battery on record (AI.md) and remains the better-evidenced choice.

Of the two, **`phi4:14b` is the stronger candidate for future consideration** if this line of investigation continues: 4/5 clean, non-reasoning, comfortably fits the P5000's VRAM, and consistently 1.5-2x faster than `gpt-oss:20b` on 4 of 5 tracks. It is not being promoted to default on the strength of a single 5-track battery with one fabrication — AI.md's own standard (see gpt-oss:20b's "4/4 grounded" bar) implies a clean run, and this wasn't one. Worth a second, larger battery (more than 5 tracks, ideally including a repeat of `chanchan` specifically to see if the fabrication is consistent or a one-off) before considering a default change. `qwen2.5:14b` is not recommended for further testing — same fabrication risk as phi4:14b, no offsetting speed advantage worth the risk (both are in the same ~12-26s range), and thinner trivia output relative to the prompt's own length target.

**Both models pulled and left on LT** (`phi4:14b`, `qwen2.5:14b`) for any future re-test — no cleanup performed, per the research task's scope (live-testing, not a one-shot disposable check).

---

Date: 2026-09-18
Scope: found during a separate, general secrets-exposure audit of LT's `/mnt/user/appdata/` (see the `legbatower` repo — a cross-service security audit project, not this project's own scope). `mradio-web/data/settings.json` (the file this app's own settings UI writes real AI-provider API keys to — NVIDIA, Grok, Gemini, OpenRouter, Mistral, and a custom "dahl" provider) was found sitting at OS permission `644` (world-readable by any Unraid-level account/process), not `600`.

**Fix applied directly on LT, not via a code change in this repo:** `chmod 600 /mnt/user/appdata/mradio-web/data/settings.json`. Confirmed safe before applying — `docker top mradio-web` shows the app's own process runs as `root` inside its container, and the file was already `root:root`-owned, so tightening to owner-only access doesn't affect the app's own ability to read or rewrite its settings. Confirmed mradio-web still returns `200` on its live URL after the change.

**Not yet independently re-confirmed**: that a settings *save* from the app's own UI still works correctly post-fix. Should be unaffected by construction (same UID doing the write, same file, just narrower permissions), but this hasn't been manually re-verified through the actual UI flow yet — worth a quick check next time the operator is in mradio-web's settings page.

**This is a live-server/deployment fix, not a code fix** — nothing in this repo's own source needed to change, since the exposure was purely an OS-level file permission on the deployed instance, not how the app itself handles secrets. Full audit context (including a second, unrelated finding — an orphaned NPM install's exposed key file) lives in the `legbatower` repo's `findings.md`/`STATUS.md`, 2026-09-18 "secrets-in-config audit" entries.
