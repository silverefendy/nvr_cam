import { create } from 'zustand'
import type { Camera } from "@/types"

export type GridSize = '1x1'|'2x2'|'3x3'|'4x4'|'5x6'

interface CameraState {
  cameras: Camera[]
  selectedCameras: string[]
  gridSize: GridSize
  streamTypeOverride: Record<string, 'main'|'sub'> // per-camera stream override
  fullscreenCameraId: string | null
  setCameras: (c: Camera[]) => void
  setGridSize: (s: GridSize) => void
  toggleSelected: (id: string) => void
  selectAll: () => void
  selectNone: () => void
  updateStatus: (id: string, s: Camera['status']) => void
  setStreamType: (id: string, type: 'main'|'sub') => void
  setFullscreen: (id: string | null) => void
}

export const useCameraStore = create<CameraState>((set, get) => ({
  cameras: [],
  selectedCameras: [],
  gridSize: '2x2',
  streamTypeOverride: {},
  fullscreenCameraId: null,

  setCameras: (cameras) => set({
    cameras,
    selectedCameras: cameras.slice(0, 4).map(c => c.id)
  }),

  setGridSize: (gridSize) => set({ gridSize }),

  toggleSelected: (id) => set((s) => ({
    selectedCameras: s.selectedCameras.includes(id)
      ? s.selectedCameras.filter(c => c !== id)
      : [...s.selectedCameras, id]
  })),

  selectAll: () => set((s) => ({ selectedCameras: s.cameras.map(c => c.id) })),
  selectNone: () => set({ selectedCameras: [] }),

  updateStatus: (id, status) => set((s) => ({
    cameras: s.cameras.map(c => c.id === id ? { ...c, status } : c)
  })),

  setStreamType: (id, type) => set((s) => ({
    streamTypeOverride: { ...s.streamTypeOverride, [id]: type }
  })),

  setFullscreen: (id) => set({ fullscreenCameraId: id }),
}))
