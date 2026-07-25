path = "frontend/src/api/recordings.ts"
content = """import { apiClient } from './client'
import type { Recording } from "@/types"

export const recordingsApi = {
  list: (p?: { camera_id?: string; date_from?: string; date_to?: string }) => {
    const params: Record<string, string> = {}
    if (p?.camera_id) params.camera_id = p.camera_id
    if (p?.date_from && (!p?.date_to || p.date_from === p.date_to)) {
      params.date = p.date_from
    }
    return apiClient.get<Recording[]>('/recordings', { params }).then(r => {
      let data = r.data as any
      if (data && !Array.isArray(data) && Array.isArray(data.data)) data = data.data
      if (!Array.isArray(data)) return []
      if (p?.date_from || p?.date_to) {
        const from = p.date_from ? new Date(p.date_from + 'T00:00:00') : null
        const to   = p.date_to   ? new Date(p.date_to   + 'T23:59:59') : null
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
  get:         (id: number) => apiClient.get<Recording>(`/recordings/${id}`).then(r => r.data),
  playUrl:     (id: number) => `/api/v1/recordings/${id}/play`,
  downloadUrl: (id: number) => `/api/v1/recordings/${id}/download`,
  protect:     (id: number) => apiClient.post(`/recordings/${id}/protect`).then(r => r.data),
  delete:      (id: number) => apiClient.delete(`/recordings/${id}`),
}
"""
open(path, "w", encoding="utf-8").write(content)
print("OK recordings.ts")
