import { useEffect, useRef, useCallback } from 'react'
interface WSEvent { type: string; payload: unknown }
export function useWebSocket(onEvent: (e: WSEvent) => void) {
  const wsRef = useRef<WebSocket|null>(null)
  const timer = useRef<number>()
  const connect = useCallback(() => {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${location.host}/api/v1/system/ws/events`)
    wsRef.current = ws
    ws.onmessage = (e) => { try { onEvent(JSON.parse(e.data)) } catch {} }
    ws.onclose = () => { timer.current = window.setTimeout(connect, 3000) }
    ws.onerror = () => ws.close()
  }, [onEvent])
  useEffect(() => { connect(); return () => { clearTimeout(timer.current); wsRef.current?.close() } }, [connect])
}