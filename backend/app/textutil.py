"""Pure text-processing helpers used by the Enricher, ported verbatim from
mradio: fixing mis-decoded ICY titles, splitting "Artist - Title
(Performer)" tags, trimming AI output to length, and pulling a JSON object
out of an LLM reply that may not be perfectly clean JSON."""

import json
import re

SINCERITY_RULES = (
    "\n\nHARD TRUTHFULNESS RULES (never violated):\n"
    "- Never invent facts. If a specific fact is not known to you with "
    "confidence - premiere date, dedicatee, film/TV/commercial appearances, "
    "notable recordings, performers, orchestras, awards - OMIT it; never hedge "
    "with a plausible guess.\n"
    "- Never claim a piece appears in a film, TV show, or commercial unless "
    "you are certain it does.\n"
    "- Prefer verifiable structural facts: composer dates and nationality, the "
    "catalogue/opus exactly as given in the tag, genre, movement titles.\n"
    '- "wiki": return the exact article title ONLY if confident the article '
    'exists; otherwise "".\n'
    "- Never mention or discuss any composer, performer, or work other than "
    "the one in the tag; if a drafted sentence drifts to someone else it is a "
    "defect - delete or rewrite it.\n"
    "- Length is secondary to truth: a shorter trivia built only from confident "
    "facts is better than a padded one. About 450 characters of true content "
    "fully satisfies the task; never pad with unverified color."
)


# Originally built Mistral-specific, extended to openai (NIM) and
# gemini on 2026-09-09 after a live provider-comparison battery showed
# BOTH of them fail the exact same hallucination trap Mistral did — a
# fabricated nonexistent artist/track — despite Gemini having zero
# hardening at the time and NIM only having the weaker SINCERITY_RULES.
# Gemini in particular did excellently on well-documented material
# (correct facts, even a real Wagner quote) but invented a complete
# fake biography, discography-sounding details, and a fake genre for a
# made-up composer/track — proof that "good on famous things" and
# "safe on obscure/unknown things" are different, uncorrelated
# properties, and every non-self-hosted provider needs the categorical
# hardening below, not just whichever one happened to fail a spot-check
# first. Arrived at by iterating live against the real API (2026-09-09),
# well beyond SINCERITY_RULES alone. Three escalating findings, in
# order:
#
# 1. A soft "only state confident facts" instruction (SINCERITY_RULES'
#    own approach, and an early "confidence-gating" variant of this
#    rule) still let precise-sounding wrong details slip through -
#    restricting by FACT CATEGORY (year not exact date, city not venue,
#    general character not specific anecdotes) worked far better than
#    restricting by confidence level, in isolated free-text tests.
#
# 2. That categorical allowlist, appended AFTER the shared
#    _PROMPT_TEMPLATE's own "aim for 750-850 characters" instruction,
#    mostly failed against the REAL app prompt (JSON output + all its
#    other rules) - the model reliably prioritized hitting the length
#    target over the later constraint, padding with fabricated
#    conductor names/venues/anecdotes in roughly 1 of every 3 runs.
#    Neither moving the rule earlier in the prompt, nor a "the target
#    doesn't apply, write shorter instead" override, nor an explicit
#    "max 4 sentences" cap fixed this on their own - the model ignored
#    sentence caps outright and kept finding new plausible-sounding
#    categories (vague "used in celebrations/soundtracks" claims,
#    invented nicknames) not explicitly on the forbidden list.
#
# 3. What actually worked, combined: (a) REPLACING the base template's
#    length instruction outright (see the .replace() call below - a
#    conflicting instruction left in the prompt keeps winning even when
#    a later one says to ignore it), (b) two worked GOOD/BAD few-shot
#    examples showing exactly what fabrication looks like even when it
#    sounds professional, (c) a self-check pass asking the model to
#    re-read its own draft sentence-by-sentence, and (d) - the biggest
#    lever - a MANDATORY SENTENCE-SLOT structure (composer/era, then
#    year+city ONLY, then musical character, then one optional certain
#    fact) with an explicit ban on any closing "legacy/popularity/
#    beloved" sentence, since that summary sentence was consistently
#    where fabrication snuck back in even after (a)-(c).
#
# One real regression found and fixed during this: the mandatory-slot
# structure alone made it WORSE on a true unknown (a fabricated
# artist/track used as a hallucination trap) - forcing slots removed
# the model's ability to say "I don't know," so it fabricated a full
# fake biography to fill them. Fixed by explicitly stating that
# skipping every slot for a genuinely unrecognized artist/work is a
# valid, required answer, not a fallback to avoid.
#
# Net result across the final version, tested live: 3-4 clean runs out
# of 4 on a well-documented classical work, 2/2 clean on a
# well-documented jazz album (one run mixed up a real substitute
# pianist for the actual one - a genuinely hard, adjacent-fact error,
# not a fabrication), 4/4 clean on a real but obscure work, and 3/3
# clean (correctly declining) on a fabricated nonexistent track. A
# meaningful, measured improvement over the near-constant fabrication
# seen without this - not a perfect fix; residual risk on genuinely
# thin training data is real and documented here rather than papered
# over.
_CATEGORICAL_LENGTH_OVERRIDE = (
    "The 750-850 character target below does NOT apply to you — ignore "
    "it. Follow the fact-category allowlist and mandatory sentence "
    "structure given after these rules instead."
)

