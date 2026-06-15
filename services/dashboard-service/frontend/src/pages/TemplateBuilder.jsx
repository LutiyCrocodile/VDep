import { useState, useEffect } from 'react'
import { apiFetch } from '../authStore'

const COLORS = {
  primary: '#AA141E',
  primaryDark: '#8B1019',
  primaryLight: '#D4404A',
  black: '#1A1A1A',
  darkGray: '#333333',
  gray: '#666666',
  lightGray: '#F0F0F0',
  white: '#FFFFFF',
  bgLight: '#FAFAFA',
  bgDark: '#F5F5F5',
}

const styles = {
  label: {
    fontSize: '13px',
    fontWeight: '600',
    color: COLORS.darkGray,
    marginBottom: '6px',
    display: 'block',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    fontFamily: "'Century Gothic', 'Futura', sans-serif",
  },
  input: {
    width: '100%',
    padding: '11px 16px',
    fontSize: '14px',
    fontFamily: "'Century Gothic', 'Futura', 'Trebuchet MS', sans-serif",
    borderRadius: '8px',
    border: '1.5px solid #E0E0E0',
    backgroundColor: COLORS.white,
    color: COLORS.black,
    outline: 'none',
  },
  select: {
    padding: '11px 16px',
    fontSize: '14px',
    fontFamily: "'Century Gothic', 'Futura', 'Trebuchet MS', sans-serif",
    borderRadius: '8px',
    border: '1.5px solid #E0E0E0',
    backgroundColor: COLORS.white,
    color: COLORS.black,
    cursor: 'pointer',
    outline: 'none',
    minWidth: '200px',
  },
  button: {
    padding: '11px 24px',
    fontSize: '14px',
    fontFamily: "'Century Gothic', 'Futura', 'Trebuchet MS', sans-serif",
    fontWeight: '700',
    borderRadius: '8px',
    border: 'none',
    cursor: 'pointer',
    letterSpacing: '0.3px',
    textTransform: 'uppercase',
  },
  card: {
    background: COLORS.white,
    border: '1px solid #E8E8E8',
    borderRadius: '8px',
    padding: '14px',
    marginBottom: '8px',
    cursor: 'pointer',
    transition: 'all 0.2s',
    fontSize: '13px',
    fontFamily: "'Century Gothic', sans-serif",
  },
  cardActive: {
    background: COLORS.primary,
    color: COLORS.white,
    border: `1px solid ${COLORS.primary}`,
  },
  elementCard: {
    background: COLORS.bgDark,
    padding: '14px',
    marginBottom: '10px',
    borderRadius: '8px',
    border: '1px solid #E8E8E8',
  },
}

