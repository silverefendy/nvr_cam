import { apiClient } from './client'
import type { TokenResponse, User } from "@/types"
export const authApi = {
  login: (username: string, password: string) => apiClient.post<TokenResponse>('/auth/login', { username, password }).then(r => r.data),
  me: () => apiClient.get<User>('/auth/me').then(r => r.data),
}