import { apiClient } from './client'
import type { Recording } from "@/types"
export const recordingsApi = {
  list:    (p?: { camera_id?: string; date_from?: string; date_to?: string }) => apiClient.get<Recording[]>('/recordings', { params: p }).then(r => r.data),
  get:     (id: number) => apiClient.get<Recording>(`/recordings/${id}`).then(r => r.data),
  playUrl: (id: number) => `/api/v1/recordings/${id}/play`,
  protect: (id: number) => apiClient.post(`/recordings/${id}/protect`).then(r => r.data),
  delete:  (id: number) => apiClient.delete(`/recordings/${id}`),
}