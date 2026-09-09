# AGENTS.md — mradio-web

Permanent rules for working in this project. Changes rarely — this is not where
current status lives (see `STATUS.md`) or where research findings live (see
`findings.md`).

This file is part of the operator's cross-project governance system — see
`~/governance/GOVERNANCE.md` for how it fits together, and `~/governance/USER.md`
for rules that apply here *and* on every other project (do not duplicate those
here; if a rule from `USER.md` seems relevant, just follow it, don't restate it).

## Verification discipline

**Never declare a UI/CSS change complete based on `npm run build` or lint passing
alone.** Neither renders the page. Actually launch the app (local dev server or the
real deployment) and look at the rendered result — Playwright screenshot against a
real running instance is the default method, or ask the operator to look — before
reporting a visual change as done. This applies to anything touching JSX/CSS/layout:
new components, buttons, badges, spacing, box-model changes. A passing TypeScript
build has shipped visually broken UI to production before in this project; treat
that as the standing proof this step is required, not optional.

If no screenshot MCP tool is available, check for a local fallback before falling
back to hand-computed guesses about layout: `chromium`/`google-chrome` on PATH, an
installed `Google Chrome.app`, or `npx playwright --version`. If any resolve, build
a small static HTML fixture that links the real CSS/component source with realistic
sample content and screenshot it. `boundingBox()` on real rendered elements gives
exact pixel measurements — more reliable than computing box heights from design
tokens by hand. Clean up any throwaway fixture/script afterward; it's scratch
tooling for the session, not something to commit.

## Internationalization (16 languages)

This app supports 16 languages:
`frontend/src/i18n/{en,es,fr,it,pt,de,nl,sv,nb,da,tr,ru,el,he,ja}.ts`. **Any change
that adds or changes user-facing text must update all of them, not just `en.ts`.**
TypeScript's `Dict` type (derived from `en.ts` via `Widen<T>` in `i18n/index.ts`)
will fail the build if a non-English file is missing a key — treat that build
failure as the correctness net it is.

Checklist for adding a new (17th+) language:
1. New `frontend/src/i18n/<code>.ts`, `Dict`-typed, mirroring `en.ts`'s key shape.
2. `frontend/src/i18n/index.ts` — add to the `Language` union, `LANGUAGES` array
   (flag + label), and the `DICTS` record.
3. `frontend/src/api/types.ts` — add the code to `Config.language`'s union.
4. `backend/app/routers/config.py` — add the code to `_VALID_LANGUAGES`.
5. `backend/app/enricher.py` — add a `_LANGUAGE_INSTRUCTIONS` entry (one line
   asking the LLM to write "trivia" in that language; keep `"wiki"` always-English,
   matching the existing entries' wording pattern).
6. `Dashboard.tsx`'s language-fallback logic validates against `LANGUAGES`
   generically already — it should not need editing for new languages. If it does,
   that's a regression, not a place to add another special case.
7. If the new language is right-to-left (Arabic, Persian, Urdu, etc.), set
   `rtl: true` on its `LANGUAGES` entry — `applyDirection(lang)` already handles the
   rest automatically.

The AI trivia cache (`cache.py`, `provider::language::raw_title` key) generalizes
per-language with zero code changes — confirmed repeatedly, no action needed there.

## README ↔ KB.md cross-linking

`README.md` must stay cross-linked to `KB.md`, not just contain one bare link.
Pattern to maintain: a top-of-file nav line, an early "full detail lives in KB.md"
pointer, deep links to specific `KB.md#section-slug` anchors next to the feature
bullet they explain, a full section-by-section link list under "Getting started,"
and a closing call-to-action link back to the KB. Whenever a feature gets its own
`KB.md` section, add or update the matching `README.md` link in the same change —
don't let the two drift apart. GitHub's heading-anchor slugging (lowercase, strip
periods/parens, spaces→hyphens) is the rule to follow when writing new deep links;
spot-check unusual punctuation after pushing.

## KB.md and public docs must stay generic

`KB.md` and any similar public-facing deployment doc must read as something a
stranger could follow: no personal infra nicknames, no real LAN IPs, no real
domains, no personal container/stack names. Use placeholders: "the server," "your
Unraid instance," `192.168.1.10`, `radio.example.com`, "an existing Ollama/NIM setup
you already run." Real deployment specifics belong in the operator's private notes,
never in a committed doc.

## Architecture decisions worth knowing (and why)

- **No self-update mechanism.** A container has no business self-modifying its own
  image; `git pull && docker compose build` is the update path. GitHub Releases are
  decorative here — nothing in the app reads them.
- **No mpv, no server-side audio.** Playback is the browser's own `<audio>` element;
  ICY "now playing" metadata is parsed directly out of proxied stream bytes
  (`backend/app/icy.py`).
- **Every station goes through `GET /api/stream`, not just HTTP-only ones** — one
  code path instead of per-station branching, since browsers block HTTP audio from
  an HTTPS page. Carries an SSRF guard (`backend/app/routers/stream.py`): the proxy
  fetches user-supplied URLs server-side, so it refuses private/loopback/link-local
  targets.
- **Multi-user with real accounts** — SQLite, PBKDF2 password hashing, server-side
  sessions (not JWT, chosen specifically so a session can be revoked outright), and
  per-user JSON files for favorites/config under `/data/users/<id>/`.
- **AI provider credentials are global (admin-managed); which provider is active is
  per-user.** Decided explicitly, reversing an earlier per-user-credentials attempt
  mid-build — nobody should need their own NIM key or Ollama URL, they pick from
  what's configured. `backend/app/settings.py` + admin-only `/api/settings/ai`.
- **The AI trivia cache is shared across all users**, keyed by
  `provider::raw_title` — same track means same answer regardless of who asked
  first. `raw_title` must be the *unparsed* ICY string (artist+track together), not
  a separate artist field, to avoid same-title collisions across different artists.
- **opencode is bundled in the Docker image**, not left to the admin to install — a
  `node:22-slim` build stage fetches the self-contained native binary, only it gets
  copied into the final image. Version pinned via a Dockerfile `ARG`, not `@latest`;
  `.github/workflows/bump-opencode.yml` opens a PR (never auto-merges) when a newer
  `opencode-ai` is published.
- **Design system**: custom OKLCH palette + Newsreader/Hanken Grotesk/IBM Plex Mono,
  picked via the Hallmark skill (`.hallmark/log.json` has the formal record) —
  deliberately avoiding the generic-AI-output look. It's an app dashboard, not a
  marketing page, so it doesn't follow a Hallmark landing-page macrostructure; the
  token/typography/motion discipline carried over, the page shape didn't.

## Deliberately not done (and why)

- **No DB migration tooling.** The SQLite schema has only grown additively
  (`backend/app/db.py`); revisit only if a column ever needs to change shape.
- **No committed test suite.** Verified with ad-hoc scripts during development (fake
  ICY/OpenAI-compatible servers, direct FastAPI-app calls, live Playwright runs),
  none checked into the repo. `pytest`/`vitest` are not set up — don't look for a
  test command that doesn't exist yet.
- **No `Makefile` / `install.sh`.** No single-command bootstrap; see `STATUS.md`'s
  "Local development" section for the actual two-terminal setup.

## Release process

Full sequence, run straight through per `~/governance/USER.md`'s no-confirmation-
prompts rule: bump version → add `CHANGELOG.md` entry → build/lint/test green →
commit → `git tag vX.Y.Z` + push tag → publish the GitHub Release (assets + notes,
verify it shows as "Latest") → push `main`. A bare git tag without a published
GitHub Release does not count as shipped.

Doc-sync check before considering any bug fix, feature, or release "done" — verify
all of these against what actually changed, not just the one that feels obviously
relevant:
- `STATUS.md` — does the current-state snapshot still match reality?
- `CHANGELOG.md` — does this change have an entry, if release-worthy?
- `KB.md` — did any setup step, config option, env var, or admin-facing behavior
  change? Update every affected section, not just the one prompted directly — if one
  AI provider's section gets a new setup note, audit whether sibling providers need
  the same treatment.
- `README.md` — does this change alter what a first-time reader understands the app
  to *be* or *do*? A new major feature or changed pitch qualifies even if not asked
  for by name.

## Curated/user-owned data

Never add curated items (e.g. default station lists) on the agent's own initiative —
the operator personally approves every one. User-owned data files are never touched
by releases.

## Never run the operator's own update/installer for them

After cutting a release, commit and push — the operator updates their own running
instance. Don't "fix" a missing feature by installing it locally on their behalf.
