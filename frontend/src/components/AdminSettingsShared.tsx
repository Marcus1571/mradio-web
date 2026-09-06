import type { TFunction } from '../i18n'

const KB_URL = 'https://github.com/Marcus1571/mradio-web/blob/main/KB.md'

export function KbNote({
  prefix,
  linkLabel,
  anchor,
  suffix,
}: {
  prefix: string
  linkLabel: string
  anchor: string
  suffix: string
}) {
  return (
    <p className="admin-note">
      {prefix}{' '}
      <a href={`${KB_URL}#${anchor}`} target="_blank" rel="noopener noreferrer">
        {linkLabel}
      </a>{' '}
      {suffix}
    </p>
  )
}

export type TestState = { status: 'idle' | 'testing' | 'success' | 'failure'; message?: string }

export const IDLE_TEST: TestState = { status: 'idle' }

export function TestBadge({ state, t }: { state: TestState; t: TFunction }) {
  if (state.status === 'idle') return null
  const pillClass =
    state.status === 'success' ? 'pill admin' : state.status === 'failure' ? 'pill disabled' : 'pill'
  const label =
    state.status === 'testing'
      ? t('aiSettings.testing')
      : state.status === 'success'
        ? t('aiSettings.testSuccess')
        : state.message || t('aiSettings.testFailure')
  return <span className={pillClass}>{label}</span>
}
