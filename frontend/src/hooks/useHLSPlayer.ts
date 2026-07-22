import { useEffect, RefObject } from 'react'
import Hls from 'hls.js'

// Updated signature: now accepts external ref so VideoPlayer controls the video element
export function useHLSPlayer(hlsUrl: string | null, videoRef: RefObject<HTMLVideoElement>) {
  useEffect(() => {
    if (!hlsUrl || !videoRef.current) return
    const video = videoRef.current
    if (Hls.isSupported()) {
      const hls = new Hls({ enableWorker: true, lowLatencyMode: true })
      hls.loadSource(hlsUrl)
      hls.attachMedia(video)
      hls.on(Hls.Events.MANIFEST_PARSED, () => video.play().catch(() => {}))
      return () => hls.destroy()
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
      video.src = hlsUrl
    }
  }, [hlsUrl])
}
