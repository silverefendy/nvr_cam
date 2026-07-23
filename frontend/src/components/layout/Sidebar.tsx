import React from 'react'
import { NavLink } from 'react-router-dom'
import { useAuthStore } from "@/store/auth"
import type { UserRole } from "@/types"

const NAV = [
  { to:"/live",     label:"Live View",   icon:"▶",  min:"viewer"   as UserRole },
  { to:"/playback", label:"Playback",    icon:"⏪",  min:"viewer"   as UserRole },
  { to:"/events",   label:"Events",      icon:"🔔",  min:"viewer"   as UserRole },
  { to:"/cameras",  label:"Kamera",      icon:"📷",  min:"admin"    as UserRole },
  { to:"/storage",  label:"Storage",     icon:"💾",  min:"admin"    as UserRole },
  { to:"/users",    label:"Users",       icon:"👥",  min:"admin"    as UserRole },
  { to:"/settings", label:"Pengaturan",  icon:"⚙️",  min:"admin"    as UserRole },
  { to:"/system",   label:"System",      icon:"📊",  min:"operator" as UserRole },
]

export const Sidebar: React.FC = () => {
  const { user, hasRole, clearAuth } = useAuthStore()
  return (
    <aside className="w-56 bg-white border-r border-slate-200 text-slate-700 flex flex-col h-screen flex-shrink-0 shadow-sm">
      {/* Logo */}
      <div className="px-5 py-4 border-b border-slate-200">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-sky-600 rounded-xl flex items-center justify-center text-lg flex-shrink-0 shadow">
            📹
          </div>
          <div>
            <div className="text-sm font-bold text-slate-800 leading-tight">CamControl</div>
            <div className="text-xs text-slate-400 leading-tight">NVR System</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-3 space-y-0.5 overflow-y-auto">
        {NAV.filter(n => hasRole(n.min)).map(n => (
          <NavLink
            key={n.to}
            to={n.to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                isActive
                  ? "bg-sky-600 text-white font-semibold shadow-sm"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              }`
            }
          >
            <span className="text-base w-5 text-center flex-shrink-0">{n.icon}</span>
            <span>{n.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* User info */}
      <div className="px-4 py-4 border-t border-slate-200 bg-slate-50">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-8 h-8 bg-sky-100 border border-sky-200 rounded-full flex items-center justify-center text-xs font-bold text-sky-700 uppercase flex-shrink-0">
            {user?.username?.[0] ?? "?"}
          </div>
          <div className="min-w-0">
            <div className="text-sm font-semibold text-slate-800 truncate">{user?.username}</div>
            <div className="text-xs text-slate-400 capitalize">{user?.role}</div>
          </div>
        </div>
        <button
          onClick={clearAuth}
          className="w-full text-left px-3 py-2 rounded-lg text-sm text-red-500 hover:bg-red-50 hover:text-red-600 transition-colors font-medium"
        >
          🚪 Logout
        </button>
      </div>
    </aside>
  )
}
