import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from '@/api/client'
import { CameraForm } from "@/components/camera/CameraForm"

type SortKey = 'id' | 'name' | 'location' | 'is_online' | 'storage_drive' | 'motion_enabled' | 'retention_days'
type SortDir = 'asc' | 'desc'
type StatusFilter = 'all' | 'online' | 'offline'

export default function CamerasPage() {
  const [showForm, setShowForm] = useState(false)
  const [editingCamera, setEditingCamera] = useState<any | null>(null)
  const [sortKey, setSortKey] = useState<SortKey>('id')
  const [sortDir, setSortDir] = useState<SortDir>('asc')
  const [filterSearch, setFilterSearch] = useState('')
  const [filterStatus, setFilterStatus] = useState<StatusFilter>('all')
  const queryClient = useQueryClient()

  const { data: cameras, isLoading } = useQuery({
    queryKey: ["cameras-list"],
    queryFn: async () => {
      const res = await apiClient.get('/cameras')
      return res.data || []
    },
    refetchInterval: 10_000,
  })

  const { data: storageDrives } = useQuery({
    queryKey: ["storage-drives"],
    queryFn: async () => {
      const res = await apiClient.get('/storage/status')
      return res.data?.drives?.map((d: any) => d.path) || []
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      const res = await apiClient.delete(`/config/cameras/${id}`)
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cameras-list"] })
    },
  })

  const handleAdd = () => { setEditingCamera(null); setShowForm(true) }
  const handleEdit = (camera: any) => { setEditingCamera(camera); setShowForm(true) }
  const handleDelete = (id: string) => {
    if (confirm("Yakin ingin menghapus kamera ini?")) deleteMutation.mutate(id)
  }
  const handleFormClose = () => { setShowForm(false); setEditingCamera(null) }
  const handleFormSave = () => {
    setShowForm(false)
    setEditingCamera(null)
    queryClient.invalidateQueries({ queryKey: ["cameras-list"] })
  }

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(key); setSortDir('asc') }
  }

  const processedCameras = useMemo(() => {
    if (!cameras) return []
    let result = [...cameras]

    // Filter search
    if (filterSearch.trim()) {
      const q = filterSearch.toLowerCase()
      result = result.filter((c: any) =>
        c.id?.toLowerCase().includes(q) ||
        c.name?.toLowerCase().includes(q) ||
        (c.location || '').toLowerCase().includes(q)
      )
    }

    // Filter status
    if (filterStatus === 'online') result = result.filter((c: any) => c.is_online)
    if (filterStatus === 'offline') result = result.filter((c: any) => !c.is_online)

    // Sort
    result.sort((a: any, b: any) => {
      let va = a[sortKey]
      let vb = b[sortKey]
      if (typeof va === 'boolean') { va = va ? 1 : 0; vb = vb ? 1 : 0 }
      if (typeof va === 'number') return sortDir === 'asc' ? va - vb : vb - va
      return sortDir === 'asc'
        ? String(va ?? '').localeCompare(String(vb ?? ''))
        : String(vb ?? '').localeCompare(String(va ?? ''))
    })

    return result
  }, [cameras, filterSearch, filterStatus, sortKey, sortDir])

  const onlineCount = cameras?.filter((c: any) => c.is_online).length || 0
  const offlineCount = cameras?.filter((c: any) => !c.is_online).length || 0

  const SortIcon = ({ col }: { col: SortKey }) => {
    if (sortKey !== col) return <span style={{ opacity: 0.25, marginLeft: 3 }}>↕</span>
    return <span style={{ marginLeft: 3, color: '#60a5fa' }}>{sortDir === 'asc' ? '↑' : '↓'}</span>
  }

  const thStyle = (col: SortKey): React.CSSProperties => ({
    textAlign: 'left', padding: '8px 16px', color: '#94a3b8', cursor: 'pointer',
    userSelect: 'none', whiteSpace: 'nowrap',
    background: sortKey === col ? 'rgba(37,99,235,0.12)' : undefined,
  })

  if (showForm) {
    const cfg = editingCamera?.config_json || {}
    return (
      <div className="flex flex-col h-full p-4">
        <CameraForm
          initialData={editingCamera ? {
            id: editingCamera.id,
            name: editingCamera.name,
            location: editingCamera.location || '',
            ip_address: cfg.ip_address || editingCamera.rtsp_main?.match(/@([^:@]+):/)?.[1] || '',
            port: cfg.port || 554,
            username: cfg.username || 'admin',
            password: cfg.password || '',
            channel: cfg.channel || 1,
            storage_drive: editingCamera.storage_drive,
            motion_enabled: editingCamera.motion_enabled ?? false,
            retention_days: editingCamera.retention_days || 30,
          } : undefined}
          storageDrives={storageDrives || []}
          onSave={handleFormSave}
          onCancel={handleFormClose}
        />
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full p-4 gap-4">
      {/* Header bar */}
      <div className="flex items-center gap-4 bg-gray-800 rounded px-4 py-3 flex-shrink-0">
        <span className="text-sm font-medium text-white">Cameras</span>
        <span className="text-xs text-green-400">{onlineCount} online</span>
        <span className="text-xs text-red-400">{offlineCount} offline</span>
        <span className="text-xs text-gray-400">{cameras?.length || 0} total</span>
        {processedCameras.length !== (cameras?.length || 0) && (
          <span className="text-xs text-blue-400">(menampilkan {processedCameras.length})</span>
        )}
        <div className="ml-auto flex items-center gap-2">
          {/* Search */}
          <input
            type="text"
            placeholder="Cari ID / Nama / Lokasi..."
            value={filterSearch}
            onChange={e => setFilterSearch(e.target.value)}
            className="text-xs bg-gray-700 text-gray-200 border border-gray-600 rounded px-2 py-1 outline-none w-44"
          />
          {/* Status filter */}
          <select
            value={filterStatus}
            onChange={e => setFilterStatus(e.target.value as StatusFilter)}
            className="text-xs bg-gray-700 text-gray-200 border border-gray-600 rounded px-2 py-1 outline-none"
          >
            <option value="all">Semua Status</option>
            <option value="online">Online</option>
            <option value="offline">Offline</option>
          </select>
          {(filterSearch || filterStatus !== 'all') && (
            <button
              onClick={() => { setFilterSearch(''); setFilterStatus('all') }}
              className="text-xs text-gray-400 hover:text-white px-1"
              title="Reset filter"
            >✕</button>
          )}
          <button
            onClick={handleAdd}
            className="px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-xs text-white"
          >+ Add Camera</button>
        </div>
      </div>

      {/* Tabel */}
      <div className="flex-1 overflow-auto bg-gray-900 rounded">
        {isLoading ? (
          <div className="flex items-center justify-center h-full text-gray-500">Loading...</div>
        ) : !cameras?.length ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-500 gap-2">
            <div className="text-4xl">📷</div>
            <div className="text-sm">Belum ada kamera. Klik "+ Add Camera" untuk menambahkan.</div>
          </div>
        ) : processedCameras.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-500 gap-2">
            <div className="text-2xl">🔍</div>
            <div className="text-sm">Tidak ada kamera yang cocok dengan filter.</div>
            <button onClick={() => { setFilterSearch(''); setFilterStatus('all') }} className="text-xs text-blue-400 hover:underline">Reset Filter</button>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-800 sticky top-0">
              <tr>
                <th style={thStyle('id')} onClick={() => handleSort('id')}>ID <SortIcon col="id" /></th>
                <th style={thStyle('name')} onClick={() => handleSort('name')}>Name <SortIcon col="name" /></th>
                <th style={thStyle('location')} onClick={() => handleSort('location')}>Location <SortIcon col="location" /></th>
                <th style={thStyle('is_online')} onClick={() => handleSort('is_online')}>Status <SortIcon col="is_online" /></th>
                <th style={thStyle('storage_drive')} onClick={() => handleSort('storage_drive')}>Storage <SortIcon col="storage_drive" /></th>
                <th style={thStyle('motion_enabled')} onClick={() => handleSort('motion_enabled')}>Motion <SortIcon col="motion_enabled" /></th>
                <th style={thStyle('retention_days')} onClick={() => handleSort('retention_days')}>Retention <SortIcon col="retention_days" /></th>
                <th className="text-left px-4 py-2 text-gray-300">Actions</th>
              </tr>
            </thead>
            <tbody>
              {processedCameras.map((camera: any) => (
                <tr key={camera.id} className="border-b border-gray-800 hover:bg-gray-800/50">
                  <td className="px-4 py-2 text-gray-300 font-mono">{camera.id}</td>
                  <td className="px-4 py-2 text-white">{camera.name}</td>
                  <td className="px-4 py-2 text-gray-400">{camera.location || "-"}</td>
                  <td className="px-4 py-2">
                    <span className={camera.is_online ? "text-green-400 font-medium" : "text-red-400"}>
                      {camera.is_online ? "● Online" : "○ Offline"}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-gray-300">{camera.storage_drive}</td>
                  <td className="px-4 py-2">
                    <span className={camera.motion_enabled ? "text-green-400" : "text-gray-500"}>
                      {camera.motion_enabled ? "Enabled" : "Disabled"}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-gray-400">{camera.retention_days || 30} days</td>
                  <td className="px-4 py-2 flex gap-2">
                    <button
                      onClick={() => handleEdit(camera)}
                      className="px-2 py-0.5 text-xs text-blue-400 border border-blue-800 rounded hover:bg-blue-900/40"
                    >Edit</button>
                    <button
                      onClick={() => handleDelete(camera.id)}
                      disabled={deleteMutation.isPending}
                      className="px-2 py-0.5 text-xs text-red-400 border border-red-900 rounded hover:bg-red-900/40 disabled:opacity-40"
                    >Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
