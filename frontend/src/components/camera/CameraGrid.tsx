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
  // Hitung berapa baris yang benar-benar terisi (minimal 1)
  const rows = Math.max(1, Math.ceil(selectedCameras.length / cols))
  // Total slot = baris × kolom (termasuk slot kosong untuk mengisi grid)
  const totalSlots = rows * cols

  return (
    <>
      {fullscreenCameraId && (
        <FullscreenPlayer
          cameraId={fullscreenCameraId}
          cameraName={nameMap[fullscreenCameraId]}
          onClose={() => setFullscreen(null)}
        />
      )}

      {/*
        KEY FIX: pakai gridTemplateRows dengan `repeat(N, 1fr)` agar setiap baris
        mengambil tinggi yang sama dan total grid mengisi container penuh.
        Tanpa ini, baris tidak punya tinggi dan semua kamera menumpuk di atas.
      */}
      <div
        style={{
          display: 'grid',
          width: '100%',
          height: '100%',
          gridTemplateColumns: `repeat(${cols}, 1fr)`,
          gridTemplateRows: `repeat(${rows}, 1fr)`,
          gap: '2px',
          background: '#000',
        }}
      >
        {/* Slot kamera yang ada */}
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
              overflow: 'hidden',
              minHeight: 0,   // penting agar flex/grid children tidak overflow
              minWidth: 0,
            }}
          >
            <VideoPlayer
              cameraId={id}
              cameraName={nameMap[id]}
              className="w-full h-full"
              showControls
            />
            {/* Drag indicator badge — muncul saat hover */}
            <div
              className="drag-handle"
              style={{
                position: 'absolute',
                top: 4,
                left: 4,
                opacity: 0,
                transition: 'opacity 0.15s',
                pointerEvents: 'none',
                background: 'rgba(0,0,0,0.6)',
                borderRadius: 3,
                padding: '1px 5px',
                color: '#fff',
                fontSize: 9,
                userSelect: 'none',
              }}
            >
              ⠿
            </div>
          </div>
        ))}

        {/* Slot kosong untuk mengisi sisa grid agar layout rapi */}
        {Array.from({ length: Math.max(0, totalSlots - selectedCameras.length) }).map((_, i) => (
          <div
            key={`empty-${i}`}
            style={{ background: '#0a0a0a', minHeight: 0, minWidth: 0 }}
          />
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