# Applied to mistral, openai (NIM), and gemini — see the comment above
# for why this isn't Mistral-specific despite the name history.
CATEGORICAL_HALLUCINATION_RULES = (
    '\n\nFACT-CATEGORY ALLOWLIST for "trivia" — you may ONLY include '
    "facts from these categories, and only if genuinely certain:\n"
    "  1. Year of composition/release/premiere (year only).\n"
    "  2. City only (never venue/theater/studio name).\n"
    "  3. Real performers/musicians certain to be involved in THIS "
    "specific recording/premiere.\n"
    "  4. General musical style/character.\n"
    "  5. Broad historical/cultural context, no specific events/films.\n"
    "  6. A well-known, certain relationship to another figure "
    "(teacher/mentor/family), specific to THIS work.\n"
    "FORBIDDEN even if plausible: exact dates, ANY specific "
    "venue/theater/studio/hall name (this is the single most common "
    "mistake — when in doubt, name only the CITY and nothing more "
    "specific), dedicatee names, nicknames, anecdotes, "
    "conductor/orchestra names unless certain of THIS specific "
    'premiere, vague "used in film/TV/celebrations/soundtracks" claims '
    "of any kind (even a vague unspecific one), sales/chart figures.\n\n"
    "TWO WORKED EXAMPLES of the exact standard required (study these "
    "before writing your own answer):\n\n"
    "GOOD example (a well-known, well-documented work):\n"
    '"trivia": "Miles Davis released Kind of Blue in 1959, a landmark '
    "modal jazz album featuring John Coltrane, Cannonball Adderley, "
    "Bill Evans, Paul Chambers, and Jimmy Cobb. Its harmonically fluid, "
    'scale-based approach redefined jazz composition."\n'
    "— Why this is GOOD: every fact is a real, well-documented, "
    "certain fact. No venue, no anecdote, no invented nickname, no "
    "unverified \"used in\" claim. Short and entirely true beats long "
    "and partly invented.\n\n"
    "BAD example (do NOT write like this, even though it sounds "
    "professional):\n"
    '"trivia": "Miles Davis recorded Kind of Blue on 2 March 1959 at '
    "Columbia's 30th Street Studio in New York, dedicating the album to "
    "his mentor Charlie Parker. The sessions were legendary for their "
    "spontaneous, one-take magic, and the album's themes have appeared "
    'in countless films and commercials since."\n'
    "— Why this is BAD: the exact session date, studio name, "
    '"dedication," "one-take magic" anecdote, and "films and '
    'commercials" claim are all EXACTLY the kind of specific, '
    "plausible-sounding, unverifiable detail you must never invent — "
    "note how natural and confident this sounds even though most of it "
    "is fabricated. Do not let your own answer sound like this.\n\n"
    "SELF-CHECK before finalizing: read your drafted \"trivia\" "
    "sentence by sentence. For each sentence, ask \"is this exactly "
    'like the GOOD example, or does it smuggle in something like the '
    'BAD example (an exact date, a venue/studio name, a dedicatee, an '
    'anecdote, a "used in" claim)?" Delete or rewrite any sentence that '
    "resembles the BAD example before outputting your final JSON.\n\n"
    'MANDATORY STRUCTURE for "trivia" — write it as EXACTLY these '
    "sentence slots, in this order, skipping any slot you are not "
    "certain of (skipping is REQUIRED when unsure, do not fill a slot "
    "with a guess):\n"
    "SLOT 1 (composer/artist, 1 sentence): who they were, era, "
    "nationality — general facts only, no specific relationships "
    "unless certain.\n"
    'SLOT 2 (year + city, 1 sentence): "[Work] was composed/released '
    'in [year] in [city]." — year and city ONLY, nothing else in this '
    "sentence.\n"
    "SLOT 3 (musical character, 1 sentence): style/character "
    "description only — no claims about reception, fame, or use "
    "elsewhere.\n"
    "SLOT 4 (OPTIONAL — only if you are certain of a specific real "
    "fact not covered by slots 1-3, such as certain real performers on "
    "THIS recording): 1 sentence, or skip entirely.\n"
    "Do NOT add any sentence outside these slots. Do NOT add a "
    'closing/summary sentence about legacy, popularity, "remains a '
    'staple", "beloved by audiences", "associated with", or any '
    "similar filler — these are exactly where fabrication has been "
    "sneaking in. Stop after slot 4 (or slot 3, if slot 4 doesn't "
    "apply) even if this makes trivia shorter than usual.\n\n"
    "CRITICAL: if you do not recognize this artist/work at all, or "
    "have no confident facts about it whatsoever, it is CORRECT and "
    "REQUIRED to skip every slot and write a very short honest trivia "
    'like "No confident details are available about this specific '
    'track." — this is a valid, complete answer. Do NOT invent a '
    "plausible-sounding biography, genre, year, or city for an "
    "artist/work you do not actually recognize. Recognizing a real, "
    "famous artist/work and genuinely not knowing one are different — "
    "only fill slots for facts you are certain of about the ACTUAL, "
    "SPECIFIC artist/work named above, never a generic-sounding "
    "invented substitute."
)


