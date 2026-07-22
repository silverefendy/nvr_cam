import { useEffect } from 'react'
import { VideoPlayer } from './VideoPlayer'

interface Props {
  cameraId: string
  cameraName?: string
  onClose: () => void
}

// C-05: Fullscreen overlay modal
export const FullscreenPlayer: React.FC<Props> = ({ cameraId, cameraName, onClose }) => {
  // ESC key closes fullscreen
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div
      className="fixed inset-0 z-50 bg-black flex flex-col"
      onClick={onClose}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-2 bg-gray-900/80 flex-shrink-0"
        onClick={(e) => e.stopPropagation()}
      >
        <span className="text-white font-medium">{cameraName || cameraId}</span>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-white text-sm px-3 py-1 rounded hover:bg-gray-700"
        >
          ✕ Tutup (ESC)
        </button>
      </div>

      {/* Video full area */}
      <div
        className="flex-1 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <VideoPlayer
          cameraId={cameraId}
          cameraName={cameraName}
          className="w-full h-full"
          showControls
        />
      </div>
    </div>
  )
}
