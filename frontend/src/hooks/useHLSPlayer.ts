import { useEffect, RefObject } from 'react'
import Hls from 'hls.js'

// Updated signature: now accepts external ref so VideoPlayer controls the video element
export function useHLSPlayer(hlsUrl: string | null, videoRef: RefObject<HTMLVideoElement>) {
  useEffect(() => {
    if (!hlsUrl || !videoRef.current) return
    const video = videoRef.current

    if (Hls.isSupported()) {
      const hls = new Hls({
        enableWorker: true,
        lowLatencyMode: true,
        // Tambah retry config agar stream tidak mati saat segment terlambat
        fragLoadingMaxRetry: 6,
        manifestLoadingMaxRetry: 4,
      })
      hls.loadSource(hlsUrl)
      hls.attachMedia(video)
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        video.play().catch((err) => console.warn('[HLS] autoplay blocked:', err))
      })
      hls.on(Hls.Events.ERROR, (_, data) => {
        if (data.fatal) {
          console.error('[HLS] Fatal error:', data.type, data.details)
          if (data.type === Hls.ErrorTypes.NETWORK_ERROR) {
            // Coba resume load jika koneksi putus sementara
            hls.startLoad()
          } else if (data.type === Hls.ErrorTypes.MEDIA_ERROR) {
            // Coba recover media decode error (sering terjadi saat stream restart)
            hls.recoverMediaError()
          } else {
            hls.destroy()
          }
        }
      })
      return () => hls.destroy()
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
      // Safari — native HLS support tanpa hls.js
      video.src = hlsUrl
      video.play().catch(() => {})
    }
  // videoRef.current diikutkan agar effect re-run jika elemen video siap
  // setelah render pertama (mencegah race condition ref null saat mount)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hlsUrl, videoRef.current])
}
