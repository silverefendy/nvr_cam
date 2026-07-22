import { apiClient } from './client'
import type { StorageStatus } from "@/types"
import type { AxiosResponse } from 'axios'

export const storageApi = {
  getStatus:           () => apiClient.get<StorageStatus>('/storage').then((r: AxiosResponse<StorageStatus>) => r.data),
  getStatsByCamera:    () => apiClient.get<CameraStorageStat[]>('/storage/stats/cameras').then(r => r.data),
  getCleanupSchedule:  () => apiClient.get('/storage/schedule').then(r => r.data),
  saveCleanupSchedule: (body: { enabled: boolean; hour: number; minute: number }) =>
                         apiClient.put('/storage/schedule', body).then(r => r.data),
  manualCleanup:       () => apiClient.post('/storage/cleanup').then((r: AxiosResponse) => r.data),
}

export interface CameraStorageStat {
  camera_id:  string
  drive:      string
  file_count: number
  total_mb:   number
}