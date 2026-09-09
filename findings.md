# Findings

Research log for options considered but not (yet) built — one entry per
question researched, with the verdict and why. Not a full history;
`STATUS.md`/`CHANGELOG.md` cover what actually shipped.

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
