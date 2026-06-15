import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { useAuthStore } from './store/authStore'
import { getPortalLoginUrl } from './lib/portal-url'
import AccessRequestPage from './pages/AccessRequestPage'
import MessengerPage from './pages/MessengerPage'
import AdminPage from './pages/AdminPage'
import ProfilePage from './pages/ProfilePage'
import CallModal from './components/CallModal'
import ConfirmDialog from './components/ConfirmDialog'
import Lightbox from './components/Lightbox'
import ErrorBoundary from './components/ErrorBoundary'

function ProtectedRoute({ children }) {
  const { token, fetchUser } = useAuthStore()

  useEffect(() => {
    if (token) fetchUser()
  }, [token, fetchUser])

  if (!token) {
    window.location.href = getPortalLoginUrl()
    return null
  }
  return children
}

function AdminRoute({ children }) {
  const { token, user, fetchUser } = useAuthStore()

  useEffect(() => {
    if (token) fetchUser()
  }, [token, fetchUser])

  if (!token) {
    window.location.href = getPortalLoginUrl()
    return null
  }
  if (user && !['super_admin', 'admin'].includes(user.role)) {
    return <Navigate to="/" />
  }
  return children
}

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Toaster position="top-center" toastOptions={{ style: { background: '#1f1f1f', color: '#f5f5f5', border: '1px solid #2a2a2a', fontFamily: '"Century Gothic", Arial, sans-serif' } }} />
        <CallModal />
        <ConfirmDialog />
        <Lightbox />
        <Routes>
          <Route path="/access-request" element={<AccessRequestPage />} />
          <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
          <Route path="/admin/*" element={<AdminRoute><AdminPage /></AdminRoute>} />
          <Route path="/*" element={<ProtectedRoute><MessengerPage /></ProtectedRoute>} />
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  )
}
