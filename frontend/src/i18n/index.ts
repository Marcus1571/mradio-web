import da from './da'
import de from './de'
import el from './el'
import en from './en'
import es from './es'
import fr from './fr'
import he from './he'
import it from './it'
import ja from './ja'
import nb from './nb'
import nl from './nl'
import pt from './pt'
import ru from './ru'
import sv from './sv'
import tr from './tr'
import type { Dict } from './en'

export type Language = 'en' | 'es' | 'it' | 'pt' | 'fr' | 'ru' | 'de' | 'el' | 'nl' | 'da' | 'sv' | 'nb' | 'ja' | 'tr' | 'he'

export const LANGUAGES: { code: Language; flag: string; label: string; rtl?: true }[] = [
  { code: 'en', flag: '🇺🇸', label: 'English' },
  { code: 'es', flag: '🇪🇸', label: 'Español' },
  { code: 'it', flag: '🇮🇹', label: 'Italiano' },
  { code: 'pt', flag: '🇵🇹', label: 'Português' },
  { code: 'fr', flag: '🇫🇷', label: 'Français' },
  { code: 'ru', flag: '🇷🇺', label: 'Русский' },
  { code: 'de', flag: '🇩🇪', label: 'Deutsch' },
  { code: 'el', flag: '🇬🇷', label: 'Ελληνικά' },
  { code: 'nl', flag: '🇳🇱', label: 'Nederlands' },
  { code: 'da', flag: '🇩🇰', label: 'Dansk' },
  { code: 'sv', flag: '🇸🇪', label: 'Svenska' },
  { code: 'nb', flag: '🇳🇴', label: 'Norsk bokmål' },
  { code: 'ja', flag: '🇯🇵', label: '日本語' },
  { code: 'tr', flag: '🇹🇷', label: 'Türkçe' },
  { code: 'he', flag: '🇮🇱', label: 'עברית', rtl: true },
]

const DICTS: Record<Language, Dict> = { en, es, it, pt, fr, ru, de, el, nl, da, sv, nb, ja, tr, he }

/** Hebrew is this app's first RTL language — every prior language reused
 * the default LTR document direction with zero changes needed. Call this
 * alongside every place `language` state changes (initial config load,
 * live switch) so `dir` stays in sync — mirrors how `theme` already
 * pushes `data-theme` onto `document.documentElement` in Dashboard.tsx. */
export function applyDirection(lang: Language): void {
  const isRtl = LANGUAGES.find((l) => l.code === lang)?.rtl === true
  document.documentElement.dir = isRtl ? 'rtl' : 'ltr'
}

function getPath(dict: Dict, path: string): string {
  return path
    .split('.')
    .reduce<unknown>((o, k) => (o as Record<string, unknown> | undefined)?.[k], dict) as string
}

export function translate(lang: Language, key: string, vars?: Record<string, string | number>): string {
  const raw = getPath(DICTS[lang], key) ?? key
  if (!vars) return raw
  return Object.entries(vars).reduce((s, [k, v]) => s.replaceAll(`{${k}}`, String(v)), raw)
}

export function useTranslation(lang: Language) {
  return (key: string, vars?: Record<string, string | number>) => translate(lang, key, vars)
}

export type TFunction = (key: string, vars?: Record<string, string | number>) => string
