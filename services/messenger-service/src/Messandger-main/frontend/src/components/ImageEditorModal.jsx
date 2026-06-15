import { useState, useRef, useEffect } from 'react'
import {
  X, RotateCw, RotateCcw, FlipHorizontal, FlipVertical, Crop, Pencil, Type,
  Undo2, Check, Send, Eraser, Square, Circle, ArrowRight, Sliders, Smile
} from 'lucide-react'

const COLORS = ['#ff0000', '#ffffff', '#000000', '#00ff00', '#0088ff', '#ffff00', '#ff00ff', '#ff8800']
const BRUSH_SIZES = [2, 4, 8, 16]
const STICKERS = ['😀', '😎', '😍', '🔥', '👍', '❤️', '⭐', '🎉', '✅', '⚠️']

const DEFAULT_FILTERS = { brightness: 100, contrast: 100, saturate: 100, blur: 0, grayscale: 0, sepia: 0 }
const filterCss = (f) =>
  `brightness(${f.brightness}%) contrast(${f.contrast}%) saturate(${f.saturate}%) blur(${f.blur}px) grayscale(${f.grayscale}%) sepia(${f.sepia}%)`

export default function ImageEditorModal({ imageData, onSave, onClose }) {
  const canvasRef = useRef(null)
  const overlayCanvasRef = useRef(null)
  const [tool, setTool] = useState('none')
  const [drawing, setDrawing] = useState(false)
  const [brushColor, setBrushColor] = useState('#ff0000')
  const [brushSize, setBrushSize] = useState(4)
  const [history, setHistory] = useState([])
  const [historyIdx, setHistoryIdx] = useState(-1)
  const [cropStart, setCropStart] = useState(null)
  const [cropEnd, setCropEnd] = useState(null)
  const [cropping, setCropping] = useState(false)
  const [shapeStart, setShapeStart] = useState(null)
  const [shapeEnd, setShapeEnd] = useState(null)
  const [textInput, setTextInput] = useState('')
  const [textPos, setTextPos] = useState(null)
  const [fontSize, setFontSize] = useState(24)
  const [sending, setSending] = useState(false)
  const [filters, setFilters] = useState(DEFAULT_FILTERS)
  const [showFilters, setShowFilters] = useState(false)
  const [showStickers, setShowStickers] = useState(false)

  useEffect(() => {
    const image = new window.Image()
    image.onload = () => loadImageToCanvas(image)
    image.src = imageData
  }, [imageData])

  const loadImageToCanvas = (image) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const maxW = Math.min(900, window.innerWidth - 80)
    const maxH = Math.min(650, window.innerHeight - 200)
    let w = image.width, h = image.height
    if (w > maxW) { h = h * maxW / w; w = maxW }
    if (h > maxH) { w = w * maxH / h; h = maxH }
    canvas.width = Math.round(w)
    canvas.height = Math.round(h)
    const ctx = canvas.getContext('2d')
    ctx.drawImage(image, 0, 0, canvas.width, canvas.height)
    const overlay = overlayCanvasRef.current
    if (overlay) { overlay.width = canvas.width; overlay.height = canvas.height }
    pushHistory()
  }

  const pushHistory = () => {
    const canvas = canvasRef.current
    if (!canvas) return
    const data = canvas.toDataURL('image/png')
    setHistory(prev => {
      const trimmed = prev.slice(0, historyIdx + 1 < prev.length ? historyIdx + 1 : prev.length)
      const next = [...trimmed, data].slice(-30)
      setHistoryIdx(next.length - 1)
      return next
    })
  }

  const undo = () => {
    if (historyIdx < 1) return
    const newIdx = historyIdx - 1
    restoreFromHistory(newIdx)
    setHistoryIdx(newIdx)
  }

  const restoreFromHistory = (idx) => {
    const src = history[idx]
    if (!src) return
    const image = new window.Image()
    image.onload = () => {
      const canvas = canvasRef.current
      if (!canvas) return
      canvas.width = image.width
      canvas.height = image.height
      canvas.getContext('2d').drawImage(image, 0, 0)
    }
    image.src = src
  }

  const rotateCanvas = (deg) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height)
    const tmpCanvas = document.createElement('canvas')
    tmpCanvas.width = canvas.width
    tmpCanvas.height = canvas.height
    tmpCanvas.getContext('2d').putImageData(imgData, 0, 0)

    canvas.width = tmpCanvas.height
    canvas.height = tmpCanvas.width
    const newCtx = canvas.getContext('2d')
    newCtx.save()
    newCtx.translate(canvas.width / 2, canvas.height / 2)
    newCtx.rotate((deg * Math.PI) / 180)
    newCtx.drawImage(tmpCanvas, -tmpCanvas.width / 2, -tmpCanvas.height / 2)
    newCtx.restore()

    const overlay = overlayCanvasRef.current
    if (overlay) { overlay.width = canvas.width; overlay.height = canvas.height }
    pushHistory()
  }

  const flipCanvas = (horizontal) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height)
    const tmpCanvas = document.createElement('canvas')
    tmpCanvas.width = canvas.width
    tmpCanvas.height = canvas.height
    tmpCanvas.getContext('2d').putImageData(imgData, 0, 0)
    ctx.save()
    if (horizontal) {
      ctx.translate(canvas.width, 0)
      ctx.scale(-1, 1)
    } else {
      ctx.translate(0, canvas.height)
      ctx.scale(1, -1)
    }
    ctx.drawImage(tmpCanvas, 0, 0)
    ctx.restore()
    pushHistory()
  }

  const getPos = (e) => {
    const rect = canvasRef.current.getBoundingClientRect()
    return {
      x: (e.clientX - rect.left) * (canvasRef.current.width / rect.width),
      y: (e.clientY - rect.top) * (canvasRef.current.height / rect.height)
    }
  }

  const handleMouseDown = (e) => {
    if (tool === 'draw' || tool === 'eraser') {
      setDrawing(true)
      const ctx = canvasRef.current.getContext('2d')
      const pos = getPos(e)
      ctx.beginPath()
      ctx.moveTo(pos.x, pos.y)
      ctx.strokeStyle = tool === 'eraser' ? '#000000' : brushColor
      ctx.globalCompositeOperation = tool === 'eraser' ? 'destination-out' : 'source-over'
      ctx.lineWidth = tool === 'eraser' ? brushSize * 3 : brushSize
      ctx.lineCap = 'round'
      ctx.lineJoin = 'round'
    } else if (tool === 'crop') {
      setCropping(true)
      const pos = getPos(e)
      setCropStart(pos)
      setCropEnd(pos)
    } else if (tool === 'rect' || tool === 'circle' || tool === 'arrow') {
      const pos = getPos(e)
      setShapeStart(pos)
      setShapeEnd(pos)
    } else if (tool === 'text') {
      setTextPos(getPos(e))
    }
  }

  const handleMouseMove = (e) => {
    if ((tool === 'draw' || tool === 'eraser') && drawing) {
      const ctx = canvasRef.current.getContext('2d')
      const pos = getPos(e)
      ctx.lineTo(pos.x, pos.y)
      ctx.stroke()
    } else if (tool === 'crop' && cropping) {
      const pos = getPos(e)
      setCropEnd(pos)
      drawCropOverlay(cropStart, pos)
    } else if ((tool === 'rect' || tool === 'circle' || tool === 'arrow') && shapeStart) {
      const pos = getPos(e)
      setShapeEnd(pos)
      drawShapePreview(tool, shapeStart, pos)
    }
  }

  const handleMouseUp = () => {
    if ((tool === 'draw' || tool === 'eraser') && drawing) {
      setDrawing(false)
      canvasRef.current.getContext('2d').globalCompositeOperation = 'source-over'
      pushHistory()
    }
    if (tool === 'crop' && cropping) setCropping(false)
    if ((tool === 'rect' || tool === 'circle' || tool === 'arrow') && shapeStart && shapeEnd) {
      commitShape(tool, shapeStart, shapeEnd)
      setShapeStart(null); setShapeEnd(null)
      clearOverlay()
    }
  }

  const clearOverlay = () => {
    const overlay = overlayCanvasRef.current
    if (overlay) overlay.getContext('2d').clearRect(0, 0, overlay.width, overlay.height)
  }

  const drawShapePreview = (kind, a, b) => {
    const overlay = overlayCanvasRef.current
    if (!overlay) return
    const ctx = overlay.getContext('2d')
    ctx.clearRect(0, 0, overlay.width, overlay.height)
    ctx.strokeStyle = brushColor
    ctx.lineWidth = brushSize
    ctx.setLineDash([5, 4])
    if (kind === 'rect') {
      ctx.strokeRect(Math.min(a.x, b.x), Math.min(a.y, b.y), Math.abs(b.x - a.x), Math.abs(b.y - a.y))
    } else if (kind === 'circle') {
      ctx.beginPath()
      const cx = (a.x + b.x) / 2, cy = (a.y + b.y) / 2
      const rx = Math.abs(b.x - a.x) / 2, ry = Math.abs(b.y - a.y) / 2
      ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2)
      ctx.stroke()
    } else if (kind === 'arrow') {
      drawArrow(ctx, a, b)
    }
    ctx.setLineDash([])
  }

  const drawArrow = (ctx, a, b) => {
    const dx = b.x - a.x, dy = b.y - a.y
    const angle = Math.atan2(dy, dx)
    const headLen = Math.max(12, brushSize * 4)
    ctx.beginPath()
    ctx.moveTo(a.x, a.y)
    ctx.lineTo(b.x, b.y)
    ctx.lineTo(b.x - headLen * Math.cos(angle - Math.PI / 6), b.y - headLen * Math.sin(angle - Math.PI / 6))
    ctx.moveTo(b.x, b.y)
    ctx.lineTo(b.x - headLen * Math.cos(angle + Math.PI / 6), b.y - headLen * Math.sin(angle + Math.PI / 6))
    ctx.stroke()
  }

  const commitShape = (kind, a, b) => {
    const ctx = canvasRef.current.getContext('2d')
    ctx.strokeStyle = brushColor
    ctx.fillStyle = brushColor
    ctx.lineWidth = brushSize
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'
    if (kind === 'rect') {
      ctx.strokeRect(Math.min(a.x, b.x), Math.min(a.y, b.y), Math.abs(b.x - a.x), Math.abs(b.y - a.y))
    } else if (kind === 'circle') {
      ctx.beginPath()
      const cx = (a.x + b.x) / 2, cy = (a.y + b.y) / 2
      const rx = Math.abs(b.x - a.x) / 2, ry = Math.abs(b.y - a.y) / 2
      ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2)
      ctx.stroke()
    } else if (kind === 'arrow') {
      drawArrow(ctx, a, b)
    }
    pushHistory()
  }

  const drawCropOverlay = (start, end) => {
    const overlay = overlayCanvasRef.current
    if (!overlay || !start || !end) return
    const ctx = overlay.getContext('2d')
    const w = overlay.width, h = overlay.height
    ctx.clearRect(0, 0, w, h)
    ctx.fillStyle = 'rgba(0,0,0,0.55)'
    ctx.fillRect(0, 0, w, h)
    const rx = Math.min(start.x, end.x), ry = Math.min(start.y, end.y)
    const rw = Math.abs(end.x - start.x), rh = Math.abs(end.y - start.y)
    ctx.clearRect(rx, ry, rw, rh)
    ctx.strokeStyle = '#ffffff'
    ctx.lineWidth = 1.5
    ctx.setLineDash([6, 4])
    ctx.strokeRect(rx, ry, rw, rh)
    ctx.setLineDash([])
    const hs = 6
    const corners = [[rx, ry], [rx + rw, ry], [rx, ry + rh], [rx + rw, ry + rh]]
    corners.forEach(([cx, cy]) => { ctx.fillStyle = '#fff'; ctx.fillRect(cx - hs / 2, cy - hs / 2, hs, hs) })
    if (rw > 40 && rh > 20) {
      ctx.fillStyle = 'rgba(0,0,0,0.7)'; ctx.fillRect(rx + rw / 2 - 30, ry + rh / 2 - 10, 60, 20)
      ctx.fillStyle = '#fff'; ctx.font = '11px sans-serif'; ctx.textAlign = 'center'
      ctx.fillText(`${Math.round(rw)}×${Math.round(rh)}`, rx + rw / 2, ry + rh / 2 + 4)
    }
  }

  const applyCrop = () => {
    if (!cropStart || !cropEnd) return
    const canvas = canvasRef.current, ctx = canvas.getContext('2d')
    const x = Math.min(cropStart.x, cropEnd.x), y = Math.min(cropStart.y, cropEnd.y)
    const w = Math.abs(cropEnd.x - cropStart.x), h = Math.abs(cropEnd.y - cropStart.y)
    if (w < 10 || h < 10) return
    const imgData = ctx.getImageData(x, y, w, h)
    canvas.width = w; canvas.height = h
    ctx.putImageData(imgData, 0, 0)
    const overlay = overlayCanvasRef.current
    if (overlay) { overlay.width = w; overlay.height = h; overlay.getContext('2d').clearRect(0, 0, w, h) }
    setCropStart(null); setCropEnd(null); setTool('none')
    pushHistory()
  }

  const cancelCrop = () => {
    setCropStart(null); setCropEnd(null)
    clearOverlay()
  }

  const addText = () => {
    if (!textPos || !textInput.trim()) return
    const ctx = canvasRef.current.getContext('2d')
    ctx.font = `bold ${fontSize}px system-ui, -apple-system, sans-serif`
    ctx.fillStyle = brushColor
    ctx.shadowColor = 'rgba(0,0,0,0.4)'; ctx.shadowBlur = 3; ctx.shadowOffsetX = 1; ctx.shadowOffsetY = 1
    ctx.fillText(textInput, textPos.x, textPos.y)
    ctx.shadowColor = 'transparent'
    setTextInput(''); setTextPos(null); setTool('none')
    pushHistory()
  }

  const addSticker = (emoji) => {
    const ctx = canvasRef.current.getContext('2d')
    const size = 64
    const x = canvasRef.current.width / 2 - size / 2
    const y = canvasRef.current.height / 2
    ctx.font = `${size}px sans-serif`
    ctx.textAlign = 'left'
    ctx.fillText(emoji, x, y)
    pushHistory()
  }

  // Применить фильтры (запекаем CSS-фильтр в пиксели)
  const bakeFilters = () => {
    const canvas = canvasRef.current
    if (!canvas) return
    const tmp = document.createElement('canvas')
    tmp.width = canvas.width; tmp.height = canvas.height
    const tctx = tmp.getContext('2d')
    tctx.filter = filterCss(filters)
    tctx.drawImage(canvas, 0, 0)
    const ctx = canvas.getContext('2d')
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    ctx.drawImage(tmp, 0, 0)
  }

  const handleSendEdited = () => {
    setSending(true)
    bakeFilters()
    canvasRef.current?.toBlob((blob) => { if (blob) onSave(blob); setSending(false) }, 'image/png')
  }

  const handleSendOriginal = () => {
    setSending(true)
    fetch(imageData).then(r => r.blob()).then(blob => { onSave(blob); setSending(false) })
  }

  const toolBtn = (id, icon, title) => (
    <button
      onClick={() => { if (tool === 'crop') cancelCrop(); setTool(tool === id ? 'none' : id) }}
      className={`p-2 rounded-lg transition-colors ${tool === id ? 'bg-primary-600 text-white shadow-lg' : 'hover:bg-dark-700 text-dark-400 hover:text-white'}`}
      title={title}
    >{icon}</button>
  )

  const resetFilters = () => setFilters(DEFAULT_FILTERS)

  return (
    <div className="fixed inset-0 z-50 bg-black/85 flex items-center justify-center p-3" onClick={onClose}>
      <div className="bg-dark-900 border border-dark-700 rounded-2xl w-full max-w-[92vw] max-h-[92vh] flex flex-col overflow-hidden shadow-2xl" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-dark-700 bg-dark-900/95">
          <h3 className="text-white font-bold text-sm">Редактор изображения</h3>
          <div className="flex items-center gap-2">
            <button onClick={undo} disabled={historyIdx < 1} className="p-2 rounded-lg hover:bg-dark-700 text-dark-400 hover:text-white disabled:opacity-30 transition-colors" title="Отменить (Ctrl+Z)"><Undo2 size={16} /></button>
            <div className="w-px h-5 bg-dark-700" />
            <button onClick={handleSendOriginal} disabled={sending} className="px-3 py-1.5 bg-dark-700 hover:bg-dark-600 text-dark-200 text-xs rounded-lg transition-colors disabled:opacity-50">Без изменений</button>
            <button onClick={handleSendEdited} disabled={sending} className="px-4 py-1.5 bg-primary-600 hover:bg-primary-700 text-white text-xs rounded-lg flex items-center gap-1.5 transition-colors disabled:opacity-50 font-medium"><Send size={13} /> Отправить</button>
            <button onClick={onClose} className="p-2 rounded-lg hover:bg-dark-700 text-dark-400 hover:text-white transition-colors"><X size={16} /></button>
          </div>
        </div>

        {/* Toolbar */}
        <div className="flex items-center gap-1 px-5 py-2 border-b border-dark-700 bg-dark-900/80 flex-wrap">
          <div className="flex items-center gap-0.5 bg-dark-800 rounded-lg p-0.5">
            <button onClick={() => rotateCanvas(-90)} className="p-1.5 rounded hover:bg-dark-700 text-dark-400 hover:text-white" title="Повернуть влево"><RotateCcw size={15} /></button>
            <button onClick={() => rotateCanvas(90)} className="p-1.5 rounded hover:bg-dark-700 text-dark-400 hover:text-white" title="Повернуть вправо"><RotateCw size={15} /></button>
            <button onClick={() => flipCanvas(true)} className="p-1.5 rounded hover:bg-dark-700 text-dark-400 hover:text-white" title="Отразить горизонтально"><FlipHorizontal size={15} /></button>
            <button onClick={() => flipCanvas(false)} className="p-1.5 rounded hover:bg-dark-700 text-dark-400 hover:text-white" title="Отразить вертикально"><FlipVertical size={15} /></button>
          </div>
          <div className="w-px h-6 bg-dark-700 mx-1" />

          <div className="flex items-center gap-0.5 bg-dark-800 rounded-lg p-0.5">
            {toolBtn('draw', <Pencil size={15} />, 'Рисовать')}
            {toolBtn('eraser', <Eraser size={15} />, 'Ластик')}
            {toolBtn('crop', <Crop size={15} />, 'Обрезать')}
            {toolBtn('text', <Type size={15} />, 'Текст')}
            {toolBtn('rect', <Square size={15} />, 'Прямоугольник')}
            {toolBtn('circle', <Circle size={15} />, 'Круг')}
            {toolBtn('arrow', <ArrowRight size={15} />, 'Стрелка')}
          </div>

          <div className="w-px h-6 bg-dark-700 mx-1" />

          <button
            onClick={() => { setShowFilters(s => !s); setShowStickers(false) }}
            className={`p-2 rounded-lg transition-colors ${showFilters ? 'bg-primary-600 text-white' : 'hover:bg-dark-700 text-dark-400 hover:text-white'}`}
            title="Фильтры"
          ><Sliders size={15} /></button>
          <button
            onClick={() => { setShowStickers(s => !s); setShowFilters(false) }}
            className={`p-2 rounded-lg transition-colors ${showStickers ? 'bg-primary-600 text-white' : 'hover:bg-dark-700 text-dark-400 hover:text-white'}`}
            title="Стикеры"
          ><Smile size={15} /></button>

          {/* Цвета / размер кисти */}
          {(tool === 'draw' || tool === 'text' || tool === 'eraser' || tool === 'rect' || tool === 'circle' || tool === 'arrow') && (
            <>
              <div className="w-px h-6 bg-dark-700 mx-1" />
              {tool !== 'eraser' && (
                <div className="flex items-center gap-1">
                  {COLORS.map(c => (
                    <button key={c} onClick={() => setBrushColor(c)}
                      className={`w-5 h-5 rounded-full border-2 transition-transform ${brushColor === c ? 'border-white scale-125' : 'border-transparent hover:border-dark-400'}`}
                      style={{ backgroundColor: c }} />
                  ))}
                </div>
              )}
              <div className="w-px h-6 bg-dark-700 mx-1" />
              <div className="flex items-center gap-0.5 bg-dark-800 rounded-lg p-0.5">
                {BRUSH_SIZES.map(s => (
                  <button key={s} onClick={() => setBrushSize(s)}
                    className={`w-7 h-7 rounded flex items-center justify-center transition-colors ${brushSize === s ? 'bg-primary-600 text-white' : 'text-dark-400 hover:text-white hover:bg-dark-700'}`}>
                    <span className="rounded-full bg-current" style={{ width: Math.min(s + 2, 14), height: Math.min(s + 2, 14) }} />
                  </button>
                ))}
              </div>
              {tool === 'text' && (
                <>
                  <div className="w-px h-6 bg-dark-700 mx-1" />
                  <input
                    type="range" min="12" max="80" value={fontSize}
                    onChange={(e) => setFontSize(parseInt(e.target.value))}
                    className="w-24"
                    title={`Размер шрифта: ${fontSize}px`}
                  />
                  <span className="text-xs text-dark-400 w-9 text-right">{fontSize}px</span>
                </>
              )}
            </>
          )}

          {tool === 'crop' && cropStart && cropEnd && (
            <>
              <div className="w-px h-6 bg-dark-700 mx-1" />
              <button onClick={applyCrop} className="px-3 py-1 bg-green-600 hover:bg-green-700 text-white text-xs rounded-lg font-medium"><Check size={13} className="inline mr-1" />Обрезать</button>
              <button onClick={cancelCrop} className="px-3 py-1 bg-dark-700 hover:bg-dark-600 text-dark-300 text-xs rounded-lg">Отмена</button>
            </>
          )}
        </div>

        {/* Filters panel */}
        {showFilters && (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 px-5 py-3 border-b border-dark-700 bg-dark-800/40">
            {[
              { k: 'brightness', label: 'Яркость', min: 0, max: 200, def: 100, suffix: '%' },
              { k: 'contrast', label: 'Контраст', min: 0, max: 200, def: 100, suffix: '%' },
              { k: 'saturate', label: 'Насыщенность', min: 0, max: 200, def: 100, suffix: '%' },
              { k: 'blur', label: 'Размытие', min: 0, max: 10, def: 0, suffix: 'px' },
              { k: 'grayscale', label: 'Ч/Б', min: 0, max: 100, def: 0, suffix: '%' },
              { k: 'sepia', label: 'Сепия', min: 0, max: 100, def: 0, suffix: '%' },
            ].map(({ k, label, min, max, def, suffix }) => (
              <div key={k} className="flex items-center gap-2">
                <label className="text-xs text-dark-300 w-28">{label}</label>
                <input
                  type="range" min={min} max={max} value={filters[k]}
                  onChange={(e) => setFilters({ ...filters, [k]: parseFloat(e.target.value) })}
                  className="flex-1"
                />
                <span className="text-xs text-dark-400 w-12 text-right">{filters[k]}{suffix}</span>
              </div>
            ))}
            <div className="col-span-2 md:col-span-3 flex justify-end">
              <button onClick={resetFilters} className="px-3 py-1 bg-dark-700 hover:bg-dark-600 text-dark-200 text-xs rounded-lg">Сбросить фильтры</button>
            </div>
          </div>
        )}

        {/* Stickers panel */}
        {showStickers && (
          <div className="flex items-center gap-2 px-5 py-3 border-b border-dark-700 bg-dark-800/40 flex-wrap">
            <span className="text-xs text-dark-400 mr-1">Стикеры:</span>
            {STICKERS.map(s => (
              <button key={s} onClick={() => addSticker(s)}
                className="text-2xl w-10 h-10 rounded-lg hover:bg-dark-700 transition-colors">{s}</button>
            ))}
          </div>
        )}

        {/* Text input bar */}
        {tool === 'text' && textPos && (
          <div className="flex items-center gap-2 px-5 py-2 bg-dark-800/80 border-b border-dark-700">
            <span className="text-xs text-dark-400">Текст:</span>
            <input type="text" value={textInput} onChange={e => setTextInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && addText()}
              className="flex-1 bg-dark-700 border border-dark-600 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-1 focus:ring-primary-500"
              placeholder="Введите текст и нажмите Enter..." autoFocus />
            <button onClick={addText} disabled={!textInput.trim()} className="px-3 py-1.5 bg-primary-600 text-white text-xs rounded-lg disabled:opacity-40 font-medium">Добавить</button>
          </div>
        )}

        {/* Hints */}
        {tool === 'crop' && !cropStart && (
          <div className="px-5 py-1.5 bg-dark-800/60 border-b border-dark-700">
            <p className="text-xs text-dark-400">Выделите область для обрезки</p>
          </div>
        )}
        {tool === 'text' && !textPos && (
          <div className="px-5 py-1.5 bg-dark-800/60 border-b border-dark-700">
            <p className="text-xs text-dark-400">Кликните на изображение, чтобы разместить текст</p>
          </div>
        )}
        {(tool === 'rect' || tool === 'circle' || tool === 'arrow') && (
          <div className="px-5 py-1.5 bg-dark-800/60 border-b border-dark-700">
            <p className="text-xs text-dark-400">Удерживайте и тяните, чтобы нарисовать {tool === 'rect' ? 'прямоугольник' : tool === 'circle' ? 'круг' : 'стрелку'}</p>
          </div>
        )}

        {/* Canvas */}
        <div className="flex-1 overflow-auto flex items-center justify-center p-4 bg-dark-950/90" style={{ minHeight: '300px' }}>
          <div className="relative inline-block">
            <canvas ref={canvasRef}
              className="rounded-lg shadow-xl"
              style={{
                maxWidth: '100%',
                maxHeight: '62vh',
                cursor: tool === 'draw' || tool === 'eraser' || tool === 'crop' || tool === 'rect' || tool === 'circle' || tool === 'arrow'
                  ? 'crosshair'
                  : tool === 'text' ? 'text' : 'default',
                filter: filterCss(filters),
              }}
              onMouseDown={handleMouseDown} onMouseMove={handleMouseMove} onMouseUp={handleMouseUp} onMouseLeave={handleMouseUp} />
            <canvas ref={overlayCanvasRef}
              className="absolute inset-0 rounded-lg pointer-events-none"
              style={{ maxWidth: '100%', maxHeight: '62vh' }} />
          </div>
        </div>
      </div>
    </div>
  )
}
