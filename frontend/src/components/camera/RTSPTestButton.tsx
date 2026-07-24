import React, { useState } from 'react'
import { useMutation } from '@tanstack/react-query'

interface RTSPTestResult {
  success: boolean
  message: string
  codec?: string
  resolution?: string
  fps?: string
}

interface Props {
  rtspUrl: string
  onResult?: (result: RTSPTestResult) => void
  className?: string
}

export const RTSPTestButton: React.FC<Props> = ({ rtspUrl, onResult, className = '' }) => {
  const [result, setResult] = useState<RTSPTestResult | null>(null)

  const testMutation = useMutation({
    mutationFn: async (url: string) => {
      const token = localStorage.getItem('access_token')
      const response = await fetch('/api/v1/config/cameras/test-connection', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ rtsp_url: url, timeout_s: 10 }),
      })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      return response.json() as Promise<RTSPTestResult>
    },
    onSuccess: (data) => { setResult(data); onResult?.(data) },
    onError: (error) => {
      const r = { success: false, message: error instanceof Error ? error.message : 'Unknown error' }
      setResult(r); onResult?.(r)
    },
  })

  return (
    <div className={`flex flex-col gap-2 ${className}`}>
      <button
        onClick={() => { setResult(null); testMutation.mutate(rtspUrl) }}
        disabled={testMutation.isPending || !rtspUrl}
        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors
          bg-sky-600 hover:bg-sky-500 text-white disabled:opacity-40 disabled:cursor-not-allowed shadow-sm"
      >
        {testMutation.isPending ? (
          <>
            <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
            </svg>
            Mengetes...
          </>
        ) : '🔌 Test Koneksi'}
      </button>

      {result && (
        <div className={`rounded-xl px-4 py-3 text-sm border ${
          result.success
            ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
            : 'bg-red-50 border-red-200 text-red-600'
        }`}>
          {result.success ? (
            <div className="space-y-0.5">
              <div className="font-semibold">✅ Koneksi berhasil</div>
              {result.codec && <div className="text-xs opacity-75">Codec: {result.codec}</div>}
              {result.resolution && <div className="text-xs opacity-75">Resolusi: {result.resolution}</div>}
              {result.fps && <div className="text-xs opacity-75">FPS: {result.fps}</div>}
            </div>
          ) : (
            <div>
              <div className="font-semibold">❌ Koneksi gagal</div>
              <div className="text-xs opacity-75 mt-0.5">{result.message}</div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
