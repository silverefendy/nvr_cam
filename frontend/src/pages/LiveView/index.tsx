import { useQuery } from "@tanstack/react-query"
import { camerasApi } from "@/api/cameras"
import { useCameraStore, GridSize } from "@/store/cameras"
import { CameraGrid } from "@/components/camera/CameraGrid"
import { useEffect } from 'react'
const GRIDS: GridSize[] = ["1x1","2x2","3x3","4x4","5x6"]
export default function LiveViewPage() {
  const { gridSize, setGridSize, setCameras } = useCameraStore()
  const { data: cameras } = useQuery({ queryKey:["cameras"], queryFn: camerasApi.list })
  
  useEffect(() => {
    if (cameras) {
      setCameras(cameras)
    }
  }, [cameras, setCameras])
  
  const online = cameras?.filter((c: any) => c.status==="online").length ?? 0
  return (
    <div className="flex flex-col h-full p-2 gap-2">
      <div className="flex items-center gap-3 bg-gray-800 rounded px-3 py-2 flex-shrink-0">
        <span className="text-sm font-medium">Live View</span>
        <div className="flex gap-1 ml-auto">
          {GRIDS.map(g=><button key={g} onClick={()=>setGridSize(g)} className={`px-2 py-1 text-xs rounded ${gridSize===g?"bg-blue-600":"bg-gray-700 hover:bg-gray-600"}`}>{g}</button>)}
        </div>
        <span className="text-xs text-green-400 ml-2">{online} online</span>
      </div>
      <div className="flex-1 overflow-hidden"><CameraGrid /></div>
    </div>
  )
}