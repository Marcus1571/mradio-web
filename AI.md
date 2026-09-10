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
  verdict and sample size.

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
    not a fix.
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

**Reliability:** no `ai_requests` data yet.

**Speed:** manual spot-check, pre-instrumentation — fastest provider
tested, ~1-3s. Timeout set to 30s (the app's baseline default).

**Accuracy:** manual fact-check, ~20 live test runs — hardened version
roughly 70-90% clean (a measured improvement over raw, not a fix). Raw
(unhardened) output had confirmed fabrication on niche classical facts;
see the Cross-cutting hardening entry above for the specific failure
modes observed.

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

**Reliability / Speed:** no `ai_requests` data yet. Manual observation,
pre-instrumentation: user's own framing is "takes FOREVER" — the binding
constraint on this provider is latency, not accuracy, but no numeric
figure has been logged. This is exactly the gap the new instrumentation
is meant to close — check `ai_stats` output once real traffic has
accumulated for an actual number here.

**Accuracy:** manual fact-check, 3 independent live test runs (see
`findings.md` and the memory file `mradio_ai_veridicity_investigation.md`
for full detail) — 2 completely clean across dense multi-paragraph
answers, 1 with a single subtle album/date-conflation error (two real
Maria Muldaur albums from different years fused into one citation; not
wholesale invention). Meaningfully more accurate, unprompted, than
Mistral's raw (unhardened) output, with zero prompt scaffolding.

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

**Reliability / Speed:** no `ai_requests` data yet. Manual spot-checks,
pre-instrumentation, two models tested: `qwen3:14b` — 47.5s. `gpt-oss:20b`
— 32.6s (faster, but see Accuracy below).

**Accuracy:** manual fact-check. `qwen3:14b` — mostly accurate, and
notably the *only* provider across this whole investigation observed to
correctly decline to guess a dedicatee it didn't know rather than
inventing one (best-behaved result on that specific axis, any provider).
`gpt-oss:20b` — worse: wrong date (both day and year), invented a venue
name.

Revisit which model is the app's effective default before relying on
this section being current — not confirmed in `settings.py` as of this
writing.

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

**Reliability:** no `ai_requests` data yet.

**Speed:** manual spot-check, pre-instrumentation, one test run only.
Timeout set to 45s, not the 30s baseline — confirmed live that Gemini's
"thinking" reasoning tokens can push a simple reply past 30s; a timeout
here silently falls through to the next provider in the fallback chain
rather than erroring loudly, so this was raised specifically to avoid
that.

**Accuracy:** one clean live test on a Beethoven trivia prompt — fully
correct facts including a real, correctly-attributed Wagner quote about
that specific symphony. Only one test run logged so far — not yet a
reliable sample size, unlike OpenCode's 3.

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

**Reliability:** no `ai_requests` data yet. Known failure mode, confirmed
live: on one test run, the auto-router landed on a reasoning model that
burned its entire token budget on visible chain-of-thought (obsessively
re-counting its own draft's character length) and never produced a
final JSON answer at all — logged as a failure, not a slow success. Not
a one-off fluke — documented behavior class for some reasoning models
under tight token budgets, not specific to this app.

**Speed:** manual spot-check, pre-instrumentation — a live
provider-comparison battery (2026-09-09) found the free lineup's working
models are reasoning models with real variance: as fast as ~3s with
categorical hardening applied, but the auto-router was observed taking
84s on one run with that same hardening. Timeout set to 90s, not the 30s
baseline, specifically because a shorter timeout would have discarded a
correct, complete answer; `max_tokens` was bumped to match (reasoning
tokens count against the same budget as content).

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
this model size too.

**Reliability:** no `ai_requests` data yet, but see the known issue
below — reliability at the account level is currently poor regardless
of prompt hardening.

**Known issue, confirmed live 2026-09-10:** the app's own default model
(`minimaxai/minimax-m3`) reached end-of-life hours before that session's
testing (HTTP 410). Most other models on the test account either 404'd
("not found for account") or hung/timed out (30-90s) even on trivial
prompts. Inconclusive whether that's account-tier gating or a genuine
service issue — not resolved. **The app's default model needs fixing**
independent of this investigation; not yet done as of this writing.

## Not yet coded / research-only

Ideas researched in `findings.md` but not implemented — do not assume
these exist in the app:

- Wikipedia snippet-injection grounding. `backend/app/wiki.py` already
  calls the MediaWiki Action API with `exintro=1&explaintext=1&exchars=600`
  for relevance-matching, then discards the text, keeping only the
  article title. Research agent's top-ranked recommendation (near-zero
  cost, no new dependency) — one return-value change would turn this into
  real injectable grounding context.
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
