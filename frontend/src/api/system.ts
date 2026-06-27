import { apiClient } from './client'
import type { SystemHealth, StorageStatus } from "@/types"
export const systemApi = {
  health:  () => apiClient.get<SystemHealth>('/system/health').then(r => r.data),
  storage: () => apiClient.get<StorageStatus>('/storage').then(r => r.data),
  cleanup: () => apiClient.post('/storage/cleanup').then(r => r.data),
}