# =============================================================================
# fix_storage_tsx.ps1
# Jalankan dari root repo: cd C:\Users\Efendy\documents\git\nvr_cam
# .\fix_storage_tsx.ps1
#
# Fix: syncMutation dideklarasi tapi tombolnya tidak dipasang di JSX
# Solusi: tulis ulang Storage/index.tsx lengkap dengan tombol Sync di filter bar
# =============================================================================

Write-Host "=== FIX Storage/index.tsx ===" -ForegroundColor Cyan

$content = @'
import { useState, useEffect } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/api/client"
import { storageApi } from "@/api/storage"
import { recordingsApi } from "@/api/recordings"
import { camerasApi } from "@/api/cameras"
import { useAuthStore } from "@/store/auth"
import { useTheme } from "@/store/theme"
import type { DriveStatus, Recording } from "@/types"

type Tab = "drives" | "recordings" | "cameras" | "schedule"

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
  const [activeTab, setActiveTab]       = useState<Tab>("drives")
  const [schedHour, setSchedHour]       = useState(3)
  const [schedMinute, setSchedMinute]   = useState(0)
  const [schedEnabled, setSchedEnabled] = useState(false)
  const [message, setMessage]           = useState<{ type: "success" | "error"; text: string } | null>(null)
  const [recCameraId, setRecCameraId]   = useState<string>("")
  const [recDateFrom, setRecDateFrom]   = useState(monthAgoStr())
  const [recDateTo, setRecDateTo]       = useState(todayStr())
  const [playingId, setPlayingId]       = useState<number | null>(null)

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
  const { data: cameraStats, isLoading: statsLoading } = useQuery({
    queryKey: ["storage-camera-stats"], queryFn: storageApi.getStatsByCamera,
    enabled: isAuthenticated && activeTab === "cameras",
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
  // FIX: syncMutation sekarang dipakai di tombol "Sync dari Disk" di filter bar rekaman
  const syncMutation = useMutation({
    mutationFn: () => apiClient.post('/recordings/sync').then(r => r.data),
    onSuccess: (data: any) => {
      queryClient.invalidateQueries({ queryKey: ["recordings"] })
      showMsg("success", `Sync selesai: ${data.inserted} file baru, ${data.skipped} sudah ada`)
    },
    onError: () => showMsg("error", "Sync dari disk gagal"),
  })

  const getUsageColor = (p: number) => p < 10 ? '#ef4444' : p < 25 ? '#f59e0b' : '#10b981'
  const getUsedPct    = (d: DriveStatus) => Math.round((d.used_gb / d.total_gb) * 100)

  const tabs: { id: Tab; label: string; icon: string }[] = [
    { id: "drives",     label: "Drive",         icon: "💾" },
    { id: "recordings", label: "Rekaman",        icon: "🎞️" },
    { id: "cameras",    label: "Per Kamera",     icon: "📷" },
    { id: "schedule",   label: "Jadwal Cleanup", icon: "🕐" },
  ]

  const cardStyle: React.CSSProperties = {
    background: card, border: `1px solid ${cardB}`,
    borderRadius: 12, padding: '16px',
    boxShadow: isDark ? '0 2px 8px rgba(0,0,0,0.3)' : '0 1px 4px rgba(0,0,0,0.06)',
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: bg, padding: 16, gap: 12, overflow: 'hidden' }}>

      {/* Header */}
      <div style={{ ...cardStyle, padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
        <span style={{ fontSize: 16 }}>💾</span>
        <h1 style={{ fontSize: 15, fontWeight: 700, color: text, margin: 0 }}>Storage</h1>
        {storage && (
          <div style={{ display: 'flex', gap: 12, marginLeft: 8, flexWrap: 'wrap' }}>
            {[
              { label: 'Total',          value: `${storage.total_tb} TB`,                      color: text },
              { label: 'Dipakai',        value: `${storage.used_tb} TB`,                       color: '#f59e0b' },
              { label: 'Sisa',           value: `${storage.free_tb} TB`,                       color: storage.free_tb < 1 ? '#ef4444' : '#10b981' },
              { label: 'Estimasi habis', value: `~${storage.estimated_days_remaining} hari`,   color: sub },
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
            {message.type === 'success' ? '✓' : '✗'} {message.text}
          </span>
        )}
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
          {cleanupMutation.isPending ? 'Membersihkan...' : '🗑️ Cleanup'}
        </button>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
        {tabs.map(t => (
          <button key={t.id} onClick={() => setActiveTab(t.id)} style={{
            padding: '8px 16px', borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: 'pointer',
            border: `1px solid ${activeTab === t.id ? '#0284c7' : cardB}`,
            background: activeTab === t.id ? '#0284c7' : card,
            color: activeTab === t.id ? '#fff' : sub,
            transition: 'all 0.15s', display: 'flex', alignItems: 'center', gap: 6,
          }}>
            <span>{t.icon}</span> {t.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto' }}>

        {/* Tab: Drive */}
        {activeTab === 'drives' && (
          isLoading
            ? <div style={{ color: sub, padding: 40, textAlign: 'center' }}>Memuat data storage...</div>
            : !storage?.drives?.length
              ? <div style={{ color: sub, padding: 40, textAlign: 'center' }}>Tidak ada drive terkonfigurasi</div>
              : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {storage.drives.map((drive: DriveStatus) => {
                    const usedPct  = getUsedPct(drive)
                    const freePct  = drive.free_pct
                    const barColor = getUsageColor(freePct)
                    return (
                      <div key={drive.path} style={cardStyle}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                          <div>
                            <div style={{ fontSize: 14, fontWeight: 700, color: text, display: 'flex', alignItems: 'center', gap: 8 }}>
                              <span>💾</span> {drive.path}
                              {freePct < (storage.threshold_pct ?? 10) && (
                                <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 99, background: '#7f1d1d', color: '#fca5a5', fontWeight: 700 }}>⚠️ Kritis</span>
                              )}
                            </div>
                            <div style={{ fontSize: 11, color: sub, marginTop: 3 }}>
                              {drive.cameras?.length ?? 0} kamera terdaftar
                              {drive.cameras?.length > 0 && ` · ${drive.cameras.join(', ')}`}
                            </div>
                          </div>
                          <div style={{ textAlign: 'right' }}>
                            <div style={{ fontSize: 22, fontWeight: 800, color: barColor, lineHeight: 1 }}>{freePct.toFixed(1)}%</div>
                            <div style={{ fontSize: 11, color: sub }}>sisa tersedia</div>
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

            {/* Filter bar — tombol Sync ada di sini */}
            <div style={{ ...cardStyle, padding: '12px 16px', display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: sub }}>Filter:</span>
              <select
                value={recCameraId} onChange={e => setRecCameraId(e.target.value)}
                style={{ padding: '6px 10px', borderRadius: 7, fontSize: 12, border: `1px solid ${cardB}`, background: inputBg, color: text, cursor: 'pointer' }}
              >
                <option value="">Semua Kamera</option>
                {cameras?.map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ fontSize: 11, color: sub }}>Dari</span>
                <input type="date" value={recDateFrom} onChange={e => setRecDateFrom(e.target.value)}
                  style={{ padding: '6px 8px', borderRadius: 7, fontSize: 12, border: `1px solid ${cardB}`, background: inputBg, color: text }} />
                <span style={{ fontSize: 11, color: sub }}>s/d</span>
                <input type="date" value={recDateTo} onChange={e => setRecDateTo(e.target.value)}
                  style={{ padding: '6px 8px', borderRadius: 7, fontSize: 12, border: `1px solid ${cardB}`, background: inputBg, color: text }} />
              </div>

              {/* TOMBOL SYNC — ini yang sebelumnya tidak terpasang */}
              <button
                onClick={() => {
                  if (confirm('Scan semua file .mp4 di storage dan daftarkan ke database?\nProses ini mungkin butuh beberapa detik.'))
                    syncMutation.mutate()
                }}
                disabled={syncMutation.isPending}
                style={{
                  padding: '6px 14px', borderRadius: 7, fontSize: 12, fontWeight: 600,
                  background: syncMutation.isPending ? sub : '#7c3aed',
                  color: '#fff', border: 'none', cursor: syncMutation.isPending ? 'not-allowed' : 'pointer',
                  whiteSpace: 'nowrap',
                }}
              >
                {syncMutation.isPending ? '⏳ Scanning...' : '🔄 Sync dari Disk'}
              </button>

              <span style={{ fontSize: 11, color: sub, marginLeft: 'auto' }}>
                {recordings ? `${recordings.length} rekaman ditemukan` : ''}
              </span>
            </div>

            {/* Video player */}
            {playingId !== null && (() => {
              const rec = recordings?.find((r: Recording) => r.id === playingId)
              return rec ? (
                <div style={cardStyle}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: text }}>
                      🎞️ {rec.camera_id} · {formatDate(rec.started_at)}
                    </span>
                    <button onClick={() => setPlayingId(null)}
                      style={{ fontSize: 12, padding: '3px 10px', borderRadius: 6, border: `1px solid ${cardB}`, background: 'transparent', color: sub, cursor: 'pointer' }}>
                      ✕ Tutup
                    </button>
                  </div>
                  <video src={recordingsApi.playUrl(rec.id)} controls autoPlay
                    style={{ width: '100%', maxHeight: 400, background: '#000', borderRadius: 8 }} />
                </div>
              ) : null
            })()}

            {/* List rekaman */}
            {recLoading ? (
              <div style={{ color: sub, padding: 40, textAlign: 'center' }}>Memuat rekaman...</div>
            ) : !recordings?.length ? (
              <div style={{ ...cardStyle, padding: 40, textAlign: 'center', color: sub }}>
                <div style={{ fontSize: 32, marginBottom: 8 }}>🎞️</div>
                <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>Tidak ada rekaman ditemukan</div>
                <div style={{ fontSize: 12, marginBottom: 12 }}>Coba ubah filter kamera atau rentang tanggal</div>
                <div style={{ fontSize: 12, color: '#7c3aed' }}>
                  💡 Jika file .mp4 sudah ada di disk, klik tombol <strong>🔄 Sync dari Disk</strong> di atas untuk mendaftarkannya ke database
                </div>
              </div>
            ) : (
              <div style={{ ...cardStyle, padding: 0, overflow: 'hidden' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr style={{ background: isDark ? '#12151f' : '#f8fafc', borderBottom: `1px solid ${cardB}` }}>
                      {['Kamera', 'Mulai', 'Durasi', 'Ukuran', 'Codec', 'Path File', 'Aksi'].map(h => (
                        <th key={h} style={{ padding: '10px 14px', textAlign: 'left', fontSize: 11, fontWeight: 700, color: sub, letterSpacing: '0.04em' }}>{h}</th>
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
                          {rec.is_protected && <span style={{ marginLeft: 6, fontSize: 9, padding: '1px 5px', borderRadius: 99, background: isDark ? '#1e3a5f' : '#dbeafe', color: '#3b82f6' }}>🔒</span>}
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
                          {rec.file_path
                            ? <span title={rec.file_path} style={{ fontSize: 11, color: sub, fontFamily: 'monospace', display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{rec.file_path}</span>
                            : <span style={{ fontSize: 11, color: sub }}>-</span>}
                        </td>
                        <td style={{ padding: '10px 14px' }}>
                          <div style={{ display: 'flex', gap: 6 }} onClick={e => e.stopPropagation()}>
                            <button onClick={() => setPlayingId(rec.id === playingId ? null : rec.id)}
                              style={{ ...smallBtn, background: isDark ? '#1a2a3a' : '#dbeafe', color: '#3b82f6' }}>▶ Putar</button>
                            <a href={recordingsApi.downloadUrl(rec.id)} download
                              style={{ ...smallBtn, background: isDark ? '#1a2a1a' : '#dcfce7', color: '#10b981', textDecoration: 'none' }}>⬇ Unduh</a>
                            <button onClick={() => protectMutation.mutate(rec.id)}
                              style={{ ...smallBtn, background: isDark ? '#1a1a2a' : '#ede9fe', color: '#8b5cf6' }}>
                              {rec.is_protected ? '🔓' : '🔒'}
                            </button>
                            {!rec.is_protected && (
                              <button onClick={() => { if (confirm(`Hapus rekaman ${rec.camera_id}?`)) deleteMutation.mutate(rec.id) }}
                                style={{ ...smallBtn, background: isDark ? '#2d0a0a' : '#fee2e2', color: '#ef4444' }}>🗑️</button>
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

        {/* Tab: Per Kamera */}
        {activeTab === 'cameras' && (
          statsLoading
            ? <div style={{ color: sub, padding: 40, textAlign: 'center' }}>Memuat statistik...</div>
            : !cameraStats?.length
              ? <div style={{ color: sub, padding: 40, textAlign: 'center' }}>Tidak ada data kamera</div>
              : (
                <div style={{ ...cardStyle, padding: 0, overflow: 'hidden' }}>
                  <div style={{ padding: '10px 16px', borderBottom: `1px solid ${cardB}`, fontSize: 11, color: sub }}>
                    {cameraStats.length} kamera · diurutkan dari penggunaan terbesar
                  </div>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                    <thead>
                      <tr style={{ background: isDark ? '#12151f' : '#f8fafc', borderBottom: `1px solid ${cardB}` }}>
                        {['#', 'Kamera', 'Drive', 'File', 'Total'].map(h => (
                          <th key={h} style={{ padding: '10px 14px', textAlign: h === 'File' || h === 'Total' ? 'right' : 'left', fontSize: 11, fontWeight: 700, color: sub }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {cameraStats.map((s: any, i: number) => (
                        <tr key={s.camera_id} style={{ borderBottom: `1px solid ${isDark ? '#1e2130' : '#f1f5f9'}` }}
                          onMouseEnter={e => (e.currentTarget.style.background = rowHov)}
                          onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                        >
                          <td style={{ padding: '10px 14px', color: sub, fontSize: 11 }}>{i + 1}</td>
                          <td style={{ padding: '10px 14px', fontWeight: 600, color: text }}>{s.camera_id}</td>
                          <td style={{ padding: '10px 14px', color: sub, fontSize: 12 }}>{s.drive}</td>
                          <td style={{ padding: '10px 14px', textAlign: 'right', color: sub }}>{s.file_count.toLocaleString()}</td>
                          <td style={{ padding: '10px 14px', textAlign: 'right', fontWeight: 700, color: i < 3 ? '#f59e0b' : text }}>{formatMB(s.total_mb)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )
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
              <p style={{ fontSize: 11, color: sub, marginTop: 6 }}>💡 Disarankan jam 03:00 saat traffic rendah</p>
            </div>
            <button
              onClick={() => scheduleMutation.mutate({ enabled: schedEnabled, hour: schedHour, minute: schedMinute })}
              disabled={scheduleMutation.isPending}
              style={{ padding: '10px 20px', borderRadius: 8, fontSize: 13, fontWeight: 700, background: '#0284c7', color: '#fff', border: 'none', cursor: 'pointer', opacity: scheduleMutation.isPending ? 0.6 : 1 }}
            >
              {scheduleMutation.isPending ? 'Menyimpan...' : '💾 Simpan Jadwal'}
            </button>
            {schedule && (
              <div style={{ marginTop: 16, padding: 12, background: isDark ? '#12151f' : '#f8fafc', borderRadius: 8, border: `1px solid ${cardB}`, fontSize: 12, color: sub }}>
                <div>Status: <span style={{ color: schedule.enabled ? '#10b981' : sub, fontWeight: 700 }}>{schedule.enabled ? 'Aktif' : 'Nonaktif'}</span></div>
                <div style={{ marginTop: 4 }}>Cron: <code style={{ background: isDark ? '#1a1d27' : '#e2e8f0', padding: '1px 6px', borderRadius: 4, color: text }}>{schedule.cron}</code></div>
                <div style={{ marginTop: 6, color: '#f59e0b' }}>⚠️ Berlaku setelah backend di-restart</div>
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

Set-Content -Path "frontend\src\pages\Storage\index.tsx" -Value $content -Encoding UTF8
Write-Host "OK: Storage/index.tsx ditulis ulang" -ForegroundColor Green

Write-Host "`nLangkah selanjutnya:" -ForegroundColor Yellow
Write-Host "  git add frontend/src/pages/Storage/index.tsx" -ForegroundColor DarkYellow
Write-Host "  git commit -m 'fix: Storage tsx - pasang tombol Sync dari Disk ke JSX'" -ForegroundColor DarkYellow
Write-Host "  git push" -ForegroundColor DarkYellow
Write-Host "  docker compose up -d --build frontend" -ForegroundColor DarkYellow
