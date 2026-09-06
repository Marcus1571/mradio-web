import type { Page } from '../components/TopBar'
import type { TFunction } from '../i18n'
import '../styles/admin.css'

export function SettingsPage({ onNavigate, t }: { onNavigate: (page: Page) => void; t: TFunction }) {
  const sections: { page: Page; title: string; description: string }[] = [
    { page: 'users', title: t('settings.usersTitle'), description: t('settings.usersDescription') },
    { page: 'ai-settings', title: t('settings.aiTitle'), description: t('settings.aiDescription') },
  ]

  return (
    <div className="admin-page">
      <div className="admin-header">
        <h1>{t('settings.title')}</h1>
        <p>{t('settings.subtitle')}</p>
      </div>

      <div className="settings-grid">
        {sections.map((s) => (
          <button
            key={s.page}
            className="settings-card"
            type="button"
            onClick={() => onNavigate(s.page)}
          >
            <span className="settings-card-title">{s.title}</span>
            <span className="settings-card-description">{s.description}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
