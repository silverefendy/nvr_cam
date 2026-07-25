import React from 'react'
import { NavLink } from 'react-router-dom'
import { useAuthStore } from "@/store/auth"
import { useTheme } from "@/store/theme"
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
  const { isDark, toggle } = useTheme()

  const bg      = isDark ? '#1a1d27' : '#ffffff'
  const border  = isDark ? '#2a2d3a' : '#e2e8f0'
  const text    = isDark ? '#94a3b8' : '#475569'
  const textHd  = isDark ? '#e2e8f0' : '#1e293b'
  const sub     = isDark ? '#4a5568' : '#94a3b8'
  const hoverBg = isDark ? '#252837' : '#f1f5f9'
  const footerBg = isDark ? '#12151f' : '#f8fafc'

  return (
    <aside style={{
      width: 224,
      height: '100%',
      flexShrink: 0,
      display: 'flex',
      flexDirection: 'column',
      background: bg,
      borderRight: `1px solid ${border}`,
      color: text,
      boxShadow: isDark ? '1px 0 8px rgba(0,0,0,0.3)' : '1px 0 4px rgba(0,0,0,0.04)',
      transition: 'background 0.2s, border-color 0.2s',
    }}>

      {/* Logo */}
      <div style={{ padding: '16px 20px', borderBottom: `1px solid ${border}`, flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{
            width: 36, height: 36, background: '#0284c7', borderRadius: 12,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 18, flexShrink: 0, boxShadow: '0 1px 4px rgba(2,132,199,0.3)',
          }}>📹</div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: textHd, lineHeight: 1.2 }}>CamControl</div>
            <div style={{ fontSize: 11, color: sub, lineHeight: 1.2 }}>NVR System</div>
          </div>
          {/* Theme toggle */}
          <button
            onClick={toggle}
            title={isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
            style={{
              marginLeft: 'auto',
              width: 28, height: 28,
              borderRadius: 8,
              border: `1px solid ${border}`,
              background: hoverBg,
              cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 15,
              flexShrink: 0,
            }}
          >
            {isDark ? '☀️' : '🌙'}
          </button>
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
              color: isActive ? '#ffffff' : text,
              transition: 'all 0.15s',
            })}
            onMouseEnter={e => {
              const el = e.currentTarget as HTMLElement
              if (!el.getAttribute('aria-current')) el.style.background = hoverBg
            }}
            onMouseLeave={e => {
              const el = e.currentTarget as HTMLElement
              if (!el.getAttribute('aria-current')) el.style.background = 'transparent'
            }}
          >
            <span style={{ fontSize: 15, width: 20, textAlign: 'center', flexShrink: 0 }}>{n.icon}</span>
            <span>{n.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* User info */}
      <div style={{ padding: '16px', borderTop: `1px solid ${border}`, background: footerBg, flexShrink: 0, transition: 'background 0.2s' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
          <div style={{
            width: 32, height: 32,
            background: isDark ? '#1e3a5f' : '#e0f2fe',
            border: `1px solid ${isDark ? '#2a5080' : '#bae6fd'}`,
            borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 12, fontWeight: 700, color: '#0369a1', flexShrink: 0, textTransform: 'uppercase',
          }}>
            {user?.username?.[0] ?? '?'}
          </div>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: textHd, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {user?.username}
            </div>
            <div style={{ fontSize: 11, color: sub, textTransform: 'capitalize' }}>{user?.role}</div>
          </div>
        </div>
        <button
          onClick={clearAuth}
          style={{
            width: '100%', textAlign: 'left', padding: '8px 12px',
            borderRadius: 8, fontSize: 13, color: '#ef4444',
            background: 'transparent', border: 'none', cursor: 'pointer',
            fontWeight: 500,
          }}
          onMouseEnter={e => (e.currentTarget.style.background = isDark ? '#2d1515' : '#fef2f2')}
          onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
        >
          🚪 Logout
        </button>
      </div>
    </aside>
  )
}
