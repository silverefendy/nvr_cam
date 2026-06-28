import React, { useState } from 'react'
import { useHLSPlayer } from "@/hooks/useHLSPlayer"
import { camerasApi } from "@/api/cameras"
import { useQuery } from "@tanstack/react-query"

interface Props {
  cameraId: string
  className?: string
  onClick?: () => void
  label?: string
  showSnapshot?: boolean
}

export const VideoPlayer: React.FC<Props> = ({ cameraId, className, onClick, label, showSnapshot = false }) => {
  const [showSnapshotView, setShowSnapshotView] = useState(false)
  const [snapshotUrl, setSnapshotUrl] = useState<string | null>(null)
  
  const { data, isLoading, error } = useQuery({
    queryKey: ["live", cameraId],
    queryFn: () => camerasApi.liveUrl(cameraId),
    staleTime: Infinity,
    refetchInterval: 30000
  })

  const videoRef = useHLSPlayer(data?.hls_url ?? null)

  const handleSnapshot = async (e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      const url = await camerasApi.getSnapshot(cameraId)
      setSnapshotUrl(url)
      setShowSnapshotView(true)
    } catch (err) {
      console.error("Failed to capture snapshot:", err)
    }
  }

  const handleCloseSnapshot = (e: React.MouseEvent) => {
    e.stopPropagation()
    setShowSnapshotView(false)
    setSnapshotUrl(null)
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

  return (
    <div className={`relative bg-black rounded overflow-hidden ${className}`} onClick={onClick}>
      {showSnapshotView && snapshotUrl ? (
        <div className="relative w-full h-full">
          <img src={snapshotUrl} alt="Snapshot" className="w-full h-full object-cover" />
          <button
            onClick={handleCloseSnapshot}
            className="absolute top-2 right-2 px-2 py-1 bg-black/70 hover:bg-black/90 rounded text-xs text-white"
          >
            Close
          </button>
        </div>
      ) : (
        <>
          <video ref={videoRef} className="w-full h-full object-cover" muted autoPlay playsInline />
          <div className="absolute bottom-0 left-0 right-0 bg-black/60 px-2 py-1 text-xs text-white flex justify-between items-center">
            <span>{label || cameraId}</span>
            <div className="flex items-center gap-2">
              <span className="text-green-400">LIVE</span>
              {showSnapshot && (
                <button
                  onClick={handleSnapshot}
                  className="px-2 py-0.5 bg-blue-600 hover:bg-blue-700 rounded text-xs"
                >
                  Snapshot
                </button>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}