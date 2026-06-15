import { useState } from 'react'

const COLORS = {
  primary: '#AA141E',
  white: '#FFFFFF',
  black: '#1A1A1A',
  gray: '#666666',
}

export default function HrStatusPage() {
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [sortField, setSortField] = useState('organization')
  const [sortOrder, setSortOrder] = useState('asc')

  const handleUpload = async () => {
    if (!file) {
      alert('Выберите файл')
      return
    }

    setLoading(true)
    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await fetch('/api/excel-import/hr_status/', {
        method: 'POST',
        body: formData,
      })
      const data = await res.json()
      setResult(data)
    } catch {
      alert('Ошибка загрузки')
    }
    setLoading(false)
  }

  const handleSort = (field) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortOrder('asc')
    }
  }

  const getSortedData = () => {
    if (!result?.summary) return []

    const entries = Object.entries(result.summary)

    entries.sort((a, b) => {
      let valA, valB

      if (sortField === 'organization') {
        valA = a[0].toLowerCase()
        valB = b[0].toLowerCase()
        if (sortOrder === 'asc') return valA.localeCompare(valB)
        return valB.localeCompare(valA)
      }

      valA = a[1][sortField] || 0
      valB = b[1][sortField] || 0

      if (sortOrder === 'asc') return valA - valB
      return valB - valA
    })

    return entries
  }

  const SortArrow = ({ field }) => {
    if (sortField !== field) return <span style={{ opacity: 0.3 }}> ⇅</span>
    return sortOrder === 'asc' ? <span> ↑</span> : <span> ↓</span>
  }

  const thStyle = (field) => ({
    padding: '12px',
    textAlign: 'center',
    fontSize: '11px',
    textTransform: 'uppercase',
    cursor: 'pointer',
    userSelect: 'none',
  })

  return (
    <div style={{ padding: '32px 40px', fontFamily: "'Century Gothic', 'Futura', sans-serif" }}>
      <h1 style={{ fontSize: '24px', color: COLORS.black, marginBottom: '24px' }}>
        HR-СТАТУСЫ ОБУЧЕНИЯ
      </h1>

      {/* Загрузка */}
      <div style={{
        background: COLORS.white,
        padding: '24px',
        borderRadius: '12px',
        marginBottom: '24px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
        border: '1px solid #E8E8E8',
        display: 'flex',
        gap: '16px',
        alignItems: 'center',
      }}>
        <input
          type="file"
          accept=".xlsx,.xls"
          onChange={e => setFile(e.target.files[0])}
          style={{ fontFamily: "'Century Gothic', sans-serif" }}
        />
        <button
          onClick={handleUpload}
          disabled={loading}
          style={{
            padding: '10px 24px',
            background: loading ? '#999' : COLORS.primary,
            color: COLORS.white,
            border: 'none',
            borderRadius: '6px',
            cursor: loading ? 'not-allowed' : 'pointer',
            fontWeight: '700',
            fontSize: '13px',
            fontFamily: "'Century Gothic', sans-serif",
            textTransform: 'uppercase',
          }}
        >
          {loading ? 'ОБРАБОТКА...' : 'ЗАГРУЗИТЬ'}
        </button>
        {file && (
          <span style={{ fontSize: '13px', color: COLORS.gray }}>
            {file.name}
          </span>
        )}
      </div>

      {/* Результат */}
      {result?.success && (
        <div style={{
          background: COLORS.white,
          padding: '24px',
          borderRadius: '12px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
          border: '1px solid #E8E8E8',
        }}>
          <h2 style={{ fontSize: '16px', color: COLORS.black, marginBottom: '16px' }}>
            СВОДКА ПО УПРАВЛЕНИЯМ (всего сотрудников: {result.total_employees})
          </h2>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: COLORS.black, color: COLORS.white }}>
                <th onClick={() => handleSort('organization')} style={{ ...thStyle(), textAlign: 'left' }}>
                  Управление / Отдел <SortArrow field="organization" />
                </th>
                <th onClick={() => handleSort('total')} style={thStyle()}>
                  Всего <SortArrow field="total" />
                </th>
                <th onClick={() => handleSort('specialists')} style={thStyle()}>
                  Специалистов <SortArrow field="specialists" />
                </th>
                <th onClick={() => handleSort('managers')} style={thStyle()}>
                  Руководителей <SortArrow field="managers" />
                </th>
                <th onClick={() => handleSort('not_completed')} style={thStyle()}>
                  Не пройдено <SortArrow field="not_completed" />
                </th>
              </tr>
            </thead>
            <tbody>
              {getSortedData().map(([org, stats]) => (
                <tr key={org} style={{ borderBottom: '1px solid #EEEEEE' }}>
                  <td style={{ padding: '12px', fontWeight: '600' }}>{org}</td>
                  <td style={{ padding: '12px', textAlign: 'center' }}>{stats.total}</td>
                  <td style={{ padding: '12px', textAlign: 'center' }}>{stats.specialists}</td>
                  <td style={{ padding: '12px', textAlign: 'center' }}>{stats.managers}</td>
                  <td style={{ padding: '12px', textAlign: 'center' }}>
                    <span style={{
                      padding: '4px 10px',
                      borderRadius: '20px',
                      fontSize: '11px',
                      fontWeight: '700',
                      color: COLORS.white,
                      background: stats.not_completed > 0 ? COLORS.primary : '#2E7D32',
                    }}>
                      {stats.not_completed}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Ошибки */}
      {result?.errors?.length > 0 && (
        <div style={{
          marginTop: '16px',
          padding: '16px',
          background: '#FFF8F8',
          borderRadius: '8px',
          border: '1px solid #AA141E',
        }}>
          <p style={{ fontWeight: '700', color: COLORS.primary, marginBottom: '8px' }}>
            Ошибки при обработке:
          </p>
          <ul style={{ fontSize: '12px', color: '#333' }}>
            {result.errors.map((e, i) => <li key={i}>{e}</li>)}
          </ul>
        </div>
      )}
    </div>
  )
}