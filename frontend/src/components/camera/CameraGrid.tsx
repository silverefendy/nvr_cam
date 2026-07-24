import React, { useRef, useState } from 'react'
import { useCameraStore, GridSize } from '@/store/cameras'
import { VideoPlayer } from './VideoPlayer'
import { FullscreenPlayer } from './FullscreenPlayer'

const COLS: Record<GridSize, number> = {
  '1x1': 1,
  '2x2': 2,
  '3x3': 3,
  '4x4': 4,
  '5x6': 5,
}

export const CameraGrid: React.FC = () => {
  const { cameras, selectedCameras, gridSize, fullscreenCameraId, setFullscreen, reorderCameras } = useCameraStore()
  const nameMap = Object.fromEntries(cameras.map(c => [c.id, c.name]))

  // Drag-drop state
  const dragIndexRef = useRef<number | null>(null)
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null)

  const handleDragStart = (index: number) => {
    dragIndexRef.current = index
  }

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault()
    setDragOverIndex(index)
  }

  const handleDrop = (e: React.DragEvent, toIndex: number) => {
    e.preventDefault()
    const fromIndex = dragIndexRef.current
    if (fromIndex !== null && fromIndex !== toIndex) {
      reorderCameras(fromIndex, toIndex)
    }
    dragIndexRef.current = null
    setDragOverIndex(null)
  }

  const handleDragEnd = () => {
    dragIndexRef.current = null
    setDragOverIndex(null)
  }

  const cols = COLS[gridSize]

  return (
    <>
      {fullscreenCameraId && (
        <FullscreenPlayer
          cameraId={fullscreenCameraId}
          cameraName={nameMap[fullscreenCameraId]}
          onClose={() => setFullscreen(null)}
        />
      )}

      <div
        className="w-full h-full bg-black"
        style={{
          display: 'grid',
          gridTemplateColumns: `repeat(${cols}, 1fr)`,
          gap: '2px',
        }}
      >
        {selectedCameras.map((id, index) => (
          <div
            key={id}
            draggable
            onDragStart={() => handleDragStart(index)}
            onDragOver={(e) => handleDragOver(e, index)}
            onDrop={(e) => handleDrop(e, index)}
            onDragEnd={handleDragEnd}
            style={{
              position: 'relative',
              outline: dragOverIndex === index ? '2px solid #38bdf8' : 'none',
              outlineOffset: '-2px',
              cursor: 'grab',
              minHeight: 0,
              overflow: 'hidden',
            }}
          >
            <VideoPlayer
              key={id}
              cameraId={id}
              cameraName={nameMap[id]}
              className="w-full h-full"
              showControls
            />
            {/* Drag indicator badge */}
            <div
              style={{
                position: 'absolute',
                top: 4,
                left: 4,
                opacity: 0,
                transition: 'opacity 0.15s',
                pointerEvents: 'none',
              }}
              className="drag-handle bg-black/60 rounded px-1 py-0.5 text-white text-[9px] select-none"
            >
              ⠿
            </div>
          </div>
        ))}

        {/* Slot kosong — isi sisa grid agar tampil rapi */}
        {Array.from({ length: Math.max(0, cols * Math.ceil(selectedCameras.length / cols) - selectedCameras.length) }).map((_, i) => (
          <div key={`empty-${i}`} style={{ background: '#111' }} />
        ))}
      </div>

      <style>{`
        [draggable="true"]:hover .drag-handle {
          opacity: 1 !important;
        }
        [draggable="true"] {
          user-select: none;
        }
      `}</style>
    </>
  )
}
