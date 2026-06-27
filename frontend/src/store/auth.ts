import { create } from 'zustand'
import type { User, UserRole } from "@/types"
const ROLE_LEVEL: Record<UserRole, number> = { super_admin:5, admin:4, operator:3, viewer:2, security:1 }
interface AuthState { user: User|null; token: string|null; isAuthenticated: boolean; setAuth:(u:User,t:string)=>void; clearAuth:()=>void; hasRole:(m:UserRole)=>boolean }
export const useAuthStore = create<AuthState>((set, get) => ({
  user: null, token: localStorage.getItem('access_token'), isAuthenticated: !!localStorage.getItem('access_token'),
  setAuth: (user, token) => { localStorage.setItem('access_token', token); set({ user, token, isAuthenticated: true }) },
  clearAuth: () => { localStorage.removeItem('access_token'); set({ user:null, token:null, isAuthenticated:false }) },
  hasRole: (min) => { const u = get().user; return u ? ROLE_LEVEL[u.role] >= ROLE_LEVEL[min] : false },
}))