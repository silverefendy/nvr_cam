import { apiClient } from './client'
import type { Camera } from '@/types'

export const camerasApi = {
  list:     ()                               => apiClient.get<Camera[]>('/cameras').then(r => r.data),
  get:      (id: string)                     => apiClient.get<Camera>(`/cameras/${id}`).then(r => r.data),
  create:   (data: Partial<Camera>)          => apiClient.post<Camera>('/cameras', data).then(r => r.data),
  update:   (id: string, d: Partial<Camera>) => apiClient.put<Camera>(`/cameras/${id}`, d).then(r => r.data),
  delete:   (id: string)                     => apiClient.delete(`/cameras/${id}`),
  snapshot: (id: string)                     => apiClient.get(`/cameras/${id}/snapshot`).then(r => r.data),
  testConn: (id: string)                     => apiClient.post(`/cameras/${id}/test`).then(r => r.data),

  // C-11: stream type param — 'main' atau 'sub'
  liveUrl:  (id: string, stream: 'main'|'sub' = 'sub') =>
    apiClient.get(`/stream/${id}/live?stream=${stream}`).then(r => r.data),
}
