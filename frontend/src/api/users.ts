import { apiClient } from './client'
import type { User } from "@/types"
import type { AxiosResponse } from 'axios'

export const usersApi = {
  list:   ()                              => apiClient.get<User[]>('/users').then((r: AxiosResponse<User[]>) => r.data),
  get:    (id: number)                    => apiClient.get<User>(`/users/${id}`).then((r: AxiosResponse<User>) => r.data),
  create: (data: Partial<User>)           => apiClient.post<User>('/users', data).then((r: AxiosResponse<User>) => r.data),
  update: (id: number, d: Partial<User>)  => apiClient.put<User>(`/users/${id}`, d).then((r: AxiosResponse<User>) => r.data),
  delete: (id: number)                    => apiClient.delete(`/users/${id}`),
  me:     ()                              => apiClient.get<User>('/users/me').then((r: AxiosResponse<User>) => r.data),
}