export default function TemplateBuilder() {
  const [templates, setTemplates] = useState([])
  const [templateName, setTemplateName] = useState('')
  const [slides, setSlides] = useState([
    {
      id: 1,
      layout: 'title',
      elements: [
        { type: 'title', content: 'Новый отчёт' },
        { type: 'subtitle', content: 'Департамент городского имущества' },
        { type: 'date', content: new Date().toLocaleDateString('ru-RU') }
      ]
    }
  ])
  const [selectedSlide, setSelectedSlide] = useState(0)

  useEffect(() => {
    loadTemplates()
  }, [])

  const loadTemplates = () => {
    apiFetch('/api/report-templates/')
      .then(res => res.json())
      .then(data => setTemplates(Array.isArray(data) ? data : []))
  }

  const saveTemplate = async () => {
    const config = {
      slides: slides,
      style: { primary_color: 'AA141E', accent_color: 'D4404A', font: 'Century Gothic' }
    }

    const response = await apiFetch('/api/report-templates/', {
      method: 'POST',
      body: JSON.stringify({
        name: templateName,
        description: 'Шаблон отчёта',
        config: config,
        is_public: false,
        created_by: 1
      })
    })

    if (response.ok) {
      alert('Шаблон сохранён!')
      loadTemplates()
      setTemplateName('')
    }
  }

  const addSlide = (layout) => {
    const newSlide = { id: slides.length + 1, layout, elements: [] }
    setSlides([...slides, newSlide])
    setSelectedSlide(slides.length)
  }

  const removeSlide = (index) => {
    if (slides.length <= 1) { alert('Должен быть хотя бы один слайд'); return }
    const updated = slides.filter((_, i) => i !== index)
    setSlides(updated)
    if (selectedSlide >= updated.length) setSelectedSlide(updated.length - 1)
  }

  const addElement = (type) => {
    const updated = [...slides]
    updated[selectedSlide].elements.push({ type, content: '', chart_type: 'bar', title: '' })
    setSlides(updated)
  }

  const removeElement = (elemIndex) => {
    const updated = [...slides]
    updated[selectedSlide].elements.splice(elemIndex, 1)
    setSlides(updated)
  }

  const updateElement = (elemIndex, field, value) => {
    const updated = [...slides]
    updated[selectedSlide].elements[elemIndex][field] = value
    setSlides(updated)
  }

  return (
    <div style={{ padding: '32px 40px', fontFamily: "'Century Gothic', 'Futura', sans-serif" }}>
      <h1 style={{ fontSize: '24px', color: COLORS.black, marginBottom: '24px' }}>КОНСТРУКТОР ШАБЛОНОВ</h1>

      <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: '24px' }}>
        {/* Панель слайдов */}
        <div style={{ background: COLORS.bgDark, padding: '16px', borderRadius: '8px', border: '1px solid #E8E8E8' }}>
          <div style={styles.label}>СЛАЙДЫ</div>
          {slides.map((slide, i) => (
            <div
              key={slide.id}
              onClick={() => setSelectedSlide(i)}
              style={{
                ...styles.card,
                ...(selectedSlide === i ? styles.cardActive : {}),
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              }}
            >
              <span>Слайд {slide.id} — {slide.layout}</span>
              <span onClick={(e) => { e.stopPropagation(); removeSlide(i); }}
                style={{ cursor: 'pointer', opacity: 0.6, fontSize: '16px' }}>×</span>
            </div>
          ))}
          <div style={{ marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <button onClick={() => addSlide('title')} style={{ ...styles.button, background: COLORS.white, color: COLORS.primary, border: `2px solid ${COLORS.primary}`, padding: '8px', fontSize: '12px', width: '100%' }}>
              Титульный слайд
            </button>
            <button onClick={() => addSlide('content')} style={{ ...styles.button, background: COLORS.white, color: COLORS.primary, border: `2px solid ${COLORS.primary}`, padding: '8px', fontSize: '12px', width: '100%' }}>
              Слайд с контентом
            </button>
            <button onClick={() => addSlide('two_columns')} style={{ ...styles.button, background: COLORS.white, color: COLORS.primary, border: `2px solid ${COLORS.primary}`, padding: '8px', fontSize: '12px', width: '100%' }}>
              Две колонки
            </button>
          </div>
        </div>

        {/* Редактор */}
        <div>
          <div style={styles.label}>НАЗВАНИЕ ШАБЛОНА</div>
          <input
            type="text"
            value={templateName}
            onChange={(e) => setTemplateName(e.target.value)}
            placeholder="Например: Ежеквартальный отчёт по реновации"
            style={{ ...styles.input, marginBottom: '16px' }}
          />

          <div style={{ marginBottom: '16px' }}>
            <div style={styles.label}>ЭЛЕМЕНТЫ СЛАЙДА {selectedSlide + 1}</div>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <button onClick={() => addElement('heading')} style={{ ...styles.button, background: COLORS.white, color: COLORS.primary, border: `2px solid ${COLORS.primary}`, padding: '8px 16px', fontSize: '12px' }}>
                Заголовок
              </button>
              <button onClick={() => addElement('text')} style={{ ...styles.button, background: COLORS.white, color: COLORS.primary, border: `2px solid ${COLORS.primary}`, padding: '8px 16px', fontSize: '12px' }}>
                Текст
              </button>
              <button onClick={() => addElement('chart')} style={{ ...styles.button, background: COLORS.white, color: COLORS.primary, border: `2px solid ${COLORS.primary}`, padding: '8px 16px', fontSize: '12px' }}>
                График
              </button>
              <button onClick={() => addElement('table')} style={{ ...styles.button, background: COLORS.white, color: COLORS.primary, border: `2px solid ${COLORS.primary}`, padding: '8px 16px', fontSize: '12px' }}>
                Таблица
              </button>
            </div>
          </div>

          {slides[selectedSlide]?.elements.map((el, i) => (
            <div key={i} style={styles.elementCard}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <strong style={{ textTransform: 'uppercase', fontSize: '11px', color: COLORS.gray, letterSpacing: '0.5px' }}>
                  {el.type}
                </strong>
                <button onClick={() => removeElement(i)}
                  style={{ color: COLORS.primary, border: 'none', background: 'none', cursor: 'pointer', fontWeight: '700' }}>
                  ×
                </button>
              </div>

              {(el.type === 'text' || el.type === 'heading' || el.type === 'title' || el.type === 'subtitle') && (
                <textarea
                  value={el.content}
                  onChange={(e) => updateElement(i, 'content', e.target.value)}
                  placeholder="Введите текст..."
                  rows={2}
                  style={{ ...styles.input, fontFamily: styles.input.fontFamily }}
                />
              )}

              {el.type === 'chart' && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                  <select value={el.chart_type} onChange={(e) => updateElement(i, 'chart_type', e.target.value)} style={styles.select}>
                    <option value="bar">Столбчатый</option>
                    <option value="line">Линейный</option>
                    <option value="pie">Круговой</option>
                  </select>
                  <input
                    type="text"
                    value={el.title}
                    onChange={(e) => updateElement(i, 'title', e.target.value)}
                    placeholder="Название графика"
                    style={styles.input}
                  />
                </div>
              )}

              {el.type === 'table' && (
                <p style={{ fontSize: '12px', color: COLORS.gray }}>
                  Таблица будет заполнена данными автоматически
                </p>
              )}
            </div>
          ))}

          {slides[selectedSlide]?.elements.length === 0 && (
            <p style={{ color: COLORS.gray, fontSize: '13px', textAlign: 'center', padding: '20px' }}>
              Добавьте элементы на слайд
            </p>
          )}
        </div>
      </div>

      <button onClick={saveTemplate} style={{
        ...styles.button,
        background: COLORS.primary,
        color: COLORS.white,
        marginTop: '24px',
        padding: '14px 32px',
        fontSize: '15px',
      }}>
        СОХРАНИТЬ ШАБЛОН
      </button>

      {/* Список существующих шаблонов */}
      <div style={{ marginTop: '40px' }}>
        <h2 style={{ fontSize: '18px', color: COLORS.black, marginBottom: '16px' }}>СОХРАНЁННЫЕ ШАБЛОНЫ</h2>
        {templates.length > 0 ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '16px' }}>
            {templates.map(t => (
              <div key={t.id} style={{ background: COLORS.white, padding: '16px', borderRadius: '8px', border: '1px solid #E8E8E8' }}>
                <div style={{ fontWeight: '700', marginBottom: '4px' }}>{t.name}</div>
                <div style={{ fontSize: '12px', color: COLORS.gray }}>
                  Слайдов: {t.config?.slides?.length || 0}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ color: COLORS.gray, fontSize: '13px' }}>Нет сохранённых шаблонов</p>
        )}
      </div>
    </div>
  )
}