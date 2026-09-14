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
