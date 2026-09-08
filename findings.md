# Findings

Research log for options considered but not (yet) built — one entry per
question researched, with the verdict and why. Not a full history;
`MEMORY.md`/`CHANGELOG.md` cover what actually shipped.

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

Candidates found, not yet tried against real stations:

- **Google Gemini (AI Studio)** — genuinely free, permanent tier (not a
  trial), no credit card required. As of April 2026 only Flash-family
  models (Flash, Flash-Lite) remain on the free tier; Pro models moved
  behind billing. OpenAI-compatible endpoint at
  `https://generativelanguage.googleapis.com/v1beta/openai/`. Rate
  limits are modest (roughly 10-15 RPM, up to 1,000 RPD on Flash) but
  comfortably enough for this app's one-track-at-a-time enrichment
  pattern.
- **Groq** — free tier, ~1,000 requests/day, no credit card. Notably
  fast (300+ tokens/sec, hardware-accelerated inference). OpenAI-
  compatible.
- **Cerebras** — free tier, ~1M tokens/day, very fast. Email-only
  signup reported by most sources, though at least one source flagged
  a possible payment-method requirement at signup — verify before
  committing to it as the "no card needed" pick.
- **OpenRouter** — one API key routes to 20+ free-tier models across
  multiple underlying providers via one OpenAI-compatible endpoint.
  Convenient for trying several models without separate signups per
  provider, at the cost of being a proxy layer (adds a hop, and free-
  model availability on OpenRouter can change without notice).

**Verdict**: no action taken yet — presented as options, not built.
None independently verified against this app's actual liner-notes
prompt/JSON-schema requirement (the same verification opencode/Ollama/
NIM/ChatGPT/Grok all got via `run_provider_test()` and/or a live
4-way timing comparison) — do that before recommending one as a
default the way the 0.5.25 comparison drove the ChatGPT/opencode/
Ollama/NIM preference order.

**How to apply if revisited**: for a quick try, just repoint the
existing NIM/OpenAI-compatible bubble's base URL + key at one of these
and use the Test button — no code change needed. For a permanent,
side-by-side-with-NIM addition, follow the Grok build's pattern
(`MEMORY.md`'s "Grok (xAI) added as 5th AI provider" section) as the
template for a new dedicated bubble.