# Providers that get the full categorical-allowlist treatment (see
# CATEGORICAL_HALLUCINATION_RULES' comment) on top of SINCERITY_RULES —
# every non-self-hosted, non-subscription cloud provider tested has
# shown real fabrication on unknown/obscure tracks, not just Mistral.
# openrouter added 2026-09-09 alongside its max_tokens bump (see
# providers.py's llm_openrouter()) — its free lineup's reasoning models
# need every advantage to actually finish within budget, and a shorter
# target (this rule set's real effect, independent of the hallucination
# angle) means less to reason through before emitting real JSON.
# Deliberately NOT applied to codex/grok (subscription-backed, the
# admin's own paid account — not tested for this failure mode this
# session, and a behavior change there is a bigger blast radius given
# real money is involved) or opencode/ollama (self-hosted, no shared
# free-tier quota pressure pushing toward a "must answer" instinct).
_CATEGORICAL_PROVIDERS = frozenset({"mistral", "openai", "gemini", "openrouter"})


def apply_provider_rules(prompt: str, provider: str) -> str:
    """Provider-targeted prompt additions. mistral/openai(NIM)/gemini/
    openrouter get SINCERITY_RULES + CATEGORICAL_HALLUCINATION_RULES +
    a length-target override — see CATEGORICAL_HALLUCINATION_RULES'
    comment for the full story: a competing "aim for 750-850
    characters" instruction earlier in the prompt kept winning against
    a later "ignore that" rule unless the original instruction was
    replaced outright, not just argued with. opencode and ollama keep
    the stock prompt; codex/grok too (see _CATEGORICAL_PROVIDERS)."""
    if provider in _CATEGORICAL_PROVIDERS:
        target = ("Aim for 750-850 characters with a hard "
                  "maximum of 850 — if your draft runs long, tighten it.")
        # Loud failure if _PROMPT_TEMPLATE's wording ever changes —
        # a silent no-op here would leave the conflicting length
        # instruction in place, which live testing showed reliably
        # wins over a same-prompt override (see the comment above
        # CATEGORICAL_HALLUCINATION_RULES).
        assert target in prompt, (
            "textutil.apply_provider_rules: expected length-target "
            "sentence not found in prompt — _PROMPT_TEMPLATE wording "
            "changed; update the .replace() target above to match.")
        prompt = prompt.replace(target, _CATEGORICAL_LENGTH_OVERRIDE)
        return prompt + SINCERITY_RULES + CATEGORICAL_HALLUCINATION_RULES
    return prompt


