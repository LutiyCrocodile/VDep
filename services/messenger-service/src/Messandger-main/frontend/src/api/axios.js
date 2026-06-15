import axios from 'axios'
import toast from 'react-hot-toast'
import { getPortalLoginUrl } from '../lib/portal-url'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 30000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const cfg = error.config || {}
    const status = error.response?.status
    const detail = error.response?.data?.detail
    const reqId = error.response?.headers?.['x-request-id']

    if (status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      window.location.href = getPortalLoginUrl()
      return Promise.reject(error)
    }

    if (cfg.skipErrorToast) return Promise.reject(error)

    let msg = detail
    if (!msg) {
      if (error.code === 'ECONNABORTED') msg = 'Превышено время ожидания запроса'
      else if (!error.response) msg = 'Сервер недоступен. Проверьте интернет-соединение.'
      else if (status === 403) msg = 'Недостаточно прав'
      else if (status === 404) msg = 'Не найдено'
      else if (status === 413) msg = 'Файл слишком большой'
      else if (status === 422) msg = 'Ошибка валидации данных'
      else if (status === 429) msg = 'Слишком много запросов. Подождите.'
      else if (status >= 500) msg = `Ошибка сервера${reqId ? ` (ID: ${reqId})` : ''}`
      else msg = 'Ошибка запроса'
    }
    if (msg && status !== 401) {
      toast.error(typeof msg === 'string' ? msg : 'Ошибка', { id: `err-${status}-${cfg.url}` })
    }
    return Promise.reject(error)
  }
)

export default api
