import { useState, useEffect } from 'react'

function App() {
  const [messages, setMessages] = useState([])
  const [helloText, setHelloText] = useState('')

  // Запрашиваем приветствие при загрузке
  useEffect(() => {
    fetch('/api/hello/')
      .then(res => res.json())
      .then(data => setHelloText(data.message))
      .catch(() => setHelloText('Не удалось подключиться к серверу'))
  }, [])

  // Запрашиваем сообщения
  const loadMessages = () => {
    fetch('/api/messages/')
      .then(res => res.json())
      .then(data => setMessages(data))
      .catch(() => alert('Ошибка загрузки сообщений'))
  }

  return (
    <div style={{ maxWidth: '600px', margin: '50px auto', fontFamily: 'Arial' }}>
      <h1>{helloText || 'Загрузка...'}</h1>

      <button onClick={loadMessages} style={{
        padding: '10px 20px',
        fontSize: '16px',
        cursor: 'pointer',
        margin: '20px 0',
        backgroundColor: '#646cff',
        color: 'white',
        border: 'none',
        borderRadius: '8px'
      }}>
        Загрузить сообщения из MySQL
      </button>

      <ul>
        {messages.map(msg => (
          <li key={msg.id} style={{ margin: '10px 0', padding: '10px', border: '1px solid #eee', borderRadius: '8px' }}>
            <strong>{msg.text}</strong>
            <br />
            <small style={{ color: '#888' }}>
              {new Date(msg.created_at).toLocaleString('ru-RU')}
            </small>
          </li>
        ))}
      </ul>

      {messages.length === 0 && (
        <p style={{ color: '#888' }}>Сообщений пока нет. Добавьте их в админке Django!</p>
      )}
    </div>
  )
}

export default App


@action(detail=True, methods=['post'])
def generate_pptx(self, request, pk=None):
    report = self.get_object()
    if not report.template:
        return Response({'error': 'Нет шаблона'}, status=400)

    generator = PPTXGenerator(report.template.config)
    pptx_path = generator.generate()

    return FileResponse(open(pptx_path, 'rb'),
                        content_type='application/...presentationml.presentation')


