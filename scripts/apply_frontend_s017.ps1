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

Write-Host "Applying frontend patch for Session #017 (Sunday, July 26, 2026)..."

$types = Get-Content "frontend/src/types/index.ts" -Raw
$types = $types -replace "export interface User \{\s+id: number", "export interface User {`r`n  id: string"
Set-Content "frontend/src/types/index.ts" $types -Encoding UTF8

Write-TextFile "frontend/src/api/users.ts" @'
import { apiClient } from './client'
import type { User } from "@/types"
import type { AxiosResponse } from 'axios'

export interface ChangePasswordPayload {
  current_password: string
  new_password: string
}

export interface ResetPasswordPayload {
  new_password: string
}

export const usersApi = {
  list:   ()                              => apiClient.get<User[]>('/users').then((r: AxiosResponse<User[]>) => r.data),
  get:    (id: string)                    => apiClient.get<User>(`/users/${id}`).then((r: AxiosResponse<User>) => r.data),
  create: (data: Partial<User>)           => apiClient.post<User>('/users', data).then((r: AxiosResponse<User>) => r.data),
  update: (id: string, d: Partial<User>)  => apiClient.put<User>(`/users/${id}`, d).then((r: AxiosResponse<User>) => r.data),
  delete: (id: string)                    => apiClient.delete(`/users/${id}`),
  me:     ()                              => apiClient.get<User>('/users/me').then((r: AxiosResponse<User>) => r.data),
  changePassword: (data: ChangePasswordPayload) =>
    apiClient.put<{ message: string }>('/users/me/password', data).then((r: AxiosResponse<{ message: string }>) => r.data),
  adminResetPassword: (id: string, data: ResetPasswordPayload) =>
    apiClient.put<{ message: string }>(`/users/${id}/reset-password`, data).then((r: AxiosResponse<{ message: string }>) => r.data),
}
'@

Write-TextFile "frontend/src/api/recordings.ts" @'
import { apiClient } from './client'
import type { Recording } from "@/types"

interface PlaybackQueued {
  job_id: string
  status: 'queued' | 'processing' | 'done' | 'error'
  status_url?: string
  progress_pct?: number
  cache_path?: string | null
  error_msg?: string | null
}

export const recordingsApi = {
  list: (p?: { camera_id?: string; date_from?: string; date_to?: string }) => {
    const params: Record<string, string> = {}
    if (p?.camera_id) params.camera_id = p.camera_id

    if (p?.date_from && p?.date_to && p.date_from !== p.date_to) {
      params.start = `${p.date_from}T00:00:00`
      params.end = `${p.date_to}T23:59:59`
    } else if (p?.date_from && p?.date_to && p.date_from === p.date_to) {
      params.date = p.date_from
    } else if (p?.date_from && !p?.date_to) {
      params.date = p.date_from
    }

    return apiClient.get<Recording[]>('/recordings', { params }).then(r => {
      let data = r.data as any
      if (data && !Array.isArray(data) && Array.isArray(data.data)) data = data.data
      return Array.isArray(data) ? data : []
    })
  },

  listAll: () => apiClient.get<Recording[]>('/recordings').then(r => {
    let data = r.data as any
    if (data && !Array.isArray(data) && Array.isArray(data.data)) data = data.data
    return Array.isArray(data) ? data : []
  }),

  get: (id: number) => apiClient.get<Recording>(`/recordings/${id}`).then(r => r.data),

  playUrl: (id: number): string => {
    const token = localStorage.getItem('access_token') ?? ''
    const qs = token ? `?token=${encodeURIComponent(token)}` : ''
    return `/api/v1/recordings/${id}/play${qs}`
  },

  preparePlayback: async (id: number): Promise<{ status: 'ready' } | PlaybackQueued> => {
    const res = await apiClient.get(`/recordings/${id}/play`, {
      headers: { Range: 'bytes=0-0' },
      validateStatus: (status) => status === 200 || status === 206 || status === 202,
    })

    if (res.status === 202) return res.data as PlaybackQueued
    return { status: 'ready' }
  },

  playStatus: (id: number, jobId?: string) =>
    apiClient.get<PlaybackQueued>(`/recordings/${id}/play/status`, {
      params: jobId ? { job_id: jobId } : undefined,
    }).then(r => r.data),

  downloadUrl: (id: number) => `/api/v1/recordings/${id}/download`,
  protect:     (id: number) => apiClient.post(`/recordings/${id}/protect`).then(r => r.data),
  delete:      (id: number) => apiClient.delete(`/recordings/${id}`),
}
'@

