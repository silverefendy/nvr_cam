path = "frontend/src/api/storage.ts"
content = """import { apiClient } from './client'
import type { StorageStatus } from "@/types"

export const storageApi = {
  getStatus: () => apiClient.get('/storage').then(r => {
    const d = r.data as any
    if (d && d.drives !== undefined) return d as StorageStatus
    if (d && d.data && d.data.drives !== undefined) return d.data as StorageStatus
    return { drives: [], total_tb: 0, used_tb: 0, free_tb: 0, estimated_days_remaining: 0, threshold_pct: 10 } as StorageStatus
  }),
  getStatsByCamera: () => apiClient.get('/storage/stats/cameras').then(r => {
    const d = r.data as any
    return Array.isArray(d) ? d : (Array.isArray(d?.data) ? d.data : [])
  }),
  getCleanupSchedule:  () => apiClient.get('/storage/schedule').then(r => r.data),
  saveCleanupSchedule: (body: { enabled: boolean; hour: number; minute: number }) =>
                         apiClient.put('/storage/schedule', body).then(r => r.data),
  manualCleanup:       () => apiClient.post('/storage/cleanup').then(r => r.data),
}

export interface CameraStorageStat {
  camera_id:  string
  drive:      string
  file_count: number
  total_mb:   number
}
"""
open(path, "w", encoding="utf-8").write(content)
print("OK storage.ts")
