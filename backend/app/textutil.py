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


def apply_provider_rules(prompt: str, provider: str) -> str:
    """Provider-targeted prompt additions. openai (NIM) gets extra
    anti-hallucination rules; opencode and ollama keep the stock prompt."""
    if provider == "openai":
        return prompt + SINCERITY_RULES
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
