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
- **SINCERITY_RULES prompt hardening** (`backend/app/textutil.py`) —
  categorical allowlist + mandatory sentence-slot structure + few-shot
  GOOD/BAD examples + self-check pass + explicit "OK to say you don't
  know" escape hatch. Built for Mistral, also applied to NIM. Shipped in
  v1.13.0; brought raw Mistral fabrication down to roughly 70-90% clean
  across ~20 live test runs — a measured improvement, not a fix.
  `_CATEGORICAL_PROVIDERS` in `textutil.py` is the source of truth for
  which providers currently get this treatment.

## codex (ChatGPT)

Admin-only (spends the admin's personal ChatGPT subscription). Manual
kill switch available. Otherwise undocumented here — expand this section
when its config/strategy is next touched.

## grok

Admin-only, both API-key and subscription modes (API-key mode is still
tied to the admin's own paid xAI account). Manual kill switch available.
Otherwise undocumented here — expand this section when its config/
strategy is next touched.

## mistral

**Model:** `open-mistral-nemo` (12B), silently aliased by Mistral itself
to `ministral-8b-2512` — confirmed live, not assumed. **Not**
`mistral-small-latest`: a live key check found Small gated to 0
requests/minute on the free "Experiment" tier, while Nemo and the
Ministral 3B/8B family get real quota (625K-1.3M tokens/min).

**Tier:** genuinely free, no card needed (phone verification only). Not
admin-only — not tied to anyone's personal paid subscription (unlike
codex/grok). Currently admin-only anyway per explicit user request
2026-09-09, reason unstated — see `ADMIN_ONLY_PROVIDERS` above.

**Accuracy strategy:** gets full `SINCERITY_RULES` hardening (see
Cross-cutting section) — raw model invented wrong dedicatee names,
fabricated venues/nicknames/"used in film" claims on well-documented
classical repertoire. Hardened version is what's in production
(v1.13.0+).

**Known limitation, confirmed live:** Mistral's real-time `web_search`
tool is NOT available on the plain `chat/completions` endpoint this app
calls — only on their separate Conversations/Agents API (different
endpoint shape). Not integrated; would need a dedicated, non-shared
integration if pursued. Unresolved: exact response envelope, free-tier
eligibility, added latency.

**Timeout:** 30s (the app's baseline default).

## opencode

Bundled local CLI/agent, genuinely free, no API key. Architecturally
different from every other provider — a coding-agent CLI
(`OpencodeSession` in `providers.py`), proxied through the app on a local
port and spawned on demand, not a stateless `chat/completions` call to a
small model answering from frozen parametric memory.

**Accuracy strategy:** none applied — no categorical allowlist, no
mandatory structure, no few-shot examples, none of the `SINCERITY_RULES`
scaffolding Mistral/NIM need. Deliberately left unhardened because live
testing (see `findings.md` and the memory file
`mradio_ai_veridicity_investigation.md`) shows it doesn't need it: 3
independent fact-checked test runs so far, 2 completely clean, 1 with a
single subtle album/date-conflation error (not wholesale invention).
Meaningfully more accurate, unprompted, than Mistral's raw (unhardened)
output.

**Known cost:** latency. User's own framing: "takes FOREVER." Not yet
measured/logged numerically — treated as the binding constraint on this
provider, not accuracy.

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

Self-hosted on the user's own GPU (P5000). Not a hosted/API-key
provider — no quota or billing concerns, but bound by local hardware
speed and whatever models have been pulled.

**Models tested live:** `qwen3:14b` — slow (47.5s) but mostly accurate,
and notably the *only* provider observed to correctly decline to guess a
dedicatee it didn't know rather than inventing one (best-behaved result
on that specific axis, across every provider tested). `gpt-oss:20b` —
faster (32.6s) but worse accuracy (wrong date, both day and year;
invented a venue name).

No hardening applied. Revisit which model is the app's effective default
before relying on this section being current — not confirmed in
`settings.py` as of this writing.

## openai (generic OpenAI-compatible slot)

Generic OpenAI-compatible `chat/completions` slot (base URL + model +
API key, user-configurable) — not literally OpenAI-the-company; the name
in `PROVIDERS` refers to the API shape. Any provider exposing this shape
works via this slot with zero code changes, per `findings.md`'s research
— only gets promoted to a dedicated provider entry (own fields, own
PROVIDERS slot, i18n) if it needs to coexist *alongside* whatever's
already pointed at this slot (this is how Gemini got its own slot,
2026-09-08).

## gemini

**Model:** `gemini-3.5-flash-lite`, not any non-Lite Flash variant.
Confirmed live via the user's own AI Studio rate-limit dashboard: every
non-Lite Flash model on the free tier (2.5/3/3.5/3.6/3.7/3.8) shares one
**20 requests/day** cap (resets midnight Pacific, not rolling) —
trivially exhausted by one or two liner-notes requests. The Lite variants
(3.1/3.5 flash-lite) get **500 RPD** instead on the same free tier, same
account — 25x the headroom.

**Tier:** genuinely free, not tied to anyone's personal paid
subscription — not admin-only (unlike codex/grok). Manual kill switch
still provided since the daily quota, while generous, is still finite.

**Timeout:** 45s, not the 30s baseline — confirmed live that Gemini's
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

**Model:** `openrouter/free` — OpenRouter's own auto-router, picks among
whichever models are currently free rather than pinning to one model ID.
The free lineup rotates over time (documented behavior, not a guess).

**Tier:** free, no card needed. Admin-only (changed from originally
non-admin-only, 2026-09-08) — its free tier is a single **shared** daily
quota (50 requests/day, confirmed live) across every account using the
one saved key, not a per-user allowance. 1,000/day once $10 has ever been
spent on the account (doesn't expire). See `ADMIN_ONLY_PROVIDERS` above.

**Timeout:** 90s, not the 30s baseline — a live provider-comparison
battery (2026-09-09) found the free lineup's working models are
reasoning models with real variance: as fast as ~3s with categorical
hardening applied, but the auto-router was observed taking 84s on one
run with that same hardening. A shorter timeout would have discarded a
correct, complete answer. `max_tokens` was bumped to match — reasoning
tokens count against the same budget as content.

**Known failure mode, confirmed live:** on one test run, the auto-router
landed on a reasoning model that burned its entire token budget on
visible chain-of-thought (obsessively re-counting its own draft's
character length) and never produced a final JSON answer at all. Not a
one-off fluke — this is a documented behavior class for some reasoning
models under tight token budgets, not specific to this app.

**Not yet integrated:** OpenRouter's `openrouter:web_search` server tool
(a different, newer mechanism than the free auto-router that failed
above) — attaches to a specific named model, not `openrouter/auto`.
Cost per-search (Perplexity-backed ~$0.005/request or Exa
~$0.007-0.015/request) — not free, unlike the grounding options flagged
for Gemini/Wikipedia.

## nim (NVIDIA NIM)

Uses the generic OpenAI-compatible slot's hosted default. Gets the same
`SINCERITY_RULES` hardening as Mistral (see Cross-cutting section) — live
testing found real fabrication risk at this model size too.

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

**Model:** which one, and why (confirmed live vs. assumed).
**Tier:** free/paid, admin-only or not, and why.
**Accuracy strategy:** hardened or not, what testing shows.
**Timeout:** if non-default, why.
**Known issues / limitations:** confirmed live, not guessed.
**Not yet integrated:** ideas on the table, pointer to findings.md.
```
