/**
 * StreamReadyPoller
 * Komponen wrapper yang polling endpoint /cameras/:id/stream-ready
 * sebelum menampilkan VideoPlayer.
 * Dipakai setelah add kamera baru agar tidak tampilkan layar hitam.
 */
import { useEffect, useState } from 'react'
import { apiClient } from '@/api/client'
import { VideoPlayer } from './VideoPlayer'

interface Props {
  cameraId: string
  cameraName?: string
  className?: string
  showControls?: boolean
  /** Timeout polling dalam ms. Default: 30000 (30 detik) */
  timeoutMs?: number
  /** Interval polling dalam ms. Default: 2000 (2 detik) */
  intervalMs?: number
}

type PollingState = 'waiting' | 'ready' | 'timeout' | 'error'

export const StreamReadyPoller: React.FC<Props> = ({
  cameraId,
  cameraName,
  className,
  showControls = true,
  timeoutMs = 30000,
  intervalMs = 2000,
}) => {
  const [state, setState] = useState<PollingState>('waiting')
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    let cancelled = false
    let timer: ReturnType<typeof setTimeout>
    const startTime = Date.now()

    const poll = async () => {
      if (cancelled) return
      try {
        const res = await apiClient.get(`/cameras/${cameraId}/stream-ready`)
        if (res.data?.ready) {
          if (!cancelled) setState('ready')
          return
        }
      } catch (e) {
        // abaikan error sementara
      }

      const now = Date.now()
      setElapsed(Math.floor((now - startTime) / 1000))

      if (now - startTime >= timeoutMs) {
        if (!cancelled) setState('timeout')
        return
      }

      timer = setTimeout(poll, intervalMs)
    }

    poll()
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [cameraId, timeoutMs, intervalMs])

  if (state === 'ready') {
    return (
      <VideoPlayer
        cameraId={cameraId}
        cameraName={cameraName}
        className={className}
        showControls={showControls}
      />
    )
  }

  const containerStyle: React.CSSProperties = {
    position: 'relative', width: '100%', height: '100%',
    background: '#000', display: 'flex', flexDirection: 'column',
    alignItems: 'center', justifyContent: 'center', gap: 8,
  }

  if (state === 'timeout') {
    return (
      <div style={containerStyle}>
        <span style={{ fontSize: 20 }}>📷</span>
        <span style={{ color: '#94a3b8', fontSize: 11 }}>{cameraName || cameraId}</span>
        <span style={{ color: '#f59e0b', fontSize: 10 }}>Stream belum siap — cek koneksi kamera</span>
        <button
          onClick={() => { setState('waiting'); setElapsed(0) }}
          style={{ marginTop: 4, fontSize: 10, padding: '3px 10px', borderRadius: 5,
            background: '#1e293b', color: '#94a3b8', border: '1px solid #334155', cursor: 'pointer' }}
        >
          Coba Lagi
        </button>
      </div>
    )
  }

  return (
    <div style={containerStyle}>
      <div style={{
        width: 28, height: 28, border: '2px solid #334155',
        borderTopColor: '#38bdf8', borderRadius: '50%',
        animation: 'spin 1s linear infinite',
      }} />
      <span style={{ color: '#64748b', fontSize: 10 }}>Menghubungkan ke kamera...</span>
      <span style={{ color: '#475569', fontSize: 9 }}>{elapsed}s / {timeoutMs / 1000}s</span>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}
