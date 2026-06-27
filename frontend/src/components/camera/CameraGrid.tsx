import React from 'react'
import { useCameraStore, GridSize } from "@/store/cameras"
import { VideoPlayer } from "./VideoPlayer"
const COLS: Record<GridSize,string> = { "1x1":"grid-cols-1", "2x2":"grid-cols-2", "3x3":"grid-cols-3", "4x4":"grid-cols-4", "5x6":"grid-cols-5" }
export const CameraGrid: React.FC = () => {
  const { selectedCameras, gridSize } = useCameraStore()
  return (
    <div className={`grid ${COLS[gridSize]} gap-1 h-full`}>
      {selectedCameras.map(id => <VideoPlayer key={id} cameraId={id} className="aspect-video" />)}
    </div>
  )
}