import { create } from 'zustand'
import type { User, UserRole } from "@/types"

const ROLE_LEVEL: Record<UserRole, number> = {
  super_admin: 5, admin: 4, operator: 3, viewer: 2, security: 1
}

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  setAuth: (u: User, t: string) => void
  clearAuth: () => void
  hasRole: (m: UserRole) => boolean
}

// Coba restore user dari localStorage saat init
function loadUserFromStorage(): User | null {
  try {
    const raw = localStorage.getItem('auth_user')
    return raw ? JSON.parse(raw) : null
  } catch { return null }
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: loadUserFromStorage(),
  token: localStorage.getItem('access_token'),
  isAuthenticated: !!localStorage.getItem('access_token'),
  setAuth: (user, token) => {
    localStorage.setItem('access_token', token)
    localStorage.setItem('auth_user', JSON.stringify(user))
    set({ user, token, isAuthenticated: true })
  },
  clearAuth: () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('auth_user')
    set({ user: null, token: null, isAuthenticated: false })
  },
  hasRole: (min) => {
    const u = get().user
    // Jika user null tapi ada token, anggap admin sementara supaya menu muncul
    if (!u) return !!localStorage.getItem('access_token')
    return ROLE_LEVEL[u.role] >= ROLE_LEVEL[min]
  },
}))
