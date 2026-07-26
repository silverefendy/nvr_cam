import { useQuery } from '@tanstack/react-query'
import { camerasApi } from '@/api/cameras'
import { useCameraStore } from '@/store/cameras'
import { CameraGrid } from '@/components/camera/CameraGrid'
import { FloatingCameraLayout } from '@/components/camera/FloatingCameraLayout'
import { useEffect, useState, useMemo } from 'react'
import type { Camera } from '@/types'

const PRESET_GRIDS: { label: string; rows: number; cols: number }[] = [
  { label: '1x1', rows: 1, cols: 1 },
  { label: '2x2', rows: 2, cols: 2 },
  { label: '3x3', rows: 3, cols: 3 },
  { label: '3x4', rows: 3, cols: 4 },
  { label: '4x4', rows: 4, cols: 4 },
  { label: '4x5', rows: 4, cols: 5 },
  { label: '5x6', rows: 5, cols: 6 },
]

type ViewMode = 'grid' | 'floating'
type LiveSortBy = 'name' | 'location' | 'status'
type LiveSortDir = 'asc' | 'desc'

export default function LiveViewPage() {
  const {
    cameras, gridRows, gridCols,
    setGridDimensions, setCameras,
    selectedCameras, toggleSelected, selectAll, selectNone
  } = useCameraStore()

  const [showFilter, setShowFilter] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [viewMode, setViewMode] = useState<ViewMode>('grid')
  const [showCustomInput, setShowCustomInput] = useState(false)
  const [customRows, setCustomRows] = useState(gridRows)
  const [customCols, setCustomCols] = useState(gridCols)
  const [sortBy, setSortBy] = useState<LiveSortBy>('name')
  const [sortDir, setSortDir] = useState<LiveSortDir>('asc')

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

  const filteredCameras = useMemo(() => {
    let result = cameras.filter((c: Camera) =>
      c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (c.location ?? '').toLowerCase().includes(searchTerm.toLowerCase())
    )

    result = [...result].sort((a: Camera, b: Camera) => {
      let va: any, vb: any
      if (sortBy === 'name') { va = a.name; vb = b.name }
      else if (sortBy === 'location') { va = a.location ?? ''; vb = b.location ?? '' }
      else { // status: online dulu (asc), offline dulu (desc)
        va = a.status === 'online' ? 0 : 1
        vb = b.status === 'online' ? 0 : 1
      }
      if (typeof va === 'number') return sortDir === 'asc' ? va - vb : vb - va
      return sortDir === 'asc'
        ? String(va).localeCompare(String(vb))
        : String(vb).localeCompare(String(va))
    })
    return result
  }, [cameras, searchTerm, sortBy, sortDir])

  const applyCustomGrid = () => {
    const r = Math.max(1, Math.min(10, customRows))
    const c = Math.max(1, Math.min(10, customCols))
    setGridDimensions(r, c)
    setShowCustomInput(false)
  }

  const toggleSort = (key: LiveSortBy) => {
    if (sortBy === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortBy(key); setSortDir('asc') }
  }

  const sortBtnStyle = (key: LiveSortBy): React.CSSProperties => ({
    fontSize: 10, padding: '3px 9px', borderRadius: 4, cursor: 'pointer',
    fontWeight: 600,
    background: sortBy === key ? '#1d4ed8' : '#1a1d27',
    color: sortBy === key ? '#fff' : '#94a3b8',
    border: `1px solid ${sortBy === key ? '#2563eb' : '#2a2d3a'}`,
  })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: '#0f1117' }}>

      <div style={{
        display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0,
        padding: '5px 10px',
        background: '#1a1d27',
        borderBottom: '1px solid #2a2d3a',
        flexWrap: 'wrap',
      }}>

        <span style={{ color: '#94a3b8', fontSize: 11, fontWeight: 700, letterSpacing: '0.07em' }}>LIVE</span>
        <span style={{
          fontSize: 10, padding: '1px 7px', borderRadius: 99, fontWeight: 600,
          background: online > 0 ? 'rgba(74,222,128,0.12)' : 'rgba(100,116,139,0.12)',
          color: online > 0 ? '#4ade80' : '#64748b',
          border: `1px solid ${online > 0 ? 'rgba(74,222,128,0.25)' : 'rgba(100,116,139,0.2)'}`,
        }}>
          {online}/{total} online
        </span>

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

        <div style={{
          display: 'flex', gap: 2, background: '#12151f',
          border: '1px solid #2a2d3a', borderRadius: 6, padding: 2,
        }}>
          <button
            onClick={() => setViewMode('grid')}
            style={{
              fontSize: 10, padding: '3px 9px', borderRadius: 4, fontWeight: 600, cursor: 'pointer',
              background: viewMode === 'grid' ? '#2563eb' : 'transparent',
              color: viewMode === 'grid' ? '#fff' : '#64748b',
              border: 'none', transition: 'all 0.15s',
            }}
          >Grid</button>
          <button
            onClick={() => setViewMode('floating')}
            style={{
              fontSize: 10, padding: '3px 9px', borderRadius: 4, fontWeight: 600, cursor: 'pointer',
              background: viewMode === 'floating' ? '#7c3aed' : 'transparent',
              color: viewMode === 'floating' ? '#fff' : '#64748b',
              border: 'none', transition: 'all 0.15s',
            }}
          >Floating</button>
        </div>

        {viewMode === 'grid' && (
          <div style={{ display: 'flex', gap: 2, alignItems: 'center', position: 'relative' }}>
            {PRESET_GRIDS.map(g => {
              const isActive = gridRows === g.rows && gridCols === g.cols && !showCustomInput
              return (
                <button
                  key={g.label}
                  onClick={() => { setGridDimensions(g.rows, g.cols); setShowCustomInput(false) }}
                  style={{
                    fontSize: 10, padding: '3px 8px', borderRadius: 5, fontWeight: 700, cursor: 'pointer',
                    background: isActive ? '#2563eb' : '#1e2130',
                    color: isActive ? '#fff' : '#64748b',
                    border: `1px solid ${isActive ? '#2563eb' : '#2a2d3a'}`,
                    transition: 'all 0.15s',
                  }}
                >{g.label}</button>
              )
            })}

            <button
              onClick={() => { setCustomRows(gridRows); setCustomCols(gridCols); setShowCustomInput(v => !v) }}
              style={{
                fontSize: 10, padding: '3px 8px', borderRadius: 5, fontWeight: 700, cursor: 'pointer',
                background: showCustomInput ? '#7c3aed' : '#1e2130',
                color: showCustomInput ? '#fff' : '#64748b',
                border: `1px solid ${showCustomInput ? '#7c3aed' : '#2a2d3a'}`,
                transition: 'all 0.15s',
              }}
            >Custom</button>

            {showCustomInput && (
              <div style={{
                position: 'absolute', top: '100%', right: 0, marginTop: 6,
                background: '#1a1d27', border: '1px solid #2a2d3a', borderRadius: 8,
                padding: '12px 14px', zIndex: 100, boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
                display: 'flex', flexDirection: 'column', gap: 10, minWidth: 180,
              }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: '#94a3b8' }}>Ukuran Grid Manual</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                    <label style={{ fontSize: 9, color: '#64748b', fontWeight: 600 }}>BARIS</label>
                    <input type="number" min={1} max={10} value={customRows}
                      onChange={e => setCustomRows(Number(e.target.value))}
                      style={{ width: 52, padding: '5px', borderRadius: 6, textAlign: 'center', background: '#12151f', color: '#e2e8f0', fontSize: 14, fontWeight: 700, border: '1px solid #2a2d3a', outline: 'none' }}
                    />
                  </div>
                  <span style={{ color: '#475569', fontSize: 18, fontWeight: 800, marginTop: 14 }}>x</span>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                    <label style={{ fontSize: 9, color: '#64748b', fontWeight: 600 }}>KOLOM</label>
                    <input type="number" min={1} max={10} value={customCols}
                      onChange={e => setCustomCols(Number(e.target.value))}
                      style={{ width: 52, padding: '5px', borderRadius: 6, textAlign: 'center', background: '#12151f', color: '#e2e8f0', fontSize: 14, fontWeight: 700, border: '1px solid #2a2d3a', outline: 'none' }}
                    />
                  </div>
                </div>
                <div style={{ fontSize: 10, color: '#475569' }}>= {customRows * customCols} slot kamera</div>
                <button onClick={applyCustomGrid}
                  style={{ padding: '7px', borderRadius: 6, fontSize: 11, fontWeight: 700, background: '#2563eb', color: '#fff', border: 'none', cursor: 'pointer' }}
                >Terapkan {customRows}x{customCols}</button>
              </div>
            )}
          </div>
        )}
      </div>

      {showFilter && (
        <div style={{ padding: '8px 10px', background: '#151822', borderBottom: '1px solid #2a2d3a', flexShrink: 0 }}>
          {/* Sort bar */}
          <div style={{ display: 'flex', gap: 5, marginBottom: 6, alignItems: 'center' }}>
            <span style={{ fontSize: 10, color: '#475569', fontWeight: 600, marginRight: 2 }}>Sort:</span>
            <button onClick={() => toggleSort('name')} style={sortBtnStyle('name')}>
              Name {sortBy === 'name' ? (sortDir === 'asc' ? '↑' : '↓') : ''}
            </button>
            <button onClick={() => toggleSort('location')} style={sortBtnStyle('location')}>
              Location {sortBy === 'location' ? (sortDir === 'asc' ? '↑' : '↓') : ''}
            </button>
            <button onClick={() => toggleSort('status')} style={sortBtnStyle('status')}>
              Status {sortBy === 'status' ? (sortDir === 'asc' ? '(online dulu)' : '(offline dulu)') : ''}
            </button>
          </div>

          {/* Search + select all/none */}
          <div style={{ display: 'flex', gap: 5, marginBottom: 6, alignItems: 'center' }}>
            <input
              type="text"
              placeholder="Cari kamera atau lokasi..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              style={{ flex: 1, background: '#1a1d27', color: '#e2e8f0', fontSize: 11, padding: '4px 9px', border: '1px solid #2a2d3a', borderRadius: 5, outline: 'none' }}
            />
            <button onClick={selectAll} style={filterBtnStyle}>Pilih Semua</button>
            <button onClick={selectNone} style={filterBtnStyle}>Hapus Semua</button>
          </div>

          {/* Chip kamera */}
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
                  <span style={{ width: 6, height: 6, borderRadius: '50%', flexShrink: 0, background: c.status === 'online' ? '#4ade80' : '#ef4444' }} />
                  {c.name}
                  {c.location && <span style={{ opacity: 0.5 }}>({c.location})</span>}
                </button>
              )
            })}
          </div>
        </div>
      )}

      <div
        style={{ flex: 1, minHeight: 0, position: 'relative' }}
        onClick={() => showCustomInput && setShowCustomInput(false)}
      >
        {viewMode === 'grid' ? (
          <div style={{ width: '100%', height: '100%' }}><CameraGrid /></div>
        ) : (
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
