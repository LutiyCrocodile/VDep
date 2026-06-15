import { useState, useEffect } from 'react'
import { apiFetch } from '../authStore'

const COLORS = {
  primary: '#AA141E',
  white: '#FFFFFF',
  black: '#1A1A1A',
  gray: '#666666',
}

export default function ImportPage() {
  const [file, setFile] = useState(null)
  const [importType, setImportType] = useState('metrics')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [history, setHistory] = useState([])

  useEffect(() => {
    loadHistory()
  }, [])

  const loadHistory = () => {
    apiFetch('/api/excel-import/history/')
      .then(res => res.json())
      .then(data => setHistory(Array.isArray(data) ? data : []))
      .catch(() => {})
  }

  const handleFileChange = (e) => {
    setFile(e.target.files[0])
    setResult(null)
  }

  const handleUpload = async () => {
    if (!file) {
      alert('Выберите файл')
      return
    }

    setLoading(true)
    const formData = new FormData()
    formData.append('file', file)
    formData.append('import_type', importType)

    try {
      const token = localStorage.getItem('access_token')
      const response = await fetch('/api/excel-import/upload/', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      })

      const data = await response.json()
      setResult(data)
      loadHistory()
    } catch (err) {
      setResult({ success: false, error: 'Ошибка соединения с сервером' })
    }

    setLoading(false)
  }

  return (
    <div style={{ padding: '32px 40px', fontFamily: "'Century Gothic', 'Futura', sans-serif" }}>
      <h1 style={{ fontSize: '24px', color: COLORS.black, marginBottom: '24px' }}>
        ИМПОРТ ДАННЫХ ИЗ EXCEL
      </h1>

      {/* Зона загрузки */}
      <div style={{
        background: COLORS.white,
        padding: '32px',
        borderRadius: '12px',
        marginBottom: '24px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
        border: '1px solid #E8E8E8',
      }}>
        <div style={{ marginBottom: '20px' }}>
          <label style={{
            display: 'block', fontSize: '11px', fontWeight: '600',
            textTransform: 'uppercase', marginBottom: '6px', color: COLORS.black,
          }}>
            Тип импорта
          </label>
          <select
            value={importType}
            onChange={(e) => setImportType(e.target.value)}
            style={{
              padding: '10px', borderRadius: '6px', border: '1px solid #E0E0E0',
              fontFamily: "'Century Gothic', sans-serif", minWidth: '250px',
            }}
          >
            <option value="metrics">Показатели (метрики)</option>
            <option value="properties">Объекты недвижимости</option>
          </select>
        </div>

        <div style={{ marginBottom: '20px' }}>
          <label style={{
            display: 'block', fontSize: '11px', fontWeight: '600',
            textTransform: 'uppercase', marginBottom: '6px', color: COLORS.black,
          }}>
            Файл Excel (.xlsx)
          </label>
          <input
            type="file"
            accept=".xlsx,.xls"
            onChange={handleFileChange}
            style={{ fontFamily: "'Century Gothic', sans-serif" }}
          />
          {file && (
            <p style={{ fontSize: '13px', color: COLORS.black, marginTop: '8px' }}>
              Выбран: <strong>{file.name}</strong> ({(file.size / 1024).toFixed(1)} КБ)
            </p>
          )}
        </div>

        <button
          onClick={handleUpload}
          disabled={loading}
          style={{
            padding: '12px 28px',
            background: loading ? '#999' : COLORS.primary,
            color: COLORS.white,
            border: 'none',
            borderRadius: '6px',
            cursor: loading ? 'not-allowed' : 'pointer',
            fontWeight: '700',
            fontSize: '14px',
            fontFamily: "'Century Gothic', sans-serif",
            textTransform: 'uppercase',
          }}
        >
          {loading ? 'ЗАГРУЗКА...' : 'ЗАГРУЗИТЬ И ИМПОРТИРОВАТЬ'}
        </button>

        {/* Результат */}
        {result && (
          <div style={{
            marginTop: '20px',
            padding: '16px',
            borderRadius: '8px',
            background: result.success ? '#E8F5E9' : '#FFEBEE',
            border: `1px solid ${result.success ? '#4CAF50' : '#EF5350'}`,
          }}>
            {result.success ? (
              <div>
                <p style={{ fontWeight: '700', color: '#2E7D32' }}>
                  Импорт завершён
                </p>
                <p style={{ fontSize: '13px', marginTop: '4px' }}>
                  Импортировано: {result.imported} из {result.total_rows} строк
                </p>
                {result.errors?.length > 0 && (
                  <details style={{ marginTop: '8px' }}>
                    <summary style={{ cursor: 'pointer', fontSize: '12px', color: '#666' }}>
                      Ошибки ({result.errors.length})
                    </summary>
                    <ul style={{ fontSize: '11px', color: '#C62828', marginTop: '4px' }}>
                      {result.errors.map((e, i) => <li key={i}>{e}</li>)}
                    </ul>
                  </details>
                )}
              </div>
            ) : (
              <p style={{ color: '#C62828', fontWeight: '600' }}>
                {result.error || 'Ошибка импорта'}
              </p>
            )}
          </div>
        )}
      </div>

      {/* История загрузок */}
      <div style={{
        background: COLORS.white,
        padding: '24px',
        borderRadius: '12px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
        border: '1px solid #E8E8E8',
      }}>
        <h2 style={{ fontSize: '16px', color: COLORS.black, marginBottom: '16px' }}>
          ИСТОРИЯ ЗАГРУЗОК
        </h2>
        {history.length > 0 ? (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: COLORS.black, color: COLORS.white }}>
                <th style={{ padding: '10px', textAlign: 'left', fontSize: '11px', textTransform: 'uppercase' }}>Файл</th>
                <th style={{ padding: '10px', textAlign: 'left', fontSize: '11px', textTransform: 'uppercase' }}>Статус</th>
                <th style={{ padding: '10px', textAlign: 'left', fontSize: '11px', textTransform: 'uppercase' }}>Дата</th>
              </tr>
            </thead>
            <tbody>
              {history.map(h => (
                <tr key={h.id} style={{ borderBottom: '1px solid #EEEEEE' }}>
                  <td style={{ padding: '10px', fontSize: '13px' }}>{h.filename}</td>
                  <td style={{ padding: '10px' }}>
                    <span style={{
                      padding: '2px 8px', borderRadius: '20px', fontSize: '10px',
                      fontWeight: '700', textTransform: 'uppercase', color: COLORS.white,
                      background: h.status === 'completed' ? '#2E7D32' :
                                  h.status === 'error' ? '#AA141E' : '#F57F17'
                    }}>
                      {h.status}
                    </span>
                  </td>
                  <td style={{ padding: '10px', fontSize: '13px', color: COLORS.gray }}>
                    {new Date(h.created_at).toLocaleString('ru-RU')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p style={{ color: COLORS.gray, fontSize: '13px', textAlign: 'center', padding: '20px' }}>
            История загрузок пуста
          </p>
        )}
      </div>
    </div>
  )
}