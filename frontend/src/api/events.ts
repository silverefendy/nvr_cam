import { apiClient } from './client'
import type { MotionEvent } from "@/types"
export const eventsApi = {
  list: (p?: { camera_id?: string; date_from?: string; date_to?: string; severity?: number }) => apiClient.get<MotionEvent[]>('/events', { params: p }).then(r => r.data),
}