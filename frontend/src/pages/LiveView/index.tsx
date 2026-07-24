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
    refetchInterval: 15000,
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
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: '#0f1117' }}>

      {/* Toolbar */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0,
        padding: '6px 12px',
        background: '#1a1d27',
        borderBottom: '1px solid #2a2d3a',
        flexWrap: 'wrap',
      }}>
        <span style={{ color: '#94a3b8', fontSize: 12, fontWeight: 600, letterSpacing: '0.05em' }}>📹 LIVE VIEW</span>
        <span style={{
          fontSize: 11, padding: '1px 8px', borderRadius: 99, fontWeight: 600,
          background: online > 0 ? 'rgba(74,222,128,0.15)' : 'rgba(100,116,139,0.15)',
          color: online > 0 ? '#4ade80' : '#64748b',
          border: `1px solid ${online > 0 ? 'rgba(74,222,128,0.3)' : 'rgba(100,116,139,0.2)'}`,
        }}>
          {online}/{total} online
        </span>

        <button
          onClick={() => setShowFilter(f => !f)}
          style={{
            fontSize: 11, padding: '3px 10px', borderRadius: 6, fontWeight: 500, cursor: 'pointer',
            background: showFilter ? '#2563eb' : '#1e2130',
            color: showFilter ? '#fff' : '#94a3b8',
            border: `1px solid ${showFilter ? '#2563eb' : '#2a2d3a'}`,
          }}
        >
          Filter ({selectedCameras.length})
        </button>

        <div style={{ flex: 1 }} />

        {/* Grid size buttons */}
        <div style={{ display: 'flex', gap: 3 }}>
          {GRIDS.map(g => (
            <button
              key={g}
              onClick={() => setGridSize(g)}
              style={{
                fontSize: 11, padding: '3px 10px', borderRadius: 6, fontWeight: 600, cursor: 'pointer',
                background: gridSize === g ? '#2563eb' : '#1e2130',
                color: gridSize === g ? '#fff' : '#64748b',
                border: `1px solid ${gridSize === g ? '#2563eb' : '#2a2d3a'}`,
                transition: 'all 0.15s',
              }}
            >
              {g}
            </button>
          ))}
        </div>
      </div>

      {/* Filter panel */}
      {showFilter && (
        <div style={{
          padding: '10px 12px', background: '#151822',
          borderBottom: '1px solid #2a2d3a', flexShrink: 0,
        }}>
          <div style={{ display: 'flex', gap: 6, marginBottom: 8, alignItems: 'center' }}>
            <input
              type="text"
              placeholder="Cari kamera atau lokasi..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              style={{
                flex: 1, background: '#1a1d27', color: '#e2e8f0', fontSize: 12,
                padding: '5px 10px', border: '1px solid #2a2d3a', borderRadius: 6, outline: 'none',
              }}
            />
            <button onClick={selectAll} style={filterBtnStyle}>Pilih Semua</button>
            <button onClick={selectNone} style={filterBtnStyle}>Hapus Semua</button>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5, maxHeight: 100, overflowY: 'auto' }}>
            {filteredCameras.map((c: Camera) => {
              const isSelected = selectedCameras.includes(c.id)
              return (
                <button
                  key={c.id}
                  onClick={() => toggleSelected(c.id)}
                  style={{
                    fontSize: 11, padding: '3px 10px', borderRadius: 5, cursor: 'pointer',
                    fontWeight: 500, display: 'flex', alignItems: 'center', gap: 5,
                    background: isSelected ? '#1d4ed8' : '#1a1d27',
                    color: isSelected ? '#fff' : '#94a3b8',
                    border: `1px solid ${isSelected ? '#2563eb' : '#2a2d3a'}`,
                  }}
                >
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: c.status === 'online' ? '#4ade80' : '#ef4444', flexShrink: 0 }} />
                  {c.name}
                  {c.location && <span style={{ opacity: 0.55 }}>({c.location})</span>}
                </button>
              )
            })}
          </div>
        </div>
      )}

      {/* Grid area — fill sisa ruang */}
      <div style={{ flex: 1, overflow: 'hidden', minHeight: 0 }}>
        <CameraGrid />
      </div>
    </div>
  )
}

const filterBtnStyle: React.CSSProperties = {
  fontSize: 11, padding: '4px 10px', borderRadius: 5, cursor: 'pointer',
  background: '#1e2130', color: '#94a3b8', border: '1px solid #2a2d3a', fontWeight: 500,
}
