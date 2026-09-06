import { AuthProvider, useAuth } from './hooks/useAuth'
import { ChangePasswordScreen } from './pages/ChangePasswordScreen'
import { Dashboard } from './pages/Dashboard'
import { LoginScreen } from './pages/LoginScreen'
import { ResetPasswordScreen } from './pages/ResetPasswordScreen'

function AppShell() {
  const { user, loading } = useAuth()

  // Checked before the auth gate: a password-reset link must work even
  // with a stale session cookie present, and there's no saved language
  // preference to load pre-auth either way.
  if (window.location.pathname === '/reset-password') return <ResetPasswordScreen />
  if (loading) return null
  if (!user) return <LoginScreen />
  if (user.must_change_password) return <ChangePasswordScreen forced />
  return <Dashboard />
}

export default function App() {
  return (
    <AuthProvider>
      <AppShell />
    </AuthProvider>
  )
}
