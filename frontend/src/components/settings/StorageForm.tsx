import { useState, useEffect } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { useTheme } from '@/store/theme'

interface DriveAssignment {
  drive: string
  cameras: string[]
}

interface DriveInfo {
  path: string
  total_gb: number
  used_gb: number
  free_gb: number
  free_pct: number
}

interface Props {
  onSave: (data: DriveAssignment[]) => void
}

const formatGB = (gb: number) =>
  gb >= 1000 ? `${(gb / 1024).toFixed(1)} TB` : `${gb.toFixed(0)} GB`

export const StorageForm: React.FC<Props> = ({ onSave }) => {
  const [assignments, setAssignments] = useState<DriveAssignment[]>([])
  const { isDark } = useTheme()

  const card  = isDark ? '#1e2130' : '#f8fafc'
  const cardB = isDark ? '#2a2d3a' : '#e2e8f0'
  const text  = isDark ? '#e2e8f0' : '#1e293b'
  const sub   = isDark ? '#64748b' : '#94a3b8'
  const inputBg = isDark ? '#12151f' : '#fff'

  // ── Config drive assignments ─────────────────────────────────────────────
  const { data: storageConfig, isLoading } = useQuery({
    queryKey: ['storage-config'],
    queryFn: async () => {
      try {
        const res = await apiClient.get('/config/storage')
        return res.data
      } catch {
        return { data: { drive_assignments: [] } }
      }
    },
    retry: false,
  })

  useEffect(() => {
    if (storageConfig?.data?.drive_assignments?.length) {
      setAssignments(storageConfig.data.drive_assignments)
    }
  }, [storageConfig])

  // ── Storage status (gunakan endpoint yang benar: /storage) ───────────────
  const { data: storageStatus } = useQuery({
    queryKey: ['storage-status-form'],
    queryFn: async () => {
      try {
        const res = await apiClient.get('/storage')
        return res.data
      } catch {
        return null
      }
    },
    retry: false,
  })

  const drives: DriveInfo[] = storageStatus?.drives ?? []
  const availableCameras: string[] = storageStatus?.available_cameras
    ?? drives.flatMap((d: any) => d.cameras ?? [])

  const updateMutation = useMutation({
    mutationFn: async (data: DriveAssignment[]) => {
      const res = await apiClient.put('/config/storage', { drive_assignments: data })
      return res.data
    },
    onSuccess: () => onSave(assignments),
  })

  const addCameraToDrive = (driveIndex: number, cameraId: string) => {
    setAssignments(prev => {
      const updated = [...prev]
      if (!updated[driveIndex].cameras.includes(cameraId)) {
        updated[driveIndex] = { ...updated[driveIndex], cameras: [...updated[driveIndex].cameras, cameraId] }
      }
      return updated
    })
  }

  const removeCameraFromDrive = (driveIndex: number, cameraId: string) => {
    setAssignments(prev => {
      const updated = [...prev]
      updated[driveIndex] = { ...updated[driveIndex], cameras: updated[driveIndex].cameras.filter(c => c !== cameraId) }
      return updated
    })
  }

  const getDriveInfo = (drivePath: string): DriveInfo | null =>
    drives.find((d: DriveInfo) => d.path === drivePath) ?? null

  if (isLoading) return (
    <div style={{ color: sub, padding: 40, textAlign: 'center' }}>Memuat konfigurasi storage...</div>
  )

  // Kalau tidak ada data konfigurasi, tampilkan info drive dari status
  if (assignments.length === 0) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div style={{
          background: isDark ? '#1a2a1a' : '#f0fdf4', border: `1px solid ${isDark ? '#1e3a2a' : '#bbf7d0'}`,
          borderRadius: 12, padding: 16, fontSize: 13, color: '#10b981',
        }}>
          ℹ️ Konfigurasi drive assignment belum tersedia di API. Drive storage terdeteksi otomatis dari sistem.
        </div>

        {/* Tampilkan drive yang terdeteksi */}
        {drives.map((drive: DriveInfo) => {
          const usedPct = Math.round((drive.used_gb / drive.total_gb) * 100)
          const barColor = drive.free_pct < 10 ? '#ef4444' : drive.free_pct < 25 ? '#f59e0b' : '#10b981'
          return (
            <div key={drive.path} style={{ background: card, border: `1px solid ${cardB}`, borderRadius: 12, padding: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: text }}>💾 {drive.path}</div>
                  <div style={{ fontSize: 11, color: sub, marginTop: 2 }}>
                    {formatGB(drive.total_gb)} total · {formatGB(drive.free_gb)} sisa
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 20, fontWeight: 800, color: barColor }}>{drive.free_pct?.toFixed(1)}%</div>
                  <div style={{ fontSize: 10, color: sub }}>sisa tersedia</div>
                </div>
              </div>
              <div style={{ height: 8, background: isDark ? '#12151f' : '#e2e8f0', borderRadius: 99, overflow: 'hidden' }}>
                <div style={{ width: `${usedPct}%`, height: '100%', background: barColor, borderRadius: 99, transition: 'width 0.5s' }} />
              </div>
            </div>
          )
        })}

        {drives.length === 0 && (
          <div style={{ color: sub, padding: 40, textAlign: 'center', fontSize: 13 }}>
            Tidak ada drive yang terdeteksi
          </div>
        )}
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {assignments.map((assignment, driveIndex) => {
        const driveInfo = getDriveInfo(assignment.drive)
        const usedPct = driveInfo ? Math.round((driveInfo.used_gb / driveInfo.total_gb) * 100) : 0
        const barColor = driveInfo && driveInfo.free_pct < 10 ? '#ef4444'
          : driveInfo && driveInfo.free_pct < 25 ? '#f59e0b' : '#10b981'

        return (
          <div key={assignment.drive} style={{ background: card, border: `1px solid ${cardB}`, borderRadius: 12, padding: 16 }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 12 }}>
              <div>
                <div style={{ fontSize: 14, fontWeight: 700, color: text }}>💾 {assignment.drive}</div>
                {driveInfo && (
                  <div style={{ fontSize: 11, color: sub, marginTop: 2 }}>
                    {formatGB(driveInfo.total_gb)} total · {driveInfo.free_pct?.toFixed(1)}% sisa
                  </div>
                )}
              </div>
              {driveInfo && (
                <div style={{ width: 120, marginTop: 4 }}>
                  <div style={{ height: 6, background: isDark ? '#12151f' : '#e2e8f0', borderRadius: 99, overflow: 'hidden' }}>
                    <div style={{ width: `${usedPct}%`, height: '100%', background: barColor, borderRadius: 99 }} />
                  </div>
                  <div style={{ fontSize: 10, color: sub, marginTop: 2, textAlign: 'right' }}>{usedPct}% dipakai</div>
                </div>
              )}
            </div>

            {/* Kamera yang sudah ter-assign */}
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: sub, marginBottom: 8 }}>
                Kamera ter-assign ({assignment.cameras.length})
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {assignment.cameras.map(cameraId => (
                  <div key={cameraId} style={{
                    display: 'flex', alignItems: 'center', gap: 6,
                    background: isDark ? '#1a2a3a' : '#dbeafe',
                    padding: '4px 10px', borderRadius: 99, fontSize: 12, color: '#3b82f6', fontWeight: 600,
                  }}>
                    <span>📷 {cameraId}</span>
                    <button
                      onClick={() => removeCameraFromDrive(driveIndex, cameraId)}
                      style={{ border: 'none', background: 'transparent', color: '#ef4444', cursor: 'pointer', fontWeight: 800, padding: 0, lineHeight: 1 }}
                    >×</button>
                  </div>
                ))}
                {assignment.cameras.length === 0 && (
                  <span style={{ fontSize: 12, color: sub, fontStyle: 'italic' }}>Belum ada kamera</span>
                )}
              </div>
            </div>

            {/* Tambah kamera */}
            <div>
              <div style={{ fontSize: 12, fontWeight: 600, color: sub, marginBottom: 6 }}>Tambah Kamera</div>
              <select
                value=""
                onChange={e => { if (e.target.value) { addCameraToDrive(driveIndex, e.target.value); e.target.value = '' } }}
                style={{ padding: '7px 12px', borderRadius: 8, border: `1px solid ${cardB}`, background: inputBg, color: text, fontSize: 12, cursor: 'pointer' }}
              >
                <option value="">Pilih kamera...</option>
                {availableCameras
                  .filter(c => !assignment.cameras.includes(c))
                  .map((cameraId: string) => (
                    <option key={cameraId} value={cameraId}>{cameraId}</option>
                  ))}
              </select>
            </div>
          </div>
        )
      })}

      {/* Tombol Save */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', paddingBottom: 8 }}>
        <button
          onClick={() => updateMutation.mutate(assignments)}
          disabled={updateMutation.isPending}
          style={{
            padding: '10px 24px', borderRadius: 8, fontSize: 13, fontWeight: 700,
            background: updateMutation.isPending ? sub : '#10b981',
            color: '#fff', border: 'none', cursor: 'pointer',
          }}
        >
          {updateMutation.isPending ? 'Menyimpan...' : '💾 Simpan Konfigurasi Storage'}
        </button>
      </div>

      {updateMutation.isError && (
        <div style={{ padding: 12, background: isDark ? '#2d0a0a' : '#fee2e2', borderRadius: 8, color: '#ef4444', fontSize: 12 }}>
          ✗ Gagal menyimpan. Cek apakah endpoint /config/storage tersedia di backend.
        </div>
      )}
    </div>
  )
}
