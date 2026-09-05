import en from './en'
import es from './es'
import it from './it'
import type { Dict } from './en'

export type Language = 'en' | 'es' | 'it'

export const LANGUAGES: { code: Language; flag: string; label: string }[] = [
  { code: 'en', flag: '🇺🇸', label: 'English' },
  { code: 'es', flag: '🇪🇸', label: 'Español' },
  { code: 'it', flag: '🇮🇹', label: 'Italiano' },
]

const DICTS: Record<Language, Dict> = { en, es, it }

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
