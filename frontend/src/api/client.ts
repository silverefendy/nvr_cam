import axios from 'axios'

export const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,  // turun dari 30s → 10s agar UI tidak hang lama saat error
})

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

apiClient.interceptors.response.use(
  (res) => res,
  (error) => {
    // Hanya redirect ke login jika 401 DAN bukan di halaman login itu sendiri
    if (error.response?.status === 401 && !window.location.pathname.includes('/login')) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('auth_user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)
