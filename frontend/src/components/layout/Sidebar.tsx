import React from 'react'
import { NavLink } from 'react-router-dom'
import { useAuthStore } from "@/store/auth"
import type { UserRole } from "@/types"
const NAV = [
  { to:"/live",     label:"Live View",    icon:"▶",  min:"viewer"   as UserRole },
  { to:"/playback", label:"Playback",     icon:"⏪",  min:"viewer"   as UserRole },
  { to:"/events",   label:"Events",       icon:"🔔",  min:"viewer"   as UserRole },
  { to:"/cameras",  label:"Kamera",       icon:"📷",  min:"admin"    as UserRole },
  { to:"/storage",  label:"Storage",      icon:"💾",  min:"admin"    as UserRole },
  { to:"/users",    label:"Users",        icon:"👥",  min:"admin"    as UserRole },
  { to:"/settings", label:"Pengaturan",   icon:"⚙️",  min:"admin"    as UserRole },
  { to:"/system",   label:"System",       icon:"📊",  min:"operator" as UserRole },
]
export const Sidebar: React.FC = () => {
  const { user, hasRole, clearAuth } = useAuthStore()
  return (
    <aside className="w-52 bg-gray-900 text-gray-100 flex flex-col h-screen flex-shrink-0">
      <div className="p-4 border-b border-gray-700 font-semibold">📹 CamControl</div>
      <nav className="flex-1 p-2 space-y-1 overflow-y-auto">
        {NAV.filter(n => hasRole(n.min)).map(n => (
          <NavLink key={n.to} to={n.to} className={({isActive}) => `flex items-center gap-2 px-3 py-2 rounded text-sm ${isActive?"bg-blue-600 text-white":"hover:bg-gray-800"}`}>
            <span>{n.icon}</span><span>{n.label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="p-3 border-t border-gray-700 text-xs">
        <div className="font-medium">{user?.username}</div>
        <div className="text-gray-400 mb-2">{user?.role}</div>
        <button onClick={clearAuth} className="text-red-400 hover:text-red-300">Logout</button>
      </div>
    </aside>
  )
}