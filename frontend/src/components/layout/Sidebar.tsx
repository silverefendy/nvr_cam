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
    /*
      Sidebar: pakai height: 100% bukan h-screen.
      Parent (ProtectedLayout) sudah 100dvh, jadi sidebar cukup ikut tinggi parent.
      flex-shrink: 0 agar sidebar tidak menyempit saat konten penuh.
    */
    <aside style={{
      width: 224,
      height: '100%',
      flexShrink: 0,
      display: 'flex',
      flexDirection: 'column',
      background: '#ffffff',
      borderRight: '1px solid #e2e8f0',
      color: '#334155',
      boxShadow: '1px 0 4px rgba(0,0,0,0.04)',
    }}>
      {/* Logo */}
      <div style={{ padding: '16px 20px', borderBottom: '1px solid #e2e8f0', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{
            width: 36, height: 36, background: '#0284c7', borderRadius: 12,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 18, flexShrink: 0, boxShadow: '0 1px 4px rgba(2,132,199,0.3)',
          }}>
            📹
          </div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: '#1e293b', lineHeight: 1.2 }}>CamControl</div>
            <div style={{ fontSize: 12, color: '#94a3b8', lineHeight: 1.2 }}>NVR System</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: '12px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 2 }}>
        {NAV.filter(n => hasRole(n.min)).map(n => (
          <NavLink
            key={n.to}
            to={n.to}
            style={({ isActive }) => ({
              display: 'flex', alignItems: 'center', gap: 12,
              padding: '10px 12px', borderRadius: 8,
              fontSize: 14, fontWeight: isActive ? 600 : 400,
              textDecoration: 'none',
              background: isActive ? '#0284c7' : 'transparent',
              color: isActive ? '#ffffff' : '#475569',
              transition: 'all 0.15s',
            })}
          >
            <span style={{ fontSize: 15, width: 20, textAlign: 'center', flexShrink: 0 }}>{n.icon}</span>
            <span>{n.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* User info */}
      <div style={{
        padding: '16px', borderTop: '1px solid #e2e8f0',
        background: '#f8fafc', flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
          <div style={{
            width: 32, height: 32, background: '#e0f2fe', border: '1px solid #bae6fd',
            borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 12, fontWeight: 700, color: '#0369a1', flexShrink: 0,
            textTransform: 'uppercase',
          }}>
            {user?.username?.[0] ?? '?'}
          </div>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: '#1e293b', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {user?.username}
            </div>
            <div style={{ fontSize: 12, color: '#94a3b8', textTransform: 'capitalize' }}>{user?.role}</div>
          </div>
        </div>
        <button
          onClick={clearAuth}
          style={{
            width: '100%', textAlign: 'left', padding: '8px 12px',
            borderRadius: 8, fontSize: 14, color: '#ef4444',
            background: 'transparent', border: 'none', cursor: 'pointer',
            fontWeight: 500, transition: 'background 0.15s',
          }}
          onMouseEnter={e => (e.currentTarget.style.background = '#fef2f2')}
          onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
        >
          🚪 Logout
        </button>
      </div>
    </aside>
  )
}
