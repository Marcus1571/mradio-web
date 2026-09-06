import da from './da'
import de from './de'
import el from './el'
import en from './en'
import es from './es'
import fr from './fr'
import it from './it'
import nl from './nl'
import pt from './pt'
import ru from './ru'
import sv from './sv'
import type { Dict } from './en'

export type Language = 'en' | 'es' | 'it' | 'pt' | 'fr' | 'ru' | 'de' | 'el' | 'nl' | 'da' | 'sv'

export const LANGUAGES: { code: Language; flag: string; label: string }[] = [
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
]

const DICTS: Record<Language, Dict> = { en, es, it, pt, fr, ru, de, el, nl, da, sv }

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
