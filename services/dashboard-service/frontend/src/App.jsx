import { Routes, Route, Link, useLocation } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import ReportsList from './pages/ReportsList'
import TemplateBuilder from './pages/TemplateBuilder'
import ImportPage from './pages/ImportPage'
import LoginPage from './pages/LoginPage'
import HrStatusPage from './pages/HrStatusPage'
import AccessRequestPage from './pages/AccessRequestPage'
import ProtectedRoute from './ProtectedRoute'
import { useAuthStore } from './authStore'

const COLORS = {
  primary: '#AA141E',
  primaryDark: '#8B1019',
  white: '#FFFFFF',
  black: '#1A1A1A',
  gray: '#888888',
  lightGray: '#F0F0F0',
}

const styles = {
  header: {
    background: `linear-gradient(135deg, ${COLORS.primaryDark}, ${COLORS.primary})`,
    color: COLORS.white,
    padding: '24px 40px',
    fontFamily: "'Century Gothic', 'Futura', sans-serif",
  },
  headerTitle: {
    margin: 0,
    fontSize: '22px',
    fontWeight: '700',
    letterSpacing: '0.5px',
  },
  headerSubtitle: {
    margin: '4px 0 0 0',
    fontSize: '13px',
    opacity: 0.8,
  },
  nav: {
    display: 'flex',
    gap: '0',
    background: COLORS.black,
    padding: '0 40px',
  },
  link: (isActive) => ({
    display: 'block',
    padding: '16px 24px',
    color: isActive ? COLORS.white : '#AAAAAA',
    background: isActive ? COLORS.primary : 'transparent',
    textDecoration: 'none',
    fontSize: '13px',
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    transition: 'all 0.2s',
  }),
}

function App() {
  const location = useLocation()
  const { logout } = useAuthStore()

  const navItems = [
    { path: '/', label: 'Дашборд' },
    { path: '/reports', label: 'Отчёты' },
    { path: '/templates', label: 'Конструктор' },
    { path: '/import', label: 'Импорт данных' },
    { path: '/hr-status', label: 'HR-статусы' }
  ]

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#FAFAFA' }}>
      {/* Шапка — на всех страницах */}
      <header style={styles.header}>
        <h1 style={styles.headerTitle}>
          ИНТЕРАКТИВНАЯ СИСТЕМА ВИЗУАЛИЗАЦИИ ОТЧЁТОВ
        </h1>
        <p style={styles.headerSubtitle}>
          Департамент городского имущества города Москвы
        </p>
      </header>

      {/* Навигация */}
      <nav style={styles.nav}>
        {navItems.map(item => (

          <Link
            key={item.path}
            to={item.path}
            style={styles.link(
              item.path === '/'
                ? location.pathname === '/'
                : location.pathname.startsWith(item.path)
            )}
          >
            {item.label}
          </Link>
        ))}
        <button
          onClick={logout}
          style={{
            ...styles.link(false),
            marginLeft: 'auto',
            cursor: 'pointer',
            background: 'transparent',
            border: 'none',
          }}
        >
          ВЫХОД
        </button>
      </nav>

      {/* Контент */}
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/access-request" element={<AccessRequestPage />} />
        <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/reports" element={<ProtectedRoute><ReportsList /></ProtectedRoute>} />
        <Route path="/templates" element={<ProtectedRoute><TemplateBuilder /></ProtectedRoute>} />
        <Route path="/import" element={<ProtectedRoute><ImportPage /></ProtectedRoute>} />
        <Route path="/hr-status" element={<ProtectedRoute><HrStatusPage /></ProtectedRoute>} />
      </Routes>
    </div>
  )
}

export default App