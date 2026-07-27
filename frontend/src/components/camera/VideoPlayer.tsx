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

  useHLSPlayer(data?.hls_url ?? null, videoRef)

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

  // ─── Double-click fullscreen ──────────────────────────────────────────────
  // Pisah dari drag handler di CameraGrid agar tidak ter-intercept.
  // Gunakan useRef untuk track click timing supaya tidak konflik dengan
  // single-click (onClick prop). dblclick event native lebih reliable
  // daripada track manual dengan setTimeout di sini.
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
            style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
            muted
            autoPlay
            playsInline
          />

          {/* Bottom bar */}
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
              }}
            >
              <button onClick={toggleStream} title="Toggle stream quality" style={btnStyle}>
                {streamType === 'main' ? 'MAIN' : 'SUB'}
              </button>
              <div style={{ display: 'flex', gap: 4 }}>
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