def repair_mojibake(s: str) -> str:
    for enc in ("cp1252", "latin-1"):
        try:
            fixed = s.encode(enc).decode("utf-8")
            if fixed != s:
                return fixed
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
    return s


def elide(s: str, limit: int = 4000) -> str:
    s = " ".join(s.split())
    if len(s) <= limit:
        return s
    cut = s[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:-") + "…"


def split_title(raw: str) -> tuple[str, str, str]:
    """Split a raw ICY title into (artist, title, performer). Typical
    shape: "Artist - Title (Performer)"."""
    raw = repair_mojibake(raw)
    raw = re.sub(r"\s*\{[^}]*\}", "", raw).strip()
    artist, sep, title = raw.partition(" - ")
    if not sep:
        artist, title = "", raw
    performer = ""
    i = title.find("(")
    if i != -1:
        candidate = title[i:].strip()
        if candidate.endswith(")") and len(candidate) > 2:
            performer = candidate
            title = title[:i].strip()
    return artist, title.strip(), performer


def extract_json_item(raw: str) -> dict:
    """Pull {work, trivia, wiki, movement} out of an LLM reply that's
    supposed to be raw JSON but might be fenced, slightly malformed, or
    (rarely) not JSON at all."""
    item = {"work": "", "trivia": "", "wiki": "", "movement": 0}
    r = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    r = re.sub(r"\s*```$", "", r)
    a, b = r.find("{"), r.rfind("}")
    if a != -1 and b > a:
        try:
            p = json.loads(r[a:b + 1])
            if isinstance(p, dict):
                return {
                    "work": str(p.get("work") or "").strip(),
                    "trivia": str(p.get("trivia") or "").strip(),
                    "wiki": str(p.get("wiki") or "").strip(),
                    "movement": 1 if p.get("movement") == 1 else 0,
                }
        except (json.JSONDecodeError, TypeError):
            pass

    def g(key):
        m = re.search(rf'"{re.escape(key)}"\s*:\s*"((?:[^"\\]|\\.)*)"', r)
        if m:
            v = m.group(1).replace('\\"', '"').replace("\\n", " ")
            v = v.replace("\\u2019", "’").replace("\\u2018", "‘")
            return v
        return None

    trivia, wiki, work = g("trivia"), g("wiki"), g("work")
    mm = re.search(r'"movement"\s*:\s*([01])', r)
    got = [v for v in (trivia, wiki, work) if v is not None] or (mm is not None)
    if got:
        item["trivia"] = trivia or ""
        item["wiki"] = wiki or ""
        item["work"] = work or ""
        item["movement"] = 1 if (mm and mm.group(1) == "1") else 0
        return item
    if re.search(r"\b(movement|tagged name|json|schema)\b", r, re.I):
        return item
    item["trivia"] = elide(" ".join(r.split()))
    return item
