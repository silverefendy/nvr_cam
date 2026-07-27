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

Write-Host "Applying frontend patch for Session #018 (ONVIF PTZ + Footage Export)..."

# 1. Update cameras.ts API with PTZ methods
Write-TextFile "frontend/src/api/cameras.ts" @'
import { apiClient } from './client'
import type { Camera } from '@/types'

export const camerasApi = {
  list:     ()                               => apiClient.get<Camera[]>('/cameras').then(r => r.data),
  get:      (id: string)                     => apiClient.get<Camera>(`/cameras/${id}`).then(r => r.data),
  create:   (data: Partial<Camera>)          => apiClient.post<Camera>('/cameras', data).then(r => r.data),
  update:   (id: string, d: Partial<Camera>) => apiClient.put<Camera>(`/cameras/${id}`, d).then(r => r.data),
  delete:   (id: string)                     => apiClient.delete(`/cameras/${id}`),
  snapshot: (id: string)                     => apiClient.get(`/cameras/${id}/snapshot`).then(r => r.data),
  testConn: (id: string)                     => apiClient.post(`/cameras/${id}/test`).then(r => r.data),

  // C-11: stream type param — 'main' atau 'sub'
  liveUrl:  (id: string, stream: 'main'|'sub' = 'sub') =>
    apiClient.get(`/stream/${id}/live?stream=${stream}`).then(r => r.data),

  // ONVIF PTZ Controls
  ptzMove:  (id: string, direction: string, speed: number = 0.5) =>
    apiClient.post(`/cameras/${id}/ptz/move`, { direction, speed }),
  ptzStop:  (id: string) =>
    apiClient.post(`/cameras/${id}/ptz/stop`),
  ptzPresets: (id: string) =>
    apiClient.get(`/cameras/${id}/ptz/presets`).then(r => r.data),
  ptzSavePreset: (id: string, name: string) =>
    apiClient.post(`/cameras/${id}/ptz/presets`, { name }),
  ptzGotoPreset: (id: string, token: string) =>
    apiClient.post(`/cameras/${id}/ptz/presets/${token}/goto`),
}
'@

