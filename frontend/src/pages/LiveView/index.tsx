import { useQuery } from '@tanstack/react-query'
import { camerasApi } from '@/api/cameras'
import { useCameraStore, GridSize } from '@/store/cameras'
import { CameraGrid } from '@/components/camera/CameraGrid'
import { useEffect, useState } from 'react'
import type { Camera } from '@/types'

const GRIDS: GridSize[] = ['1x1', '2x2', '3x3', '4x4', '5x6']

export default function LiveViewPage() {
  const { cameras, gridSize, setGridSize, setCameras, selectedCameras, toggleSelected, selectAll, selectNone } = useCameraStore()
  const [showFilter, setShowFilter] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')

  const { data: fetchedCameras } = useQuery({
    queryKey: ['cameras'],
    queryFn: camerasApi.list,
  })

  useEffect(() => {
    if (fetchedCameras) setCameras(fetchedCameras)
  }, [fetchedCameras, setCameras])

  const online = cameras.filter((c: Camera) => c.status === 'online').length
  const total = cameras.length

  // C-07: filter kamera berdasarkan search
  const filteredCameras = cameras.filter((c: Camera) =>
    c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (c.location ?? '').toLowerCase().includes(searchTerm.toLowerCase())
  )

  return (
    <div className="flex flex-col h-full p-2 gap-2">
      {/* Toolbar */}
      <div className="flex items-center gap-2 bg-gray-800 rounded px-3 py-2 flex-shrink-0 flex-wrap">
        <span className="text-sm font-medium text-white">Live View</span>

        {/* Status */}
        <span className="text-xs text-green-400">
          {online}/{total} online
        </span>

        {/* C-07: Filter toggle */}
        <button
          onClick={() => setShowFilter(f => !f)}
          className={`ml-1 px-2 py-1 text-xs rounded ${
            showFilter ? 'bg-blue-600 text-white' : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
          }`}
        >
          Filter Kamera ({selectedCameras.length})
        </button>

        {/* Spacer */}
        <div className="flex-1" />

        {/* C-06: Grid size selector */}
        <div className="flex gap-1">
          {GRIDS.map(g => (
            <button
              key={g}
              onClick={() => setGridSize(g)}
              className={`px-2 py-1 text-xs rounded ${
                gridSize === g ? 'bg-blue-600 text-white' : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
              }`}
              title={`Layout ${g}`}
            >
              {g}
            </button>
          ))}
        </div>
      </div>

      {/* C-07: Filter panel */}
      {showFilter && (
        <div className="bg-gray-800 rounded px-3 py-2 flex-shrink-0">
          <div className="flex items-center gap-2 mb-2">
            <input
              type="text"
              placeholder="Cari kamera atau lokasi..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="flex-1 bg-gray-700 text-white text-xs px-2 py-1.5 rounded border border-gray-600 focus:outline-none focus:border-blue-500"
            />
            <button
              onClick={selectAll}
              className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 rounded"
            >
              Pilih Semua
            </button>
            <button
              onClick={selectNone}
              className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 rounded"
            >
              Hapus Semua
            </button>
          </div>
          <div className="flex flex-wrap gap-1 max-h-28 overflow-y-auto">
            {filteredCameras.map((c: Camera) => (
              <button
                key={c.id}
                onClick={() => toggleSelected(c.id)}
                className={`px-2 py-1 text-xs rounded flex items-center gap-1 ${
                  selectedCameras.includes(c.id)
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                }`}
              >
                <span className={`w-1.5 h-1.5 rounded-full ${
                  c.status === 'online' ? 'bg-green-400' : 'bg-red-400'
                }`} />
                {c.name}
                {c.location ? <span className="text-gray-400 text-[10px]">({c.location})</span> : null}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Grid */}
      <div className="flex-1 overflow-hidden">
        <CameraGrid />
      </div>
    </div>
  )
}
