import React from 'react'
import { useCameraStore, GridSize } from '@/store/cameras'
import { VideoPlayer } from './VideoPlayer'
import { FullscreenPlayer } from './FullscreenPlayer'

const COLS: Record<GridSize, string> = {
  '1x1': 'grid-cols-1',
  '2x2': 'grid-cols-2',
  '3x3': 'grid-cols-3',
  '4x4': 'grid-cols-4',
  '5x6': 'grid-cols-5',
}

export const CameraGrid: React.FC = () => {
  const { cameras, selectedCameras, gridSize, fullscreenCameraId, setFullscreen } = useCameraStore()

  // Map id -> name for label display
  const nameMap = Object.fromEntries(cameras.map(c => [c.id, c.name]))

  return (
    <>
      {/* C-05: Fullscreen overlay */}
      {fullscreenCameraId && (
        <FullscreenPlayer
          cameraId={fullscreenCameraId}
          cameraName={nameMap[fullscreenCameraId]}
          onClose={() => setFullscreen(null)}
        />
      )}

      <div className={`grid ${COLS[gridSize]} gap-1 h-full`}>
        {selectedCameras.map(id => (
          <VideoPlayer
            key={id}
            cameraId={id}
            cameraName={nameMap[id]}
            className="aspect-video"
            showControls
          />
        ))}
      </div>
    </>
  )
}
