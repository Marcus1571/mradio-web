# Findings

Research log for options considered but not (yet) built — one entry per
question researched, with the verdict and why. Not a full history;
`STATUS.md`/`CHANGELOG.md` cover what actually shipped. For the
distilled, currently-adopted per-provider AI strategy derived from this
research, see `AI.md` — this file stays raw evidence, `AI.md` is the
"what we decided" layer.

## AI provider fact-check battery (researched 2026-09-11)

Resumed the parked veridicity investigation. Goal: move past anecdotal
spot-checks and measure both mechanical reliability (production logs) and
content accuracy (manual fact-check) for the providers that looked
problematic.

### Production mechanical snapshot (from LT `ai_requests`)

Run with `MRADIO_DB_PATH=/tmp/mradio-web-lt.db python -m app.ai_stats` on a
copy of the production DB taken 2026-09-11:

| provider | success_rate | median | p90 | n |
|---|---|---|---|---|
| mistral | 100% | 1,741ms | 2,297ms | 17 |
| grok | 93% | 5,141ms | 7,675ms | 14 |
| openrouter | 100% | 5,998ms | 21,322ms | 5 |
| opencode | 100% | 21,141ms | 61,259ms | 14 |
| gemini | 71% | 11,629ms | 25,695ms | 5 |

Mechanical winners: Mistral (fast + never fails), OpenCode (slow but always
returns). Gemini is the only provider with a visible failure rate in live
traffic right now.

### Structured battery

