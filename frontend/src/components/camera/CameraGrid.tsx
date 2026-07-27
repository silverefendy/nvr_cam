import React, { useRef, useState } from 'react'
import { useCameraStore } from '@/store/cameras'
import { VideoPlayer } from './VideoPlayer'
import { FullscreenPlayer } from './FullscreenPlayer'
import { useNavigate } from 'react-router-dom'

export const CameraGrid: React.FC = () => {
  const {
    cameras, selectedCameras, gridRows, gridCols,
    fullscreenCameraId, setFullscreen, reorderCameras
  } = useCameraStore()
  const nameMap = Object.fromEntries(cameras.map(c => [c.id, c.name]))
  const navigate = useNavigate()

  const dragIndexRef = useRef<number | null>(null)
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null)

  // Track drag state untuk bedakan drag vs dblclick
  const isDraggingRef = useRef(false)

  const handleDragStart = (index: number) => {
    isDraggingRef.current = true
    dragIndexRef.current = index
  }

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault()
    setDragOverIndex(index)
  }

  const handleDrop = (e: React.DragEvent, toIndex: number) => {
    e.preventDefault()
    const fromIndex = dragIndexRef.current
    if (fromIndex !== null && fromIndex !== toIndex) reorderCameras(fromIndex, toIndex)
    dragIndexRef.current = null
    setDragOverIndex(null)
  }

  const handleDragEnd = () => {
    dragIndexRef.current = null
    setDragOverIndex(null)
    // Reset setelah delay kecil agar dblclick tidak terpicu saat drag selesai
    setTimeout(() => { isDraggingRef.current = false }, 50)
  }

  const totalSlots = gridRows * gridCols

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
        style={{
          position: 'absolute',
          inset: 0,
          display: 'grid',
          gridTemplateColumns: `repeat(${gridCols}, 1fr)`,
          gridTemplateRows: `repeat(${gridRows}, 1fr)`,
          gap: '2px',
          background: '#000',
          overflow: 'hidden',
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
              // Gunakan 'default' bukan 'grab' agar dblclick lebih mudah
              cursor: 'default',
              overflow: 'hidden',
              minHeight: 0,
              minWidth: 0,
            }}
          >
            <VideoPlayer
              cameraId={id}
              cameraName={nameMap[id]}
              className="w-full h-full"
              showControls
            />
            <div
              className="drag-handle"
              style={{
                position: 'absolute', top: 4, left: 4,
                opacity: 0, transition: 'opacity 0.15s',
                background: 'rgba(0,0,0,0.6)', borderRadius: 3,
                padding: '1px 5px', color: '#fff', fontSize: 9, userSelect: 'none',
                cursor: 'grab', pointerEvents: 'auto',
              }}
            >
              ⠿
            </div>
          </div>
        ))}

        {Array.from({ length: Math.max(0, totalSlots - selectedCameras.length) }).map((_, i) => (
          <div
            key={`empty-${i}`}
            onClick={() => navigate('/cameras')}
            title="Klik untuk tambah kamera"
            style={{
              background: '#0d1117',
              minHeight: 0, minWidth: 0,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
              cursor: 'pointer',
              border: '1px dashed #1e2a3a',
              transition: 'background 0.15s, border-color 0.15s',
            }}
            onMouseEnter={e => {
              (e.currentTarget as HTMLDivElement).style.background = '#111827'
              ;(e.currentTarget as HTMLDivElement).style.borderColor = '#2563eb'
            }}
            onMouseLeave={e => {
              (e.currentTarget as HTMLDivElement).style.background = '#0d1117'
              ;(e.currentTarget as HTMLDivElement).style.borderColor = '#1e2a3a'
            }}
          >
            <div style={{
              width: 36, height: 36, borderRadius: '50%',
              background: 'rgba(37,99,235,0.15)',
              border: '1px solid rgba(37,99,235,0.3)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 20, color: '#2563eb',
            }}>+</div>
            <span style={{ fontSize: 10, color: '#334155', fontWeight: 500 }}>Tambah Kamera</span>
          </div>
        ))}
      </div>

      <style>{`
        [draggable="true"]:hover .drag-handle { opacity: 1 !important; }
        [draggable="true"] { user-select: none; }
      `}</style>
    </>
  )
}
