import { AuthProvider, useAuth } from './hooks/useAuth'
import { ChangePasswordScreen } from './pages/ChangePasswordScreen'
import { Dashboard } from './pages/Dashboard'
import { LoginScreen } from './pages/LoginScreen'

function AppShell() {
  const { user, loading } = useAuth()

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
