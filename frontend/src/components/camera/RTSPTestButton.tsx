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
      const response = await fetch('/api/v1/config/cameras/test-rtsp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rtsp_url: url, timeout_s: 10 }),
      })
      if (!response.ok) throw new Error('Test failed')
      return response.json() as Promise<RTSPTestResult>
    },
    onSuccess: (data) => {
      setResult(data)
      onResult?.(data)
    },
    onError: (error) => {
      const errorResult: RTSPTestResult = {
        success: false,
        message: error instanceof Error ? error.message : 'Unknown error',
      }
      setResult(errorResult)
      onResult?.(errorResult)
    },
  })

  const handleTest = () => {
    if (!rtspUrl) return
    setResult(null)
    testMutation.mutate(rtspUrl)
  }

  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      <button
        onClick={handleTest}
        disabled={testMutation.isPending || !rtspUrl}
        className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
          testMutation.isPending
            ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
            : 'bg-blue-600 hover:bg-blue-700 text-white'
        }`}
      >
        {testMutation.isPending ? 'Testing...' : 'Test Connection'}
      </button>

      {result && (
        <div
          className={`text-xs p-2 rounded ${
            result.success ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'
          }`}
        >
          {result.success ? (
            <div className="flex flex-col gap-0.5">
              <span className="font-medium">✓ Online</span>
              {result.codec && <span>Codec: {result.codec}</span>}
              {result.resolution && <span>Resolution: {result.resolution}</span>}
              {result.fps && <span>FPS: {result.fps}</span>}
            </div>
          ) : (
            <span>✗ {result.message}</span>
          )}
        </div>
      )}
    </div>
  )
}
