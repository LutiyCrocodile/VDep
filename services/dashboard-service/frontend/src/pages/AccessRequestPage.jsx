import { getPortalLoginUrl } from '../portal-url'

export default function AccessRequestPage() {
  return (
    <div style={{ 
      minHeight: '100vh', 
      backgroundColor: '#FAFAFA',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px'
    }}>
      <div style={{ 
        maxWidth: '500px',
        textAlign: 'center',
        backgroundColor: 'white',
        padding: '40px',
        borderRadius: '12px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
      }}>
        <h2 style={{ 
          fontSize: '24px',
          fontWeight: '700',
          color: '#1A1A1A',
          marginBottom: '16px'
        }}>
          Нет доступа к дашборду
        </h2>
        <p style={{ 
          fontSize: '14px',
          color: '#888888',
          marginBottom: '24px',
          lineHeight: '1.5'
        }}>
          У вас нет прав доступа к аналитической панели. Обратитесь к администратору для получения доступа.
        </p>
        <a 
          href={getPortalLoginUrl()}
          style={{
            display: 'inline-block',
            padding: '12px 24px',
            backgroundColor: '#AA141E',
            color: 'white',
            textDecoration: 'none',
            borderRadius: '4px',
            fontWeight: '700',
            fontSize: '13px'
          }}
        >
          Вернуться на портал
        </a>
      </div>
    </div>
  )
}
