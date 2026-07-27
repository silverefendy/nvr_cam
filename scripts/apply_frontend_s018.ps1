param(
  [string]$RepoRoot = (Get-Location).Path
)

$ErrorActionPreference = "Stop"
Set-Location $RepoRoot

function Write-TextFile($Path, $Content) {
  $dir = Split-Path $Path -Parent
  if ($dir -and !(Test-Path $dir)) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
  }
  Set-Content -Path $Path -Value $Content -Encoding UTF8
}

Write-Host "Applying frontend patch for Session #018 (Sunday, July 26, 2026)..."

# 1. PostCSS & Tailwind configs
Write-TextFile "frontend/tailwind.config.js" @'
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
'@

Write-TextFile "frontend/postcss.config.js" @'
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
'@

# 2. Permissions utils
Write-TextFile "frontend/src/utils/permissions.ts" @'
export const canDeleteRecording = (role: string) => ['admin', 'super_admin'].includes(role)
export const canManageCameras = (role: string) => ['admin', 'super_admin'].includes(role)
export const canDownloadRecording = (role: string) => ['operator', 'admin', 'super_admin'].includes(role)
export const canManageUsers = (role: string) => ['admin', 'super_admin'].includes(role)
export const canChangeRole = (role: string) => ['super_admin'].includes(role)
export const canManageDrives = (role: string) => ['super_admin'].includes(role)
export const canViewAuditLogs = (role: string) => ['admin', 'super_admin'].includes(role)
export const canDeleteAuditLogs = (role: string) => ['super_admin'].includes(role)
export const canManualCleanup = (role: string) => ['admin', 'super_admin'].includes(role)
export const canManageSettings = (role: string) => ['admin', 'super_admin'].includes(role)
'@

# 3. Users Page Update
Write-TextFile "frontend/src/pages/Users/index.tsx" @'
import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { usersApi } from "@/api/users"
import type { User } from "@/types"
import { useAuthStore } from "@/store/auth"
import { canChangeRole } from "@/utils/permissions"

