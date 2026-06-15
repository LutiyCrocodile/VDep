import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

const COLORS = {
  primary: '#AA141E',
  primaryDark: '#8B1019',
  white: '#FFFFFF',
  black: '#1A1A1A',
  gray: '#666666',
}

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const handleLogin = async (e) => {
    e.preventDefault()
    setError('')

    try {
      const response = await fetch('/api/token/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      })

      if (response.ok) {
        const data = await response.json()
        localStorage.setItem('access_token', data.access)
        localStorage.setItem('refresh_token', data.refresh)

        // Получаем роль пользователя
        const userResponse = await fetch('/api/users/me/', {
          headers: { 'Authorization': `Bearer ${data.access}` }
        })

        if (userResponse.ok) {
          const userData = await userResponse.json()
          localStorage.setItem('user_role', userData.role_name || '')
          localStorage.setItem('username', userData.username)
        }

        navigate('/')
      } else {
        setError('Неверный логин или пароль')
      }
    } catch {
      setError('Ошибка соединения с сервером')
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: `linear-gradient(135deg, ${COLORS.primaryDark}, ${COLORS.primary})`,
      fontFamily: "'Century Gothic', 'Futura', sans-serif",
    }}>
      <div style={{
        background: COLORS.white,
        padding: '40px',
        borderRadius: '12px',
        width: '400px',
        boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
      }}>
        <h1 style={{
          fontSize: '20px',
          color: COLORS.black,
          textAlign: 'center',
          marginBottom: '8px',
          fontWeight: '700',
        }}>
          ИНТЕРАКТИВНАЯ СИСТЕМА
        </h1>
        <p style={{
          fontSize: '12px',
          color: COLORS.gray,
          textAlign: 'center',
          marginBottom: '28px',
        }}>
          Визуализация отчётов ДГИ
        </p>

        <form onSubmit={handleLogin}>
          <div style={{ marginBottom: '16px' }}>
            <label style={{
              display: 'block', fontSize: '11px', fontWeight: '600',
              textTransform: 'uppercase', marginBottom: '6px', color: COLORS.black,
            }}>
              Логин
            </label>
            <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} required
              style={{
                width: '100%', padding: '12px', borderRadius: '6px',
                border: '1px solid #E0E0E0', fontFamily: "'Century Gothic', sans-serif",
                fontSize: '14px', boxSizing: 'border-box',
              }} />
          </div>

          <div style={{ marginBottom: '24px' }}>
            <label style={{
              display: 'block', fontSize: '11px', fontWeight: '600',
              textTransform: 'uppercase', marginBottom: '6px', color: COLORS.black,
            }}>
              Пароль
            </label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required
              style={{
                width: '100%', padding: '12px', borderRadius: '6px',
                border: '1px solid #E0E0E0', fontFamily: "'Century Gothic', sans-serif",
                fontSize: '14px', boxSizing: 'border-box',
              }} />
          </div>

          {error && (
            <p style={{
              color: COLORS.primary, fontSize: '13px',
              marginBottom: '16px', textAlign: 'center',
            }}>
              {error}
            </p>
          )}

          <button type="submit" style={{
            width: '100%', padding: '14px', background: COLORS.primary,
            color: COLORS.white, border: 'none', borderRadius: '6px',
            cursor: 'pointer', fontWeight: '700', fontSize: '14px',
            fontFamily: "'Century Gothic', sans-serif", textTransform: 'uppercase',
          }}>
            ВОЙТИ
          </button>
        </form>
      </div>
    </div>
  )
}