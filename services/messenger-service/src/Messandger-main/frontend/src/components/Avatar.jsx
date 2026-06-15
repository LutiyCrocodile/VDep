// ГКМ brand palette: оттенки фирменного красного + нейтрали
const colors = ['#aa141e', '#c8141e', '#8c141e', '#6e1218', '#db404a', '#3a3a3a', '#525252', '#2a2a2a', '#4a0d11', '#ee7079']

export default function Avatar({ name, url, size = 'md' }) {
  const sizeClass = { sm: 'w-8 h-8 text-xs', md: 'w-10 h-10 text-sm', lg: 'w-14 h-14 text-lg' }[size]

  if (url) {
    return <img src={url} alt={name} className={`${sizeClass} rounded-full object-cover flex-shrink-0`} />
  }

  const initial = (name || '?')[0].toUpperCase()
  const colorIdx = (name || '').split('').reduce((a, c) => a + c.charCodeAt(0), 0) % colors.length
  return (
    <div className={`${sizeClass} rounded-full flex items-center justify-center font-semibold text-white flex-shrink-0`} style={{ backgroundColor: colors[colorIdx] }}>
      {initial}
    </div>
  )
}
