import { useEffect, useState } from 'react'
import { useAuthStore } from './authStore'
import { getPortalLoginUrl } from './portal-url'

function ProtectedRoute({ children }) {
  const { token, user, fetchUser } = useAuthStore()
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (token) {
      fetchUser().finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [token, fetchUser])

  if (loading) {
    return (
      <div style={{ 
        minHeight: '100vh', 
        backgroundColor: '#FAFAFA',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        <div style={{ color: '#888888' }}>Загрузка...</div>
      </div>
    )
  }

  if (!token) {
    window.location.href = getPortalLoginUrl()
    return null
  }

  // Check if user has dashboard access
  if (user && !user.dashboard_role) {
    console.log('No dashboard_role, redirecting to access-request')
    window.location.href = '/access-request'
    return null
  }

  console.log('User has dashboard_role:', user.dashboard_role)
  return children
}

export default ProtectedRoute
