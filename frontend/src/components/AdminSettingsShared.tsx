import { useState } from 'react'
import type { ReactNode } from 'react'
import type { TFunction } from '../i18n'
import { ChevronDownIcon } from './Icons'

const KB_URL = 'https://github.com/Marcus1571/mradio-web/blob/main/KB.md'

/** One collapsible provider card on the AI providers page — the shared
 * shell every provider bubble was duplicating by hand (icon, name,
 * status dot, expand/collapse). Added when Gemini became the 6th
 * provider and the page's copy-pasted-bubble pattern stopped scaling —
 * each provider now only supplies its own fields/test button as
 * children, not the whole header/toggle machinery.
 *
 * defaultOpen seeds initial state once (a configured/connected provider
 * starts expanded, an unconfigured one starts collapsed) — it does NOT
 * force re-expansion later if `enabled` flips true after the admin has
 * deliberately collapsed it (e.g. right after a successful Connect);
 * that would fight a manual collapse. Callers that want "snap open on
 * connect" handle that themselves by keying this component to remount,
 * same as any other defaultProp-seeded state in React.
 *
 * saveLabel/saveBusy/onSave add a redundant Save button at the top of
 * the header, next to the collapse chevron — the page's one real Save
 * action (a single form submit covering every bubble) lived only at
 * the very bottom, so tweaking one bubble meant scrolling past every
 * other one to save it. This button is `type="submit"` inside that
 * same form (no separate save path to keep in sync) with
 * `stopPropagation` so clicking it doesn't also toggle collapse — the
 * header itself remains the collapse control everywhere else. */
export function ProviderBubble({
  icon,
  name,
  enabled,
  defaultOpen,
  saveLabel,
  saveBusyLabel,
  saveBusy,
  children,
}: {
  icon: ReactNode
  name: string
  enabled: boolean
  defaultOpen: boolean
  saveLabel?: string
  saveBusyLabel?: string
  saveBusy?: boolean
  children: ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="settings-group">
      <div className="settings-group-head">
        <button
          type="button"
          className="settings-group-head-toggle"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
        >
          <h2>
            {icon}
            <span className={`provider-status-dot ${enabled ? 'on' : ''}`} aria-hidden="true" />
            {name}
          </h2>
          <ChevronDownIcon className={`provider-collapse-chevron ${open ? 'open' : ''}`} />
        </button>
        {saveLabel && (
          <button
            className="admin-submit provider-bubble-save"
            type="submit"
            disabled={saveBusy}
            onClick={(e) => e.stopPropagation()}
          >
            {saveBusy ? saveBusyLabel : saveLabel}
          </button>
        )}
      </div>
      {open && <div className="provider-bubble-body">{children}</div>}
    </div>
  )
}

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
