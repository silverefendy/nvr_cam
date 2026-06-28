import React, { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'

interface DriveAssignment {
  drive: string
  cameras: string[]
}

interface DriveInfo {
  path: string
  total_gb: number
  used_gb: number
  free_gb: number
  used_pct: number
}

interface Props {
  onSave: (data: DriveAssignment[]) => void
}

export const StorageForm: React.FC<Props> = ({ onSave }) => {
  const [assignments, setAssignments] = useState<DriveAssignment[]>([])

  const { data: storageConfig, isLoading } = useQuery({
    queryKey: ['storage-config'],
    queryFn: async () => {
      const response = await fetch('/api/v1/config/storage')
      if (!response.ok) throw new Error('Failed to fetch storage config')
      return response.json()
    },
    onSuccess: (data) => {
      if (data.data?.drive_assignments) {
        setAssignments(data.data.drive_assignments)
      }
    },
  })

  const { data: storageStatus } = useQuery({
    queryKey: ['storage-status'],
    queryFn: async () => {
      const response = await fetch('/api/v1/storage/status')
      if (!response.ok) throw new Error('Failed to fetch storage status')
      return response.json()
    },
  })

  const updateMutation = useMutation({
    mutationFn: async (data: DriveAssignment[]) => {
      const response = await fetch('/api/v1/config/storage', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ drive_assignments: data }),
      })
      if (!response.ok) throw new Error('Failed to update storage config')
      return response.json()
    },
    onSuccess: () => {
      onSave(assignments)
    },
  })

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault()
    updateMutation.mutate(assignments)
  }

  const addCameraToDrive = (driveIndex: number, cameraId: string) => {
    setAssignments(prev => {
      const updated = [...prev]
      if (!updated[driveIndex].cameras.includes(cameraId)) {
        updated[driveIndex].cameras.push(cameraId)
      }
      return updated
    })
  }

  const removeCameraFromDrive = (driveIndex: number, cameraId: string) => {
    setAssignments(prev => {
      const updated = [...prev]
      updated[driveIndex].cameras = updated[driveIndex].cameras.filter(c => c !== cameraId)
      return updated
    })
  }

  const getDriveInfo = (drivePath: string): DriveInfo | null => {
    if (!storageStatus?.drives) return null
    return storageStatus.drives.find((d: DriveInfo) => d.path === drivePath) || null
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8 text-gray-400">
        Loading storage configuration...
      </div>
    )
  }

  return (
    <form onSubmit={handleSave} className="space-y-4">
      {assignments.map((assignment, driveIndex) => {
        const driveInfo = getDriveInfo(assignment.drive)
        const usedPct = driveInfo?.used_pct || 0
        const usedColor = usedPct > 80 ? 'bg-red-500' : usedPct > 60 ? 'bg-yellow-500' : 'bg-green-500'

        return (
          <div key={assignment.drive} className="bg-gray-800 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="text-lg font-semibold text-white">{assignment.drive}</h3>
                {driveInfo && (
                  <div className="text-sm text-gray-400">
                    {driveInfo.total_gb.toFixed(0)} GB total · {usedPct.toFixed(0)}% used
                  </div>
                )}
              </div>
              {driveInfo && (
                <div className="w-32">
                  <div className="w-full bg-gray-700 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${usedColor}`}
                      style={{ width: `${usedPct}%` }}
                    />
                  </div>
                </div>
              )}
            </div>

            <div className="mb-3">
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Assigned Cameras ({assignment.cameras.length})
              </label>
              <div className="flex flex-wrap gap-2">
                {assignment.cameras.map(cameraId => (
                  <div
                    key={cameraId}
                    className="flex items-center gap-2 bg-gray-700 px-3 py-1.5 rounded text-sm text-white"
                  >
                    <span>{cameraId}</span>
                    <button
                      type="button"
                      onClick={() => removeCameraFromDrive(driveIndex, cameraId)}
                      className="text-red-400 hover:text-red-300"
                    >
                      ×
                    </button>
                  </div>
                ))}
                {assignment.cameras.length === 0 && (
                  <span className="text-gray-500 text-sm italic">No cameras assigned</span>
                )}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Add Camera</label>
              <select
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                onChange={(e) => {
                  if (e.target.value) {
                    addCameraToDrive(driveIndex, e.target.value)
                    e.target.value = ''
                  }
                }}
                value=""
              >
                <option value="">Select camera to add...</option>
                {storageStatus?.available_cameras?.map((cameraId: string) => (
                  <option key={cameraId} value={cameraId}>
                    {cameraId}
                  </option>
                ))}
              </select>
            </div>
          </div>
        )
      })}

      <div className="flex justify-end pt-4 border-t border-gray-700">
        <button
          type="submit"
          disabled={updateMutation.isPending}
          className="px-6 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 rounded text-white"
        >
          {updateMutation.isPending ? 'Saving...' : 'Save Storage Configuration'}
        </button>
      </div>

      {updateMutation.error && (
        <div className="bg-red-900/50 text-red-400 p-3 rounded">
          Failed to save: {updateMutation.error instanceof Error ? updateMutation.error.message : 'Unknown error'}
        </div>
      )}
    </form>
  )
}
