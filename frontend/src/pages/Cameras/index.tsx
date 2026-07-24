import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from '@/api/client'
import { CameraForm } from "@/components/camera/CameraForm"

export default function CamerasPage() {
  const [showForm, setShowForm] = useState(false)
  const [editingCamera, setEditingCamera] = useState<any | null>(null)
  const queryClient = useQueryClient()

  // Gunakan /cameras (bukan /config/cameras) agar dapat field is_online dari RecordingManager
  const { data: cameras, isLoading } = useQuery({
    queryKey: ["cameras-list"],
    queryFn: async () => {
      const res = await apiClient.get('/cameras')
      return res.data || []
    },
    refetchInterval: 10_000,   // refresh status online/offline setiap 10 detik
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

  const handleAdd = () => {
    setEditingCamera(null)
    setShowForm(true)
  }

  const handleEdit = (camera: any) => {
    setEditingCamera(camera)
    setShowForm(true)
  }

  const handleDelete = (id: string) => {
    if (confirm("Yakin ingin menghapus kamera ini?")) {
      deleteMutation.mutate(id)
    }
  }

  const handleFormClose = () => {
    setShowForm(false)
    setEditingCamera(null)
  }

  const handleFormSave = () => {
    setShowForm(false)
    setEditingCamera(null)
    queryClient.invalidateQueries({ queryKey: ["cameras-list"] })
  }

  const onlineCount = cameras?.filter((c: any) => c.is_online).length || 0
  const offlineCount = cameras?.filter((c: any) => !c.is_online).length || 0

  if (showForm) {
    // Ambil credential dari config_json (disimpan saat kamera dibuat/diupdate)
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
            password: cfg.password || '',   // ← ambil dari config_json, bukan string kosong
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
      <div className="flex items-center gap-4 bg-gray-800 rounded px-4 py-3 flex-shrink-0">
        <span className="text-sm font-medium text-white">Cameras</span>
        <span className="text-xs text-green-400">{onlineCount} online</span>
        <span className="text-xs text-red-400">{offlineCount} offline</span>
        <span className="text-xs text-gray-400 ml-auto">{cameras?.length || 0} total</span>
        <button
          onClick={handleAdd}
          className="ml-4 px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-xs text-white"
        >
          + Add Camera
        </button>
      </div>

      <div className="flex-1 overflow-auto bg-gray-900 rounded">
        {isLoading ? (
          <div className="flex items-center justify-center h-full text-gray-500">Loading...</div>
        ) : !cameras?.length ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-500 gap-2">
            <div className="text-4xl">📷</div>
            <div className="text-sm">Belum ada kamera. Klik &quot;+ Add Camera&quot; untuk menambahkan.</div>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-800 sticky top-0">
              <tr>
                <th className="text-left px-4 py-2 text-gray-300">ID</th>
                <th className="text-left px-4 py-2 text-gray-300">Name</th>
                <th className="text-left px-4 py-2 text-gray-300">Location</th>
                <th className="text-left px-4 py-2 text-gray-300">Status</th>
                <th className="text-left px-4 py-2 text-gray-300">Storage</th>
                <th className="text-left px-4 py-2 text-gray-300">Motion</th>
                <th className="text-left px-4 py-2 text-gray-300">Retention</th>
                <th className="text-left px-4 py-2 text-gray-300">Actions</th>
              </tr>
            </thead>
            <tbody>
              {cameras.map((camera: any) => (
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
