import { useEffect, useRef } from 'react'
import Hls from 'hls.js'
export function useHLSPlayer(hlsUrl: string | null) {
  const videoRef = useRef<HTMLVideoElement>(null)
  useEffect(() => {
    if (!hlsUrl || !videoRef.current) return
    if (Hls.isSupported()) {
      const hls = new Hls({ enableWorker:true, lowLatencyMode:true })
      hls.loadSource(hlsUrl); hls.attachMedia(videoRef.current)
      hls.on(Hls.Events.MANIFEST_PARSED, () => videoRef.current?.play().catch(()=>{}))
      return () => hls.destroy()
    } else if (videoRef.current.canPlayType('application/vnd.apple.mpegurl')) {
      videoRef.current.src = hlsUrl
    }
  }, [hlsUrl])
  return videoRef
}