Write-TextFile "frontend/src/hooks/useHLSPlayer.ts" @'
import { useEffect, useState, RefObject } from 'react'
import Hls from 'hls.js'

export function useHLSPlayer(hlsUrl: string | null, videoRef: RefObject<HTMLVideoElement>) {
  const [isRetrying, setIsRetrying] = useState(false)
  const [hasError, setHasError] = useState(false)

  useEffect(() => {
    if (!hlsUrl || !videoRef.current) return

    const video = videoRef.current
    let hls: Hls | null = null
    let cancelled = false
    let retryTimer: ReturnType<typeof setTimeout> | null = null
    let loadingTimer: ReturnType<typeof setTimeout> | null = null
    let retryCount = 0
    const maxRetries = 5

    const cleanupTimers = () => {
      if (retryTimer) clearTimeout(retryTimer)
      if (loadingTimer) clearTimeout(loadingTimer)
    }

    const attach = () => {
      if (cancelled) return
      setHasError(false)
      loadingTimer = setTimeout(() => setIsRetrying(true), 10000)

      if (Hls.isSupported()) {
        hls = new Hls({
          enableWorker: true,
          lowLatencyMode: true,
          manifestLoadingMaxRetry: 0,
          fragLoadingMaxRetry: 6,
        })
        hls.loadSource(hlsUrl)
        hls.attachMedia(video)

        hls.on(Hls.Events.MANIFEST_PARSED, () => {
          cleanupTimers()
          setIsRetrying(false)
          video.play().catch(() => undefined)
        })

        hls.on(Hls.Events.ERROR, (_, data) => {
          const isManifestError =
            data.details === Hls.ErrorDetails.MANIFEST_LOAD_ERROR ||
            data.details === Hls.ErrorDetails.MANIFEST_LOAD_TIMEOUT

          if (isManifestError && retryCount < maxRetries) {
            retryCount += 1
            setIsRetrying(true)
            hls?.destroy()
            hls = null
            retryTimer = setTimeout(attach, 2000)
            return
          }

          if (data.fatal) {
            if (data.type === Hls.ErrorTypes.NETWORK_ERROR && retryCount < maxRetries) {
              retryCount += 1
              setIsRetrying(true)
              retryTimer = setTimeout(() => hls?.startLoad(), 2000)
            } else if (data.type === Hls.ErrorTypes.MEDIA_ERROR) {
              hls?.recoverMediaError()
            } else {
              cleanupTimers()
              setHasError(true)
              hls?.destroy()
              hls = null
            }
          }
        })
      } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
        video.src = hlsUrl
        video.play()
          .then(() => {
            cleanupTimers()
            setIsRetrying(false)
          })
          .catch(() => setIsRetrying(true))
      }
    }

    attach()

    return () => {
      cancelled = true
      cleanupTimers()
      hls?.destroy()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hlsUrl, videoRef.current])

  return { isRetrying, hasError }
}
'@

Write-TextFile "frontend/src/components/camera/VideoPlayer.tsx" @'
import { useState, useRef, useCallback } from 'react'
import { useHLSPlayer } from '@/hooks/useHLSPlayer'
import { camerasApi } from '@/api/cameras'
import { useQuery } from '@tanstack/react-query'
import { useCameraStore } from '@/store/cameras'

interface Props {
  cameraId: string
  cameraName?: string
  className?: string
  onClick?: () => void
  showControls?: boolean
}

