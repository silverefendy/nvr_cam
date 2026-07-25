path = "frontend/src/api/client.ts"
content = open(path, encoding="utf-8-sig").read()
new = """import axios from 'axios'

export const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
})

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

const NON_AUTH_ENDPOINTS = ['/config/storage', '/config/notifications', '/config/system']

apiClient.interceptors.response.use(
  (res) => res,
  (error) => {
    const url = error.config?.url || ''
    const status = error.response?.status
    const isLoginPage = window.location.pathname.includes('/login')
    if (
      status === 401 &&
      !isLoginPage &&
      !NON_AUTH_ENDPOINTS.some(ep => url.includes(ep))
    ) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('auth_user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)
"""
open(path, "w", encoding="utf-8").write(new)
print("OK client.ts")
