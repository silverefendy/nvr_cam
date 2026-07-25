import React, { useRef, useState, useCallback, useEffect } from 'react'
import { useCameraStore } from '@/store/cameras'
import { VideoPlayer } from './VideoPlayer'

// Ukuran default window kamera (px)
const DEFAULT_W = 400
const DEFAULT_H = 225  // 16:9

interface WindowState {
  x: number
  y: number
  w: number
  h: number
  zIndex: number
  minimized: boolean
}

let zCounter = 10

/**
 * FloatingCameraLayout — setiap kamera tampil sebagai window floating.
 * Bisa di-drag (drag header), di-resize (drag sudut kanan-bawah),
 * dan di-minimize (klik tombol _). Ratio video dijaga oleh VideoPlayer
 * (object-fit: contain), tapi window bisa bebas di-resize.
 */
export const FloatingCameraLayout: React.FC = () => {
  const { cameras, selectedCameras } = useCameraStore()
  const nameMap = Object.fromEntries(cameras.map(c => [c.id, c.name]))

  // Inisialisasi posisi: tile grid 4 kolom supaya tidak tumpuk
  const initWindows = (): Record<string, WindowState> => {
    const result: Record<string, WindowState> = {}
    const cols = 4
    const gapX = 16
    const gapY = 16
    const startX = 12
    const startY = 12
    selectedCameras.forEach((id, i) => {
      const col = i % cols
      const row = Math.floor(i / cols)
      result[id] = {
        x: startX + col * (DEFAULT_W + gapX),
        y: startY + row * (DEFAULT_H + 40 + gapY),  // +40 untuk header
        w: DEFAULT_W,
        h: DEFAULT_H,
        zIndex: zCounter++,
        minimized: false,
      }
    })
    return result
  }

  const [windows, setWindows] = useState<Record<string, WindowState>>(initWindows)

  // Saat selectedCameras berubah: tambah window baru yang belum ada
  useEffect(() => {
    setWindows(prev => {
      const next = { ...prev }
      selectedCameras.forEach((id, i) => {
        if (!next[id]) {
          const col = i % 4
          const row = Math.floor(i / 4)
          next[id] = {
            x: 12 + col * (DEFAULT_W + 16),
            y: 12 + row * (DEFAULT_H + 56),
            w: DEFAULT_W,
            h: DEFAULT_H,
            zIndex: zCounter++,
            minimized: false,
          }
        }
      })
      return next
    })
  }, [selectedCameras])

  // Bawa window ke depan
  const bringToFront = useCallback((id: string) => {
    setWindows(prev => ({
      ...prev,
      [id]: { ...prev[id], zIndex: zCounter++ },
    }))
  }, [])

  // Toggle minimize
  const toggleMinimize = useCallback((e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    setWindows(prev => ({
      ...prev,
      [id]: { ...prev[id], minimized: !prev[id].minimized },
    }))
  }, [])

  // ─── DRAG (geser window) ───────────────────────────────────────
  const dragRef = useRef<{ id: string; startMouseX: number; startMouseY: number; startX: number; startY: number } | null>(null)

  const onHeaderMouseDown = useCallback((e: React.MouseEvent, id: string) => {
    if (e.button !== 0) return
    e.preventDefault()
    bringToFront(id)
    const win = windows[id]
    dragRef.current = { id, startMouseX: e.clientX, startMouseY: e.clientY, startX: win.x, startY: win.y }

    const onMove = (ev: MouseEvent) => {
      if (!dragRef.current) return
      const dx = ev.clientX - dragRef.current.startMouseX
      const dy = ev.clientY - dragRef.current.startMouseY
      setWindows(prev => ({
        ...prev,
        [id]: {
          ...prev[id],
          x: Math.max(0, dragRef.current!.startX + dx),
          y: Math.max(0, dragRef.current!.startY + dy),
        },
      }))
    }
    const onUp = () => {
      dragRef.current = null
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }, [windows, bringToFront])

  // ─── RESIZE (sudut kanan-bawah) ───────────────────────────────
  const resizeRef = useRef<{ id: string; startMouseX: number; startMouseY: number; startW: number; startH: number } | null>(null)

  const onResizeMouseDown = useCallback((e: React.MouseEvent, id: string) => {
    if (e.button !== 0) return
    e.preventDefault()
    e.stopPropagation()
    bringToFront(id)
    const win = windows[id]
    resizeRef.current = { id, startMouseX: e.clientX, startMouseY: e.clientY, startW: win.w, startH: win.h }

    const onMove = (ev: MouseEvent) => {
      if (!resizeRef.current) return
      const dx = ev.clientX - resizeRef.current.startMouseX
      const dy = ev.clientY - resizeRef.current.startMouseY
      setWindows(prev => ({
        ...prev,
        [id]: {
          ...prev[id],
          w: Math.max(200, resizeRef.current!.startW + dx),
          h: Math.max(120, resizeRef.current!.startH + dy),
        },
      }))
    }
    const onUp = () => {
      resizeRef.current = null
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }, [windows, bringToFront])

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        background: '#0a0c12',
        overflow: 'hidden',
      }}
    >
      {/* Hint kalau tidak ada kamera */}
      {selectedCameras.length === 0 && (
        <div style={{
          position: 'absolute', inset: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: '#4b5563', fontSize: 13,
        }}>
          Belum ada kamera dipilih. Gunakan Filter untuk memilih kamera.
        </div>
      )}

      {selectedCameras.map(id => {
        const win = windows[id]
        if (!win) return null
        const HEADER_H = 32

        return (
          <div
            key={id}
            onMouseDown={() => bringToFront(id)}
            style={{
              position: 'absolute',
              left: win.x,
              top: win.y,
              width: win.w,
              height: win.minimized ? HEADER_H : win.h + HEADER_H,
              zIndex: win.zIndex,
              display: 'flex',
              flexDirection: 'column',
              boxShadow: '0 4px 24px rgba(0,0,0,0.7)',
              border: '1px solid #2a2d3a',
              borderRadius: 6,
              overflow: 'hidden',
              userSelect: 'none',
              minWidth: 200,
            }}
          >
            {/* Header — area drag */}
            <div
              onMouseDown={(e) => onHeaderMouseDown(e, id)}
              style={{
                height: HEADER_H,
                background: '#1a1d27',
                borderBottom: '1px solid #2a2d3a',
                display: 'flex',
                alignItems: 'center',
                padding: '0 8px',
                gap: 6,
                cursor: 'move',
                flexShrink: 0,
              }}
            >
              {/* Dot status */}
              <span style={{
                width: 7, height: 7, borderRadius: '50%', flexShrink: 0,
                background: cameras.find(c => c.id === id)?.status === 'online' ? '#4ade80' : '#ef4444',
              }} />
              <span style={{
                flex: 1, color: '#cbd5e1', fontSize: 11, fontWeight: 600,
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}>
                {nameMap[id] || id}
              </span>
              {/* Tombol minimize */}
              <button
                onMouseDown={(e) => e.stopPropagation()}
                onClick={(e) => toggleMinimize(e, id)}
                title={win.minimized ? 'Restore' : 'Minimize'}
                style={{
                  background: 'transparent', border: 'none', cursor: 'pointer',
                  color: '#94a3b8', fontSize: 14, lineHeight: 1,
                  padding: '2px 4px', borderRadius: 3,
                  display: 'flex', alignItems: 'center',
                }}
              >
                {win.minimized ? '▢' : '─'}
              </button>
            </div>

            {/* Video area */}
            {!win.minimized && (
              <div style={{ flex: 1, position: 'relative', minHeight: 0, background: '#000' }}>
                <VideoPlayer
                  cameraId={id}
                  cameraName={nameMap[id]}
                  className="w-full h-full"
                  showControls
                />
              </div>
            )}

            {/* Resize handle — sudut kanan bawah */}
            {!win.minimized && (
              <div
                onMouseDown={(e) => onResizeMouseDown(e, id)}
                title="Drag untuk resize"
                style={{
                  position: 'absolute',
                  right: 0,
                  bottom: 0,
                  width: 16,
                  height: 16,
                  cursor: 'se-resize',
                  zIndex: 10,
                  display: 'flex',
                  alignItems: 'flex-end',
                  justifyContent: 'flex-end',
                  padding: '2px',
                }}
              >
                <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                  <path d="M2 10L10 2M6 10L10 6" stroke="#475569" strokeWidth="1.5" strokeLinecap="round"/>
                </svg>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
