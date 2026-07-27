import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { apiClient } from '@/api/client'

interface DiscoveredCamera {
  ip: string
  ip_address?: string
  port: number
  manufacturer?: string
  model?: string
  onvif_support?: boolean
  is_camera?: boolean
  rtsp_url?: string
  mac_address?: string
}

interface Props {
  onSelect?: (camera: DiscoveredCamera) => void
}

export const CameraDiscovery: React.FC<Props> = ({ onSelect }) => {
  const [discovered, setDiscovered] = useState<DiscoveredCamera[]>([])
  const [scanInfo, setScanInfo] = useState<{ total: number; filtered: number } | null>(null)
  const [cameraOnly, setCameraOnly] = useState(true)

  const scanMutation = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post('/discovery/cameras', { camera_only: cameraOnly })
      return res.data
    },
    onSuccess: (data) => {
      const cameras = data?.cameras || data?.data || []
      setDiscovered(cameras)
      setScanInfo({
        total: data?.total_found ?? cameras.length,
        filtered: data?.filtered_out ?? 0,
      })
    },
  })

  const getIp = (cam: DiscoveredCamera) => cam.ip || cam.ip_address || ''

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-slate-800">Scan Kamera di Jaringan</h3>
          <p className="text-xs text-slate-500 mt-0.5">Deteksi otomatis kamera IP via ONVIF / port scan</p>
        </div>
        <div className="flex items-center gap-3">
          {/* Toggle: hanya kamera */}
          <label className="flex items-center gap-2 text-xs text-slate-500 cursor-pointer select-none">
            <div
              className={`w-8 h-4 rounded-full transition-colors relative flex-shrink-0 ${
                cameraOnly ? 'bg-sky-500' : 'bg-slate-300'
              }`}
              onClick={() => setCameraOnly(v => !v)}
            >
              <div className={`absolute top-0.5 w-3 h-3 bg-white rounded-full shadow transition-transform ${
                cameraOnly ? 'translate-x-4' : 'translate-x-0.5'
              }`} />
            </div>
            Kamera saja
          </label>

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
      </div>

      {/* Info hasil scan */}
      {scanInfo && !scanMutation.isPending && (
        <div className="text-xs text-slate-400 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2">
          Ditemukan <strong className="text-slate-600">{scanInfo.total}</strong> device di jaringan
          {cameraOnly && scanInfo.filtered > 0 && (
            <> · <strong className="text-slate-500">{scanInfo.filtered}</strong> non-kamera disaring</>
          )}
          {cameraOnly && (
            <> · filter aktif: <span className="text-sky-600 font-medium">hanya kamera IP</span></>
          )}
        </div>
      )}

      {scanMutation.isError && (
        <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-600">
          ❌ Gagal scan: {(scanMutation.error as any)?.response?.data?.detail || 'Terjadi kesalahan.'}
        </div>
      )}

      {discovered.length > 0 && (
        <div className="space-y-2">
          {discovered.map((cam) => (
            <div
              key={`${getIp(cam)}:${cam.port}`}
              className="flex items-center justify-between bg-slate-50 border border-slate-200 rounded-xl px-4 py-3"
            >
              <div>
                <div className="text-sm font-medium text-slate-800">
                  {getIp(cam)}:{cam.port}
                </div>
                <div className="text-xs text-slate-500 mt-0.5">
                  {cam.manufacturer || 'Unknown vendor'}
                  {cam.model ? ` · ${cam.model}` : ''}
                  {cam.onvif_support ? ' · ✅ ONVIF' : ''}
                  {cam.mac_address ? ` · MAC: ${cam.mac_address}` : ''}
                </div>
              </div>
              {onSelect && (
                <button
                  type="button"
                  onClick={() => onSelect({ ...cam, ip_address: getIp(cam) })}
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
          {cameraOnly
            ? 'Tidak ada kamera IP ditemukan. Coba matikan filter "Kamera saja" untuk lihat semua device.'
            : 'Tidak ada device ditemukan di jaringan.'}
        </div>
      )}
    </div>
  )
}
