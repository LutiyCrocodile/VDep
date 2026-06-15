import { useState, useEffect } from 'react'

export default function PropertiesPage() {
  const [properties, setProperties] = useState([])

  useEffect(() => {
    // Заглушка — у вас пока нет API для properties
    setProperties([])
  }, [])

  return (
    <div style={{ padding: '32px 40px', fontFamily: "'Century Gothic', 'Futura', sans-serif" }}>
      <h1 style={{ fontSize: '24px', color: '#1A1A1A', marginBottom: '24px' }}>ОБЪЕКТЫ НЕДВИЖИМОСТИ</h1>
      <div style={{ background: 'white', padding: '40px', borderRadius: '12px', textAlign: 'center', color: '#666' }}>
        <p style={{ fontSize: '48px', margin: '0 0 16px 0' }}>🏠</p>
        <p>Модуль в разработке</p>
        <p style={{ fontSize: '13px' }}>Загрузка данных из Excel будет доступна позже</p>
      </div>
    </div>
  )
}