export const VideoPlayer: React.FC<Props> = ({
  cameraId,
  cameraName,
  className,
  onClick,
  showControls = true,
}) => {
  const [snapshotUrl, setSnapshotUrl] = useState<string | null>(null)
  const [showSnapshotView, setShowSnapshotView] = useState(false)
  const videoRef = useRef<HTMLVideoElement>(null)

  const { streamTypeOverride, setStreamType, setFullscreen } = useCameraStore()
  const streamType = streamTypeOverride[cameraId] ?? 'sub'

  const { data, isLoading, error } = useQuery({
    queryKey: ['live', cameraId, streamType],
    queryFn: () => camerasApi.liveUrl(cameraId, streamType),
    staleTime: Infinity,
    refetchInterval: 30000,
  })

  const { isRetrying, hasError } = useHLSPlayer(data?.hls_url ?? null, videoRef)

  const handleSnapshot = async (e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      const url = await camerasApi.snapshot(cameraId)
      setSnapshotUrl(url)
      setShowSnapshotView(true)
    } catch (err) {
      console.error('Failed to capture snapshot:', err)
    }
  }

  const handlePiP = useCallback(async (e: React.MouseEvent) => {
    e.stopPropagation()
    const video = videoRef.current
    if (!video) return
    try {
      if (document.pictureInPictureElement === video) {
        await document.exitPictureInPicture()
      } else {
        await video.requestPictureInPicture()
      }
    } catch (err) {
      console.error('PiP not supported:', err)
    }
  }, [])

  const handleFullscreen = useCallback((e: React.MouseEvent) => {
    e.stopPropagation()
    setFullscreen(cameraId)
  }, [cameraId, setFullscreen])

  const toggleStream = (e: React.MouseEvent) => {
    e.stopPropagation()
    setStreamType(cameraId, streamType === 'main' ? 'sub' : 'main')
  }

  const containerStyle: React.CSSProperties = {
    position: 'relative',
    width: '100%',
    height: '100%',
    background: '#000',
    overflow: 'hidden',
  }

  if (isLoading) {
    return (
      <div className={className} style={containerStyle}>
        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <span style={{ color: '#6b7280', fontSize: 12 }}>Memuat...</span>
        </div>
      </div>
    )
  }

  if (error || !data?.hls_url) {
    return (
      <div className={className} style={containerStyle}>
        <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
          <span style={{ fontSize: 24 }}>📷</span>
          <span style={{ color: '#9ca3af', fontSize: 11 }}>{cameraName || cameraId}</span>
          <span style={{ color: '#ef4444', fontSize: 10 }}>Offline</span>
        </div>
      </div>
    )
  }

  const pipSupported = typeof document !== 'undefined' && 'pictureInPictureEnabled' in document

  return (
    <div className={`group ${className ?? ''}`} style={containerStyle} onClick={onClick}>
      {showSnapshotView && snapshotUrl ? (
        <div style={{ position: 'absolute', inset: 0 }}>
          <img src={snapshotUrl} alt="Snapshot" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
          <button
            onClick={(e) => { e.stopPropagation(); setShowSnapshotView(false); setSnapshotUrl(null) }}
            style={{ position: 'absolute', top: 6, right: 6, padding: '2px 6px', background: 'rgba(0,0,0,0.75)', color: '#fff', fontSize: 11, border: 'none', borderRadius: 4, cursor: 'pointer' }}
          >
            ✕
          </button>
        </div>
      ) : (
        <>
          <video
            ref={videoRef}
            style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block', background: '#000' }}
            muted
            autoPlay
            playsInline
            onDoubleClick={handleFullscreen}
          />

          {(isRetrying || hasError) && (
            <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', pointerEvents: 'none', background: hasError ? 'rgba(0,0,0,0.55)' : 'transparent' }}>
              <span style={{ color: hasError ? '#f87171' : '#e5e7eb', fontSize: 12, background: 'rgba(0,0,0,0.7)', padding: '6px 10px', borderRadius: 6 }}>
                {hasError ? 'Stream belum tersedia' : 'Menghubungkan... (mencoba ulang)'}
              </span>
            </div>
          )}

          {showControls && (
            <div style={{
              position: 'absolute', bottom: 0, left: 0, right: 0,
              background: 'linear-gradient(to top, rgba(0,0,0,0.8) 0%, transparent 100%)',
              padding: '20px 8px 6px',
              display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end',
              pointerEvents: 'none',
            }}>
              <div>
                <div style={{ color: '#e2e8f0', fontSize: 12, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 180, textShadow: '0 1px 3px rgba(0,0,0,0.8)' }}>
                  {cameraName || cameraId}
                </div>
                <div style={{ color: '#94a3b8', fontSize: 9, marginTop: 1 }}>{cameraId}</div>
              </div>
              <span style={{ color: '#4ade80', fontSize: 10, fontWeight: 700, letterSpacing: '0.05em', textShadow: '0 1px 3px rgba(0,0,0,0.8)' }}>● LIVE</span>
            </div>
          )}

          {showControls && (
            <div
              className="opacity-0 group-hover:opacity-100 transition-opacity"
              style={{
                position: 'absolute', top: 0, left: 0, right: 0,
                background: 'linear-gradient(to bottom, rgba(0,0,0,0.7) 0%, transparent 100%)',
                padding: '6px 6px 16px',
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                gap: 4,
              }}
            >
              <button onClick={toggleStream} title="Toggle stream quality" style={btnStyle}>
                {streamType === 'main' ? 'MAIN' : 'SUB'}
              </button>
              <div style={{ display: 'flex', gap: 4 }}>
                <button onClick={handleSnapshot} title="Snapshot" style={btnStyle}>📷</button>
                {pipSupported && <button onClick={handlePiP} title="Picture in Picture" style={btnStyle}>⧉</button>}
                <button onClick={handleFullscreen} title="Fullscreen" style={btnStyle}>⛶</button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

const btnStyle: React.CSSProperties = {
  padding: '2px 7px',
  background: 'rgba(0,0,0,0.6)',
  color: '#fff',
  fontSize: 10,
  fontWeight: 600,
  border: '1px solid rgba(255,255,255,0.15)',
  borderRadius: 3,
  cursor: 'pointer',
  lineHeight: '18px',
  backdropFilter: 'blur(4px)',
}
'@

Write-TextFile "frontend/src/pages/Profile/index.tsx" @'
import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { usersApi } from '@/api/users'

export default function ProfilePage() {
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [message, setMessage] = useState<string | null>(null)

  const { data: user } = useQuery({
    queryKey: ['profile'],
    queryFn: usersApi.me,
  })

  const mutation = useMutation({
    mutationFn: usersApi.changePassword,
    onSuccess: (data) => {
      setMessage(data?.message ?? 'Password berhasil diubah')
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    },
    onError: (err: any) => {
      setMessage(err?.response?.data?.detail ?? 'Gagal mengubah password')
    },
  })

  const submit = () => {
    if (newPassword.length < 8) {
      setMessage('Password baru minimal 8 karakter')
      return
    }
    if (newPassword !== confirmPassword) {
      setMessage('Konfirmasi password tidak cocok')
      return
    }
    mutation.mutate({
      current_password: currentPassword,
      new_password: newPassword,
    })
  }

  return (
    <div className="h-full overflow-auto p-4">
      <div className="mx-auto max-w-2xl space-y-4">
        <div className="rounded bg-gray-800 p-4">
          <h1 className="mb-4 text-lg font-semibold">Profile</h1>
          <div className="grid grid-cols-1 gap-3 text-sm md:grid-cols-2">
            <div><div className="text-gray-400">Username</div><div>{user?.username ?? '-'}</div></div>
            <div><div className="text-gray-400">Nama Lengkap</div><div>{user?.full_name ?? '-'}</div></div>
            <div><div className="text-gray-400">Email</div><div>{user?.email ?? '-'}</div></div>
            <div><div className="text-gray-400">Role</div><div className="capitalize">{user?.role ?? '-'}</div></div>
            <div><div className="text-gray-400">Dibuat</div><div>{user?.created_at ? new Date(user.created_at).toLocaleString('id-ID') : '-'}</div></div>
          </div>
        </div>

        <div className="rounded bg-gray-800 p-4">
          <h2 className="mb-3 font-semibold">Ganti Password</h2>
          <div className="space-y-3">
            <input
              type="password"
              placeholder="Password lama"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className="w-full rounded border border-gray-600 bg-gray-700 px-3 py-2"
            />
            <input
              type="password"
              placeholder="Password baru (minimal 8 karakter)"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full rounded border border-gray-600 bg-gray-700 px-3 py-2"
            />
            <input
              type="password"
              placeholder="Konfirmasi password baru"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full rounded border border-gray-600 bg-gray-700 px-3 py-2"
            />
            <button
              onClick={submit}
              disabled={mutation.isPending}
              className="rounded bg-blue-600 px-4 py-2 text-sm hover:bg-blue-700 disabled:bg-gray-600"
            >
              {mutation.isPending ? 'Menyimpan...' : 'Simpan Password'}
            </button>
            {message && <div className="text-sm text-gray-300">{message}</div>}
          </div>
        </div>
      </div>
    </div>
  )
}
'@

Write-TextFile "frontend/src/pages/Users/index.tsx" @'
import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { usersApi } from "@/api/users"
import type { User } from "@/types"

export default function UsersPage() {
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

  return (
    <div className="flex h-full flex-col gap-4 p-4">
      <div className="flex flex-shrink-0 items-center gap-4 rounded bg-gray-800 px-4 py-3">
        <span className="text-sm font-medium">Users</span>
        <button onClick={() => setShowAddForm(true)} className="ml-auto rounded bg-blue-600 px-3 py-1 text-sm hover:bg-blue-700">
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
          <h3 className="mb-3 font-medium">Add New User</h3>
          <div className="grid grid-cols-2 gap-4">
            <input type="text" placeholder="Username" value={formData.username || ""} onChange={(e) => handleChange("username", e.target.value)} className="rounded border border-gray-600 bg-gray-700 px-3 py-2" />
            <input type="email" placeholder="Email" value={formData.email || ""} onChange={(e) => handleChange("email", e.target.value)} className="rounded border border-gray-600 bg-gray-700 px-3 py-2" />
            <input type="password" placeholder="Password" value={formData.password || ""} onChange={(e) => handleChange("password", e.target.value)} className="rounded border border-gray-600 bg-gray-700 px-3 py-2" />
            <select value={formData.role || "viewer"} onChange={(e) => handleChange("role", e.target.value)} className="rounded border border-gray-600 bg-gray-700 px-3 py-2">
              <option value="admin">Admin</option>
              <option value="operator">Operator</option>
              <option value="viewer">Viewer</option>
            </select>
          </div>
          <div className="mt-3 flex gap-2">
            <button onClick={handleCreate} disabled={createMutation.isPending} className="rounded bg-green-600 px-3 py-1 text-sm hover:bg-green-700 disabled:bg-gray-600">
              {createMutation.isPending ? "Creating..." : "Create"}
            </button>
            <button onClick={handleCancel} className="rounded bg-gray-700 px-3 py-1 text-sm hover:bg-gray-600">Cancel</button>
          </div>
        </div>
      )}

      <div className="flex-1 overflow-auto rounded bg-gray-900">
        {isLoading ? (
          <div className="flex h-full items-center justify-center text-gray-500">Loading...</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-gray-800">
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
                      <td className="px-4 py-2"><input value={formData.username || ""} onChange={(e) => handleChange("username", e.target.value)} className="w-full rounded bg-gray-700 px-2 py-1" /></td>
                      <td className="px-4 py-2"><input value={formData.email || ""} onChange={(e) => handleChange("email", e.target.value)} className="w-full rounded bg-gray-700 px-2 py-1" /></td>
                      <td className="px-4 py-2">
                        <select value={formData.role || "viewer"} onChange={(e) => handleChange("role", e.target.value)} className="w-full rounded bg-gray-700 px-2 py-1">
                          <option value="admin">Admin</option>
                          <option value="operator">Operator</option>
                          <option value="viewer">Viewer</option>
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
                      <td className="px-4 py-2">{user.username}</td>
                      <td className="px-4 py-2">{user.email || "-"}</td>
                      <td className="px-4 py-2"><span className="capitalize">{user.role}</span></td>
                      <td className="px-4 py-2"><span className={user.is_active ? "text-green-400" : "text-red-400"}>{user.is_active ? "Yes" : "No"}</span></td>
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

Write-TextFile "frontend/src/pages/Playback/index.tsx" @'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useQuery } from "@tanstack/react-query"
import { camerasApi } from "@/api/cameras"
import { recordingsApi } from "@/api/recordings"

type PlaybackState = 'idle' | 'loading' | 'processing' | 'ready' | 'error'

export default function PlaybackPage() {
  const today = new Date().toISOString().split("T")[0]
  const [camId, setCamId] = useState("")
  const [dateFrom, setDateFrom] = useState(today)
  const [dateTo, setDateTo] = useState(today)
  const [playUrl, setPlayUrl] = useState<string | null>(null)
  const [selectedRec, setSelectedRec] = useState<any | null>(null)
  const [selectedHour, setSelectedHour] = useState<number | null>(null)
  const [playbackState, setPlaybackState] = useState<PlaybackState>('idle')
  const [statusMessage, setStatusMessage] = useState('Pilih rekaman untuk diputar')
  const [progressPct, setProgressPct] = useState(0)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const { data: cameras } = useQuery({ queryKey: ["cameras"], queryFn: camerasApi.list })
  const { data: recs } = useQuery({
    queryKey: ["recs", camId, dateFrom, dateTo],
    queryFn: () => recordingsApi.list({ camera_id: camId, date_from: dateFrom, date_to: dateTo }),
    enabled: !!camId,
  })

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  const filteredRecs = useMemo(() => (
    selectedHour !== null
      ? recs?.filter((r: any) => new Date(r.started_at).getHours() === selectedHour)
      : recs
  ), [recs, selectedHour])

  const formatSize = (mb: number) => mb >= 1024 ? `${(mb / 1024).toFixed(1)} GB` : `${mb?.toFixed(0)} MB`

  const handleDownload = (r: any) => {
    const url = recordingsApi.downloadUrl(r.id)
    const a = document.createElement('a')
    a.href = url
    a.download = ''
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }

  const startPolling = (recordingId: number, jobId: string) => {
    stopPolling()
    pollRef.current = setInterval(async () => {
      try {
        const status = await recordingsApi.playStatus(recordingId, jobId)
        setProgressPct(status.progress_pct ?? 0)

        if (status.status === 'done') {
          stopPolling()
          setPlaybackState('ready')
          setStatusMessage('Video siap diputar')
          setPlayUrl(recordingsApi.playUrl(recordingId))
        } else if (status.status === 'error') {
          stopPolling()
          setPlaybackState('error')
          setStatusMessage(status.error_msg || 'Gagal memproses video')
        } else {
          setPlaybackState('processing')
          setStatusMessage(`Memproses video, harap tunggu... ${status.progress_pct ?? 0}%`)
        }
      } catch {
        stopPolling()
        setPlaybackState('error')
        setStatusMessage('Gagal membaca status pemrosesan video')
      }
    }, 3000)
  }

  const handlePlay = async (r: any) => {
    stopPolling()
    setSelectedRec(r)
    setPlayUrl(null)
    setProgressPct(0)
    setPlaybackState('loading')
    setStatusMessage('Memeriksa file rekaman...')

    try {
      const result = await recordingsApi.preparePlayback(r.id)
      if (result.status === 'queued' || result.status === 'processing') {
        setPlaybackState('processing')
        setStatusMessage('Memproses video, harap tunggu...')
        startPolling(r.id, result.job_id)
        return
      }

      setPlaybackState('ready')
      setStatusMessage('Video siap diputar')
      setPlayUrl(recordingsApi.playUrl(r.id))
    } catch (err: any) {
      const status = err?.response?.status
      setPlaybackState('error')
      if (status === 404) setStatusMessage('File rekaman tidak ditemukan')
      else setStatusMessage(err?.response?.data?.detail ?? 'Gagal memutar rekaman')
    }
  }

  const retrySelected = () => {
    if (selectedRec) handlePlay(selectedRec)
  }

  return (
    <div className="flex h-full flex-col gap-2 p-2">
      <div className="flex flex-shrink-0 items-center gap-2 rounded bg-gray-800 px-3 py-2">
        <select value={camId} onChange={e => { setCamId(e.target.value); setPlayUrl(null); setSelectedRec(null); setPlaybackState('idle'); setStatusMessage('Pilih rekaman untuk diputar') }} className="rounded border border-gray-600 bg-gray-700 px-3 py-1.5 text-sm">
          <option value="">-- Pilih Kamera --</option>
          {cameras?.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} className="rounded border border-gray-600 bg-gray-700 px-3 py-1.5 text-sm" />
        <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} className="rounded border border-gray-600 bg-gray-700 px-3 py-1.5 text-sm" />
        {selectedHour !== null && (
          <button onClick={() => setSelectedHour(null)} className="rounded bg-gray-700 px-3 py-1.5 text-sm hover:bg-gray-600">
            ✕ Filter: {String(selectedHour).padStart(2,'0')}:00
          </button>
        )}
      </div>

      <div className="flex flex-1 gap-2 overflow-hidden">
        <div className="flex w-72 flex-col gap-1 overflow-hidden rounded bg-gray-800 p-2">
          <div className="mb-1 px-1 text-xs text-gray-400">
            {filteredRecs?.length || 0} rekaman
            {selectedHour !== null ? ` · jam ${String(selectedHour).padStart(2,'0')}:00` : ''}
          </div>
          <div className="flex-1 space-y-1 overflow-y-auto">
            {filteredRecs?.length === 0 && (
              <div className="py-4 text-center text-xs text-gray-500">Tidak ada rekaman</div>
            )}
            {filteredRecs?.map((r: any) => (
              <div key={r.id} className={`rounded border text-xs ${selectedRec?.id === r.id ? 'border-blue-500 bg-blue-900/30' : 'border-transparent bg-gray-700 hover:bg-gray-600'}`}>
                <button onClick={() => handlePlay(r)} className="w-full p-2 text-left">
                  <div className="font-medium text-white">
                    {new Date(r.started_at).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    {r.is_protected && <span className="ml-1 text-yellow-400">🔒</span>}
                  </div>
                  <div className="mt-0.5 text-gray-400">{r.codec ?? 'mp4'} · {formatSize(r.file_size_mb ?? 0)}</div>
                </button>
                <div className="flex border-t border-gray-600">
                  <button onClick={() => handlePlay(r)} className="flex-1 rounded-bl py-1 text-center text-xs text-gray-400 hover:bg-gray-600 hover:text-white">▶ Putar</button>
                  <button onClick={() => handleDownload(r)} className="flex-1 rounded-br border-l border-gray-600 py-1 text-center text-xs text-blue-400 hover:bg-gray-600 hover:text-blue-200">⬇ Download</button>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="flex flex-1 flex-col gap-2 overflow-hidden">
          <div className="flex-1 overflow-hidden rounded bg-black">
            {playUrl && playbackState === 'ready' ? (
              <video key={playUrl} src={playUrl} controls autoPlay className="h-full w-full" />
            ) : (
              <div className="flex h-full flex-col items-center justify-center gap-3 px-6 text-center text-sm text-gray-400">
                <span className="text-3xl">🎬</span>
                <span>{statusMessage}</span>
                {playbackState === 'processing' && (
                  <div className="w-full max-w-sm">
                    <div className="h-2 rounded bg-gray-700">
                      <div className="h-2 rounded bg-blue-500 transition-all" style={{ width: `${progressPct}%` }} />
                    </div>
                  </div>
                )}
                {playbackState === 'error' && (
                  <button onClick={retrySelected} className="rounded bg-blue-600 px-4 py-2 text-xs text-white hover:bg-blue-700">
                    Coba Lagi
                  </button>
                )}
              </div>
            )}
          </div>

          {selectedRec && (
            <div className="flex flex-shrink-0 items-center gap-4 rounded bg-gray-800 px-3 py-2 text-xs text-gray-300">
              <span className="font-medium text-white">{new Date(selectedRec.started_at).toLocaleString('id-ID')}</span>
              <span>{selectedRec.codec ?? 'mp4'}</span>
              <span>{formatSize(selectedRec.file_size_mb ?? 0)}</span>
              {selectedRec.is_protected && <span className="text-yellow-400">🔒 Dilindungi</span>}
              <button onClick={() => handleDownload(selectedRec)} className="ml-auto rounded bg-blue-600 px-3 py-1 text-xs text-white hover:bg-blue-700">
                ⬇ Download
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
'@

Write-TextFile "frontend/src/App.tsx" @'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useAuthStore } from "@/store/auth"
import { ThemeProvider, useTheme } from "@/store/theme"
import { Sidebar } from "@/components/layout/Sidebar"
import LoginPage    from "@/pages/Login"
import LiveViewPage from "@/pages/LiveView"
import PlaybackPage from "@/pages/Playback"
import EventsPage   from "@/pages/Events"
import CamerasPage  from "@/pages/Cameras"
import StoragePage  from "@/pages/Storage"
import UsersPage    from "@/pages/Users"
import SettingsPage from "@/pages/Settings"
import SystemPage   from "@/pages/System"
import SetupPage    from "@/pages/Setup"
import ProfilePage  from "@/pages/Profile"

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 0,
      staleTime: 60_000,
      gcTime: 300_000,
      refetchOnWindowFocus: false,
    }
  }
})

function ProtectedLayout() {
  const { isAuthenticated } = useAuthStore()
  const { isDark } = useTheme()
  if (!isAuthenticated) return <Navigate to="/login" replace />

  return (
    <div style={{
      display: 'flex',
      width: '100vw',
      height: '100dvh',
      overflow: 'hidden',
      background: isDark ? '#0f1117' : '#f1f5f9',
    }}>
      <Sidebar />
      <main style={{
        flex: 1,
        height: '100%',
        overflow: 'hidden',
        minWidth: 0,
        display: 'flex',
        flexDirection: 'column',
        background: isDark ? '#0f1117' : '#f1f5f9',
      }}>
        <Routes>
          <Route path="/live"     element={<LiveViewPage />} />
          <Route path="/playback" element={<PlaybackPage />} />
          <Route path="/events"   element={<EventsPage />} />
          <Route path="/cameras"  element={<CamerasPage />} />
          <Route path="/storage"  element={<StoragePage />} />
          <Route path="/users"    element={<UsersPage />} />
          <Route path="/profile"  element={<ProfilePage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/system"   element={<SystemPage />} />
          <Route path="/setup"    element={<SetupPage />} />
          <Route path="*"         element={<Navigate to="/cameras" replace />} />
        </Routes>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/*"     element={<ProtectedLayout />} />
          </Routes>
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  )
}
'@

Write-TextFile "frontend/src/components/layout/Sidebar.tsx" @'
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
  { to:"/profile",  label:"Profile",     icon:"👤",  min:"viewer"   as UserRole },
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
      <div style={{ padding: '16px 20px', borderBottom: `1px solid ${border}`, flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 36, height: 36, background: '#0284c7', borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, flexShrink: 0, boxShadow: '0 1px 4px rgba(2,132,199,0.3)' }}>📹</div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: textHd, lineHeight: 1.2 }}>CamControl</div>
            <div style={{ fontSize: 11, color: sub, lineHeight: 1.2 }}>NVR System</div>
          </div>
          <button
            onClick={toggle}
            title={isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
            style={{ marginLeft: 'auto', width: 28, height: 28, borderRadius: 8, border: `1px solid ${border}`, background: hoverBg, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 15, flexShrink: 0 }}
          >
            {isDark ? '☀️' : '🌙'}
          </button>
        </div>
      </div>

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
          >
            <span style={{ fontSize: 15, width: 20, textAlign: 'center', flexShrink: 0 }}>{n.icon}</span>
            <span>{n.label}</span>
          </NavLink>
        ))}
      </nav>

      <div style={{ padding: '16px', borderTop: `1px solid ${border}`, background: footerBg, flexShrink: 0, transition: 'background 0.2s' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
          <div style={{ width: 32, height: 32, background: isDark ? '#1e3a5f' : '#e0f2fe', border: `1px solid ${isDark ? '#2a5080' : '#bae6fd'}`, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 700, color: '#0369a1', flexShrink: 0, textTransform: 'uppercase' }}>
            {user?.username?.[0] ?? '?'}
          </div>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: textHd, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{user?.username}</div>
            <div style={{ fontSize: 11, color: sub, textTransform: 'capitalize' }}>{user?.role}</div>
          </div>
        </div>
        <button
          onClick={clearAuth}
          style={{ width: '100%', textAlign: 'left', padding: '8px 12px', borderRadius: 8, fontSize: 13, color: '#ef4444', background: 'transparent', border: 'none', cursor: 'pointer', fontWeight: 500 }}
        >
          🚪 Logout
        </button>
      </div>
    </aside>
  )
}
'@

Write-Host "Frontend Sesi #017 patch applied."
Write-Host "Next:"
Write-Host "  1) powershell -ExecutionPolicy Bypass -File .\\scripts\\apply_frontend_s017.ps1"
Write-Host "  2) cd frontend"
Write-Host "  3) npm run build"
