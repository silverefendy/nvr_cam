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

  // C-13: Browser Picture-in-Picture
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

  // C-05: Fullscreen
  const handleFullscreen = useCallback((e: React.MouseEvent) => {
    e.stopPropagation()
    setFullscreen(cameraId)
  }, [cameraId, setFullscreen])

  const toggleStream = (e: React.MouseEvent) => {
    e.stopPropagation()
    setStreamType(cameraId, streamType === 'main' ? 'sub' : 'main')
  }

  if (isLoading) {
    return (
      <div className={`relative bg-gray-900 rounded overflow-hidden flex items-center justify-center ${className}`}>
        <div className="text-gray-500 text-sm">Loading...</div>
      </div>
    )
  }

  if (error || !data?.hls_url) {
    return (
      <div className={`relative bg-gray-900 rounded overflow-hidden flex items-center justify-center ${className}`}>
        <div className="text-red-400 text-sm">Camera offline</div>
      </div>
    )
  }

  const pipSupported = typeof document !== 'undefined' && 'pictureInPictureEnabled' in document

  return (
    <div
      className={`relative bg-black rounded overflow-hidden group ${className}`}
      onClick={onClick}
    >
      {showSnapshotView && snapshotUrl ? (
        <div className="relative w-full h-full">
          <img src={snapshotUrl} alt="Snapshot" className="w-full h-full object-cover" />
          <button
            onClick={(e) => { e.stopPropagation(); setShowSnapshotView(false); setSnapshotUrl(null) }}
            className="absolute top-2 right-2 px-2 py-1 bg-black/70 hover:bg-black/90 rounded text-xs text-white"
          >
            âœ•
          </button>
        </div>
      ) : (
        <>
          <video
            ref={videoRef}
            className="w-full h-full object-cover"
            muted
            autoPlay
            playsInline
            onDoubleClick={handleFullscreen}
          />

          {/* Bottom bar â€” selalu tampil */}
          {showControls && (
            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent px-2 py-1.5 text-xs text-white flex justify-between items-center">
              <span className="truncate max-w-[60%]">{cameraName || cameraId}</span>
              <div className="flex items-center gap-1.5">
                <span className="text-green-400 font-medium">LIVE</span>
              </div>
            </div>
          )}

          {/* Hover overlay controls */}
          {showControls && (
            <div className="absolute top-0 left-0 right-0 flex justify-between items-center px-1.5 py-1 bg-gradient-to-b from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
              {/* Stream toggle */}
              <button
                onClick={toggleStream}
                title={streamType === 'main' ? 'Switch to Sub stream' : 'Switch to Main stream'}
                className="px-1.5 py-0.5 bg-black/60 hover:bg-blue-600 rounded text-[10px] text-white"
              >
                {streamType === 'main' ? 'MAIN' : 'SUB'}
              </button>

              <div className="flex items-center gap-1">
                {/* Snapshot */}
                <button
                  onClick={handleSnapshot}
                  title="Capture snapshot"
                  className="px-1.5 py-0.5 bg-black/60 hover:bg-gray-600 rounded text-[10px] text-white"
                >
                  ðŸ“·
                </button>

                {/* PiP â€” C-13 */}
                {pipSupported && (
                  <button
                    onClick={handlePiP}
                    title="Picture in Picture"
                    className="px-1.5 py-0.5 bg-black/60 hover:bg-purple-600 rounded text-[10px] text-white"
                  >
                    â§‰
                  </button>
                )}

                {/* Fullscreen â€” C-05 */}
                <button
                  onClick={handleFullscreen}
                  title="Fullscreen (or double-click video)"
                  className="px-1.5 py-0.5 bg-black/60 hover:bg-gray-600 rounded text-[10px] text-white"
                >
                  â›¶
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

