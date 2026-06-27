import React from 'react'
import { useHLSPlayer } from "@/hooks/useHLSPlayer"
import { camerasApi } from "@/api/cameras"
import { useQuery } from "@tanstack/react-query"
interface Props { cameraId: string; className?: string; onClick?: () => void; label?: string }
export const VideoPlayer: React.FC<Props> = ({ cameraId, className, onClick, label }) => {
  const { data } = useQuery({ queryKey: ["live", cameraId], queryFn: () => camerasApi.liveUrl(cameraId), staleTime: Infinity })
  const videoRef = useHLSPlayer(data?.hls_url ?? null)
  return (
    <div className={`relative bg-black rounded overflow-hidden ${className}`} onClick={onClick}>
      <video ref={videoRef} className="w-full h-full object-cover" muted autoPlay playsInline />
      <div className="absolute bottom-0 left-0 right-0 bg-black/60 px-2 py-1 text-xs text-white flex justify-between">
        <span>{label || cameraId}</span>
        <span className="text-green-400">LIVE</span>
      </div>
    </div>
  )
}