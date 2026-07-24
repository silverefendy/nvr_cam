import { create } from 'zustand'
import type { Camera } from "@/types"

export type GridSize = '1x1'|'2x2'|'3x3'|'4x4'|'5x6'

// Jumlah kamera maksimal per ukuran grid
const GRID_CAPACITY: Record<GridSize, number> = {
  '1x1': 1,
  '2x2': 4,
  '3x3': 9,
  '4x4': 16,
  '5x6': 30,
}

interface CameraState {
  cameras: Camera[]
  selectedCameras: string[]   // urutan ini adalah urutan tampil di grid
  gridSize: GridSize
  streamTypeOverride: Record<string, 'main'|'sub'>
  fullscreenCameraId: string | null
  setCameras: (c: Camera[]) => void
  setGridSize: (s: GridSize) => void
  toggleSelected: (id: string) => void
  selectAll: () => void
  selectNone: () => void
  updateStatus: (id: string, s: Camera['status']) => void
  setStreamType: (id: string, type: 'main'|'sub') => void
  setFullscreen: (id: string | null) => void
  reorderCameras: (fromIndex: number, toIndex: number) => void  // drag-drop
}

export const useCameraStore = create<CameraState>((set) => ({
  cameras: [],
  selectedCameras: [],
  gridSize: '2x2',
  streamTypeOverride: {},
  fullscreenCameraId: null,

  setCameras: (cameras) => set((s) => {
    // Saat cameras di-load: pertahankan urutan yg sudah ada, tambah yg baru
    const existing = s.selectedCameras.filter(id => cameras.some(c => c.id === id))
    const newIds = cameras.map(c => c.id).filter(id => !existing.includes(id))
    const all = [...existing, ...newIds]
    const capacity = GRID_CAPACITY[s.gridSize]
    return {
      cameras,
      selectedCameras: all.slice(0, capacity),
    }
  }),

  // Saat grid size berubah: sesuaikan jumlah kamera yang ditampilkan
  setGridSize: (gridSize) => set((s) => {
    const capacity = GRID_CAPACITY[gridSize]
    const currentSelected = s.selectedCameras
    if (currentSelected.length <= capacity) {
      // Grid lebih besar: tambah kamera yang belum tampil
      const notShown = s.cameras.map(c => c.id).filter(id => !currentSelected.includes(id))
      const toAdd = notShown.slice(0, capacity - currentSelected.length)
      return { gridSize, selectedCameras: [...currentSelected, ...toAdd] }
    } else {
      // Grid lebih kecil: potong dari belakang
      return { gridSize, selectedCameras: currentSelected.slice(0, capacity) }
    }
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

  // Drag-drop: tukar posisi dua kamera di grid
  reorderCameras: (fromIndex, toIndex) => set((s) => {
    const arr = [...s.selectedCameras]
    const [moved] = arr.splice(fromIndex, 1)
    arr.splice(toIndex, 0, moved)
    return { selectedCameras: arr }
  }),
}))
