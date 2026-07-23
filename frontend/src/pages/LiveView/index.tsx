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
  const filteredCameras = cameras.filter((c: Camera) =>
    c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (c.location ?? '').toLowerCase().includes(searchTerm.toLowerCase())
  )

  return (
    <div className="flex flex-col h-full p-3 gap-3 bg-slate-100">
      {/* Toolbar */}
      <div className="flex items-center gap-3 bg-white border border-slate-200 rounded-xl px-4 py-2.5 flex-shrink-0 flex-wrap shadow-sm">
        <span className="text-sm font-semibold text-slate-700">📹 Live View</span>
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${online > 0 ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>
          {online}/{total} online
        </span>

        <button
          onClick={() => setShowFilter(f => !f)}
          className={`ml-1 px-3 py-1.5 text-xs rounded-lg font-medium transition-colors ${
            showFilter ? 'bg-sky-600 text-white' : 'bg-slate-100 hover:bg-slate-200 text-slate-600 border border-slate-300'
          }`}
        >
          Filter Kamera ({selectedCameras.length})
        </button>

        <div className="flex-1" />

        <div className="flex gap-1">
          {GRIDS.map(g => (
            <button
              key={g}
              onClick={() => setGridSize(g)}
              className={`px-2.5 py-1.5 text-xs rounded-lg font-medium transition-colors ${
                gridSize === g
                  ? 'bg-sky-600 text-white shadow-sm'
                  : 'bg-slate-100 hover:bg-slate-200 text-slate-600 border border-slate-300'
              }`}
            >
              {g}
            </button>
          ))}
        </div>
      </div>

      {/* Filter panel */}
      {showFilter && (
        <div className="bg-white border border-slate-200 rounded-xl px-4 py-3 flex-shrink-0 shadow-sm">
          <div className="flex items-center gap-2 mb-3">
            <input
              type="text"
              placeholder="Cari kamera atau lokasi..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="flex-1 bg-slate-50 text-slate-800 text-xs px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-200"
            />
            <button onClick={selectAll} className="px-3 py-2 text-xs bg-slate-100 hover:bg-slate-200 text-slate-600 border border-slate-300 rounded-lg font-medium">
              Pilih Semua
            </button>
            <button onClick={selectNone} className="px-3 py-2 text-xs bg-slate-100 hover:bg-slate-200 text-slate-600 border border-slate-300 rounded-lg font-medium">
              Hapus Semua
            </button>
          </div>
          <div className="flex flex-wrap gap-1.5 max-h-28 overflow-y-auto">
            {filteredCameras.map((c: Camera) => (
              <button
                key={c.id}
                onClick={() => toggleSelected(c.id)}
                className={`px-3 py-1.5 text-xs rounded-lg flex items-center gap-1.5 font-medium border transition-colors ${
                  selectedCameras.includes(c.id)
                    ? 'bg-sky-600 text-white border-sky-600'
                    : 'bg-white text-slate-600 border-slate-300 hover:bg-slate-50'
                }`}
              >
                <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${c.status === 'online' ? 'bg-emerald-400' : 'bg-red-400'}`} />
                {c.name}
                {c.location ? <span className="opacity-60">({c.location})</span> : null}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Grid */}
      <div className="flex-1 overflow-hidden rounded-xl">
        <CameraGrid />
      </div>
    </div>
  )
}
