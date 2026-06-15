import { useState, useEffect } from 'react'
import { Bar, Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, BarElement, LineElement, PointElement, Title, Tooltip, Legend)

const COLORS = {
  primary: '#AA141E',
  primaryLight: '#D4404A',
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

const METRIC_OPTIONS = [
  { id: 1, label: 'Переселённые семьи' },
  { id: 2, label: 'Расселённые дома' },
  { id: 3, label: 'Новые дома' },
  { id: 4, label: 'Укомплектованность штата' },
  { id: 5, label: 'Текучесть кадров' },
  { id: 6, label: 'Обращения граждан' },
  { id: 7, label: 'Сроки рассмотрения' },
]

export default function Dashboard() {
  const [stats, setStats] = useState({ total: 0, recent: 0, templates: 0 })
  const [reports, setReports] = useState([])
  const [statuses, setStatuses] = useState([])
  const [chartData, setChartData] = useState(null)
  const [propertyChartData, setPropertyChartData] = useState(null)
  const [selectedMetric, setSelectedMetric] = useState(1)

  useEffect(() => {
    loadData()
    loadStatuses()
    loadPropertyData()
    const interval = setInterval(loadData, 30000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    loadChartData()
  }, [selectedMetric])

  const loadData = () => {
    fetch('/api/reports/')
      .then(res => res.json())
      .then(data => {
        const list = Array.isArray(data) ? data : []
        setReports(list.slice(0, 10))

        const weekAgo = new Date()
        weekAgo.setDate(weekAgo.getDate() - 7)
        const recent = list.filter(r => new Date(r.created_at) >= weekAgo).length

        setStats(prev => ({
          ...prev,
          total: list.length,
          recent: recent,
        }))
      })
      .catch(() => {})

    fetch('/api/report-templates/')
      .then(res => res.json())
      .then(data => {
        setStats(prev => ({
          ...prev,
          templates: Array.isArray(data) ? data.length : 0,
        }))
      })
      .catch(() => {})
  }

  const loadChartData = () => {
    fetch(`/api/metrics-data/?metric_type_id=${selectedMetric}`)
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data) && data.length > 0) {
          const districts = {}
          data.forEach(item => {
            const d = item.district || 'Не указан'
            districts[d] = (districts[d] || 0) + Number(item.value)
          })

          setChartData({
            labels: Object.keys(districts),
            datasets: [{
              label: METRIC_OPTIONS.find(m => m.id === selectedMetric)?.label || 'Значение',
              data: Object.values(districts),
              backgroundColor: ['#AA141E', '#8B1019', '#D4404A', '#666666', '#333333'],
              borderRadius: 4,
            }]
          })
        } else {
          setChartData({
            labels: ['Нет данных'],
            datasets: [{ label: 'Нет данных', data: [0], backgroundColor: ['#CCCCCC'] }]
          })
        }
      })
      .catch(() => {
        setChartData({
          labels: ['Ошибка'],
          datasets: [{ label: 'Ошибка загрузки', data: [0], backgroundColor: ['#CCCCCC'] }]
        })
      })
  }

  const loadPropertyData = () => {
    fetch('/api/properties/stats/')
      .then(res => res.json())
      .then(data => {
        if (data?.by_district?.length > 0) {
          const labels = data.by_district.map(d => d.district || 'Не указан')
          const values = data.by_district.map(d => d.count)

          setPropertyChartData({
            labels: labels,
            datasets: [{
              label: 'Объектов недвижимости',
              data: values,
              borderColor: '#AA141E',
              backgroundColor: 'rgba(170, 20, 30, 0.1)',
              borderWidth: 3,
              pointBackgroundColor: '#AA141E',
              pointBorderColor: '#FFFFFF',
              pointBorderWidth: 2,
              pointRadius: 5,
              tension: 0.3,
              fill: true,
            }]
          })
        } else {
          setPropertyChartData({
            labels: ['Нет данных'],
            datasets: [{ label: 'Нет данных', data: [0], borderColor: '#CCCCCC' }]
          })
        }
      })
      .catch(() => {
        setPropertyChartData({
          labels: ['Ошибка'],
          datasets: [{ label: 'Ошибка загрузки', data: [0], borderColor: '#CCCCCC' }]
        })
      })
  }

  const loadStatuses = () => {
    fetch('/api/report-statuses/')
      .then(res => res.json())
      .then(data => setStatuses(Array.isArray(data) ? data : []))
      .catch(() => {})
  }

  const changeStatus = async (reportId, newStatusId) => {
    try {
      const res = await fetch(`/api/reports/${reportId}/change_status/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status_id: newStatusId })
      })
      if (res.ok) loadData()
    } catch (err) {}
  }

  const cardStyle = {
    background: COLORS.white,
    padding: '24px',
    borderRadius: '12px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
    textAlign: 'center',
    flex: 1,
    border: '1px solid #E8E8E8',
  }

  const bigNumber = {
    fontSize: '36px',
    fontWeight: '700',
    color: COLORS.primary,
    margin: '8px 0',
    fontFamily: "'Century Gothic', sans-serif",
  }

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: { display: false },
      title: {
        display: true,
        text: METRIC_OPTIONS.find(m => m.id === selectedMetric)?.label || 'График',
        font: { family: "'Century Gothic', sans-serif", size: 14, weight: 'bold' },
        color: COLORS.black,
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: { font: { family: "'Century Gothic', sans-serif" } },
      },
      x: {
        ticks: { font: { family: "'Century Gothic', sans-serif" } },
      },
    },
  }

  const lineChartOptions = {
    responsive: true,
    plugins: {
      legend: { display: false },
      title: {
        display: true,
        text: 'Объекты недвижимости по районам',
        font: { family: "'Century Gothic', sans-serif", size: 14, weight: 'bold' },
        color: COLORS.black,
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: { font: { family: "'Century Gothic', sans-serif" } },
      },
      x: {
        ticks: { font: { family: "'Century Gothic', sans-serif" } },
      },
    },
  }

  return (
    <div style={{ padding: '32px 40px', fontFamily: "'Century Gothic', 'Futura', sans-serif" }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h1 style={{ fontSize: '24px', color: COLORS.black, margin: 0 }}>ДАШБОРД</h1>
        <button style={{
          padding: '10px 20px', background: COLORS.primary, color: COLORS.white,
          border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: '700',
          fontSize: '13px', fontFamily: "'Century Gothic', sans-serif",
        }} onClick={() => alert('Функция в разработке')}>
          ДОБАВИТЬ ДАШБОРД
        </button>
      </div>

      {/* KPI */}
      <div style={{ display: 'flex', gap: '20px', marginBottom: '30px' }}>
        <div style={cardStyle}>
          <div style={{ fontSize: '13px', color: COLORS.gray, textTransform: 'uppercase', fontWeight: '600' }}>Всего отчётов</div>
          <div style={bigNumber}>{stats.total}</div>
        </div>
        <div style={cardStyle}>
          <div style={{ fontSize: '13px', color: COLORS.gray, textTransform: 'uppercase', fontWeight: '600' }}>За 7 дней</div>
          <div style={bigNumber}>{stats.recent}</div>
        </div>
        <div style={cardStyle}>
          <div style={{ fontSize: '13px', color: COLORS.gray, textTransform: 'uppercase', fontWeight: '600' }}>Шаблонов</div>
          <div style={bigNumber}>{stats.templates}</div>
        </div>
      </div>

      {/* Графики */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '30px' }}>
        {/* График метрик */}
        <div style={{ background: COLORS.white, padding: '24px', borderRadius: '12px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)', border: '1px solid #E8E8E8' }}>
          <div style={{ marginBottom: '16px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {METRIC_OPTIONS.map(metric => (
              <button key={metric.id} onClick={() => setSelectedMetric(metric.id)} style={{
                padding: '6px 14px', borderRadius: '20px',
                border: selectedMetric === metric.id ? 'none' : '1px solid #E0E0E0',
                background: selectedMetric === metric.id ? COLORS.primary : COLORS.white,
                color: selectedMetric === metric.id ? COLORS.white : COLORS.gray,
                cursor: 'pointer', fontSize: '11px', fontWeight: '600',
                fontFamily: "'Century Gothic', sans-serif", transition: 'all 0.2s',
              }}>{metric.label}</button>
            ))}
          </div>
          {chartData && <Bar data={chartData} options={chartOptions} />}
        </div>

        {/* График объектов недвижимости */}
        <div style={{ background: COLORS.white, padding: '24px', borderRadius: '12px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)', border: '1px solid #E8E8E8' }}>
          {propertyChartData && <Line data={propertyChartData} options={lineChartOptions} />}
        </div>
      </div>

      {/* Управление отчётами */}
      <div style={{ background: COLORS.white, padding: '24px', borderRadius: '12px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)', border: '1px solid #E8E8E8' }}>
        <h3 style={{ fontFamily: "'Century Gothic', sans-serif", fontSize: '14px', color: COLORS.black, marginBottom: '16px' }}>
          УПРАВЛЕНИЕ ОТЧЁТАМИ
        </h3>
        {reports.length > 0 ? (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: COLORS.black, color: COLORS.white }}>
                <th style={{ padding: '8px', textAlign: 'left', fontSize: '10px', textTransform: 'uppercase' }}>Название</th>
                <th style={{ padding: '8px', textAlign: 'left', fontSize: '10px', textTransform: 'uppercase' }}>Статус</th>
                <th style={{ padding: '8px', textAlign: 'left', fontSize: '10px', textTransform: 'uppercase' }}>Сменить</th>
              </tr>
            </thead>
            <tbody>
              {reports.map(r => (
                <tr key={r.id} style={{ borderBottom: '1px solid #EEEEEE' }}>
                  <td style={{ padding: '8px', fontSize: '12px' }}>{r.title}</td>
                  <td style={{ padding: '8px' }}>
                    <span style={{
                      padding: '2px 8px', borderRadius: '20px', fontSize: '10px',
                      fontWeight: '700', textTransform: 'uppercase', color: COLORS.white,
                      background: STATUS_COLORS[r.status_name] || '#9E9E9E'
                    }}>{r.status_name || 'draft'}</span>
                  </td>
                  <td style={{ padding: '8px' }}>
                    <select value={r.status} onChange={(e) => changeStatus(r.id, parseInt(e.target.value))}
                      style={{
                        padding: '3px 6px', borderRadius: '4px', border: '1px solid #E0E0E0',
                        fontSize: '11px', fontFamily: "'Century Gothic', sans-serif", cursor: 'pointer', maxWidth: '140px',
                      }}>
                      {statuses.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p style={{ color: COLORS.gray, textAlign: 'center', padding: '20px', fontSize: '13px' }}>Нет созданных отчётов</p>
        )}
      </div>
    </div>
  )
}