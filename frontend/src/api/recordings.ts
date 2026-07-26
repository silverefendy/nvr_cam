import { apiClient } from './client'
import type { Recording } from "@/types"

export const recordingsApi = {
  list: (p?: { camera_id?: string; date_from?: string; date_to?: string }) => {
    const params: Record<string, string> = {}
    if (p?.camera_id) params.camera_id = p.camera_id

    // FIX: Kirim date (bukan date_from/date_to) sesuai backend API.
    // Backend /recordings hanya terima: camera_id + date (YYYY-MM-DD).
    // Jika range multi-hari, ambil per-hari dan gabungkan.
    // Untuk simplisitas: jika date_from == date_to â†’ kirim date=date_from
    // Jika range berbeda â†’ tidak filter date (ambil semua), filter di frontend.
    if (p?.date_from && p?.date_to && p.date_from === p.date_to) {
      params.date = p.date_from
    } else if (p?.date_from && !p?.date_to) {
      params.date = p.date_from
    }

    return apiClient.get<Recording[]>('/recordings', { params }).then(r => {
      let data = r.data as any
      if (data && !Array.isArray(data) && Array.isArray(data.data)) data = data.data
      if (!Array.isArray(data)) return []

      // Filter di frontend untuk range tanggal
      if (p?.date_from || p?.date_to) {
        const from = p?.date_from ? new Date(p.date_from + 'T00:00:00') : null
        const to   = p?.date_to   ? new Date(p.date_to   + 'T23:59:59') : null
        data = data.filter((rec: Recording) => {
          const d = new Date(rec.started_at)
          if (from && d < from) return false
          if (to   && d > to)   return false
          return true
        })
      }
      return data
    })
  },

  // Ambil SEMUA rekaman tanpa filter (untuk halaman rekaman yang kosong)
  listAll: () => apiClient.get<Recording[]>('/recordings').then(r => {
    let data = r.data as any
    if (data && !Array.isArray(data) && Array.isArray(data.data)) data = data.data
    return Array.isArray(data) ? data : []
  }),

  get:         (id: number) => apiClient.get<Recording>(`/recordings/${id}`).then(r => r.data),
  playUrl: (id: number): string => {
    // HTML5 <video src="..."> tidak bisa kirim Authorization header otomatis.
    // Token diambil dari localStorage (key: 'access_token' — set oleh useAuthStore).
    // Kalau token tidak ada (belum login), URL tanpa token → backend akan 401.
    const token = localStorage.getItem('access_token') ?? '';
    const qs = token ? `?token=${encodeURIComponent(token)}` : '';
    return `/api/v1/recordings/${id}/play${qs}`;
  },
  downloadUrl: (id: number) => `/api/v1/recordings/${id}/download`,
  protect:     (id: number) => apiClient.post(`/recordings/${id}/protect`).then(r => r.data),
  delete:      (id: number) => apiClient.delete(`/recordings/${id}`),
}
