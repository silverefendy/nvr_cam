import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { apiClient } from '@/api/client'

interface DiscoveredCamera {
  ip_address: string
  port: number
  manufacturer?: string
  model?: string
  onvif_support?: boolean
}

interface Props {
  onSelect?: (camera: DiscoveredCamera) => void
}

export const CameraDiscovery: React.FC<Props> = ({ onSelect }) => {
  const [discovered, setDiscovered] = useState<DiscoveredCamera[]>([])

  const scanMutation = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post('/discovery/cameras')
      return res.data
    },
    onSuccess: (data) => {
      setDiscovered(data?.cameras || data?.data || [])
    },
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-slate-800">Scan Kamera di Jaringan</h3>
          <p className="text-xs text-slate-500 mt-0.5">Deteksi otomatis kamera IP via ONVIF / port scan</p>
        </div>
        <button
          type="button"
          onClick={() => scanMutation.mutate()}
          disabled={scanMutation.isPending}
          className="px-4 py-2 rounded-lg text-sm font-medium bg-sky-600 hover:bg-sky-500 text-white
            disabled:opacity-40 disabled:cursor-not-allowed transition-colors shadow-sm"
        >
          {scanMutation.isPending ? (
            <span className="flex items-center gap-2">
              <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
              </svg>
              Scanning...
            </span>
          ) : '🔍 Scan Jaringan'}
        </button>
      </div>

      {scanMutation.isError && (
        <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-600">
          ❌ Gagal scan: {(scanMutation.error as any)?.response?.data?.detail || 'Terjadi kesalahan.'}
        </div>
      )}

      {discovered.length > 0 && (
        <div className="space-y-2">
          {discovered.map((cam) => (
            <div
              key={`${cam.ip_address}:${cam.port}`}
              className="flex items-center justify-between bg-slate-50 border border-slate-200 rounded-xl px-4 py-3"
            >
              <div>
                <div className="text-sm font-medium text-slate-800">
                  {cam.ip_address}:{cam.port}
                </div>
                <div className="text-xs text-slate-500 mt-0.5">
                  {cam.manufacturer || 'Unknown'} {cam.model ? `· ${cam.model}` : ''}
                  {cam.onvif_support ? ' · ✅ ONVIF' : ''}
                </div>
              </div>
              {onSelect && (
                <button
                  type="button"
                  onClick={() => onSelect(cam)}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium bg-sky-100 hover:bg-sky-200 text-sky-700 transition-colors"
                >
                  Gunakan
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {!scanMutation.isPending && !scanMutation.isError && discovered.length === 0 && scanMutation.isSuccess && (
        <div className="text-center py-6 text-sm text-slate-400">
          Tidak ada kamera ditemukan di jaringan.
        </div>
      )}
    </div>
  )
}
