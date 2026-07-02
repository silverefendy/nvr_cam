import { apiClient } from './client'
import type { StorageStatus } from "@/types"
import type { AxiosResponse } from 'axios'

export const storageApi = {
  getStatus:     () => apiClient.get<StorageStatus>('/storage').then((r: AxiosResponse<StorageStatus>) => r.data),
  manualCleanup: () => apiClient.post('/storage/cleanup').then((r: AxiosResponse) => r.data),
}