# 2. Update VideoPlayer.tsx to support floating PTZ Overlay Panel
Write-TextFile "frontend/src/components/camera/VideoPlayer.tsx" @'
import { useState, useRef, useCallback, useEffect } from 'react'
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
  const [showPTZPanel, setShowPTZPanel] = useState(false)
  const [presets, setPresets] = useState<{ token: string; name: string }[]>([])
  const [selectedPreset, setSelectedPreset] = useState("")
  const [newPresetName, setNewPresetName] = useState("")
  const videoRef = useRef<HTMLVideoElement>(null)

  const { streamTypeOverride, setStreamType, setFullscreen } = useCameraStore()
  const streamType = streamTypeOverride[cameraId] ?? 'sub'

  const { data, isLoading, error } = useQuery({
    queryKey: ['live', cameraId, streamType],
    queryFn: () => camerasApi.liveUrl(cameraId, streamType),
    staleTime: Infinity,
    refetchInterval: 30000,
  })

  // Query camera profile to check ptz_enabled flag
  const { data: cameraData } = useQuery({
    queryKey: ['camera', cameraId],
    queryFn: () => camerasApi.get(cameraId),
    staleTime: Infinity,
  })

  const ptzEnabled = cameraData?.config_json?.ptz_enabled ?? false

  useHLSPlayer(data?.hls_url ?? null, videoRef)

  // Fetch presets when PTZ panel is opened
  const loadPresets = useCallback(async () => {
    if (!ptzEnabled) return
    try {
      const res = await camerasApi.ptzPresets(cameraId)
      setPresets(res || [])
    } catch (err) {
      console.error("Failed to load PTZ presets:", err)
    }
  }, [cameraId, ptzEnabled])

  useEffect(() => {
    if (showPTZPanel) {
      loadPresets()
    }
  }, [showPTZPanel, loadPresets])

  const handlePTZMove = async (direction: string) => {
    try {
      await camerasApi.ptzMove(cameraId, direction, 0.5)
    } catch (err) {
      console.error(`Failed to move PTZ ${direction}:`, err)
    }
  }

  const handlePTZStop = async () => {
    try {
      await camerasApi.ptzStop(cameraId)
    } catch (err) {
      console.error("Failed to stop PTZ:", err)
    }
  }

  const handleGotoPreset = async () => {
    if (!selectedPreset) return
    try {
      await camerasApi.ptzGotoPreset(cameraId, selectedPreset)
    } catch (err) {
      console.error("Failed to go to preset:", err)
    }
  }

  const handleSavePreset = async () => {
    if (!newPresetName.trim()) return
    try {
      await camerasApi.ptzSavePreset(cameraId, newPresetName)
      setNewPresetName("")
      loadPresets()
    } catch (err) {
      console.error("Failed to save preset:", err)
    }
  }

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

  const handleDoubleClick = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setFullscreen(cameraId)
  }, [cameraId, setFullscreen])

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
    <div
      className={`group ${className ?? ''}`}
      style={containerStyle}
      onClick={onClick}
      onDoubleClick={handleDoubleClick}
    >
      {showSnapshotView && snapshotUrl ? (
        <div style={{ position: 'absolute', inset: 0, zIndex: 10 }}>
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
            style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
            muted
            autoPlay
            playsInline
          />

          {/* PTZ Panel Overlay */}
          {showPTZPanel && ptzEnabled && (
            <div
              onClick={(e) => e.stopPropagation()}
              style={{
                position: 'absolute',
                top: 40,
                right: 10,
                background: 'rgba(26,29,39,0.95)',
                border: '1px solid rgba(255,255,255,0.15)',
                borderRadius: 8,
                padding: 10,
                width: 140,
                color: '#fff',
                zIndex: 30,
                fontSize: 11,
                boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <span style={{ fontWeight: 'bold' }}>PTZ Controls</span>
                <button onClick={() => setShowPTZPanel(false)} style={{ border: 'none', background: 'transparent', color: '#94a3b8', cursor: 'pointer' }}>✕</button>
              </div>

              {/* D-Pad */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 4, justifyItems: 'center', marginBottom: 10 }}>
                <div />
                <button
                  onMouseDown={() => handlePTZMove("up")}
                  onMouseUp={handlePTZStop}
                  onTouchStart={() => handlePTZMove("up")}
                  onTouchEnd={handlePTZStop}
                  style={ptzBtnStyle}
                >▲</button>
                <div />
                <button
                  onMouseDown={() => handlePTZMove("left")}
                  onMouseUp={handlePTZStop}
                  onTouchStart={() => handlePTZMove("left")}
                  onTouchEnd={handlePTZStop}
                  style={ptzBtnStyle}
                >◀</button>
                <div style={{ width: 24, height: 24, background: 'rgba(255,255,255,0.1)', borderRadius: '50%' }} />
                <button
                  onMouseDown={() => handlePTZMove("right")}
                  onMouseUp={handlePTZStop}
                  onTouchStart={() => handlePTZMove("right")}
                  onTouchEnd={handlePTZStop}
                  style={ptzBtnStyle}
                >▶</button>
                <div />
                <button
                  onMouseDown={() => handlePTZMove("down")}
                  onMouseUp={handlePTZStop}
                  onTouchStart={() => handlePTZMove("down")}
                  onTouchEnd={handlePTZStop}
                  style={ptzBtnStyle}
                >▼</button>
                <div />
              </div>

              {/* Zoom */}
              <div style={{ display: 'flex', gap: 6, marginBottom: 10 }}>
                <button
                  onMouseDown={() => handlePTZMove("zoom_in")}
                  onMouseUp={handlePTZStop}
                  onTouchStart={() => handlePTZMove("zoom_in")}
                  onTouchEnd={handlePTZStop}
                  style={{ ...ptzBtnStyle, flex: 1 }}
                >Zoom +</button>
                <button
                  onMouseDown={() => handlePTZMove("zoom_out")}
                  onMouseUp={handlePTZStop}
                  onTouchStart={() => handlePTZMove("zoom_out")}
                  onTouchEnd={handlePTZStop}
                  style={{ ...ptzBtnStyle, flex: 1 }}
                >Zoom -</button>
              </div>

              {/* Presets */}
              <div style={{ borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: 6, marginBottom: 6 }}>
                <div style={{ marginBottom: 3, fontWeight: 'bold' }}>Presets</div>
                <select
                  value={selectedPreset}
                  onChange={(e) => setSelectedPreset(e.target.value)}
                  style={{ width: '100%', background: '#12151f', border: '1px solid rgba(255,255,255,0.2)', color: '#fff', fontSize: 10, padding: 2, borderRadius: 4, marginBottom: 4 }}
                >
                  <option value="">— Select —</option>
                  {presets.map(p => <option key={p.token} value={p.token}>{p.name}</option>)}
                </select>
                <button onClick={handleGotoPreset} style={{ width: '100%', background: '#0284c7', border: 'none', color: '#fff', padding: '3px 0', borderRadius: 4, fontSize: 10, cursor: 'pointer' }}>Go</button>
              </div>

              {/* Save Preset */}
              <div style={{ borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: 6 }}>
                <input
                  type="text"
                  placeholder="New Preset..."
                  value={newPresetName}
                  onChange={(e) => setNewPresetName(e.target.value)}
                  style={{ width: '100%', background: '#12151f', border: '1px solid rgba(255,255,255,0.2)', color: '#fff', fontSize: 9, padding: 3, borderRadius: 4, boxSizing: 'border-box', marginBottom: 4 }}
                />
                <button onClick={handleSavePreset} style={{ width: '100%', background: '#10b981', border: 'none', color: '#fff', padding: '3px 0', borderRadius: 4, fontSize: 10, cursor: 'pointer' }}>Save</button>
              </div>
            </div>
          )}

          {/* Bottom bar */}
          {showControls && (
            <div style={{
              position: 'absolute', bottom: 0, left: 0, right: 0,
              background: 'linear-gradient(to top, rgba(0,0,0,0.8) 0%, transparent 100%)',
              padding: '20px 8px 6px',
              display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end',
              pointerEvents: 'none',
              zIndex: 5,
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

          {/* Top hover controls */}
          {showControls && (
            <div
              className="opacity-0 group-hover:opacity-100 transition-opacity"
              style={{
                position: 'absolute', top: 0, left: 0, right: 0,
                background: 'linear-gradient(to bottom, rgba(0,0,0,0.7) 0%, transparent 100%)',
                padding: '6px 6px 16px',
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                gap: 4,
                zIndex: 20,
              }}
            >
              <button onClick={toggleStream} title="Toggle stream quality" style={btnStyle}>
                {streamType === 'main' ? 'MAIN' : 'SUB'}
              </button>
              <div style={{ display: 'flex', gap: 4 }}>
                {ptzEnabled && (
                  <button onClick={(e) => { e.stopPropagation(); setShowPTZPanel(!showPTZPanel) }} title="ONVIF PTZ Controls" style={{ ...btnStyle, background: showPTZPanel ? '#0284c7' : 'rgba(0,0,0,0.6)' }}>
                    🕹️ PTZ
                  </button>
                )}
                <button onClick={handleSnapshot} title="Snapshot" style={btnStyle}>📷</button>
                {pipSupported && <button onClick={handlePiP} title="Picture in Picture" style={btnStyle}>⧉</button>}
                <button onClick={handleFullscreen} title="Fullscreen (juga bisa double-click)" style={btnStyle}>⛶</button>
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

const ptzBtnStyle: React.CSSProperties = {
  width: 24,
  height: 24,
  background: 'rgba(0,0,0,0.8)',
  border: '1px solid rgba(255,255,255,0.2)',
  color: '#fff',
  borderRadius: 4,
  fontSize: 10,
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
}
'@

# 3. Update Playback/index.tsx to support exporting merged video clips with datetime range and status polling
Write-TextFile "frontend/src/pages/Playback/index.tsx" @'
import { useState, useEffect } from 'react'
import { useQuery, useMutation } from "@tanstack/react-query"
import { camerasApi } from "@/api/cameras"
import { recordingsApi } from "@/api/recordings"
import { apiClient } from "@/api/client"

export default function PlaybackPage() {
  const [camId, setCamId]               = useState("")
  const [date, setDate]                 = useState(new Date().toISOString().split("T")[0])
  const [playUrl, setPlayUrl]           = useState<string | null>(null)
  const [selectedRec, setSelectedRec]   = useState<any | null>(null)
  const [selectedHour, setSelectedHour] = useState<number | null>(null)

  // Export States
  const [showExportModal, setShowExportModal] = useState(false)
  const [exportStart, setExportStart]         = useState("")
  const [exportEnd, setExportEnd]             = useState("")
  const [exportJobId, setExportJobId]         = useState<string | null>(null)
  const [exportStatus, setExportStatus]       = useState<string | null>(null)
  const [exportDownloadUrl, setExportDownloadUrl] = useState<string | null>(null)
  const [exportError, setExportError]         = useState<string | null>(null)

  const { data: cameras } = useQuery({ queryKey: ["cameras"], queryFn: camerasApi.list })
  const { data: recs }    = useQuery({
    queryKey: ["recs", camId, date],
    queryFn:  () => recordingsApi.list({ camera_id: camId, date_from: date, date_to: date }),
    enabled:  !!camId,
  })

  const filteredRecs = selectedHour !== null
    ? recs?.filter((r: any) => new Date(r.started_at).getHours() === selectedHour)
    : recs

  const handlePlay = (r: any) => {
    setSelectedRec(r)
    setPlayUrl(recordingsApi.playUrl(r.id))
  }

  const handleDownload = (r: any) => {
    const url = recordingsApi.downloadUrl(r.id)
    const a   = document.createElement('a')
    a.href    = url
    a.download = ''
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }

  // Trigger export mutation
  const exportMutation = useMutation({
    mutationFn: (data: { camera_id: string; start_time: string; end_time: string }) =>
      apiClient.post('/recordings/export', data).then(r => r.data),
    onSuccess: (data) => {
      setExportJobId(data.job_id)
      setExportStatus("queued")
      setExportError(null)
      setExportDownloadUrl(null)
    },
    onError: (err: any) => {
      setExportError(err?.response?.data?.detail ?? "Gagal mengirimkan request export")
    }
  })

  // Poll export status
  useEffect(() => {
    if (!exportJobId || exportStatus === "done" || exportStatus === "failed") return

    const interval = setInterval(async () => {
      try {
        const res = await apiClient.get(`/recordings/export/${exportJobId}`)
        setExportStatus(res.data.status)
        if (res.data.status === "done") {
          setExportDownloadUrl(res.data.download_url)
          clearInterval(interval)
        } else if (res.data.status === "failed") {
          setExportError("Proses export di server gagal (FFmpeg error / file tidak valid)")
          clearInterval(interval)
        }
      } catch (err) {
        console.error("Error polling export status:", err)
      }
    }, 3000)

    return () => clearInterval(interval)
  }, [exportJobId, exportStatus])

  const handleOpenExport = () => {
    if (!camId) {
      alert("Silakan pilih kamera terlebih dahulu.")
      return
    }
    // Pre-fill with selected date
    setExportStart(`${date}T00:00`)
    setExportEnd(`${date}T23:59`)
    setShowExportModal(true)
    setExportJobId(null)
    setExportStatus(null)
    setExportDownloadUrl(null)
    setExportError(null)
  }

  const handleTriggerExport = () => {
    if (!exportStart || !exportEnd) {
      alert("Silakan tentukan waktu mulai dan selesai.")
      return
    }
    exportMutation.mutate({
      camera_id: camId,
      start_time: new Date(exportStart).toISOString(),
      end_time: new Date(exportEnd).toISOString(),
    })
  }

  const formatSize = (mb: number) =>
    mb >= 1024 ? `${(mb / 1024).toFixed(1)} GB` : `${mb?.toFixed(0)} MB`

  return (
    <div className="flex flex-col h-full gap-2 p-2 relative">
      {/* Toolbar */}
      <div className="flex items-center gap-2 bg-gray-800 rounded px-3 py-2 flex-shrink-0">
        <select
          value={camId}
          onChange={e => { setCamId(e.target.value); setPlayUrl(null); setSelectedRec(null) }}
          className="bg-gray-700 rounded px-3 py-1.5 border border-gray-600 text-sm text-white"
        >
          <option value="">-- Pilih Kamera --</option>
          {cameras?.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <input
          type="date"
          value={date}
          onChange={e => { setDate(e.target.value); setPlayUrl(null); setSelectedRec(null) }}
          className="bg-gray-700 rounded px-3 py-1.5 border border-gray-600 text-sm text-white"
        />
        {selectedHour !== null && (
          <button
            onClick={() => setSelectedHour(null)}
            className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded text-sm text-white"
          >
            ✕ Filter: {String(selectedHour).padStart(2,'0')}:00
          </button>
        )}

        {camId && (
          <button
            onClick={handleOpenExport}
            className="ml-auto px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded text-sm"
          >
            🎬 Export Video Gabungan
          </button>
        )}
      </div>

      <div className="flex-1 flex gap-2 overflow-hidden">
        {/* Daftar Rekaman */}
        <div className="w-64 flex flex-col gap-1 bg-gray-800 rounded p-2 overflow-hidden">
          <div className="text-xs text-gray-400 px-1 mb-1">
            {filteredRecs?.length || 0} rekaman
            {selectedHour !== null ? ` · jam ${String(selectedHour).padStart(2,'0')}:00` : ''}
          </div>
          <div className="flex-1 overflow-y-auto space-y-1">
            {filteredRecs?.length === 0 && (
              <div className="text-center text-gray-500 text-xs py-4">Tidak ada rekaman</div>
            )}
            {filteredRecs?.map((r: any) => (
              <div
                key={r.id}
                className={`rounded border text-xs ${
                  selectedRec?.id === r.id
                    ? 'border-blue-500 bg-blue-900/30'
                    : 'border-transparent bg-gray-700 hover:bg-gray-600'
                }`}
              >
                <button onClick={() => handlePlay(r)} className="w-full text-left p-2">
                  <div className="font-medium text-white">
                    {new Date(r.started_at).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    {r.is_protected && <span className="ml-1 text-yellow-400">🔒</span>}
                  </div>
                  <div className="text-gray-400 mt-0.5">
                    {r.codec ?? 'mp4'} · {formatSize(r.file_size_mb ?? 0)}
                  </div>
                </button>
                <div className="flex border-t border-gray-600">
                  <button
                    onClick={() => handlePlay(r)}
                    className="flex-1 py-1 text-center text-gray-400 hover:text-white hover:bg-gray-600 text-xs rounded-bl"
                  >
                    ▶ Putar
                  </button>
                  <button
                    onClick={() => handleDownload(r)}
                    className="flex-1 py-1 text-center text-blue-400 hover:text-blue-200 hover:bg-gray-600 text-xs rounded-br border-l border-gray-600"
                  >
                    ⬇ Download
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Video Player */}
        <div className="flex-1 flex flex-col gap-2 overflow-hidden">
          <div className="flex-1 bg-black rounded overflow-hidden">
            {playUrl ? (
              <video key={playUrl} src={playUrl} controls autoPlay className="w-full h-full" />
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-gray-500 text-sm gap-2">
                <span className="text-3xl">🎬</span>
                <span>Pilih rekaman untuk diputar</span>
              </div>
            )}
          </div>
          {selectedRec && (
            <div className="bg-gray-800 rounded px-3 py-2 flex items-center gap-4 text-xs text-gray-300 flex-shrink-0">
              <span className="font-medium text-white">
                {new Date(selectedRec.started_at).toLocaleString('id-ID')}
              </span>
              <span>{selectedRec.codec ?? 'mp4'}</span>
              <span>{formatSize(selectedRec.file_size_mb ?? 0)}</span>
              {selectedRec.is_protected && <span className="text-yellow-400">🔒 Dilindungi</span>}
              <button
                onClick={() => handleDownload(selectedRec)}
                className="ml-auto px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs"
              >
                ⬇ Download
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Export Modal */}
      {showExportModal && (
        <div className="absolute inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 border border-gray-700 rounded-xl p-5 w-full max-w-md text-white space-y-4 shadow-xl">
            <div className="flex justify-between items-center pb-2 border-b border-gray-700">
              <h3 className="font-bold text-sm">🎥 Export Video Gabungan</h3>
              <button onClick={() => setShowExportModal(false)} className="text-gray-400 hover:text-white text-lg">✕</button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-xs text-gray-400 mb-1">Mulai Tanggal & Jam</label>
                <input
                  type="datetime-local"
                  value={exportStart}
                  onChange={e => setExportStart(e.target.value)}
                  className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Selesai Tanggal & Jam</label>
                <input
                  type="datetime-local"
                  value={exportEnd}
                  onChange={e => setExportEnd(e.target.value)}
                  className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                />
              </div>
              <p className="text-[10px] text-gray-400">
                Sistem akan menggabungkan semua rekaman MP4 kamera ini dalam rentang waktu di atas secara mulus (seamless concat). Maksimal rentang 24 jam.
              </p>
            </div>

            {/* Status / Progress Indicator */}
            {exportStatus && (
              <div className="p-3 bg-gray-900 border border-gray-700 rounded-lg space-y-2">
                <div className="flex justify-between text-xs">
                  <span>Status Pekerjaan:</span>
                  <span className={`font-bold capitalize ${
                    exportStatus === "done" ? "text-green-400" :
                    exportStatus === "failed" ? "text-red-400" : "text-yellow-400"
                  }`}>{exportStatus}</span>
                </div>
                {exportStatus === "processing" && (
                  <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden relative">
                    <div className="absolute inset-0 bg-blue-500 animate-pulse" style={{ width: "50%" }} />
                  </div>
                )}
                {exportDownloadUrl && (
                  <a
                    href={exportDownloadUrl}
                    download
                    className="block text-center w-full bg-green-600 hover:bg-green-700 text-white font-bold text-xs py-2 rounded mt-1"
                  >
                    ⬇ Download Video MP4
                  </a>
                )}
              </div>
            )}

            {exportError && (
              <div className="p-3 bg-red-950/30 border border-red-900 rounded-lg text-xs text-red-300">
                {exportError}
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2 border-t border-gray-700">
              <button
                onClick={() => setShowExportModal(false)}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-sm font-semibold rounded-lg"
              >
                Batal
              </button>
              <button
                onClick={handleTriggerExport}
                disabled={exportMutation.isPending || (exportStatus !== null && exportStatus !== "done" && exportStatus !== "failed")}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-sm font-semibold rounded-lg disabled:opacity-50"
              >
                {exportMutation.isPending ? "Mengirim..." : "Mulai Export"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
'@

Write-Host "Frontend Sesi #018 patch generated successfully."
Write-Host "Please run:"
Write-Host "  powershell -ExecutionPolicy Bypass -File .\\scripts\\apply_frontend_s018.ps1"
Write-Host "to apply all frontend additions!"
