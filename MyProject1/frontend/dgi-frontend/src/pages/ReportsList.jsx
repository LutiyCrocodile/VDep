import { useState, useEffect } from 'react'

const COLORS = {
  primary: '#AA141E',
  white: '#FFFFFF',
  black: '#1A1A1A',
  gray: '#666666',
}

const STATUS_COLORS = {
  'Черновик': '#F57F17',
  'На согласовании': '#FF9800',
  'Согласован': '#1565C0',
  'Отклонён': '#AA141E',
  'Опубликован': '#2E7D32',
}

export default function ReportsList() {
  const [reports, setReports] = useState([])
  const [templates, setTemplates] = useState([])
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [reportTitle, setReportTitle] = useState('')
  const [selectedTemplate, setSelectedTemplate] = useState('')

  useEffect(() => {
    loadReports()
    loadTemplates()
  }, [])

  const loadReports = () => {
    let url = '/api/reports/?'
    if (search) url += `search=${search}&`
    if (statusFilter) url += `status=${statusFilter}&`
    fetch(url)
      .then(res => res.json())
      .then(data => setReports(Array.isArray(data) ? data : []))
      .catch(() => setReports([]))
  }

  const loadTemplates = () => {
    fetch('/api/report-templates/')
      .then(res => res.json())
      .then(data => setTemplates(Array.isArray(data) ? data : []))
      .catch(() => setTemplates([]))
  }

  const createReport = async (e) => {
    e.preventDefault()
    if (!reportTitle.trim()) {
      alert('Введите название отчёта')
      return
    }

    const body = {
      title: reportTitle,
      author: 1,
      status: 1,
    }
    if (selectedTemplate) {
      body.template = parseInt(selectedTemplate)
    }

    try {
      const res = await fetch('/api/reports/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      })

      if (res.ok) {
        loadReports()
        setReportTitle('')
        setSelectedTemplate('')
      } else {
        const error = await res.json()
        alert('Ошибка создания отчёта: ' + JSON.stringify(error))
      }
    } catch (err) {
      alert('Ошибка соединения с сервером')
    }
  }

  const generatePPTX = async (id) => {
    try {
      const res = await fetch(`/api/reports/${id}/generate_pptx/`, { method: 'POST' })
      if (res.ok) {
        const blob = await res.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `report_${id}.pptx`
        a.click()
        window.URL.revokeObjectURL(url)
      } else {
        const error = await res.json()
        alert('Ошибка генерации PPTX. ' + (error.error || 'Проверьте, что у отчёта есть шаблон.'))
      }
    } catch (err) {
      alert('Ошибка соединения с сервером')
    }
  }

  const deleteReport = async (id) => {
    if (!window.confirm('Удалить отчёт?')) return
    try {
      await fetch(`/api/reports/${id}/`, { method: 'DELETE' })
      loadReports()
    } catch (err) {
      alert('Ошибка удаления')
    }
  }

const generatePDF = async (id) => {
  try {
    const res = await fetch(`/api/reports/${id}/generate_pdf/`, { method: 'POST' })
    if (res.ok) {
      const blob = await res.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `report_${id}.pdf`
      a.click()
      window.URL.revokeObjectURL(url)
    } else {
      const error = await res.json()
      alert('Ошибка генерации PDF. ' + (error.error || ''))
    }
  } catch (err) {
    alert('Ошибка соединения с сервером')
  }
}

const shareReport = async (report) => {
  try {
    const res = await fetch(`/api/reports/${report.id}/generate_pdf/`, { method: 'POST' })
    if (res.ok) {
      const blob = await res.blob()
      const url = window.URL.createObjectURL(blob)

      // Открываем PDF в новом окне
      window.open(url, '_blank')

      // Копируем информацию в буфер обмена для отправки в мессенджер
      const shareText = `Отчёт: ${report.title}\nСтатус: ${report.status_name}\nДата: ${new Date(report.created_at).toLocaleDateString('ru-RU')}`

      try {
        await navigator.clipboard.writeText(shareText)
        alert('PDF открыт в новом окне.\nТекст отчёта скопирован в буфер обмена — вставьте в мессенджер.')
      } catch {
        alert('PDF открыт в новом окне.\nСкопируйте ссылку и отправьте в мессенджер.')
      }
    } else {
      const error = await res.json()
      alert('Ошибка генерации PDF. ' + (error.error || ''))
    }
  } catch (err) {
    alert('Ошибка соединения с сервером')
  }
}
  return (
    <div style={{ padding: '32px 40px', fontFamily: "'Century Gothic', 'Futura', sans-serif" }}>
      <h1 style={{ fontSize: '24px', color: COLORS.black, marginBottom: '24px' }}>ОТЧЁТЫ</h1>

      {/* Форма создания */}
      <form onSubmit={createReport} style={{
        background: COLORS.white, padding: '20px', borderRadius: '12px',
        marginBottom: '24px', display: 'flex', gap: '12px', alignItems: 'flex-end',
        boxShadow: '0 2px 8px rgba(0,0,0,0.06)', border: '1px solid #E8E8E8', flexWrap: 'wrap'
      }}>
        <div>
          <label style={{ display: 'block', fontSize: '11px', fontWeight: '600', textTransform: 'uppercase', marginBottom: '4px' }}>
            Название *
          </label>
          <input value={reportTitle} onChange={e => setReportTitle(e.target.value)} required
            placeholder="Название отчёта"
            style={{ padding: '10px', borderRadius: '6px', border: '1px solid #E0E0E0', minWidth: '250px', fontFamily: "'Century Gothic', sans-serif" }} />
        </div>
        <div>
          <label style={{ display: 'block', fontSize: '11px', fontWeight: '600', textTransform: 'uppercase', marginBottom: '4px' }}>
            Шаблон
          </label>
          <select value={selectedTemplate} onChange={e => setSelectedTemplate(e.target.value)}
            style={{ padding: '10px', borderRadius: '6px', border: '1px solid #E0E0E0', minWidth: '200px', fontFamily: "'Century Gothic', sans-serif" }}>
            <option value="">Без шаблона</option>
            {templates.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
        </div>
        <button type="submit" style={{
          padding: '10px 20px', background: COLORS.primary, color: COLORS.white,
          border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: '700',
          fontSize: '13px', fontFamily: "'Century Gothic', sans-serif"
        }}>
          СОЗДАТЬ
        </button>
      </form>

      {/* Фильтры */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '20px' }}>
        <input value={search} onChange={e => setSearch(e.target.value)}
          placeholder="Поиск по названию..."
          style={{ padding: '10px', borderRadius: '6px', border: '1px solid #E0E0E0', flex: 1, fontFamily: "'Century Gothic', sans-serif" }} />
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
          style={{ padding: '10px', borderRadius: '6px', border: '1px solid #E0E0E0', fontFamily: "'Century Gothic', sans-serif" }}>
          <option value="">Все статусы</option>
          <option value="Черновик">Черновик</option>
          <option value="На согласовании">На согласовании</option>
          <option value="Согласован">Согласован</option>
          <option value="Отклонён">Отклонён</option>
          <option value="Опубликован">Опубликован</option>
        </select>
        <button onClick={loadReports} style={{
          padding: '10px 20px', background: COLORS.black, color: COLORS.white,
          border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: '700',
          fontSize: '13px', fontFamily: "'Century Gothic', sans-serif"
        }}>
          НАЙТИ
        </button>
      </div>

      {/* Таблица */}
      <div style={{ background: COLORS.white, borderRadius: '12px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)', border: '1px solid #E8E8E8', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: COLORS.black, color: COLORS.white }}>
              <th style={{ padding: '12px', textAlign: 'left', fontSize: '11px', textTransform: 'uppercase' }}>ID</th>
              <th style={{ padding: '12px', textAlign: 'left', fontSize: '11px', textTransform: 'uppercase' }}>Название</th>
              <th style={{ padding: '12px', textAlign: 'left', fontSize: '11px', textTransform: 'uppercase' }}>Шаблон</th>
              <th style={{ padding: '12px', textAlign: 'left', fontSize: '11px', textTransform: 'uppercase' }}>Статус</th>
              <th style={{ padding: '12px', textAlign: 'left', fontSize: '11px', textTransform: 'uppercase' }}>Дата</th>
              <th style={{ padding: '12px', textAlign: 'left', fontSize: '11px', textTransform: 'uppercase' }}>Действия</th>
            </tr>
          </thead>
          <tbody>
            {reports.map(r => (
              <tr key={r.id} style={{ borderBottom: '1px solid #EEEEEE' }}>
                <td style={{ padding: '12px', fontSize: '13px' }}>#{r.id}</td>
                <td style={{ padding: '12px', fontWeight: '600' }}>{r.title}</td>
                <td style={{ padding: '12px', fontSize: '13px', color: COLORS.gray }}>{r.template_name || '—'}</td>
                <td style={{ padding: '12px' }}>
                  <span style={{
                    padding: '3px 10px', borderRadius: '20px', fontSize: '10px', fontWeight: '700',
                    textTransform: 'uppercase', color: COLORS.white,
                    background: STATUS_COLORS[r.status_name] || '#9E9E9E'
                  }}>
                    {r.status_name || 'draft'}
                  </span>
                </td>
                <td style={{ padding: '12px', display: 'flex', gap: '8px' }}>
  <button onClick={() => generatePPTX(r.id)} style={{
    padding: '6px 12px', background: COLORS.primary, color: COLORS.white,
    border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '12px', fontWeight: '600',
    fontFamily: "'Century Gothic', sans-serif"
  }}>PPTX</button>
  <button onClick={() => generatePDF(r.id)} style={{
    padding: '6px 12px', background: '#333', color: COLORS.white,
    border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '12px', fontWeight: '600',
    fontFamily: "'Century Gothic', sans-serif"
  }}>PDF</button>
  <button onClick={() => shareReport(r)} style={{
    padding: '6px 12px', background: '#1565C0', color: COLORS.white,
    border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '12px', fontWeight: '600',
    fontFamily: "'Century Gothic', sans-serif"
  }}>ОТПРАВИТЬ</button>
  <button onClick={() => deleteReport(r.id)} style={{
    padding: '6px 12px', background: 'transparent', color: COLORS.primary,
    border: `1px solid ${COLORS.primary}`, borderRadius: '4px', cursor: 'pointer', fontSize: '12px',
    fontFamily: "'Century Gothic', sans-serif"
  }}>УДАЛИТЬ</button>
</td>
              </tr>
            ))}
          </tbody>
        </table>
        {reports.length === 0 && (
          <p style={{ textAlign: 'center', padding: '40px', color: COLORS.gray, fontSize: '13px' }}>
            Нет созданных отчётов
          </p>
        )}
      </div>
    </div>
  )
}