export default function UsersPage() {
  const { user: currentUser } = useAuthStore()
  const [editingId, setEditingId] = useState<string | null>(null)
  const [formData, setFormData] = useState<Partial<User>>({})
  const [showAddForm, setShowAddForm] = useState(false)
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null)
  const queryClient = useQueryClient()

  const { data: users, isLoading } = useQuery({ queryKey: ["users"], queryFn: usersApi.list })

  const createMutation = useMutation({ mutationFn: usersApi.create })
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<User> }) => usersApi.update(id, data),
  })
  const deleteMutation = useMutation({ mutationFn: usersApi.delete })
  const resetMutation = useMutation({
    mutationFn: ({ id, newPassword }: { id: string; newPassword: string }) =>
      usersApi.adminResetPassword(id, { new_password: newPassword }),
  })

  useEffect(() => {
    if (createMutation.isSuccess || updateMutation.isSuccess || deleteMutation.isSuccess || resetMutation.isSuccess) {
      queryClient.invalidateQueries({ queryKey: ["users"] })
    }
  }, [createMutation.isSuccess, updateMutation.isSuccess, deleteMutation.isSuccess, resetMutation.isSuccess, queryClient])

  useEffect(() => {
    if (createMutation.isSuccess) setMessage({ type: "success", text: "User berhasil dibuat" })
    else if (updateMutation.isSuccess) setMessage({ type: "success", text: "User berhasil diupdate" })
    else if (deleteMutation.isSuccess) setMessage({ type: "success", text: "User berhasil dihapus" })
    else if (resetMutation.isSuccess) setMessage({ type: "success", text: resetMutation.data?.message ?? "Password berhasil direset" })
    else if (createMutation.isError || updateMutation.isError || deleteMutation.isError || resetMutation.isError) {
      setMessage({ type: "error", text: "Aksi gagal diproses" })
    } else {
      return
    }
    const timer = setTimeout(() => setMessage(null), 3000)
    return () => clearTimeout(timer)
  }, [
    createMutation.isSuccess, createMutation.isError,
    updateMutation.isSuccess, updateMutation.isError,
    deleteMutation.isSuccess, deleteMutation.isError,
    resetMutation.isSuccess, resetMutation.isError, resetMutation.data,
  ])

  const handleEdit = (user: User) => {
    setEditingId(user.id)
    setFormData(user)
  }

  const handleSave = (id: string) => updateMutation.mutate({ id, data: formData })

  const handleDelete = (id: string) => {
    if (confirm("Hapus user ini?")) deleteMutation.mutate(id)
  }

  const handleResetPassword = (user: User) => {
    const newPassword = window.prompt(`Reset password untuk ${user.username}. Masukkan password baru:`)
    if (!newPassword) return
    if (newPassword.length < 8) {
      setMessage({ type: "error", text: "Password baru minimal 8 karakter" })
      return
    }
    if (confirm(`Reset password ${user.username}?`)) {
      resetMutation.mutate({ id: user.id, newPassword })
    }
  }

  const handleCancel = () => {
    setEditingId(null)
    setFormData({})
    setShowAddForm(false)
  }

  const handleChange = (field: keyof User, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const handleCreate = () => createMutation.mutate(formData as User)

  const getRoleBadgeClass = (role: string) => {
    switch (role) {
      case "super_admin":
        return "bg-purple-100 text-purple-800 border border-purple-200 px-2.5 py-1.5 rounded-full text-xs font-bold"
      case "admin":
        return "bg-red-100 text-red-800 border border-red-200 px-2.5 py-1.5 rounded-full text-xs font-bold"
      case "operator":
        return "bg-yellow-100 text-yellow-800 border border-yellow-200 px-2.5 py-1.5 rounded-full text-xs font-bold"
      default:
        return "bg-gray-100 text-gray-800 border border-gray-200 px-2.5 py-1.5 rounded-full text-xs font-bold"
    }
  }

  return (
    <div className="flex h-full flex-col gap-4 p-4">
      <div className="flex flex-shrink-0 items-center gap-4 rounded bg-gray-800 px-4 py-3">
        <span className="text-sm font-medium text-white">Users</span>
        <button onClick={() => setShowAddForm(true)} className="ml-auto rounded bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700">
          Add User
        </button>
        {message && (
          <span className={`text-xs ${message.type === "success" ? "text-green-400" : "text-red-400"}`}>
            {message.text}
          </span>
        )}
      </div>

      {showAddForm && (
        <div className="rounded bg-gray-800 p-4">
          <h3 className="mb-3 font-medium text-white">Add New User</h3>
          <div className="grid grid-cols-2 gap-4">
            <input type="text" placeholder="Username" value={formData.username || ""} onChange={(e) => handleChange("username", e.target.value)} className="rounded border border-gray-600 bg-gray-700 px-3 py-2 text-white" />
            <input type="email" placeholder="Email" value={formData.email || ""} onChange={(e) => handleChange("email", e.target.value)} className="rounded border border-gray-600 bg-gray-700 px-3 py-2 text-white" />
            <input type="password" placeholder="Password" value={formData.password || ""} onChange={(e) => handleChange("password", e.target.value)} className="rounded border border-gray-600 bg-gray-700 px-3 py-2 text-white" />
            <select value={formData.role || "viewer"} onChange={(e) => handleChange("role", e.target.value)} className="rounded border border-gray-600 bg-gray-700 px-3 py-2 text-white" disabled={!canChangeRole(currentUser?.role || "")}>
              <option value="admin">Admin</option>
              <option value="operator">Operator</option>
              <option value="viewer">Viewer</option>
              {canChangeRole(currentUser?.role || "") && <option value="super_admin">Super Admin</option>}
            </select>
          </div>
          <div className="mt-3 flex gap-2">
            <button onClick={handleCreate} disabled={createMutation.isPending} className="rounded bg-green-600 px-3 py-1 text-sm text-white hover:bg-green-700 disabled:bg-gray-600">
              {createMutation.isPending ? "Creating..." : "Create"}
            </button>
            <button onClick={handleCancel} className="rounded bg-gray-700 px-3 py-1 text-sm text-white hover:bg-gray-600">Cancel</button>
          </div>
        </div>
      )}

      <div className="flex-1 overflow-auto rounded bg-gray-900">
        {isLoading ? (
          <div className="flex h-full items-center justify-center text-gray-500">Loading...</div>
        ) : (
          <table className="w-full text-sm text-gray-300">
            <thead className="sticky top-0 bg-gray-800 text-white">
              <tr>
                <th className="px-4 py-2 text-left">Username</th>
                <th className="px-4 py-2 text-left">Email</th>
                <th className="px-4 py-2 text-left">Role</th>
                <th className="px-4 py-2 text-left">Active</th>
                <th className="px-4 py-2 text-left">Last Login</th>
                <th className="px-4 py-2 text-left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users?.map((user) => (
                <tr key={user.id} className="border-b border-gray-800 hover:bg-gray-800/50">
                  {editingId === user.id ? (
                    <>
                      <td className="px-4 py-2"><input value={formData.username || ""} onChange={(e) => handleChange("username", e.target.value)} className="w-full rounded bg-gray-700 px-2 py-1 text-white" /></td>
                      <td className="px-4 py-2"><input value={formData.email || ""} onChange={(e) => handleChange("email", e.target.value)} className="w-full rounded bg-gray-700 px-2 py-1 text-white" /></td>
                      <td className="px-4 py-2">
                        <select value={formData.role || "viewer"} onChange={(e) => handleChange("role", e.target.value)} className="w-full rounded bg-gray-700 px-2 py-1 text-white" disabled={!canChangeRole(currentUser?.role || "")}>
                          <option value="admin">Admin</option>
                          <option value="operator">Operator</option>
                          <option value="viewer">Viewer</option>
                          {canChangeRole(currentUser?.role || "") && <option value="super_admin">Super Admin</option>}
                        </select>
                      </td>
                      <td className="px-4 py-2"><input type="checkbox" checked={formData.is_active || false} onChange={(e) => handleChange("is_active", e.target.checked)} /></td>
                      <td className="px-4 py-2">-</td>
                      <td className="px-4 py-2">
                        <button onClick={() => handleSave(user.id)} className="mr-2 text-green-400 hover:underline">Save</button>
                        <button onClick={handleCancel} className="text-gray-400 hover:underline">Cancel</button>
                      </td>
                    </>
                  ) : (
                    <>
                      <td className="px-4 py-2 font-bold text-white">{user.username}</td>
                      <td className="px-4 py-2">{user.email || "-"}</td>
                      <td className="px-4 py-2">
                        <span className={getRoleBadgeClass(user.role)}>
                          {user.role}
                        </span>
                      </td>
                      <td className="px-4 py-2"><span className={user.is_active ? "text-green-400 font-bold" : "text-red-400"}>{user.is_active ? "Yes" : "No"}</span></td>
                      <td className="px-4 py-2">{user.last_login ? new Date(user.last_login).toLocaleString('id-ID') : "-"}</td>
                      <td className="px-4 py-2">
                        <button onClick={() => handleEdit(user)} className="mr-2 text-blue-400 hover:underline">Edit</button>
                        <button onClick={() => handleResetPassword(user)} className="mr-2 text-yellow-400 hover:underline">Reset Password</button>
                        {user.username !== "admin" && (
                          <button onClick={() => handleDelete(user.id)} className="text-red-400 hover:underline">Delete</button>
                        )}
                      </td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
'@

# 4. Storage page redesign
Write-TextFile "frontend/src/pages/Storage/index.tsx" @'
import { useState, useEffect } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/api/client"
import { storageApi } from "@/api/storage"
import { recordingsApi } from "@/api/recordings"
import { camerasApi } from "@/api/cameras"
import { useAuthStore } from "@/store/auth"
import { useTheme } from "@/store/theme"
import { canManualCleanup, canManageDrives } from "@/utils/permissions"
import type { DriveStatus, Recording } from "@/types"

type Tab = "overview" | "recordings" | "drives" | "schedule"

const formatGB  = (gb: number) => gb >= 1000 ? `${(gb / 1024).toFixed(2)} TB` : `${gb.toFixed(1)} GB`
const formatMB  = (mb: number) => mb >= 1024  ? `${(mb / 1024).toFixed(2)} GB` : `${mb.toFixed(0)} MB`
const formatDur = (s?: number) => {
  if (!s) return '-'
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = Math.floor(s % 60)
  return h > 0 ? `${h}j ${m}m` : m > 0 ? `${m}m ${sec}s` : `${sec}s`
}
const formatDate = (iso: string) => {
  const d = new Date(iso)
  return d.toLocaleString('id-ID', { day:'2-digit', month:'short', year:'numeric', hour:'2-digit', minute:'2-digit' })
}
const todayStr    = () => new Date().toISOString().slice(0, 10)
const monthAgoStr = () => { const d = new Date(); d.setDate(d.getDate() - 30); return d.toISOString().slice(0, 10) }

export default function StoragePage() {
  const { user: currentUser } = useAuthStore()
  const [activeTab, setActiveTab]       = useState<Tab>("overview")
  const [schedHour, setSchedHour]       = useState(3)
  const [schedMinute, setSchedMinute]   = useState(0)
  const [schedEnabled, setSchedEnabled] = useState(false)
  const [message, setMessage]           = useState<{ type: "success" | "error"; text: string } | null>(null)
  const [recCameraId, setRecCameraId]   = useState<string>("")
  const [recDateFrom, setRecDateFrom]   = useState(monthAgoStr())
  const [recDateTo, setRecDateTo]       = useState(todayStr())
  const [playingId, setPlayingId]       = useState<number | null>(null)

  // Drive settings states (super_admin only)
  const [newDrivePath, setNewDrivePath] = useState("")
  const [newDriveName, setNewDriveName] = useState("")
  const [assignDrivePath, setAssignDrivePath] = useState("")
  const [assignCameras, setAssignCameras] = useState<string[]>([])

  const queryClient = useQueryClient()
  const { isAuthenticated } = useAuthStore()
  const { isDark } = useTheme()

  const bg      = isDark ? '#0f1117' : '#f1f5f9'
  const card    = isDark ? '#1a1d27' : '#ffffff'
  const cardB   = isDark ? '#2a2d3a' : '#e2e8f0'
  const text    = isDark ? '#e2e8f0' : '#1e293b'
  const sub     = isDark ? '#64748b' : '#94a3b8'
  const inputBg = isDark ? '#12151f' : '#f8fafc'
  const rowHov  = isDark ? '#1e2130' : '#f8fafc'

  const { data: storage, isLoading, refetch } = useQuery({
    queryKey: ["storage"], queryFn: storageApi.getStatus,
    enabled: isAuthenticated, refetchInterval: 30000,
  })

  const { data: drivesList, refetch: refetchDrives } = useQuery({
    queryKey: ["storage-drives"],
    queryFn: () => apiClient.get('/storage/drives').then(r => r.data),
    enabled: isAuthenticated && canManageDrives(currentUser?.role || ""),
  })

  const { data: schedule } = useQuery({
    queryKey: ["cleanup-schedule"], queryFn: storageApi.getCleanupSchedule,
    enabled: isAuthenticated && activeTab === "schedule",
  })
  const { data: cameras } = useQuery({
    queryKey: ["cameras"], queryFn: camerasApi.list,
    enabled: isAuthenticated,
  })
  const { data: recordings, isLoading: recLoading } = useQuery({
    queryKey: ["recordings", recCameraId, recDateFrom, recDateTo],
    queryFn: () => recordingsApi.list({
      camera_id: recCameraId || undefined,
      date_from: recDateFrom || undefined,
      date_to:   recDateTo   || undefined,
    }),
    enabled: isAuthenticated && activeTab === "recordings",
  })

  useEffect(() => {
    if (schedule) {
      setSchedEnabled(schedule.enabled ?? false)
      setSchedHour(schedule.hour ?? 3)
      setSchedMinute(schedule.minute ?? 0)
    }
  }, [schedule])

  const showMsg = (type: "success" | "error", text: string) => {
    setMessage({ type, text })
    setTimeout(() => setMessage(null), 4000)
  }

  const cleanupMutation = useMutation({
    mutationFn: storageApi.manualCleanup,
    onSuccess: () => { refetch(); showMsg("success", "Cleanup selesai") },
    onError:   () => showMsg("error", "Cleanup gagal"),
  })
  const scheduleMutation = useMutation({
    mutationFn: storageApi.saveCleanupSchedule,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["cleanup-schedule"] }); showMsg("success", "Jadwal disimpan") },
    onError:   () => showMsg("error", "Gagal menyimpan jadwal"),
  })
  const protectMutation = useMutation({
    mutationFn: (id: number) => recordingsApi.protect(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["recordings"] }),
  })
  const deleteMutation = useMutation({
    mutationFn: (id: number) => recordingsApi.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["recordings"] }),
  })
  const syncMutation = useMutation({
    mutationFn: () => apiClient.post('/recordings/sync').then(r => r.data),
    onSuccess: (data: any) => {
      queryClient.invalidateQueries({ queryKey: ["recordings"] })
      showMsg("success", `Sync selesai: ${data.inserted} file baru, ${data.skipped} sudah ada`)
    },
    onError: () => showMsg("error", "Sync dari disk gagal"),
  })

  // Drives mutations (super_admin only)
  const addDriveMutation = useMutation({
    mutationFn: (data: { path: string; name: string }) => apiClient.post('/storage/drives', data),
    onSuccess: () => {
      refetchDrives()
      refetch()
      setNewDrivePath("")
      setNewDriveName("")
      showMsg("success", "Drive berhasil ditambahkan")
    },
    onError: (err: any) => showMsg("error", err?.response?.data?.detail ?? "Gagal menambahkan drive"),
  })

  const deleteDriveMutation = useMutation({
    mutationFn: (path: string) => apiClient.delete(`/storage/drives/${encodeURIComponent(path)}`),
    onSuccess: () => {
      refetchDrives()
      refetch()
      showMsg("success", "Drive berhasil dihapus")
    },
    onError: (err: any) => showMsg("error", err?.response?.data?.detail ?? "Gagal menghapus drive"),
  })

  const assignMutation = useMutation({
    mutationFn: ({ path, camera_ids }: { path: string; camera_ids: string[] }) =>
      apiClient.put(`/storage/drives/${encodeURIComponent(path)}/assign`, { camera_ids }),
    onSuccess: () => {
      refetchDrives()
      refetch()
      setAssignCameras([])
      showMsg("success", "Kamera berhasil dipetakan ke drive")
    },
    onError: (err: any) => showMsg("error", err?.response?.data?.detail ?? "Gagal memetakan kamera"),
  })

  const handleAddDrive = () => {
    if (!newDrivePath.trim()) return
    addDriveMutation.mutate({ path: newDrivePath, name: newDriveName })
  }

  const handleAssignCameras = () => {
    if (!assignDrivePath) return
    assignMutation.mutate({ path: assignDrivePath, camera_ids: assignCameras })
  }

  const toggleCameraSelection = (id: string) => {
    setAssignCameras(prev => prev.includes(id) ? prev.filter(c => c !== id) : [...prev, id])
  }

  const getUsageColor = (p: number) => p < 10 ? '#ef4444' : p < 25 ? '#f59e0b' : '#10b981'
  const getUsedPct    = (d: DriveStatus) => Math.round((d.used_gb / d.total_gb) * 100)

  const tabs: { id: Tab; label: string }[] = [
    { id: "overview",   label: "Overview"       },
    { id: "recordings", label: "Rekaman"        },
    { id: "drives",     label: "Pengaturan Drive" },
    { id: "schedule",   label: "Jadwal Cleanup" },
  ]

  const cardStyle: React.CSSProperties = {
    background: card, border: `1px solid ${cardB}`,
    borderRadius: 12, padding: '16px',
    boxShadow: isDark ? '0 2px 8px rgba(0,0,0,0.3)' : '0 1px 4px rgba(0,0,0,0.06)',
  }

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '8px 12px',
    borderRadius: 8, border: `1px solid ${cardB}`,
    background: inputBg, color: text,
    fontSize: 13, outline: 'none', boxSizing: 'border-box',
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: bg, padding: 16, gap: 12, overflow: 'hidden' }}>

      {/* Header */}
      <div style={{ ...cardStyle, padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
        <h1 style={{ fontSize: 15, fontWeight: 700, color: text, margin: 0 }}>Storage Management</h1>
        {storage && (
          <div style={{ display: 'flex', gap: 12, marginLeft: 8, flexWrap: 'wrap' }}>
            {[
              { label: 'Total',          value: `${storage.total_tb} TB`,                    color: text },
              { label: 'Dipakai',        value: `${storage.used_tb} TB`,                     color: '#f59e0b' },
              { label: 'Sisa',           value: `${storage.free_tb} TB`,                     color: storage.free_tb < 1 ? '#ef4444' : '#10b981' },
              { label: 'Estimasi habis', value: `~${storage.estimated_days_remaining} hari`, color: sub },
            ].map(s => (
              <div key={s.label} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                <span style={{ fontSize: 11, color: sub }}>{s.label}</span>
                <span style={{ fontSize: 13, fontWeight: 700, color: s.color }}>{s.value}</span>
              </div>
            ))}
          </div>
        )}
        {message && (
          <span style={{
            marginLeft: 'auto', fontSize: 12, padding: '4px 12px', borderRadius: 99, fontWeight: 600,
            background: message.type === 'success' ? (isDark ? '#052e16' : '#dcfce7') : (isDark ? '#2d0a0a' : '#fee2e2'),
            color: message.type === 'success' ? '#10b981' : '#ef4444',
            border: `1px solid ${message.type === 'success' ? '#10b98140' : '#ef444440'}`,
          }}>
            {message.type === 'success' ? 'OK' : 'Error'} {message.text}
          </span>
        )}
        {canManualCleanup(currentUser?.role || "") && (
          <button
            onClick={() => { if (confirm('Jalankan cleanup sekarang?')) cleanupMutation.mutate() }}
            disabled={cleanupMutation.isPending}
            style={{
              marginLeft: message ? 8 : 'auto', padding: '7px 14px', borderRadius: 8,
              fontSize: 12, fontWeight: 600,
              background: cleanupMutation.isPending ? sub : '#ef4444',
              color: '#fff', border: 'none', cursor: 'pointer',
            }}
          >
            {cleanupMutation.isPending ? 'Membersihkan...' : 'Hapus Video Sekarang'}
          </button>
        )}
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
        {tabs.map(t => (
          <button key={t.id} onClick={() => setActiveTab(t.id)} style={{
            padding: '8px 16px', borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: 'pointer',
            border: `1px solid ${activeTab === t.id ? '#0284c7' : cardB}`,
            background: activeTab === t.id ? '#0284c7' : card,
            color: activeTab === t.id ? '#fff' : sub,
            transition: 'all 0.15s',
          }}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto' }}>

        {/* Tab: Overview */}
        {activeTab === 'overview' && (
          isLoading
            ? <div style={{ color: sub, padding: 40, textAlign: 'center' }}>Memuat data storage...</div>
            : !storage?.drives?.length
              ? <div style={{ color: sub, padding: 40, textAlign: 'center' }}>Tidak ada drive terkonfigurasi. Hubungi Super Admin untuk menambahkan.</div>
              : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {storage._warning && (
                    <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 text-yellow-800 text-sm mb-2">
                      ⚠️ {storage._warning}
                    </div>
                  )}
                  {storage.drives.map((drive: DriveStatus) => {
                    const usedPct  = getUsedPct(drive)
                    const freePct  = drive.free_pct
                    const barColor = getUsageColor(freePct)
                    return (
                      <div key={drive.path} style={cardStyle}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                          <div>
                            <div style={{ fontSize: 14, fontWeight: 700, color: text, display: 'flex', alignItems: 'center', gap: 8 }}>
                              {drive.path}
                              {freePct < (storage.threshold_pct ?? 10) && (
                                <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 99, background: '#7f1d1d', color: '#fca5a5', fontWeight: 700 }}>Kritis</span>
                              )}
                            </div>
                            <div style={{ fontSize: 11, color: sub, marginTop: 3 }}>
                              {drive.cameras?.length ?? 0} kamera terpetakan
                              {drive.cameras?.length > 0 && ` — [${drive.cameras.join(', ')}]`}
                            </div>
                          </div>
                          <div style={{ textAlign: 'right' }}>
                            <div style={{ fontSize: 22, fontWeight: 800, color: barColor, lineHeight: 1 }}>{freePct.toFixed(1)}%</div>
                            <div style={{ fontSize: 11, color: sub }}>tersisa</div>
                          </div>
                        </div>
                        <div style={{ position: 'relative', height: 10, background: isDark ? '#1e2130' : '#e2e8f0', borderRadius: 99, overflow: 'hidden', marginBottom: 10 }}>
                          <div style={{
                            position: 'absolute', left: 0, top: 0, bottom: 0, width: `${usedPct}%`,
                            background: usedPct > 90 ? '#ef4444' : usedPct > 75 ? '#f59e0b' : '#0284c7',
                            borderRadius: 99, transition: 'width 0.5s ease',
                          }} />
                        </div>
                        <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
                          {[
                            { label: 'Total',     value: formatGB(drive.total_gb), color: text },
                            { label: 'Dipakai',   value: formatGB(drive.used_gb),  color: '#f59e0b' },
                            { label: 'Sisa',      value: formatGB(drive.free_gb),  color: '#10b981' },
                            { label: 'Threshold', value: `${storage.threshold_pct ?? 10}%`, color: sub },
                          ].map(s => (
                            <div key={s.label}>
                              <div style={{ fontSize: 10, color: sub, marginBottom: 2 }}>{s.label}</div>
                              <div style={{ fontSize: 14, fontWeight: 700, color: s.color }}>{s.value}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )
        )}

        {/* Tab: Rekaman */}
        {activeTab === 'recordings' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ ...cardStyle, padding: '12px 16px', display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: sub }}>Filter Kamera:</span>
              <select value={recCameraId} onChange={e => setRecCameraId(e.target.value)}
                style={{ padding: '6px 10px', borderRadius: 7, fontSize: 12, border: `1px solid ${cardB}`, background: inputBg, color: text, cursor: 'pointer' }}>
                <option value="">Semua Kamera</option>
                {cameras?.map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ fontSize: 11, color: sub }}>Rentang</span>
                <input type="date" value={recDateFrom} onChange={e => setRecDateFrom(e.target.value)}
                  style={{ padding: '6px 8px', borderRadius: 7, fontSize: 12, border: `1px solid ${cardB}`, background: inputBg, color: text }} />
                <span style={{ fontSize: 11, color: sub }}>s/d</span>
                <input type="date" value={recDateTo} onChange={e => setRecDateTo(e.target.value)}
                  style={{ padding: '6px 8px', borderRadius: 7, fontSize: 12, border: `1px solid ${cardB}`, background: inputBg, color: text }} />
              </div>
              <button
                onClick={() => { if (confirm('Scan file .mp4 di storage dan daftarkan ke database?')) syncMutation.mutate() }}
                disabled={syncMutation.isPending}
                style={{
                  padding: '6px 14px', borderRadius: 7, fontSize: 12, fontWeight: 600,
                  background: syncMutation.isPending ? sub : '#7c3aed',
                  color: '#fff', border: 'none', cursor: syncMutation.isPending ? 'not-allowed' : 'pointer',
                  whiteSpace: 'nowrap',
                }}
              >
                {syncMutation.isPending ? 'Scanning...' : 'Sync dari Disk'}
              </button>
              <span style={{ fontSize: 11, color: sub, marginLeft: 'auto' }}>
                {recordings ? `${recordings.length} rekaman` : ''}
              </span>
            </div>

            {playingId !== null && (() => {
              const rec = recordings?.find((r: Recording) => r.id === playingId)
              return rec ? (
                <div style={cardStyle}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: text }}>{rec.camera_id} - {formatDate(rec.started_at)}</span>
                    <button onClick={() => setPlayingId(null)}
                      style={{ fontSize: 12, padding: '3px 10px', borderRadius: 6, border: `1px solid ${cardB}`, background: 'transparent', color: sub, cursor: 'pointer' }}>
                      Tutup
                    </button>
                  </div>
                  <video src={recordingsApi.playUrl(rec.id)} controls autoPlay
                    style={{ width: '100%', maxHeight: 480, background: '#000', borderRadius: 8 }} />
                </div>
              ) : null
            })()}

            {recLoading ? (
              <div style={{ color: sub, padding: 40, textAlign: 'center' }}>Memuat rekaman...</div>
            ) : !recordings?.length ? (
              <div style={{ ...cardStyle, padding: 40, textAlign: 'center', color: sub }}>
                <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>Tidak ada rekaman ditemukan</div>
                <div style={{ fontSize: 12, color: '#7c3aed' }}>
                  Silakan sync disk jika file video sudah diletakkan manual di folder.
                </div>
              </div>
            ) : (
              <div style={{ ...cardStyle, padding: 0, overflow: 'hidden' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr style={{ background: isDark ? '#12151f' : '#f8fafc', borderBottom: `1px solid ${cardB}` }}>
                      {['Kamera', 'Mulai', 'Durasi', 'Ukuran', 'Codec', 'Path File', 'Aksi'].map(h => (
                        <th key={h} style={{ padding: '10px 14px', textAlign: 'left', fontSize: 11, fontWeight: 700, color: sub }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {recordings.map((rec: Recording) => (
                      <tr key={rec.id} style={{
                        borderBottom: `1px solid ${isDark ? '#1e2130' : '#f1f5f9'}`,
                        background: playingId === rec.id ? (isDark ? '#1a2a3a' : '#eff6ff') : 'transparent',
                        transition: 'background 0.1s', cursor: 'pointer',
                      }}
                        onMouseEnter={e => (e.currentTarget.style.background = playingId === rec.id ? (isDark ? '#1a2a3a' : '#eff6ff') : rowHov)}
                        onMouseLeave={e => (e.currentTarget.style.background = playingId === rec.id ? (isDark ? '#1a2a3a' : '#eff6ff') : 'transparent')}
                        onClick={() => setPlayingId(rec.id === playingId ? null : rec.id)}
                      >
                        <td style={{ padding: '10px 14px', fontWeight: 600, color: text }}>
                          {rec.camera_id}
                          {rec.is_protected && <span style={{ marginLeft: 6, fontSize: 9, padding: '1px 5px', borderRadius: 99, background: isDark ? '#1e3a5f' : '#dbeafe', color: '#3b82f6' }}>Protected</span>}
                        </td>
                        <td style={{ padding: '10px 14px', color: sub, fontSize: 12 }}>{formatDate(rec.started_at)}</td>
                        <td style={{ padding: '10px 14px', color: sub }}>{formatDur(rec.duration_s)}</td>
                        <td style={{ padding: '10px 14px', color: sub }}>{rec.file_size_mb ? formatMB(rec.file_size_mb) : '-'}</td>
                        <td style={{ padding: '10px 14px' }}>
                          <span style={{
                            fontSize: 10, padding: '2px 7px', borderRadius: 99, fontWeight: 700,
                            background: rec.codec === 'H265' ? (isDark ? '#1e2d1e' : '#dcfce7') : (isDark ? '#1e2130' : '#f1f5f9'),
                            color: rec.codec === 'H265' ? '#10b981' : sub,
                          }}>{rec.codec}</span>
                        </td>
                        <td style={{ padding: '10px 14px', maxWidth: 200 }}>
                          <span title={rec.file_path} style={{ fontSize: 11, color: sub, fontFamily: 'monospace', display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{rec.file_path}</span>
                        </td>
                        <td style={{ padding: '10px 14px' }}>
                          <div style={{ display: 'flex', gap: 6 }} onClick={e => e.stopPropagation()}>
                            <button onClick={() => setPlayingId(rec.id === playingId ? null : rec.id)}
                              style={{ ...smallBtn, background: isDark ? '#1a2a3a' : '#dbeafe', color: '#3b82f6' }}>Putar</button>
                            <a href={recordingsApi.downloadUrl(rec.id)} download
                              style={{ ...smallBtn, background: isDark ? '#1a2a1a' : '#dcfce7', color: '#10b981', textDecoration: 'none' }}>Unduh</a>
                            <button onClick={() => protectMutation.mutate(rec.id)}
                              style={{ ...smallBtn, background: isDark ? '#1a1a2a' : '#ede9fe', color: '#8b5cf6' }}>
                              {rec.is_protected ? 'Buka' : 'Protect'}
                            </button>
                            {!rec.is_protected && (
                              <button onClick={() => { if (confirm(`Hapus rekaman ${rec.camera_id}?`)) deleteMutation.mutate(rec.id) }}
                                style={{ ...smallBtn, background: isDark ? '#2d0a0a' : '#fee2e2', color: '#ef4444' }}>Hapus</button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Tab: Pengaturan Drive */}
        {activeTab === 'drives' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {!canManageDrives(currentUser?.role || "") ? (
              <div style={cardStyle} className="text-red-500 font-bold">
                ⚠️ Hanya Super Admin yang dapat mengakses tab ini untuk mengelola drive penyimpanan fisik.
              </div>
            ) : (
              <>
                {/* List drive & Tambah */}
                <div style={cardStyle}>
                  <h3 style={{ fontSize: 14, fontWeight: 700, color: text, marginBottom: 16 }}>Daftar Drive Aktif</h3>
                  <div className="space-y-4 mb-6">
                    {drivesList?.map((d: any) => (
                      <div key={d.path} className="flex justify-between items-center p-3 rounded-lg bg-gray-800 border border-gray-700">
                        <div>
                          <div className="font-bold text-white text-sm">{d.path} {d.name ? `(${d.name})` : ''}</div>
                          <div className="text-xs text-gray-400 mt-1">Kamera: {d.cameras?.length > 0 ? d.cameras.join(", ") : "—"}</div>
                        </div>
                        <button
                          onClick={() => { if (confirm(`Hapus drive ${d.path}?`)) deleteDriveMutation.mutate(d.path) }}
                          className="bg-red-600 hover:bg-red-500 text-white font-semibold text-xs px-3 py-1.5 rounded-lg"
                        >
                          Hapus Drive
                        </button>
                      </div>
                    ))}
                  </div>

                  <h4 className="text-sm font-semibold text-white mb-2">Tambah Drive Baru</h4>
                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <input type="text" placeholder="Path (cth: /mnt/hdd1)" value={newDrivePath} onChange={e => setNewDrivePath(e.target.value)} style={inputStyle} />
                    <input type="text" placeholder="Nama Drive (cth: CCTV HDD 4TB)" value={newDriveName} onChange={e => setNewDriveName(e.target.value)} style={inputStyle} />
                  </div>
                  <button onClick={handleAddDrive} className="bg-sky-600 hover:bg-sky-500 text-white font-bold text-xs px-4 py-2 rounded-xl">
                    + Tambah Drive
                  </button>
                </div>

                {/* Petakan Kamera ke Drive */}
                <div style={cardStyle}>
                  <h3 style={{ fontSize: 14, fontWeight: 700, color: text, marginBottom: 16 }}>Petakan Kamera ke Drive</h3>
                  <div className="mb-4">
                    <label className="block text-xs text-gray-400 font-bold mb-1">Pilih Drive</label>
                    <select value={assignDrivePath} onChange={e => setAssignDrivePath(e.target.value)} style={inputStyle}>
                      <option value="">— Pilih Drive —</option>
                      {drivesList?.map((d: any) => <option key={d.path} value={d.path}>{d.path} {d.name ? `(${d.name})` : ''}</option>)}
                    </select>
                  </div>
                  <div className="mb-4">
                    <label className="block text-xs text-gray-400 font-bold mb-2">Pilih Kamera yang Akan Di-Assign</label>
                    <div className="grid grid-cols-3 gap-2">
                      {cameras?.map((c: any) => (
                        <label key={c.id} className="flex items-center gap-2 p-2 rounded bg-gray-800 border border-gray-700 cursor-pointer">
                          <input type="checkbox" checked={assignCameras.includes(c.id)} onChange={() => toggleCameraSelection(c.id)} />
                          <span className="text-xs text-white">{c.name} ({c.id})</span>
                        </label>
                      ))}
                    </div>
                  </div>
                  <button onClick={handleAssignCameras} className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs px-4 py-2 rounded-xl">
                    Simpan Pemetaan Kamera
                  </button>
                </div>
              </>
            )}
          </div>
        )}

        {/* Tab: Jadwal Cleanup */}
        {activeTab === 'schedule' && (
          <div style={{ ...cardStyle, maxWidth: 500 }}>
            <h2 style={{ fontSize: 15, fontWeight: 700, color: text, margin: '0 0 6px' }}>Jadwal Cleanup Otomatis</h2>
            <p style={{ fontSize: 12, color: sub, margin: '0 0 20px', lineHeight: 1.6 }}>
              Cleanup terjadwal menghapus file terlama yang tidak diproteksi agar ruang disk selalu tersedia.
            </p>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
              <span style={{ fontSize: 13, color: text }}>Aktifkan cleanup terjadwal</span>
              <div onClick={() => setSchedEnabled(!schedEnabled)} style={{
                width: 44, height: 24, borderRadius: 99, cursor: 'pointer', position: 'relative',
                background: schedEnabled ? '#0284c7' : (isDark ? '#2a2d3a' : '#cbd5e1'),
                transition: 'background 0.2s', flexShrink: 0,
              }}>
                <div style={{
                  position: 'absolute', top: 2, width: 20, height: 20, borderRadius: '50%',
                  background: '#fff', boxShadow: '0 1px 4px rgba(0,0,0,0.3)',
                  left: schedEnabled ? 22 : 2, transition: 'left 0.2s',
                }} />
              </div>
              <span style={{ fontSize: 11, color: schedEnabled ? '#10b981' : sub, fontWeight: 600 }}>
                {schedEnabled ? 'Aktif' : 'Nonaktif'}
              </span>
            </div>
            <div style={{ opacity: schedEnabled ? 1 : 0.4, pointerEvents: schedEnabled ? 'auto' : 'none', marginBottom: 20 }}>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: sub, marginBottom: 8 }}>Jam cleanup (HH : MM)</label>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <input type="number" min={0} max={23} value={schedHour} onChange={e => setSchedHour(Number(e.target.value))}
                  style={{ width: 64, padding: '8px', borderRadius: 8, border: `1px solid ${cardB}`, background: inputBg, color: text, fontSize: 18, fontWeight: 700, textAlign: 'center' }} />
                <span style={{ fontSize: 20, fontWeight: 800, color: sub }}>:</span>
                <input type="number" min={0} max={59} value={schedMinute} onChange={e => setSchedMinute(Number(e.target.value))}
                  style={{ width: 64, padding: '8px', borderRadius: 8, border: `1px solid ${cardB}`, background: inputBg, color: text, fontSize: 18, fontWeight: 700, textAlign: 'center' }} />
                <span style={{ fontSize: 11, color: sub }}>
                  cron: <code style={{ background: isDark ? '#12151f' : '#f1f5f9', padding: '2px 6px', borderRadius: 4 }}>
                    {String(schedMinute).padStart(2,'0')} {String(schedHour).padStart(2,'0')} * * *
                  </code>
                </span>
              </div>
              <p style={{ fontSize: 11, color: sub, marginTop: 6 }}>Disarankan jam 03:00 saat traffic rendah</p>
            </div>
            <button
              onClick={() => scheduleMutation.mutate({ enabled: schedEnabled, hour: schedHour, minute: schedMinute })}
              disabled={scheduleMutation.isPending}
              style={{ padding: '10px 20px', borderRadius: 8, fontSize: 13, fontWeight: 700, background: '#0284c7', color: '#fff', border: 'none', cursor: 'pointer', opacity: scheduleMutation.isPending ? 0.6 : 1 }}
            >
              {scheduleMutation.isPending ? 'Menyimpan...' : 'Simpan Jadwal'}
            </button>
            {schedule && (
              <div style={{ marginTop: 16, padding: 12, background: isDark ? '#12151f' : '#f8fafc', borderRadius: 8, border: `1px solid ${cardB}`, fontSize: 12, color: sub }}>
                <div>Status: <span style={{ color: schedule.enabled ? '#10b981' : sub, fontWeight: 700 }}>{schedule.enabled ? 'Aktif' : 'Nonaktif'}</span></div>
                <div style={{ marginTop: 4 }}>Cron: <code style={{ background: isDark ? '#1a1d27' : '#e2e8f0', padding: '1px 6px', borderRadius: 4, color: text }}>{schedule.cron}</code></div>
                <div style={{ marginTop: 6, color: '#f59e0b' }}>Berlaku setelah backend di-restart</div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

const smallBtn: React.CSSProperties = {
  padding: '3px 8px', borderRadius: 5, fontSize: 11, fontWeight: 600,
  border: 'none', cursor: 'pointer', whiteSpace: 'nowrap',
}
'@

# 5. Redesign Settings page
Write-TextFile "frontend/src/pages/Settings/index.tsx" @'
import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useTheme } from "@/store/theme"
import { apiClient } from "@/api/client"

type TabType = "general" | "recording" | "streaming" | "notification" | "backup" | "about"

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabType>("general")
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null)

  // States per tab
  const [generalVals, setGeneralValues] = useState({ site_name: "CML NVR System", timezone: "Asia/Makassar", date_format: "DD/MM/YYYY", language: "id" })
  const [recordingVals, setRecordingValues] = useState({ default_retention_days: 30, default_stream: "main", segment_duration_seconds: 300, max_file_size_mb: 500, recording_schedule: "24h" })
  const [streamingVals, setStreamingValues] = useState({ hls_segment_duration: 2, hls_playlist_size: 3, default_stream_quality: "sub", transcode_concurrent_max: 3, motion_detection_fps: 5 })
  const [notifVals, setNotificationValues] = useState({ telegram_enabled: false, telegram_bot_token: "", telegram_chat_id: "", email_enabled: false, smtp_host: "", smtp_port: 587, smtp_user: "", smtp_password: "", notify_camera_offline: false, notify_disk_full: false, notify_motion_detected: false })

  // Notification test state
  const [testMsg, setTestMsg] = useState("Test message from CamControl Settings")

  const queryClient = useQueryClient()
  const { isDark } = useTheme()

  const bg    = isDark ? '#0f1117' : '#f1f5f9'
  const card  = isDark ? '#1a1d27' : '#ffffff'
  const cardB = isDark ? '#2a2d3a' : '#e2e8f0'
  const text  = isDark ? '#e2e8f0' : '#1e293b'
  const sub   = isDark ? '#64748b' : '#94a3b8'
  const inputBg = isDark ? '#12151f' : '#f8fafc'
  const sideActive = isDark ? '#0284c7' : '#0284c7'

  const showMsg = (type: "success" | "error", msg: string) => {
    setMessage({ type, text: msg })
    setTimeout(() => setMessage(null), 3500)
  }

  // Queries
  const { data: generalData } = useQuery({
    queryKey: ["settings-general"],
    queryFn: () => apiClient.get('/settings/general').then(r => r.data),
  })

  const { data: recordingData } = useQuery({
    queryKey: ["settings-recording"],
    queryFn: () => apiClient.get('/settings/recording').then(r => r.data),
  })

  const { data: streamingData } = useQuery({
    queryKey: ["settings-streaming"],
    queryFn: () => apiClient.get('/settings/streaming').then(r => r.data),
  })

  const { data: notifData } = useQuery({
    queryKey: ["settings-notification"],
    queryFn: () => apiClient.get('/settings/notification').then(r => r.data),
  })

  const { data: backupsList, refetch: refetchBackups } = useQuery({
    queryKey: ["backups-list"],
    queryFn: () => apiClient.get('/config/backups').then(r => r.data),
  })

  useEffect(() => { if (generalData) setGeneralValues(generalData) }, [generalData])
  useEffect(() => { if (recordingData) setRecordingValues(recordingData) }, [recordingData])
  useEffect(() => { if (streamingData) setStreamingValues(streamingData) }, [streamingData])
  useEffect(() => { if (notifData) setNotificationValues(notifData) }, [notifData])

  // Mutations
  const updateGeneralMutation = useMutation({
    mutationFn: (data: typeof generalVals) => apiClient.put('/settings/general', data),
    onSuccess: () => showMsg("success", "Pengaturan Umum berhasil disimpan"),
    onError: () => showMsg("error", "Gagal menyimpan Pengaturan Umum"),
  })

  const updateRecordingMutation = useMutation({
    mutationFn: (data: typeof recordingVals) => apiClient.put('/settings/recording', data),
    onSuccess: () => showMsg("success", "Pengaturan Rekaman berhasil disimpan"),
    onError: () => showMsg("error", "Gagal menyimpan Pengaturan Rekaman"),
  })

  const updateStreamingMutation = useMutation({
    mutationFn: (data: typeof streamingVals) => apiClient.put('/settings/streaming', data),
    onSuccess: () => showMsg("success", "Pengaturan Streaming berhasil disimpan"),
    onError: () => showMsg("error", "Gagal menyimpan Pengaturan Streaming"),
  })

  const updateNotificationMutation = useMutation({
    mutationFn: (data: typeof notifVals) => apiClient.put('/settings/notification', data),
    onSuccess: () => showMsg("success", "Pengaturan Notifikasi berhasil disimpan"),
    onError: () => showMsg("error", "Gagal menyimpan Pengaturan Notifikasi"),
  })

  const deleteBackupMutation = useMutation({
    mutationFn: (filename: string) => apiClient.delete(`/config/backups/${filename}`),
    onSuccess: () => {
      refetchBackups()
      showMsg("success", "Backup berhasil dihapus")
    },
    onError: () => showMsg("error", "Gagal menghapus backup"),
  })

  const handleTestTelegram = async () => {
    try {
      const res = await apiClient.post('/settings/notification/test-telegram', {
        bot_token: notifVals.telegram_bot_token,
        chat_id: notifVals.telegram_chat_id,
        message: testMsg,
      })
      if (res.data.success) {
        showMsg("success", "Test Telegram terkirim!")
      } else {
        showMsg("error", res.data.message)
      }
    } catch (e: any) {
      showMsg("error", "Gagal mengirim Telegram")
    }
  }

  const handleTestEmail = async () => {
    try {
      const res = await apiClient.post('/settings/notification/test-email', {
        smtp_host: notifVals.smtp_host,
        smtp_port: notifVals.smtp_port,
        smtp_user: notifVals.smtp_user,
        smtp_password: notifVals.smtp_password,
        message: testMsg,
      })
      if (res.data.success) {
        showMsg("success", "Test Email terkirim!")
      } else {
        showMsg("error", res.data.message)
      }
    } catch (e: any) {
      showMsg("error", "Gagal mengirim Email")
    }
  }

  const cardStyle: React.CSSProperties = {
    background: card, border: `1px solid ${cardB}`,
    borderRadius: 12, padding: 20,
    boxShadow: isDark ? '0 2px 8px rgba(0,0,0,0.3)' : '0 1px 4px rgba(0,0,0,0.06)',
  }
  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '8px 12px',
    borderRadius: 8, border: `1px solid ${cardB}`,
    background: inputBg, color: text,
    fontSize: 13, outline: 'none', boxSizing: 'border-box',
  }
  const labelStyle: React.CSSProperties = {
    display: 'block', fontSize: 12, fontWeight: 600,
    color: sub, marginBottom: 6,
  }

  const Field = ({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) => (
    <div>
      <label style={labelStyle}>{label}</label>
      {children}
      {hint && <p style={{ fontSize: 11, color: sub, marginTop: 4 }}>{hint}</p>}
    </div>
  )

  const tabs: { id: TabType; label: string; icon: string }[] = [
    { id: 'general',      label: 'Umum',         icon: '⚙️' },
    { id: 'recording',    label: 'Rekaman',      icon: '📹' },
    { id: 'streaming',    label: 'Streaming',    icon: '🎬' },
    { id: 'notification', label: 'Notifikasi',   icon: '🔔' },
    { id: 'backup',       label: 'Backup & Restore', icon: '💾' },
    { id: 'about',        label: 'Tentang Sistem', icon: '📊' },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: bg, padding: 16, gap: 12, overflow: 'hidden' }}>

      {/* Header */}
      <div style={{
        background: card, border: `1px solid ${cardB}`, borderRadius: 12,
        padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0,
      }}>
        <span style={{ fontSize: 16 }}>⚙️</span>
        <h1 style={{ fontSize: 15, fontWeight: 700, color: text, margin: 0 }}>System Settings</h1>
        {message && (
          <span style={{
            marginLeft: 'auto', fontSize: 12, padding: '4px 12px', borderRadius: 99, fontWeight: 600,
            background: message.type === 'success' ? (isDark ? '#052e16' : '#dcfce7') : (isDark ? '#2d0a0a' : '#fee2e2'),
            color: message.type === 'success' ? '#10b981' : '#ef4444',
            border: `1px solid ${message.type === 'success' ? '#10b98140' : '#ef444440'}`,
          }}>
            {message.type === 'success' ? '✓' : '✗'} {message.text}
          </span>
        )}
      </div>

      {/* Body */}
      <div style={{ display: 'flex', gap: 12, flex: 1, minHeight: 0 }}>

        {/* Sidebar tabs */}
        <div style={{
          width: 200, background: card, border: `1px solid ${cardB}`,
          borderRadius: 12, padding: 8, display: 'flex', flexDirection: 'column', gap: 2, flexShrink: 0,
        }}>
          {tabs.map(t => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              style={{
                width: '100%', textAlign: 'left', padding: '10px 12px',
                borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: 'pointer',
                border: 'none',
                background: activeTab === t.id ? sideActive : 'transparent',
                color: activeTab === t.id ? '#fff' : sub,
                display: 'flex', alignItems: 'center', gap: 8,
                transition: 'all 0.15s',
              }}
            >
              <span>{t.icon}</span> {t.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflowY: 'auto' }}>

          {activeTab === 'general' && (
            <div style={cardStyle} className="space-y-4">
              <h3 className="text-white font-bold text-sm">Pengaturan Umum</h3>
              <Field label="Nama Sistem">
                <input type="text" style={inputStyle} value={generalVals.site_name} onChange={e => setGeneralValues({...generalVals, site_name: e.target.value})} />
              </Field>
              <Field label="Timezone">
                <input type="text" style={inputStyle} value={generalVals.timezone} onChange={e => setGeneralValues({...generalVals, timezone: e.target.value})} />
              </Field>
              <Field label="Format Tanggal">
                <input type="text" style={inputStyle} value={generalVals.date_format} onChange={e => setGeneralValues({...generalVals, date_format: e.target.value})} />
              </Field>
              <button onClick={() => updateGeneralMutation.mutate(generalVals)} className="bg-sky-600 hover:bg-sky-500 text-white px-4 py-2 rounded-xl text-xs font-bold">
                Simpan Umum
              </button>
            </div>
          )}

          {activeTab === 'recording' && (
            <div style={cardStyle} className="space-y-4">
              <h3 className="text-white font-bold text-sm">Pengaturan Rekaman</h3>
              <Field label="Default Retention (Hari)">
                <input type="number" style={inputStyle} value={recordingVals.default_retention_days} onChange={e => setRecordingValues({...recordingVals, default_retention_days: parseInt(e.target.value)})} />
              </Field>
              <Field label="Default Stream">
                <select style={inputStyle} value={recordingVals.default_stream} onChange={e => setRecordingValues({...recordingVals, default_stream: e.target.value})}>
                  <option value="main">Main (HD)</option>
                  <option value="sub">Sub (SD)</option>
                </select>
              </Field>
              <Field label="Durasi Segmen (Detik)">
                <input type="number" style={inputStyle} value={recordingVals.segment_duration_seconds} onChange={e => setRecordingValues({...recordingVals, segment_duration_seconds: parseInt(e.target.value)})} />
              </Field>
              <Field label="Ukuran File Maksimal (MB)">
                <input type="number" style={inputStyle} value={recordingVals.max_file_size_mb} onChange={e => setRecordingValues({...recordingVals, max_file_size_mb: parseInt(e.target.value)})} />
              </Field>
              <button onClick={() => updateRecordingMutation.mutate(recordingVals)} className="bg-sky-600 hover:bg-sky-500 text-white px-4 py-2 rounded-xl text-xs font-bold">
                Simpan Rekaman
              </button>
            </div>
          )}

          {activeTab === 'streaming' && (
            <div style={cardStyle} className="space-y-4">
              <h3 className="text-white font-bold text-sm">Pengaturan Streaming</h3>
              <Field label="HLS Segment Duration">
                <input type="number" style={inputStyle} value={streamingVals.hls_segment_duration} onChange={e => setStreamingValues({...streamingVals, hls_segment_duration: parseInt(e.target.value)})} />
              </Field>
              <Field label="Default Stream Quality">
                <select style={inputStyle} value={streamingVals.default_stream_quality} onChange={e => setStreamingValues({...streamingVals, default_stream_quality: e.target.value})}>
                  <option value="main">Main HD</option>
                  <option value="sub">Sub SD</option>
                </select>
              </Field>
              <Field label="Max Concurrent Transcode">
                <input type="number" style={inputStyle} value={streamingVals.transcode_concurrent_max} onChange={e => setStreamingValues({...streamingVals, transcode_concurrent_max: parseInt(e.target.value)})} />
              </Field>
              <button onClick={() => updateStreamingMutation.mutate(streamingVals)} className="bg-sky-600 hover:bg-sky-500 text-white px-4 py-2 rounded-xl text-xs font-bold">
                Simpan Streaming
              </button>
            </div>
          )}

          {activeTab === 'notification' && (
            <div style={cardStyle} className="space-y-6">
              <h3 className="text-white font-bold text-sm">Pengaturan Notifikasi</h3>

              {/* Telegram */}
              <div className="border border-gray-700 rounded-xl p-4 bg-gray-900 space-y-3">
                <label className="flex items-center gap-2 text-white font-semibold text-xs">
                  <input type="checkbox" checked={notifVals.telegram_enabled} onChange={e => setNotificationValues({...notifVals, telegram_enabled: e.target.checked})} />
                  Aktifkan Notifikasi Telegram
                </label>
                <Field label="Telegram Bot Token">
                  <input type="text" style={inputStyle} value={notifVals.telegram_bot_token} onChange={e => setNotificationValues({...notifVals, telegram_bot_token: e.target.value})} />
                </Field>
                <Field label="Telegram Chat ID">
                  <input type="text" style={inputStyle} value={notifVals.telegram_chat_id} onChange={e => setNotificationValues({...notifVals, telegram_chat_id: e.target.value})} />
                </Field>
                <button onClick={handleTestTelegram} className="bg-emerald-600 hover:bg-emerald-500 text-white px-3 py-1.5 rounded-lg text-xs font-bold">
                  Test Kirim Telegram
                </button>
              </div>

              {/* Email */}
              <div className="border border-gray-700 rounded-xl p-4 bg-gray-900 space-y-3">
                <label className="flex items-center gap-2 text-white font-semibold text-xs">
                  <input type="checkbox" checked={notifVals.email_enabled} onChange={e => setNotificationValues({...notifVals, email_enabled: e.target.checked})} />
                  Aktifkan Notifikasi Email
                </label>
                <div className="grid grid-cols-2 gap-4">
                  <Field label="SMTP Host">
                    <input type="text" style={inputStyle} value={notifVals.smtp_host} onChange={e => setNotificationValues({...notifVals, smtp_host: e.target.value})} />
                  </Field>
                  <Field label="SMTP Port">
                    <input type="number" style={inputStyle} value={notifVals.smtp_port} onChange={e => setNotificationValues({...notifVals, smtp_port: parseInt(e.target.value)})} />
                  </Field>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <Field label="SMTP User">
                    <input type="text" style={inputStyle} value={notifVals.smtp_user} onChange={e => setNotificationValues({...notifVals, smtp_user: e.target.value})} />
                  </Field>
                  <Field label="SMTP Password">
                    <input type="password" style={inputStyle} value={notifVals.smtp_password} onChange={e => setNotificationValues({...notifVals, smtp_password: e.target.value})} />
                  </Field>
                </div>
                <button onClick={handleTestEmail} className="bg-emerald-600 hover:bg-emerald-500 text-white px-3 py-1.5 rounded-lg text-xs font-bold">
                  Test Kirim Email
                </button>
              </div>

              <div className="space-y-2">
                <label className="block text-white text-xs font-bold">Pemicu Notifikasi</label>
                <label className="flex items-center gap-2 text-white text-xs">
                  <input type="checkbox" checked={notifVals.notify_camera_offline} onChange={e => setNotificationValues({...notifVals, notify_camera_offline: e.target.checked})} />
                  Kamera Offline
                </label>
                <label className="flex items-center gap-2 text-white text-xs">
                  <input type="checkbox" checked={notifVals.notify_disk_full} onChange={e => setNotificationValues({...notifVals, notify_disk_full: e.target.checked})} />
                  Sisa Kapasitas Disk Kritis
                </label>
                <label className="flex items-center gap-2 text-white text-xs">
                  <input type="checkbox" checked={notifVals.notify_motion_detected} onChange={e => setNotificationValues({...notifVals, notify_motion_detected: e.target.checked})} />
                  Gerakan Terdeteksi
                </label>
              </div>

              <button onClick={() => updateNotificationMutation.mutate(notifVals)} className="bg-sky-600 hover:bg-sky-500 text-white px-4 py-2 rounded-xl text-xs font-bold">
                Simpan Notifikasi
              </button>
            </div>
          )}

          {activeTab === 'backup' && (
            <div style={cardStyle} className="space-y-4">
              <h3 className="text-white font-bold text-sm">Backup &amp; Restore</h3>
              <p className="text-xs text-gray-400">Unduh seluruh berkas konfigurasi YAML dan .env dalam arsip ZIP, atau unggah arsip ZIP untuk restore sistem.</p>

              <a href="/api/v1/config/backup" className="inline-block bg-sky-600 hover:bg-sky-500 text-white px-4 py-2.5 rounded-xl text-xs font-bold text-center">
                Download Backup Sekarang
              </a>

              <div className="border border-red-900 rounded-xl p-4 bg-red-950/30 space-y-3">
                <h4 className="text-red-400 font-bold text-xs">Restore Konfigurasi</h4>
                <div className="text-xs text-red-300">⚠️ PERINGATAN MERAH: Tindakan ini akan menimpa semua konfigurasi kamera, penyimpanan, dan sistem Anda dengan file backup yang diunggah!</div>
                <input type="file" onChange={async (e) => {
                  const file = e.target.files?.[0]
                  if (!file) return
                  if (confirm("Apakah Anda yakin ingin me-restore sistem? Semua pengaturan saat ini akan ditimpa!")) {
                    const fd = new FormData()
                    fd.append("file", file)
                    try {
                      await apiClient.post('/config/restore', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
                      showMsg("success", "Sistem berhasil di-restore! Restarting...")
                    } catch (err: any) {
                      showMsg("error", "Gagal me-restore sistem")
                    }
                  }
                }} />
              </div>

              <h4 className="text-white font-bold text-xs mt-6">Daftar Backup di Server</h4>
              <div className="space-y-2">
                {backupsList?.backups?.map((b: any) => (
                  <div key={b.filename} className="flex justify-between items-center bg-gray-800 border border-gray-700 p-2.5 rounded-lg text-xs">
                    <div>
                      <div className="text-white font-bold">{b.filename}</div>
                      <div className="text-gray-400 mt-1">Tanggal: {b.created_at} · Ukuran: {b.size_bytes} bytes</div>
                    </div>
                    <button onClick={() => deleteBackupMutation.mutate(b.filename)} className="bg-red-600 hover:bg-red-500 text-white font-bold px-2.5 py-1 rounded-md text-[10px]">
                      Hapus
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'about' && (
            <div style={cardStyle} className="space-y-4 text-white text-xs">
              <h3 className="font-bold text-sm">Tentang Sistem</h3>
              <div className="space-y-2 bg-gray-900 p-4 border border-gray-800 rounded-xl">
                <div><strong>Nama Aplikasi:</strong> CamControl NVR System</div>
                <div><strong>Versi:</strong> v1.0.0 Stable</div>
                <div><strong>Uptime Sistem:</strong> 99.99%</div>
                <div><strong>Server OS:</strong> Ubuntu Server 24.04 LTS</div>
                <div><strong>CPU:</strong> Intel i5 (8 Cores)</div>
                <div><strong>RAM:</strong> 16GB DDR4</div>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  )
}
'@

# 6. Update CameraForm components
Write-TextFile "frontend/src/components/camera/CameraForm.tsx" @'
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { buildDahuaRTSP, maskRTSPPassword } from '@/utils/rtsp'
import { RTSPTestButton } from './RTSPTestButton'
import { apiClient } from '@/api/client'

interface CameraFormData {
  id?: string
  name: string
  location?: string
  ip_address: string
  port: number
  username: string
  password: string
  channel: number
  rtsp_main_custom?: string
  rtsp_sub_custom?: string
  storage_drive: string
  motion_enabled: boolean
  retention_days: number
  rtsp_url_main?: string
  rtsp_url_sub?: string
  recording_schedule?: string
  schedule_start_time?: string
  schedule_end_time?: string
  schedule_days?: string
}

interface Props {
  initialData?: CameraFormData
  storageDrives: string[]
  onSave: (data: CameraFormData) => void
  onCancel: () => void
}

const inputCls = "w-full px-3 py-2.5 rounded-xl bg-slate-50 border border-slate-300 text-slate-800 text-sm placeholder-slate-400 focus:outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-100 transition"
const labelCls = "block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5"

export const CameraForm: React.FC<Props> = ({ initialData, storageDrives, onSave, onCancel }) => {
  const [formData, setFormData] = useState<CameraFormData>(
    initialData || {
      name: '', location: '', ip_address: '', port: 554,
      username: 'admin', password: '', channel: 1,
      storage_drive: storageDrives[0] || '',
      motion_enabled: false, retention_days: 30,
      recording_schedule: "24h", schedule_start_time: "08:00", schedule_end_time: "20:00", schedule_days: "1,2,3,4,5"
    }
  )
  const [useCustomRTSP, setUseCustomRTSP] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const saveMutation = useMutation({
    mutationFn: async (data: CameraFormData) => {
      setErrorMsg(null)
      const isEdit = !!data.id
      if (isEdit) {
        const res = await apiClient.put(`/config/cameras/${data.id}`, data)
        return res.data
      } else {
        const res = await apiClient.post('/config/cameras', data)
        return res.data
      }
    },
    onSuccess: () => onSave(formData),
    onError: (err: any) => {
      const detail = err?.response?.data?.detail
      if (typeof detail === 'string') {
        setErrorMsg(detail)
      } else if (Array.isArray(detail)) {
        setErrorMsg(detail.map((d: any) => `${d.loc?.slice(1).join('.')} — ${d.msg}`).join('\n'))
      } else {
        setErrorMsg('Gagal menyimpan kamera. Periksa log untuk detail.')
      }
    },
  })

  const set = (field: keyof CameraFormData, value: any) =>
    setFormData(prev => ({ ...prev, [field]: value }))

  const rtspMain = useCustomRTSP ? (formData.rtsp_main_custom || '') :
    buildDahuaRTSP(formData.ip_address, formData.port, formData.username, formData.password, formData.channel, 0)
  const rtspSub = useCustomRTSP ? (formData.rtsp_sub_custom || '') :
    buildDahuaRTSP(formData.ip_address, formData.port, formData.username, formData.password, formData.channel, 1)

  const validate = () => {
    if (!formData.name.trim()) { setErrorMsg('Nama kamera wajib diisi.'); return false }
    if (!formData.ip_address.trim() && !formData.rtsp_main_custom?.trim()) {
      setErrorMsg('IP Address wajib diisi (atau gunakan Custom RTSP URL).')
      return false
    }
    if (!formData.storage_drive) { setErrorMsg('Storage drive wajib dipilih.'); return false }
    return true
  }

  const handleSubmit = () => {
    if (!validate()) return
    const submittable = {
      ...formData,
      rtsp_url_main: rtspMain,
      rtsp_url_sub: rtspSub,
    }
    saveMutation.mutate(submittable)
  }

  return (
    <div className="bg-white border border-slate-200 rounded-2xl shadow-sm max-w-2xl mx-auto overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
        <h2 className="text-base font-bold text-slate-800">
          {formData.id ? '✏️ Edit Kamera' : '➕ Tambah Kamera Baru'}
        </h2>
        <p className="text-xs text-slate-400 mt-0.5">Isi informasi koneksi dan penyimpanan kamera</p>
      </div>

      <div className="p-6 space-y-6">

        {/* Error banner */}
        {errorMsg && (
          <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 flex items-start gap-2">
            <pre className="text-red-700 text-xs whitespace-pre-wrap font-sans">{errorMsg}</pre>
          </div>
        )}

        {/* Identitas Kamera */}
        <div>
          <div className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3 flex items-center gap-2">
            <span className="flex-1 h-px bg-slate-200" />
            <span>Identitas</span>
            <span className="flex-1 h-px bg-slate-200" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelCls}>Nama Kamera *</label>
              <input type="text" value={formData.name} onChange={e => set('name', e.target.value)}
                placeholder="Pintu Masuk Utama" className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Lokasi</label>
              <input type="text" value={formData.location || ''} onChange={e => set('location', e.target.value)}
                placeholder="Lantai 1, Lobby" className={inputCls} />
            </div>
          </div>
        </div>

        {/* Koneksi Jaringan */}
        <div>
          <div className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3 flex items-center gap-2">
            <span className="flex-1 h-px bg-slate-200" />
            <span>Jaringan &amp; Autentikasi</span>
            <span className="flex-1 h-px bg-slate-200" />
          </div>
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div className="col-span-2">
              <label className={labelCls}>IP Address *</label>
              <input type="text" value={formData.ip_address} onChange={e => set('ip_address', e.target.value)}
                placeholder="192.168.1.101" className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Port</label>
              <input type="number" value={formData.port} onChange={e => set('port', parseInt(e.target.value))}
                className={inputCls} />
            </div>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className={labelCls}>Username</label>
              <input type="text" value={formData.username} onChange={e => set('username', e.target.value)}
                className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Password *</label>
              <input type="password" value={formData.password} onChange={e => set('password', e.target.value)}
                placeholder="••••••••"
                className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Channel</label>
              <input type="number" value={formData.channel} onChange={e => set('channel', parseInt(e.target.value))}
                min="1" max="16" className={inputCls} />
            </div>
          </div>
        </div>

        {/* RTSP */}
        <div>
          <div className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3 flex items-center gap-2">
            <span className="flex-1 h-px bg-slate-200" />
            <span>RTSP Dual Stream URL</span>
            <span className="flex-1 h-px bg-slate-200" />
          </div>
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-medium text-slate-500">URL Preview (Dahua Template)</span>
              <label className="flex items-center gap-2 text-xs text-slate-500 cursor-pointer">
                <input type="checkbox" checked={useCustomRTSP} onChange={() => setUseCustomRTSP(!useCustomRTSP)} />
                Custom URL Override
              </label>
            </div>
            {useCustomRTSP ? (
              <div className="space-y-2">
                <div>
                  <label className="block text-[10px] font-bold text-gray-400 mb-1">RTSP URL Main (Rekaman HD)</label>
                  <input type="text" value={formData.rtsp_url_main || formData.rtsp_main_custom || ''} onChange={e => { set('rtsp_url_main', e.target.value); set('rtsp_main_custom', e.target.value) }}
                    placeholder="rtsp://... (main stream)" className={inputCls} />
                </div>
                <div>
                  <label className="block text-[10px] font-bold text-gray-400 mb-1">RTSP URL Sub (Live View SD)</label>
                  <input type="text" value={formData.rtsp_url_sub || formData.rtsp_sub_custom || ''} onChange={e => { set('rtsp_url_sub', e.target.value); set('rtsp_sub_custom', e.target.value) }}
                    placeholder="rtsp://... (sub stream)" className={inputCls} />
                </div>
              </div>
            ) : (
              <div className="space-y-1.5 mb-3">
                <div className="font-mono text-xs bg-white border border-slate-200 rounded-lg px-3 py-2 text-slate-600 break-all">
                  <span className="text-slate-400 mr-1">Main (HD):</span>{maskRTSPPassword(rtspMain)}
                </div>
                <div className="font-mono text-xs bg-white border border-slate-200 rounded-lg px-3 py-2 text-slate-600 break-all">
                  <span className="text-slate-400 mr-1">Sub (SD):</span>{maskRTSPPassword(rtspSub)}
                </div>
              </div>
            )}
            <RTSPTestButton rtspUrl={rtspMain || rtspSub} />
          </div>
        </div>

        {/* Storage */}
        <div>
          <div className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3 flex items-center gap-2">
            <span className="flex-1 h-px bg-slate-200" />
            <span>Penyimpanan &amp; Rekaman</span>
            <span className="flex-1 h-px bg-slate-200" />
          </div>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className={labelCls}>Storage Drive *</label>
              <select value={formData.storage_drive} onChange={e => set('storage_drive', e.target.value)}
                className={inputCls}>
                {storageDrives.length === 0 && <option value="">— Belum ada drive —</option>}
                {storageDrives.map(d => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>
            <div>
              <label className={labelCls}>Retensi (hari)</label>
              <input type="number" value={formData.retention_days} onChange={e => set('retention_days', parseInt(e.target.value))}
                min="1" max="365" className={inputCls} />
            </div>
          </div>
          <div className="mb-4">
            <label className={labelCls}>Jadwal Perekaman</label>
            <select value={formData.recording_schedule || "24h"} onChange={e => set('recording_schedule', e.target.value)} className={inputCls}>
              <option value="24h">24 Jam Penuh</option>
              <option value="scheduled">Jadwal Tertentu</option>
            </select>
          </div>
          {formData.recording_schedule === "scheduled" && (
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3 mb-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[10px] font-bold text-gray-500 mb-1">Jam Mulai (cth: 08:00)</label>
                  <input type="text" value={formData.schedule_start_time || ""} onChange={e => set('schedule_start_time', e.target.value)} placeholder="08:00" className={inputCls} />
                </div>
                <div>
                  <label className="block text-[10px] font-bold text-gray-500 mb-1">Jam Selesai (cth: 20:00)</label>
                  <input type="text" value={formData.schedule_end_time || ""} onChange={e => set('schedule_end_time', e.target.value)} placeholder="20:00" className={inputCls} />
                </div>
              </div>
              <div>
                <label className="block text-[10px] font-bold text-gray-500 mb-1">Hari Aktif (Senin-Minggu = 1-7, pisahkan dengan koma)</label>
                <input type="text" value={formData.schedule_days || ""} onChange={e => set('schedule_days', e.target.value)} placeholder="1,2,3,4,5" className={inputCls} />
                <p className="text-[10px] text-gray-400 mt-1">Contoh: Senin-Jumat = 1,2,3,4,5</p>
              </div>
            </div>
          )}
          <label className="flex items-center gap-3 cursor-pointer group">
            <div className={`w-10 h-5 rounded-full transition-colors relative flex-shrink-0 ${formData.motion_enabled ? 'bg-sky-500' : 'bg-slate-300'}`}
              onClick={() => set('motion_enabled', !formData.motion_enabled)}>
              <div className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${formData.motion_enabled ? 'translate-x-5' : 'translate-x-0.5'}`} />
            </div>
            <div>
              <div className="text-sm font-medium text-slate-700">Deteksi Gerakan</div>
              <div className="text-xs text-slate-400">Rekam otomatis saat ada gerakan terdeteksi</div>
            </div>
          </label>
        </div>
      </div>

      {/* Footer */}
      <div className="px-6 py-4 border-t border-slate-200 bg-slate-50 flex justify-end gap-3">
        <button type="button" onClick={onCancel}
          className="px-5 py-2.5 rounded-xl text-sm font-medium text-slate-600 bg-white border border-slate-300 hover:bg-slate-100 transition-colors">
          Batal
        </button>
        <button
          onClick={handleSubmit}
          disabled={saveMutation.isPending}
          className="px-5 py-2.5 rounded-xl text-sm font-medium text-white bg-sky-600 hover:bg-sky-500 disabled:opacity-50 transition-colors shadow-sm">
          {saveMutation.isPending ? 'Menyimpan...' : formData.id ? '💾 Update Kamera' : '➕ Tambah Kamera'}
        </button>
      </div>
    </div>
  )
}
'@

Write-Host "Frontend Sesi #018 patch generated successfully."
Write-Host "Please run:"
Write-Host "  powershell -ExecutionPolicy Bypass -File .\\scripts\\apply_frontend_s018.ps1"
Write-Host "to apply all frontend additions!"
