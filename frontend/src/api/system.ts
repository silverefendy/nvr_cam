import { apiClient } from './client'
import type { SystemHealth, StorageStatus } from "@/types"
import type { AxiosResponse } from 'axios'

export const systemApi = {
  health:    () => apiClient.get<SystemHealth>('/system/health').then((r: AxiosResponse<SystemHealth>) => r.data),
  getHealth: () => apiClient.get<SystemHealth>('/system/health').then((r: AxiosResponse<SystemHealth>) => r.data),
  storage:   () => apiClient.get<StorageStatus>('/storage').then((r: AxiosResponse<StorageStatus>) => r.data),
  cleanup:   () => apiClient.post('/storage/cleanup').then((r: AxiosResponse) => r.data),
}