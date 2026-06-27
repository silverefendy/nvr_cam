import { create } from 'zustand'
import type { Camera } from "@/types"
export type GridSize = '1x1'|'2x2'|'3x3'|'4x4'|'5x6'
interface CameraState { cameras:Camera[]; selectedCameras:string[]; gridSize:GridSize; setCameras:(c:Camera[])=>void; setGridSize:(s:GridSize)=>void; toggleSelected:(id:string)=>void; updateStatus:(id:string,s:Camera["status"])=>void }
export const useCameraStore = create<CameraState>((set) => ({
  cameras:[], selectedCameras:[], gridSize:'2x2',
  setCameras: (cameras) => set({ cameras, selectedCameras: cameras.slice(0,4).map(c=>c.id) }),
  setGridSize: (gridSize) => set({ gridSize }),
  toggleSelected: (id) => set((s) => ({ selectedCameras: s.selectedCameras.includes(id) ? s.selectedCameras.filter(c=>c!==id) : [...s.selectedCameras, id] })),
  updateStatus: (id, status) => set((s) => ({ cameras: s.cameras.map(c=>c.id===id?{...c,status}:c) })),
}))