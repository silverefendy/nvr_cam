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
    <aside className="w-56 bg-gray-900 border-r border-gray-800 text-gray-100 flex flex-col h-screen flex-shrink-0">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-base flex-shrink-0">📹</div>
          <div>
            <div className="text-sm font-bold text-white leading-tight">CamControl</div>
            <div className="text-xs text-gray-500 leading-tight">NVR System</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        {NAV.filter(n => hasRole(n.min)).map(n => (
          <NavLink
            key={n.to}
            to={n.to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                isActive
                  ? "bg-blue-600 text-white font-medium"
                  : "text-gray-400 hover:bg-gray-800 hover:text-gray-100"
              }`
            }
          >
            <span className="text-base w-5 text-center flex-shrink-0">{n.icon}</span>
            <span>{n.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* User info + Logout */}
      <div className="px-4 py-4 border-t border-gray-800">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-8 h-8 bg-gray-700 rounded-full flex items-center justify-center text-xs font-bold text-gray-300 uppercase flex-shrink-0">
            {user?.username?.[0] ?? "?"}
          </div>
          <div className="min-w-0">
            <div className="text-sm font-medium text-white truncate">{user?.username}</div>
            <div className="text-xs text-gray-500 capitalize">{user?.role}</div>
          </div>
        </div>
        <button
          onClick={clearAuth}
          className="w-full text-left px-3 py-2 rounded-lg text-sm text-red-400 hover:bg-red-900/20 hover:text-red-300 transition-colors"
        >
          🚪 Logout
        </button>
      </div>
    </aside>
  )
}