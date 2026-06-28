import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { CameraForm } from "@/components/camera/CameraForm"
import type { Camera } from "@/types"

export default function CamerasPage() {
  const [showForm, setShowForm] = useState(false)
  const [editingCamera, setEditingCamera] = useState<Camera | null>(null)
  const queryClient = useQueryClient()

  const { data: cameras, isLoading } = useQuery({ 
    queryKey: ["cameras"], 
    queryFn: async () => {
      const response = await fetch('/api/v1/config/cameras')
      if (!response.ok) throw new Error('Failed to fetch cameras')
      const data = await response.json()
      return data.data?.cameras || []
    }
  })

  const { data: storageDrives } = useQuery({
    queryKey: ["storage-drives"],
    queryFn: async () => {
      const response = await fetch('/api/v1/storage/status')
      if (!response.ok) throw new Error('Failed to fetch storage drives')
      const data = await response.json()
      return data.drives?.map((d: any) => d.path) || []
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      const response = await fetch(`/api/v1/config/cameras/${id}`, {
        method: 'DELETE',
      })
      if (!response.ok) throw new Error('Failed to delete camera')
      return response.json()
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["cameras"] })
  })

  const handleAdd = () => {
    setEditingCamera(null)
    setShowForm(true)
  }

  const handleEdit = (camera: Camera) => {
    setEditingCamera(camera)
    setShowForm(true)
  }

  const handleDelete = (id: string) => {
    if (confirm("Are you sure you want to delete this camera?")) {
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
    queryClient.invalidateQueries({ queryKey: ["cameras"] })
  }

  const onlineCount = cameras?.filter((c: any) => c.is_online).length || 0
  const offlineCount = cameras?.filter((c: any) => !c.is_online).length || 0

  if (showForm) {
    return (
      <div className="flex flex-col h-full p-4">
        <CameraForm
          initialData={editingCamera ? {
            id: editingCamera.id,
            name: editingCamera.name,
            location: editingCamera.location,
            ip_address: editingCamera.rtsp_main?.match(/@([^:]+):/)?.[1] || '',
            port: 554,
            username: 'admin',
            password: '',
            channel: 1,
            storage_drive: editingCamera.storage_drive,
            motion_enabled: editingCamera.motion_enabled,
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
              {cameras?.map((camera: any) => (
                <tr key={camera.id} className="border-b border-gray-800 hover:bg-gray-800/50">
                  <td className="px-4 py-2 text-gray-300">{camera.id}</td>
                  <td className="px-4 py-2 text-white">{camera.name}</td>
                  <td className="px-4 py-2 text-gray-400">{camera.location || "-"}</td>
                  <td className="px-4 py-2">
                    <span className={camera.is_online ? "text-green-400" : "text-red-400"}>
                      {camera.is_online ? "Online" : "Offline"}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-gray-300">{camera.storage_drive}</td>
                  <td className="px-4 py-2">
                    <span className={camera.motion_enabled ? "text-green-400" : "text-gray-500"}>
                      {camera.motion_enabled ? "Enabled" : "Disabled"}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-gray-400">{camera.retention_days || 30} days</td>
                  <td className="px-4 py-2">
                    <button onClick={() => handleEdit(camera)} className="text-blue-400 hover:underline mr-2">Edit</button>
                    <button onClick={() => handleDelete(camera.id)} className="text-red-400 hover:underline">Delete</button>
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
