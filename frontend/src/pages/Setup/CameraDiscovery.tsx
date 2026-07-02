import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'

export interface DiscoveredCamera {
  ip: string
  port: number
  manufacturer?: string
  model?: string
  name?: string
  rtsp_url?: string
  onvif_url?: string
  mac_address?: string
}

interface Props {
  onNext: (cameras: DiscoveredCamera[]) => void
  onSkip: () => void
}

export const CameraDiscovery: React.FC<Props> = ({ onNext, onSkip }) => {
  const [selectedCameras, setSelectedCameras] = useState<Set<string>>(new Set())
  const [network, setNetwork] = useState('')
  const [isScanning, setIsScanning] = useState(false)

  const discoverMutation = useMutation({
    mutationFn: async (network?: string) => {
      const body = network ? { network, timeout: 10 } : { timeout: 10 }
      const response = await fetch('/api/v1/discovery/cameras', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!response.ok) throw new Error('Discovery failed')
      return response.json()
    },
  })

  const { data: discoveredCameras, refetch } = useQuery({
    queryKey: ['discovered-cameras'],
    queryFn: () => Promise.resolve(discoverMutation.data),
    enabled: false,
  })

  const handleScan = () => {
    setIsScanning(true)
    discoverMutation.mutate(network || undefined)
  }

  useEffect(() => {
    if (discoverMutation.isSuccess) {
      setIsScanning(false)
      refetch()
    }
    if (discoverMutation.isError) {
      setIsScanning(false)
    }
  }, [discoverMutation.isSuccess, discoverMutation.isError, refetch])

  const handleToggleCamera = (ip: string) => {
    setSelectedCameras(prev => {
      const next = new Set(prev)
      if (next.has(ip)) {
        next.delete(ip)
      } else {
        next.add(ip)
      }
      return next
    })
  }

  const handleAddSelected = () => {
    const cameras = discoveredCameras?.cameras?.filter((c: DiscoveredCamera) => 
      selectedCameras.has(c.ip)
    ) || []
    onNext(cameras)
  }

  const handleSkip = () => {
    onSkip()
  }

  return (
    <div className="bg-gray-800 rounded-lg p-8 max-w-4xl w-full">
      <h2 className="text-2xl font-bold text-white mb-4">Discover Cameras</h2>
      <p className="text-gray-400 mb-6">
        Automatically discover ONVIF-compatible cameras on your network. You can also manually add cameras later.
      </p>

      {/* Network Input */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Network (optional)
        </label>
        <div className="flex gap-3">
          <input
            type="text"
            value={network}
            onChange={(e) => setNetwork(e.target.value)}
            placeholder="e.g., 192.168.1.0/24 (leave empty for local subnet)"
            className="flex-1 bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
          />
          <button
            onClick={handleScan}
            disabled={isScanning}
            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded text-white"
          >
            {isScanning ? 'Scanning...' : 'Scan Network'}
          </button>
        </div>
      </div>

      {/* Discovered Cameras */}
      {discoveredCameras?.cameras && discoveredCameras.cameras.length > 0 && (
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-white mb-3">
            Found {discoveredCameras.cameras.length} Camera(s)
          </h3>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {discoveredCameras.cameras.map((camera: DiscoveredCamera) => (
              <div
                key={camera.ip}
                className={`flex items-center gap-4 p-3 rounded border ${
                  selectedCameras.has(camera.ip)
                    ? 'bg-blue-900/30 border-blue-600'
                    : 'bg-gray-700 border-gray-600'
                }`}
              >
                <input
                  type="checkbox"
                  checked={selectedCameras.has(camera.ip)}
                  onChange={() => handleToggleCamera(camera.ip)}
                  className="rounded"
                />
                <div className="flex-1">
                  <div className="text-white font-medium">
                    {camera.name || camera.model || 'Unknown Camera'}
                  </div>
                  <div className="text-sm text-gray-400">
                    {camera.manufacturer && `${camera.manufacturer} · `}
                    {camera.ip}:{camera.port}
                  </div>
                </div>
                {camera.onvif_url && (
                  <div className="text-xs text-green-400">ONVIF</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {discoveredCameras?.cameras && discoveredCameras.cameras.length === 0 && !isScanning && (
        <div className="bg-gray-700 rounded p-4 mb-6 text-center">
          <p className="text-gray-400">No cameras found on the network.</p>
          <p className="text-sm text-gray-500 mt-1">
            Make sure cameras are ONVIF-compatible and on the same network.
          </p>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-4">
        {selectedCameras.size > 0 && (
          <button
            onClick={handleAddSelected}
            className="px-6 py-2 bg-green-600 hover:bg-green-700 rounded text-white"
          >
            Add Selected ({selectedCameras.size})
          </button>
        )}
        <button
          onClick={handleSkip}
          className="px-6 py-2 bg-gray-600 hover:bg-gray-700 rounded text-white"
        >
          Skip for Now
        </button>
      </div>

      {discoverMutation.error && (
        <div className="mt-4 text-red-400 text-sm">
          Discovery failed: {discoverMutation.error instanceof Error ? discoverMutation.error.message : 'Unknown error'}
        </div>
      )}
    </div>
  )
}
