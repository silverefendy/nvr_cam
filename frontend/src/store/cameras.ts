import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Camera } from "@/types"

export type GridSize = '1x1'|'2x2'|'3x3'|'4x4'|'5x6'|'custom'

const GRID_CAPACITY: Record<GridSize, number> = {
  '1x1': 1,
  '2x2': 4,
  '3x3': 9,
  '4x4': 16,
  '5x6': 30,
  'custom': 999,
}

interface CameraState {
  cameras: Camera[]
  selectedCameras: string[]
  gridSize: GridSize
  gridRows: number
  gridCols: number
  streamTypeOverride: Record<string, 'main'|'sub'>
  fullscreenCameraId: string | null
  setCameras: (c: Camera[]) => void
  setGridSize: (s: GridSize) => void
  setGridDimensions: (rows: number, cols: number) => void
  toggleSelected: (id: string) => void
  selectAll: () => void
  selectNone: () => void
  updateStatus: (id: string, s: Camera['status']) => void
  setStreamType: (id: string, type: 'main'|'sub') => void
  setFullscreen: (id: string | null) => void
  reorderCameras: (fromIndex: number, toIndex: number) => void
}

// FIX: Pakai persist middleware agar gridRows, gridCols, gridSize
// disimpan ke localStorage dan tidak reset saat halaman di-refresh.
// cameras & fullscreenCameraId sengaja tidak di-persist (data live).
export const useCameraStore = create<CameraState>()(
  persist(
    (set) => ({
      cameras: [],
      selectedCameras: [],
      gridSize: '2x2',
      gridRows: 2,
      gridCols: 2,
      streamTypeOverride: {},
      fullscreenCameraId: null,

      setCameras: (cameras) => set((s) => {
        const existing = s.selectedCameras.filter(id => cameras.some(c => c.id === id))
        const newIds = cameras.map(c => c.id).filter(id => !existing.includes(id))
        const all = [...existing, ...newIds]
        const capacity = s.gridSize === 'custom'
          ? s.gridRows * s.gridCols
          : GRID_CAPACITY[s.gridSize]
        return { cameras, selectedCameras: all.slice(0, capacity) }
      }),

      setGridSize: (gridSize) => set((s) => {
        if (gridSize === 'custom') return { gridSize }
        const [r, c] = gridSize.split('x').map(Number)
        const rows = r, cols = c
        const capacity = rows * cols
        const currentSelected = s.selectedCameras
        if (currentSelected.length <= capacity) {
          const notShown = s.cameras.map(c => c.id).filter(id => !currentSelected.includes(id))
          const toAdd = notShown.slice(0, capacity - currentSelected.length)
          return { gridSize, gridRows: rows, gridCols: cols, selectedCameras: [...currentSelected, ...toAdd] }
        } else {
          return { gridSize, gridRows: rows, gridCols: cols, selectedCameras: currentSelected.slice(0, capacity) }
        }
      }),

      setGridDimensions: (rows, cols) => set((s) => {
        const capacity = rows * cols
        const currentSelected = s.selectedCameras
        let newSelected = currentSelected
        if (currentSelected.length < capacity) {
          const notShown = s.cameras.map(c => c.id).filter(id => !currentSelected.includes(id))
          const toAdd = notShown.slice(0, capacity - currentSelected.length)
          newSelected = [...currentSelected, ...toAdd]
        } else {
          newSelected = currentSelected.slice(0, capacity)
        }
        return { gridRows: rows, gridCols: cols, gridSize: 'custom', selectedCameras: newSelected }
      }),

      toggleSelected: (id) => set((s) => ({
        selectedCameras: s.selectedCameras.includes(id)
          ? s.selectedCameras.filter(c => c !== id)
          : [...s.selectedCameras, id],
      })),

      selectAll: () => set((s) => ({ selectedCameras: s.cameras.map(c => c.id) })),
      selectNone: () => set({ selectedCameras: [] }),

      updateStatus: (id, status) => set((s) => ({
        cameras: s.cameras.map(c => c.id === id ? { ...c, status } : c),
      })),

      setStreamType: (id, type) => set((s) => ({
        streamTypeOverride: { ...s.streamTypeOverride, [id]: type },
      })),

      setFullscreen: (id) => set({ fullscreenCameraId: id }),

      reorderCameras: (fromIndex, toIndex) => set((s) => {
        const arr = [...s.selectedCameras]
        const [moved] = arr.splice(fromIndex, 1)
        arr.splice(toIndex, 0, moved)
        return { selectedCameras: arr }
      }),
    }),
    {
      name: 'nvr-camera-store',  // key di localStorage
      // Hanya persist setting grid & stream override, bukan state live
      partialize: (s) => ({
        gridSize: s.gridSize,
        gridRows: s.gridRows,
        gridCols: s.gridCols,
        streamTypeOverride: s.streamTypeOverride,
        selectedCameras: s.selectedCameras,
      }),
    }
  )
)
