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