23 calls across 6 providers × 4 tracks chosen to stress different failure
modes: a canonical classical work (`beethoven9`), a canonical jazz album
(`kindofblue`), a real but less-documented blues recording
(`muldaur_empty_bed` — Maria Muldaur's version of "Empty Bed Blues"), and an
obscure live cover (`obscure_trap` — Kora Jazz Trio, "Chan Chan"). Prompts
used the same `apply_provider_rules()` hardening the app uses in production.

| provider | OK | median | notes |
|---|---|---|---|
| mistral | 4/4 | 3,124ms | Fast, never empty; invented vague filler on the obscure track. |
| gemini | 4/4 | 7,664ms | Falsely dated Muldaur's "Empty Bed Blues" to 1978 Los Angeles. |
| openrouter | 4/4 | 34,051ms | Returned literal `"User Safety: safe"` for Muldaur; misdated/misattributed `obscure_trap`. |
| opencode | 3/4 | 24,071ms | `kindofblue` timed out at 90s; otherwise accurate, including correct 1928 Bessie Smith origin for "Empty Bed Blues". |
| ollama_gptoss | 4/4 | 29,500ms | Correctly declined on obscure track; otherwise acceptable. |
| ollama_qwen3 | 3/3* | 57,784ms | *obscure_trap not reached before the run was killed; falsely placed "Empty Bed Blues" on `Midnight at the Oasis` (1974). |

### Fact-check verdicts

- **Beethoven 9 / Kind of Blue**: every provider that returned output got
the well-documented facts broadly right. Minor issue: OpenRouter's
`kindofblue` listed Wynton Kelly as a generic feature without noting he
played only on "Freddie Freeloader."
- **Maria Muldaur — "Empty Bed Blues"**: confirmed against AllMusic/Discogs
— Muldaur's recording appears on the 2001 album *Richland Woman Blues*
(Stony Plain). **Gemini** invented "recorded in 1978 in Los Angeles."
**Mistral** strongly implied a 1970s origin. **Ollama qwen3** claimed it was
a 1977 track from *Midnight at the Oasis*. **OpenRouter** returned `"User
Safety: safe"`. **OpenCode** correctly identified the song as a Bessie
Smith standard and avoided inventing a date for Muldaur's version.
- **Kora Jazz Trio — "Chan Chan" (live cover)**: Chan Chan was written by
Compay Segundo in 1984; the Buena Vista Social Club recording is from 1997.
**OpenRouter** called it "a cover of Buena Vista Social Club's 1996
recording" — wrong year, wrong primary attribution. **Gemini** correctly
identified it as a Chan Chan cover. **Mistral** emitted generic filler.
**Ollama gpt-oss** correctly declined. **OpenCode** gave detailed, correct
context about both Kora Jazz Trio and the original.

### Mechanical bug found

`_llm_openai_compatible()` in `backend/app/providers.py` crashes with
`AttributeError: 'NoneType' object has no attribute 'strip'` when a provider
returns `"content": null` instead of a string. Observed on OpenRouter
reasoning-loop outputs. The fix is to coerce `None` content to `""` before
`.strip()`.

### NIM default model still EOL

Confirmed the configured default `minimaxai/minimax-m3` returns HTTP 410.
Other models on the test account either 404'd or hung. NIM remains
non-functional independent of prompt quality.

### Implications for strategy

- **Speed ≠ accuracy**: Mistral is the fastest and most reliable
mechanically, but still fabricates on obscure tracks even with categorical
hardening. The hardening helped on famous works; it is not enough when the
model has no real source to draw on.
- **Gemini's production failures (29%) are the immediate reliability
problem**, separate from its accuracy problem.
- **OpenCode is the only provider that both declines *and* gets obscure
facts right**, but its latency makes it unsuitable as a default for every
request.
- **Grounding is the most promising next step**: the existing
`backend/app/wiki.py` already fetches article intros via MediaWiki and
throws away the text. Injecting that snippet before the LLM call would give
every provider (especially the fast, fallible ones) a shared retrieved
anchor. See `AI.md` for the adopted-strategy view.

## AI provider fact-check battery — grounded re-run (researched 2026-09-11)

Implemented Wikipedia snippet grounding (`backend/app/wiki.py` now returns
article intros, `backend/app/enricher.py` prepends them for
`_CATEGORICAL_PROVIDERS`) and re-ran the same 4-track structured battery.

### What changed

- `backend/app/wiki.py`: in-memory 1-hour cache, 1-second global API throttle,
  429/5xx retry, title-only search tier first (artist+title confused
  Wikipedia's search), strict surname-aware relevance, and scoring that
  boosts exact title matches (+1000) and music markers (+200) while
  penalizing disambiguation pages (-300).
- `backend/app/enricher.py`: `_ask()` now calls `wiki.ground(artist, title,
  surname)` for `_CATEGORICAL_PROVIDERS` and injects the excerpt before the
  LLM prompt.
- `backend/app/settings.py`: NIM default model switched from EOL
  `minimaxai/minimax-m3` to `meta/llama-3.2-11b-vision-instruct`.
- `backend/app/providers.py`: `_llm_openai_compatible()` coerces `None`
  content to `""` before `.strip()`.

### Grounding resolution accuracy

All four test tracks resolved to the intended article:

| track | resolved article |
|---|---|
| Beethoven 9 | Symphony No. 9 in D minor, Opus 125 (Beethoven) |
| Kind of Blue | Kind of Blue |
| Empty Bed Blues | Empty Bed Blues |
| Chan Chan (live cover) | Chan Chan (song) |

One intermittent failure mode was fixed: Wikipedia search for "Kind of Blue"
was returning "Kind of Blue (TQ album)" because the music-marker bonus
outweighed the exact-title match; exact matches now get a +1000 bonus.

### Grounded battery results (28 calls, 7 provider configs)

| provider | OK | median | notes |
|---|---|---|---|
| mistral | 4/4 | 1,878ms | All grounded; still generic on obscure track but no invented dates. |
| gemini | 4/4 | 2,680ms | All grounded; no repeat of the 1978 Los Angeles fabrication on Muldaur. |
| openrouter | 2/4 | 29,376ms | `muldaur_empty_bed` and `obscure_trap` returned empty; well-known tracks improved. |
| nim | 4/4 | 6,520ms | All grounded after mapping the battery's "nim" label to production's "openai" rules; Kind of Blue answer explicitly cites Coltrane/Adderley/Evans. |
| opencode | 4/4 | 12,535ms | Not grounded (plain taxonomy); still accurate, now also returns within timeout. |
| ollama_gptoss | 4/4 | 25,570ms | All grounded; obscure track no longer a clean decline but factually anchored. |
| ollama_qwen3 | 3/4 | 46,424ms | All grounded; `muldaur_empty_bed` still timed out, obscure track now correct. |

### Fact-check verdicts after grounding

- **Beethoven 9 / Kind of Blue**: every provider that returned output gave
  factually correct, grounded answers. NIM's grounded Kind of Blue reply
  named the 1959 release and the correct key sidemen.
- **Maria Muldaur — "Empty Bed Blues"**: Gemini, Mistral, NIM, and Ollama
  gpt-oss no longer invented a date/venue for Muldaur's version; grounded
  answers stayed close to the Wikipedia excerpt (Bessie Smith origin, 1928).
  OpenRouter and Ollama qwen3 still failed mechanically (empty/timeout).
- **Kora Jazz Trio — "Chan Chan" (live cover)**: grounded answers correctly
  attributed the song to Compay Segundo (1984). OpenRouter still failed on
  this track.

### Implications

- Wikipedia grounding eliminated the most egregious fabrications on the
  less-documented tracks for the providers that received it.
- OpenRouter's remaining failures are mechanical (empty response / timeout),
  not factual; its free auto-router is still unreliable end-to-end.
- Opencode remains accurate without grounding, confirming it is a different
  class of system (likely with its own retrieval path). It is still too slow
  for the default hot path.
- The next veridicity improvement is probably provider-specific: Gemini's
  native `google_search` tool, a stronger OpenRouter model pin, or a
  self-consistency critic pass — but those are out of scope for this
  grounding-focused iteration.

## Additional free AI providers for liner-notes enrichment (researched 2026-09-07)

User asked whether other free AI options exist beyond opencode/Ollama/NIM/
ChatGPT/Grok. Researched current (2026) free tiers rather than assuming
stale pricing.

**Key fact that shapes all of these**: mradio-web already has a generic
OpenAI-compatible provider slot (the "NIM, etc." bubble in AI providers —
base URL + model + API key, currently defaulting to NVIDIA NIM's hosted
endpoint). Any provider below that exposes an OpenAI-compatible
`chat/completions` endpoint works **today, with zero code changes** —
just repoint that one bubble's base URL/key. Only worth a dedicated
bubble (own fields, own PROVIDERS entry, i18n, etc. — the Grok/ChatGPT
treatment) if the user wants it available *alongside* NIM rather than
replacing it.

Candidates found:

- **Google Gemini (AI Studio)** — **built 2026-09-08, see MEMORY.md's
  "Google Gemini added as 6th AI provider" section.** Genuinely free,
  permanent tier (not a trial), no credit card required, available to
  every account (not admin-only, unlike ChatGPT/Grok). As of April
  2026 only Flash-family models (Flash, Flash-Lite) remain on the free
  tier; Pro models moved behind billing. OpenAI-compatible endpoint at
  `https://generativelanguage.googleapis.com/v1beta/openai/`. Rate
  limits are modest (roughly 10-15 RPM, up to 1,000 RPD on Flash) but
  comfortably enough for this app's one-track-at-a-time enrichment
  pattern.
- **Groq** — **checked live 2026-09-08, NOT actually free — struck
  from consideration.** Widely-repeated "free tier, ~1,000 req/day"
  claims (including this entry's own original wording) turned out to
  be stale/wrong. A real API key's `GET /v1/models` response shows
  every currently-available model with real, non-zero per-token
  pricing (e.g. `openai/gpt-oss-120b` at $0.15/$0.60 per 1M tokens).
  The models the free-tier claims were actually based on
  (`llama-3.3-70b-versatile`, `llama-3.1-8b-instant`) aren't in the
  live model list at all anymore — Groq's own docs page
  (console.groq.com/docs/models) now marks both "Enterprise"/
  "ContactSales", i.e. pulled from self-serve/free access entirely.
  Groq is a real, fast, OpenAI-compatible **paid, metered** API (same
  shape as NIM) — not a free-for-everyone option like Gemini. Could
  still be added the way NIM/OpenAI are (admin brings their own paid
  key, not admin-only-restricted since it's not a personal
  subscription) if ever wanted, but doesn't belong on this "free
  providers" list.
- **Cerebras** — **checked 2026-09-08, disqualified — struck from
  consideration.** The earlier "possible payment-method requirement"
  flag turned out correct: as of August 2026, Cerebras ended its
  no-card free tier. New accounts get $5 in free credits, but only
  after adding a **verified payment method** — API access stays
  inactive without one. Breaks this list's whole premise ("no credit
  card needed"), so not pursued further (would need a real card on
  file just to get a key to verify, defeating the point). Otherwise a
  real, fast, OpenAI-compatible API (`https://api.cerebras.ai/v1`) —
  same category as NIM/Groq (paid/metered with a trial credit), not a
  free-for-everyone option.
- **OpenRouter** — **built 2026-09-08, see MEMORY.md's "OpenRouter
  added as 7th AI provider" section.** Checked live before building
  (unlike the Groq research this session corrected): `GET /v1/models`
  is public/unauthenticated and shows ~19 genuinely free (`:free`
  suffix, `"prompt": "0", "completion": "0"`) models; no card needed to
  sign up (confirmed via the user's own successful signup); a real
  authenticated `POST /chat/completions` against `openrouter/free`
  (OpenRouter's own free-model auto-router) returned the correct JSON
  at `cost: 0` in the standard `choices[0].message.content` shape — no
  new request/response code needed, reuses the existing
  `_llm_openai_compatible()` helper unmodified. One real gotcha: unlike
  NIM/OpenAI, OpenRouter's `GET /models` doesn't validate the key (it's
  public), so the shared `_test_openai_compatible()` test helper
  doesn't work here — needed a dedicated `_test_openrouter()` that
  makes a real completion call instead. Free tier: 50 requests/day (no
  spend), 1,000/day permanently once $10 has ever been spent.

**Verdict**: Gemini built 2026-09-08 (own dedicated bubble, not
admin-only). Groq checked live 2026-09-08 and struck — not actually
free anymore (models pulled from self-serve, real per-token pricing on
everything left). Cerebras checked 2026-09-08 and struck — now
requires a card on file to activate API access at all, breaking the
"no card needed" premise. OpenRouter checked live 2026-09-08 and
built — genuinely free, no card, verified end-to-end before shipping.
This list is now fully resolved: 1 of 3 remaining candidates (Groq,
Cerebras, OpenRouter) actually qualified.

**How to apply if revisited**: NIM's OpenAI-compatible bubble can still
be repointed at Groq's or Cerebras's paid endpoints directly (base URL
+ key, Test button, no code change) if a metered/paid provider is ever
wanted alongside the free ones — they just don't belong on *this* free-
providers list. For any future free-tier candidate, follow the
OpenRouter/Gemini build pattern: verify live with a real key (`GET
/models` + at least one real completion) before writing any code, not
just a docs/blog-summary pass — that live-check step is what caught
Groq's and Cerebras's status changes this session, which the original
research (written from summaries, not live checks) had gotten wrong or
only half-flagged.
