import { useQuery } from '@tanstack/react-query'
import { camerasApi } from '@/api/cameras'
import { useCameraStore, GridSize } from '@/store/cameras'
import { CameraGrid } from '@/components/camera/CameraGrid'
import { FloatingCameraLayout } from '@/components/camera/FloatingCameraLayout'
import { useEffect, useState } from 'react'
import type { Camera } from '@/types'

const GRIDS: GridSize[] = ['1x1', '2x2', '3x3', '4x4', '5x6']

// Mode tampilan Live View
type ViewMode = 'grid' | 'floating'

export default function LiveViewPage() {
  const { cameras, gridSize, setGridSize, setCameras, selectedCameras, toggleSelected, selectAll, selectNone } = useCameraStore()
  const [showFilter, setShowFilter] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [viewMode, setViewMode] = useState<ViewMode>('grid')

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
    // Tinggi penuh layar, tidak ada scroll — semua konten harus muat
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: '#0f1117' }}>

      {/* ── Toolbar ───────────────────────────────────────────────────── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0,
        padding: '5px 10px',
        background: '#1a1d27',
        borderBottom: '1px solid #2a2d3a',
        flexWrap: 'wrap',
      }}>

        {/* Label + status badge */}
        <span style={{ color: '#94a3b8', fontSize: 11, fontWeight: 700, letterSpacing: '0.07em' }}>📹 LIVE</span>
        <span style={{
          fontSize: 10, padding: '1px 7px', borderRadius: 99, fontWeight: 600,
          background: online > 0 ? 'rgba(74,222,128,0.12)' : 'rgba(100,116,139,0.12)',
          color: online > 0 ? '#4ade80' : '#64748b',
          border: `1px solid ${online > 0 ? 'rgba(74,222,128,0.25)' : 'rgba(100,116,139,0.2)'}`,
        }}>
          {online}/{total} online
        </span>

        {/* Filter toggle */}
        <button
          onClick={() => setShowFilter(f => !f)}
          style={{
            fontSize: 10, padding: '3px 9px', borderRadius: 5, fontWeight: 600, cursor: 'pointer',
            background: showFilter ? '#2563eb' : '#1e2130',
            color: showFilter ? '#fff' : '#94a3b8',
            border: `1px solid ${showFilter ? '#2563eb' : '#2a2d3a'}`,
          }}
        >
          Filter ({selectedCameras.length})
        </button>

        <div style={{ flex: 1 }} />

        {/* ── Mode toggle: Grid / Floating ─────────── */}
        <div style={{
          display: 'flex', gap: 2,
          background: '#12151f',
          border: '1px solid #2a2d3a',
          borderRadius: 6,
          padding: 2,
        }}>
          <button
            onClick={() => setViewMode('grid')}
            title="Grid Mode — kamera mengisi layar secara merata"
            style={{
              fontSize: 10, padding: '3px 9px', borderRadius: 4, fontWeight: 600, cursor: 'pointer',
              background: viewMode === 'grid' ? '#2563eb' : 'transparent',
              color: viewMode === 'grid' ? '#fff' : '#64748b',
              border: 'none',
              transition: 'all 0.15s',
            }}
          >
            ⊞ Grid
          </button>
          <button
            onClick={() => setViewMode('floating')}
            title="Floating Mode — setiap kamera bisa dipindah dan di-resize"
            style={{
              fontSize: 10, padding: '3px 9px', borderRadius: 4, fontWeight: 600, cursor: 'pointer',
              background: viewMode === 'floating' ? '#7c3aed' : 'transparent',
              color: viewMode === 'floating' ? '#fff' : '#64748b',
              border: 'none',
              transition: 'all 0.15s',
            }}
          >
            ⧉ Floating
          </button>
        </div>

        {/* ── Grid size buttons (hanya tampil di mode Grid) ─── */}
        {viewMode === 'grid' && (
          <div style={{ display: 'flex', gap: 2 }}>
            {GRIDS.map(g => (
              <button
                key={g}
                onClick={() => setGridSize(g)}
                style={{
                  fontSize: 10, padding: '3px 8px', borderRadius: 5, fontWeight: 700, cursor: 'pointer',
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
        )}
      </div>

      {/* ── Filter panel ──────────────────────────────────────────────── */}
      {showFilter && (
        <div style={{
          padding: '8px 10px',
          background: '#151822',
          borderBottom: '1px solid #2a2d3a',
          flexShrink: 0,
        }}>
          <div style={{ display: 'flex', gap: 5, marginBottom: 6, alignItems: 'center' }}>
            <input
              type="text"
              placeholder="Cari kamera atau lokasi..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              style={{
                flex: 1, background: '#1a1d27', color: '#e2e8f0', fontSize: 11,
                padding: '4px 9px', border: '1px solid #2a2d3a', borderRadius: 5, outline: 'none',
              }}
            />
            <button onClick={selectAll} style={filterBtnStyle}>Pilih Semua</button>
            <button onClick={selectNone} style={filterBtnStyle}>Hapus Semua</button>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, maxHeight: 90, overflowY: 'auto' }}>
            {filteredCameras.map((c: Camera) => {
              const isSelected = selectedCameras.includes(c.id)
              return (
                <button
                  key={c.id}
                  onClick={() => toggleSelected(c.id)}
                  style={{
                    fontSize: 10, padding: '3px 9px', borderRadius: 4, cursor: 'pointer',
                    fontWeight: 500, display: 'flex', alignItems: 'center', gap: 4,
                    background: isSelected ? '#1d4ed8' : '#1a1d27',
                    color: isSelected ? '#fff' : '#94a3b8',
                    border: `1px solid ${isSelected ? '#2563eb' : '#2a2d3a'}`,
                  }}
                >
                  <span style={{
                    width: 6, height: 6, borderRadius: '50%', flexShrink: 0,
                    background: c.status === 'online' ? '#4ade80' : '#ef4444',
                  }} />
                  {c.name}
                  {c.location && <span style={{ opacity: 0.5 }}>({c.location})</span>}
                </button>
              )
            })}
          </div>
        </div>
      )}

      {/* ── Area konten utama ─────────────────────────────────────────── */}
      {/*
        flex: 1 + min-height: 0 adalah kunci agar area ini mengisi sisa tinggi
        tanpa menyebabkan overflow. Tanpa min-height: 0, flex item bisa overflow
        melebihi parent di beberapa browser.
      */}
      <div style={{ flex: 1, minHeight: 0, position: 'relative' }}>
        {viewMode === 'grid' ? (
          // Grid mode: kamera mengisi area secara merata
          <div style={{ width: '100%', height: '100%' }}>
            <CameraGrid />
          </div>
        ) : (
          // Floating mode: kamera sebagai window yang bisa dipindah dan di-resize
          <FloatingCameraLayout />
        )}
      </div>
    </div>
  )
}

const filterBtnStyle: React.CSSProperties = {
  fontSize: 10, padding: '3px 9px', borderRadius: 4, cursor: 'pointer',
  background: '#1e2130', color: '#94a3b8', border: '1px solid #2a2d3a', fontWeight: 500,
  whiteSpace: 'nowrap',
}
