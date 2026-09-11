# AI.md — AI provider strategy

Living document. One section per provider: the **currently adopted
strategy** — what's actually coded into the app right now, and why.
Updated whenever a provider's configuration, hardening, or quota
handling changes; this is the "what we decided" layer, not the "what we
found" layer.

- **`findings.md`** is the raw evidence feed — test results, web
  research, live quota/latency checks, fact-check outcomes. Append-only,
  chronological, one entry per question researched.
- **`AI.md`** (this file) is the distilled current state — what each
  provider's adopted strategy is *today*, derived from that evidence.
  Gets rewritten in place as strategy changes, not appended to.
- **`STATUS.md`** covers the rest of the app's current state; provider
  strategy lives here instead so STATUS.md doesn't grow another
  fast-churning section.

Providers are inherently mercurial — models get silently aliased or
deprecated, free tiers change quota, pricing shifts, accuracy varies by
model size and prompt. Re-verify a section's facts (via `findings.md`
research or a live test) before trusting it if it looks stale, rather
than assuming it's still accurate.

## Three separate axes, not one quality score

Every provider section below tracks three distinct things. They are
deliberately **not** blended into a single number:

- **Reliability** — did the call return usable output at all (vs.
  timeout/error/empty)? Mechanical, automatic: every real production
  call through `enricher.py`'s `_llm()` dispatch loop logs a row to the
  `ai_requests` SQLite table (see `backend/app/db.py`'s schema and
  `enricher.py`'s `_record_ai_request()`). Query it with
  `python -m app.ai_stats` (see `backend/app/ai_stats.py`) to refresh
  the numbers below — don't hand-edit stale figures, re-run the query.
- **Speed** — how long a successful call took. Same mechanical source,
  same query tool. `ai_requests.elapsed_ms` is wall-clock time for the
  whole provider call as seen by `_llm()`, not a provider-reported
  figure.
- **Accuracy** — was the *content* actually true? This **cannot** be
  inferred from logs or automated — it requires a human or an agent to
  check specific claims against real sources, the same way the OpenCode
  and Mistral fact-checks below were done. Stays a manual, evidence-based
  process logged in `findings.md`; this file only summarizes the
  verdict and sample size. `trivia_history` (per-user SQLite, see
  `backend/app/trivia_history.py`) now tags every stored answer with the
  provider that actually produced it (`provider` column, added
  2026-09-10 via `db.py`'s `_ensure_column`) — this is where real
  production answers worth fact-checking can be pulled from. Storage
  retains up to 100 rows per user (`STORAGE_LIMIT`); the UI only shows
  the most recent 10 by default (`RECENT_DEFAULT_LIMIT`) — the wider
  retention exists specifically so there's enough real material to
  sample from for this investigation without changing what a normal
  user sees. `ai_stats.trivia_history_provider_counts()` gives a quick
  per-provider row count as a cross-check against `ai_requests`' own
  numbers (the two won't match exactly — `ai_requests` logs every
  attempt including ones a fallback chain moved past, `trivia_history`
  only logs final answers actually shown to a user — divergence between
  them isn't a bug).

Why not combine them: a fast, reliable, confidently-**wrong** provider
(raw/unhardened Mistral, before its prompt hardening shipped) would
score deceptively well on a blended metric built mostly from mechanical
data, since "returned something quickly" and "returned something true"
are unrelated properties. Keeping them separate is a deliberate design
choice — don't collapse them back into one number without re-deriving
why this section exists.

**Data maturity note (as of 2026-09-10):** the `ai_requests` logging
table was added this session — there is no historical production data
yet, only whatever accumulates from real traffic going forward. Where a
provider section below has no Reliability/Speed numbers, that's why;
check back after real usage accrues. The Speed figures that *do* appear
below (Mistral ~1-3s, Ollama 47.5s, etc.) are manual spot-checks from
live testing sessions **before** this instrumentation existed — labeled
as such, not to be confused with `ai_requests`-derived numbers once
those exist.

## Cross-cutting mechanisms

- **`ADMIN_ONLY_PROVIDERS`** (`backend/app/providers.py`) — providers
  hidden from regular users, visible to admins only. Three distinct
  reasons feed this set, not one policy: `codex`/`grok` because picking
  them spends the admin's real subscription money with no per-user
  visibility; `openrouter` because its free tier is a single **shared**
  daily quota (50 req/day) across every account using the one saved key;
  `mistral` is a deliberately unexplained temporary restriction (user's
  explicit call, 2026-09-09) — revisit if a reason surfaces later.
  Deliberately NOT applied to `gemini`, whose free-tier caps are
  per-model and high enough (500/day on the default Lite model) that
  shared-quota exhaustion isn't a live concern.
- **Manual kill switches** (`*_manually_enabled` in `settings.py`) — lets
  an admin hide a provider from the dropdown without losing its saved
  key/token, e.g. to ride out a subscription quota window. Exists for
  every provider, defaults `True`.
- **Global offline cooldown** (`providers.py`: `is_offline()` /
  `mark_offline()`) — if every configured provider fails, the whole app
  backs off together for a cooldown window rather than each user's
  request hammering dead providers on its own schedule. Shared because
  credentials are global (admin-managed), not per-user.
- **Wikipedia snippet grounding** (`backend/app/wiki.py` +
  `enricher.py`) — for providers in `_CATEGORICAL_PROVIDERS`, the
  enricher resolves the work title to an English Wikipedia article,
  fetches the intro extract (up to ~600 chars), and prepends it to the
  prompt as "GROUNDING CONTEXT". The resolver uses a 1-hour in-memory
  cache, a 1-second global API throttle, 429/5xx retry, title-first
  search, and scoring that strongly prefers exact title matches (+1000)
  and music-specific articles (+200) while penalizing disambiguation
  pages (-300). Implemented 2026-09-11; see `findings.md` for the
  grounded battery results.
- **Known bug, fixed 2026-09-11:** `_llm_openai_compatible()` in
  `backend/app/providers.py` used to crash with `AttributeError` when a
  provider returned `"content": null` (observed with OpenRouter reasoning
  outputs). It now coerces `None` to `""` before `.strip()`.
- **Prompting strategy — three variants, not two** (`backend/app/textutil.py`).
  `apply_provider_rules(prompt, provider, model="")` picks one of:
  - **`plain`** — the stock prompt template, completely unmodified. Used
    for providers not in `_CATEGORICAL_PROVIDERS`: `codex`, `opencode`.
  - **`hardened`** — the stock prompt plus `SINCERITY_RULES` (a soft
    "never invent facts" instruction: omit unknowns, no unverified
    film/TV/commercial claims, prefer verifiable structural facts,
    prefer shorter-truthful over padded) **and**
    `CATEGORICAL_HALLUCINATION_RULES` (the real hardening): an 8-item
    fact-category **allowlist** (year-only, city-only-never-venue,
    certain performers, general style, broad context, certain
    relationships, cover-song artist+year only, 2-3 other notable
    performers name+era only) plus an explicit forbidden list (exact
    dates, venue/studio names, dedicatees, "used in film/TV" claims,
    chart figures); two few-shot **GOOD/BAD examples** built around
    Miles Davis' *Kind of Blue* (GOOD states only year+lineup; BAD
    invents a specific recording date, studio, and a fabricated
    dedication, annotated as "looks natural/confident despite being
    invented"); a mandatory **self-check pass** ("read your drafted
    trivia sentence by sentence... delete or rewrite any sentence that
    resembles the BAD example"); and a **mandatory sentence-slot
    structure** (composer/era → year+city-only → musical character →
    optional certain extras, banning any closing "legacy/beloved"
    filler sentence, with explicit guidance to distinguish "unknown
    artist → decline entirely" from "known artist, unknown track →
    artist-only partial answer"). Applied to the providers in
    `_CATEGORICAL_PROVIDERS` = `{"mistral", "openai", "gemini",
    "openrouter", "ollama", "grok"}`. Built originally for Mistral;
    shipped v1.13.0; brought raw Mistral fabrication down to roughly
    70-90% clean across ~20 live test runs — a measured improvement,
    not a fix. Since 2026-09-11, hardened prompts are also prefixed with
    a Wikipedia snippet grounding excerpt when a relevant English article
    is found (see "Wikipedia snippet grounding" above).
  - **`hardened + anti-loop`** — the hardened variant plus
    `_GPT_OSS_ANTI_LOOP_RULES`, applied *only* when `provider == "ollama"`
    **and** the configured model starts with `gpt-oss` — tells the model
    to stop deliberating after one pass, addressing a specific observed
    failure mode (see the ollama section below) where that model family
    burns its entire token budget on internal reasoning and never emits
    a response.
  - `_CATEGORICAL_PROVIDERS` in `textutil.py` is the single source of
    truth for which bucket a provider is in — check there, not this
    file, if this taxonomy might have drifted.

## codex (ChatGPT)

**Consumption model:** subscription-backed API — spends the admin's
personal ChatGPT subscription, not a metered API key.

**Prompting strategy:** `plain` — not in `_CATEGORICAL_PROVIDERS`, gets
the stock prompt unmodified. (Untested/assumed low fabrication risk
given subscription-tier model quality, not empirically verified in this
investigation — don't treat "plain" as evidence it's been checked.)

**Access:** admin-only. Manual kill switch available.

**Reliability / Speed:** no `ai_requests` data yet (instrumentation
added 2026-09-10) and no manual spot-check on record either — least
-documented provider in this file. Expand when next touched.

## grok

**Consumption model:** subscription-backed API in one mode, personal
paid xAI API key in the other — both modes tied to the admin's own money,
which is why both are admin-only, not just the subscription path.

**Prompting strategy:** `hardened` — in `_CATEGORICAL_PROVIDERS`.

**Access:** admin-only, both modes. Manual kill switch available.

**Reliability / Speed:** no `ai_requests` data yet, no manual spot-check
on record. Expand when next touched.

## mistral

**Consumption model:** free API key (no card, phone verification only).

**Prompting strategy:** `hardened` — this is the provider
`CATEGORICAL_HALLUCINATION_RULES` was originally built for (see
Cross-cutting section). Raw/unhardened output invented wrong dedicatee
names and fabricated venues/nicknames/"used in film" claims on
well-documented classical repertoire.

**Model:** `open-mistral-nemo` (12B), silently aliased by Mistral itself
to `ministral-8b-2512` — confirmed live, not assumed. **Not**
`mistral-small-latest`: a live key check found Small gated to 0
requests/minute on the free "Experiment" tier, while Nemo and the
Ministral 3B/8B family get real quota (625K-1.3M tokens/min).

**Access:** genuinely free, not tied to anyone's personal paid
subscription (unlike codex/grok) — but currently admin-only anyway per
explicit user request 2026-09-09, reason unstated. See
`ADMIN_ONLY_PROVIDERS` above.

**Reliability:** `ai_requests` snapshot 2026-09-11: 100% success, n=17.

**Speed:** `ai_requests` median 1,741ms, p90 2,297ms (2026-09-11).
Manual spot-checks pre-instrumentation were ~1-3s. Timeout set to 30s
(the app's baseline default).

**Accuracy:** fact-check battery 2026-09-11: correct on well-documented
classical/jazz tracks; invented vague/1970s-implied details for Maria
Muldaur's "Empty Bed Blues" and the obscure Kora Jazz Trio live cover.
Grounded re-run 2026-09-11: 4/4, all grounded, no invented dates on the
less-documented tracks; still generic on the obscure live cover but
factually safe. The retrieved grounding source resolved the main
fabrication path.

**Known limitation, confirmed live:** Mistral's real-time `web_search`
tool is NOT available on the plain `chat/completions` endpoint this app
calls — only on their separate Conversations/Agents API (different
endpoint shape). Not integrated; would need a dedicated, non-shared
integration if pursued. Unresolved: exact response envelope, free-tier
eligibility, added latency.

## opencode

**Consumption model:** free packaged executable — a bundled local
CLI/agent, no API key at all. Architecturally different from every
other provider here: a coding-agent CLI (`OpencodeSession` in
`providers.py`), proxied through the app on a local port and spawned on
demand, not a stateless `chat/completions` call to a small model
answering from frozen parametric memory.

**Prompting strategy:** `plain` — not in `_CATEGORICAL_PROVIDERS`, no
categorical allowlist, no mandatory structure, no few-shot examples,
none of the hardening Mistral/NIM need. Deliberately left unhardened
because live testing shows it doesn't need it (see Accuracy below).

**Access:** not admin-only, no manual kill switch restriction beyond the
standard toggle.

**Reliability:** `ai_requests` snapshot 2026-09-11: 100% success, n=14.

**Speed:** `ai_requests` median 21,141ms, p90 61,259ms (2026-09-11).
Manual observation pre-instrumentation: user's own framing is "takes
FOREVER." The binding constraint is latency, not accuracy. The 90s
fact-check battery timeout was exceeded on `kindofblue` in one run.

**Accuracy:** fact-check battery 2026-09-11 plus 3 earlier independent
live test runs (see `findings.md` and the memory file
`mradio_ai_veridicity_investigation.md` for full detail): consistently the
most accurate provider, including correct identification of obscure
recordings and the only provider to correctly cite Bessie Smith's 1928
origin for "Empty Bed Blues" without inventing a date for Muldaur's
version. The one prior error was a subtle album/date-conflation (two real
Maria Muldaur albums fused), not wholesale invention. Grounded re-run
2026-09-11: 4/4, all within the 90s timeout, still accurate without
receiving Wikipedia grounding (it is a `plain` provider). OpenCode is the
accuracy benchmark; the question is how to use it without paying its
latency on every request.

**Open hypothesis, not yet confirmed:** OpenCode's own agent loop may
have real tool access (web fetch/search) baked into its execution model,
which plain API-key providers structurally don't get — would explain
both the accuracy (can actually check facts) and the slowness (a real
search-and-verify loop costs wall-clock time a single forward pass
doesn't). Circumstantial support: the one observed error was two real
facts merged incorrectly, not invention from nothing — consistent with a
retrieval-capable system misusing real sources rather than a purely
parametric model confabulating. Next step to confirm: check
`OpencodeSession`'s actual tool/capability surface in `providers.py`, or
ask OpenCode directly what tools it has.

## ollama (self-hosted)

**Consumption model:** self-hosted, on the user's own GPU (P5000). Not a
hosted/API-key provider — no quota or billing concerns, but bound by
local hardware speed and whatever models have been pulled.

**Prompting strategy:** `hardened` for every model; `hardened +
anti-loop` specifically when the configured model starts with
`gpt-oss` (see Cross-cutting section for why — that model family was
observed burning its whole token budget on internal deliberation
without emitting a response).

**Access:** not admin-only.

**Reliability:** `ai_requests` snapshot 2026-09-11 has no Ollama rows
yet (self-hosted, lower traffic).

**Speed:** fact-check battery 2026-09-11: `gpt-oss:20b` median ~25s
(`ollama_timeout` 75s); `qwen3:14b` median ~58s. Pre-instrumentation
manual spot-checks: `qwen3:14b` — 47.5s; `gpt-oss:20b` — 32.6s.

**Accuracy:** fact-check battery 2026-09-11: `gpt-oss:20b` gave a
correct, clean decline on the obscure track and acceptable facts on the
well-known tracks. `qwen3:14b` was slow and hallucinated on "Empty Bed
Blues" (claimed it was a 1977 track from *Midnight at the Oasis*). Prior
manual fact-check: `qwen3:14b` had been the only provider to decline a
dedicatee it didn't know; `gpt-oss:20b` invented a venue and wrong date.
Grounded re-run 2026-09-11: `gpt-oss:20b` 4/4, all grounded, obscure track
now factually anchored rather than declined; `qwen3:14b` 3/4, still timed
out on "Empty Bed Blues" but got the obscure track right when it did
return. The preference toward `gpt-oss:20b` is now stronger.

## openai (generic OpenAI-compatible slot)

Not a single provider — a generic OpenAI-compatible `chat/completions`
slot (base URL + model + API key, user-configurable). The name in
`PROVIDERS` refers to the API shape, not literally OpenAI-the-company.
Any provider exposing this shape works via this slot with zero code
changes, per `findings.md`'s research — only gets promoted to a
dedicated provider entry (own fields, own `PROVIDERS` slot, i18n) if it
needs to coexist *alongside* whatever's already pointed at this slot
(this is how Gemini got its own slot, 2026-09-08). See the **nim**
section below for what's actually configured in this slot today.

**Prompting strategy:** `hardened` — in `_CATEGORICAL_PROVIDERS` under
the name `openai`.

## gemini

**Consumption model:** free API key, not tied to anyone's personal paid
subscription — not admin-only (unlike codex/grok).

**Prompting strategy:** `hardened` — in `_CATEGORICAL_PROVIDERS`.

**Model:** `gemini-3.5-flash-lite`, not any non-Lite Flash variant.
Confirmed live via the user's own AI Studio rate-limit dashboard: every
non-Lite Flash model on the free tier (2.5/3/3.5/3.6/3.7/3.8) shares one
**20 requests/day** cap (resets midnight Pacific, not rolling) —
trivially exhausted by one or two liner-notes requests. The Lite variants
(3.1/3.5 flash-lite) get **500 RPD** instead on the same free tier, same
account — 25x the headroom.

**Access:** manual kill switch still provided since the daily quota,
while generous, is still finite.

**Reliability:** `ai_requests` snapshot 2026-09-11: 71% success, n=5 —
the only provider in the live snapshot with a visible failure rate. Some
failures are likely the 45s timeout being exceeded by reasoning tokens;
others may be quota-related.

**Speed:** `ai_requests` median 11,629ms, p90 25,695ms (2026-09-11).
Timeout set to 45s, not the 30s baseline — confirmed live that Gemini's
"thinking" reasoning tokens can push a simple reply past 30s; a timeout
here silently falls through to the next provider in the fallback chain
rather than erroring loudly, so this was raised specifically to avoid
that.

**Accuracy:** fact-check battery 2026-09-11: correct on well-documented
tracks; falsely dated Maria Muldaur's "Empty Bed Blues" to "1978 in Los
Angeles" (the recording is on the 2001 album *Richland Woman Blues*).
Grounded re-run 2026-09-11: 4/4, all grounded, no repeat of the 1978 Los
Angeles fabrication; answers stayed close to the Wikipedia excerpt.

**Not yet integrated:** Gemini's built-in `google_search` grounding tool
(`"tools": [{"google_search": {}}]` on the same endpoint already in use).
Flagged in `findings.md`'s research as a promising near-zero-code
grounding option, paired with Wikipedia snippet-injection (see that
file). One live risk noted but not empirically verified: some free-tier
accounts reportedly have grounding requests incorrectly hit the tiny
20/day quota instead of a dedicated search quota.

## openrouter

**Consumption model:** free API key, no card needed.

**Prompting strategy:** `hardened` — in `_CATEGORICAL_PROVIDERS`.

**Model:** `openrouter/free` — OpenRouter's own auto-router, picks among
whichever models are currently free rather than pinning to one model ID.
The free lineup rotates over time (documented behavior, not a guess).

**Access:** admin-only (changed from originally non-admin-only,
2026-09-08) — its free tier is a single **shared** daily quota (50
requests/day, confirmed live) across every account using the one saved
key, not a per-user allowance. 1,000/day once $10 has ever been spent on
the account (doesn't expire). See `ADMIN_ONLY_PROVIDERS` above.

**Reliability:** `ai_requests` snapshot 2026-09-11: 100% mechanical
success, n=5. The `"content": null` crash was fixed 2026-09-11, but the
grounded battery still saw 2/4 empty responses (`muldaur_empty_bed` and
`obscure_trap`), so mechanical reliability under the free auto-router
remains inconsistent.

**Speed:** `ai_requests` median 5,998ms, p90 21,322ms (2026-09-11).
Manual spot-checks pre-instrumentation showed high variance: as fast as
~3s, as slow as 84s. Timeout set to 90s, not the 30s baseline; `max_tokens`
was bumped to match because reasoning tokens count against the same budget.

**Accuracy:** fact-check battery 2026-09-11: content quality is poor.
`muldaur_empty_bed` returned literal `"User Safety: safe"` instead of
JSON. `obscure_trap` misattributed Chan Chan as "a cover of Buena Vista
Social Club's 1996 recording" (wrong year; BVSC recorded it in 1997 and
the song was written by Compay Segundo in 1984). Grounded re-run
2026-09-11: 2/4 empty responses; the two well-known tracks that did
return (`beethoven9`, `kindofblue`) were factually correct and clearly
used the grounding excerpt. The free auto-router's unreliability is now
the bigger problem than fabrication on the tracks it completes.

**Not yet integrated:** OpenRouter's `openrouter:web_search` server tool
(a different, newer mechanism than the free auto-router that failed
above) — attaches to a specific named model, not `openrouter/auto`.
Cost per-search (Perplexity-backed ~$0.005/request or Exa
~$0.007-0.015/request) — not free, unlike the grounding options flagged
for Gemini/Wikipedia.

## nim (NVIDIA NIM)

**Consumption model:** free API key, configured as the hosted default of
 the generic **openai** slot above (not a separate `PROVIDERS` entry).

**Prompting strategy:** `hardened` (inherits the `openai` slot's
 categorical hardening) — live testing found real fabrication risk at
 this model size too. Since 2026-09-11 it also receives Wikipedia snippet
 grounding like every other `hardened` provider.

**Model:** `meta/llama-3.2-11b-vision-instruct` (changed from EOL
 `minimaxai/minimax-m3` 2026-09-11). A live probe of NVIDIA's
 account-enabled models found most catalog entries 404'd for the account;
 of the few that responded, this was the only one that consistently
 returned valid JSON within the timeout. It is a vision-capable instruct
 model but accepts text prompts normally.

**Reliability:** no production `ai_requests` data yet. Grounded battery
 2026-09-11: 4/4 mechanical success, median ~6.5s.

**Accuracy:** grounded battery 2026-09-11: 4/4 factually correct,
 including an explicit, grounded Kind of Blue answer that named the 1959
 release and the correct key sidemen (Coltrane, Adderley, Evans). Before
 Wikipedia grounding it had shown the same fabrication risk as other small
 hosted models.

## Not yet coded / research-only

Ideas researched in `findings.md` but not implemented — do not assume
these exist in the app:

- Gemini's `google_search` grounding tool (see gemini section above).
- OpenRouter's `web_search` server tool (see openrouter section above).
- Self-consistency/voting and critic-pass verification — researched and
  judged secondary: valuable as a confidence *signal* (flag disagreement
  across samples/providers), not a primary fix; a critic pass without
  real retrieved evidence to check against suffers confirmation bias.

## Template for a new provider section

```
## <provider name>

**Consumption model:** subscription API / free API key / self-hosted / free packaged executable — and why.
**Prompting strategy:** plain / hardened / hardened+anti-loop, referencing textutil.py's _CATEGORICAL_PROVIDERS.
**Model:** which one, and why (confirmed live vs. assumed).
**Access:** admin-only or not, and why.
**Reliability:** ai_requests-derived success rate, or "no data yet."
**Speed:** ai_requests-derived latency, or a labeled manual spot-check.
**Accuracy:** manual fact-check verdict + sample size, pointer to findings.md.
**Known issues / limitations:** confirmed live, not guessed.
**Not yet integrated:** ideas on the table, pointer to findings.md.
```
