import React, { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'

interface BackupInfo {
  filename: string
  created_at: string
  size_bytes: number
}

interface Props {
  onSave: () => void
}

export const BackupRestore: React.FC<Props> = ({ onSave }) => {
  const [uploadFile, setUploadFile] = useState<File | null>(null)

  const { data: backups, isLoading } = useQuery({
    queryKey: ['config-backups'],
    queryFn: async () => {
      const response = await fetch('/api/v1/config/backups')
      if (!response.ok) throw new Error('Failed to fetch backups')
      return response.json()
    },
  })

  const downloadMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch('/api/v1/config/backup')
      if (!response.ok) throw new Error('Failed to download backup')
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5)
      a.download = `nvr_backup_${timestamp}.zip`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    },
    onSuccess: () => {
      onSave()
    },
  })

  const restoreMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData()
      formData.append('file', file)
      const response = await fetch('/api/v1/config/restore', {
        method: 'POST',
        body: formData,
      })
      if (!response.ok) throw new Error('Failed to restore backup')
      return response.json()
    },
    onSuccess: () => {
      onSave()
      setUploadFile(null)
    },
  })

  const handleDownload = () => {
    downloadMutation.mutate()
  }

  const handleRestore = (e: React.FormEvent) => {
    e.preventDefault()
    if (uploadFile) {
      if (confirm('This will replace all current settings. Are you sure?')) {
        restoreMutation.mutate(uploadFile)
      }
    }
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString)
    return date.toLocaleString()
  }

  return (
    <div className="space-y-6">
      {/* Download Backup */}
      <div className="bg-gray-800 rounded-lg p-4">
        <h3 className="text-lg font-semibold text-white mb-3">Download Backup</h3>
        <p className="text-sm text-gray-400 mb-4">
          Download a complete backup of all configuration files (cameras, system settings, storage, notifications).
        </p>
        <button
          onClick={handleDownload}
          disabled={downloadMutation.isPending}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded text-white"
        >
          {downloadMutation.isPending ? 'Downloading...' : 'Download Backup'}
        </button>
      </div>

      {/* Restore Backup */}
      <div className="bg-gray-800 rounded-lg p-4">
        <h3 className="text-lg font-semibold text-white mb-3">Restore Backup</h3>
        <p className="text-sm text-gray-400 mb-4">
          Upload a previously downloaded backup ZIP file to restore all configurations.
        </p>
        <form onSubmit={handleRestore} className="space-y-3">
          <div>
            <input
              type="file"
              accept=".zip"
              onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            />
          </div>
          <button
            type="submit"
            disabled={!uploadFile || restoreMutation.isPending}
            className="px-4 py-2 bg-orange-600 hover:bg-orange-700 disabled:bg-gray-600 rounded text-white"
          >
            {restoreMutation.isPending ? 'Restoring...' : 'Restore Backup'}
          </button>
        </form>
        {restoreMutation.error && (
          <div className="mt-3 text-red-400 text-sm">
            Failed to restore: {restoreMutation.error instanceof Error ? restoreMutation.error.message : 'Unknown error'}
          </div>
        )}
      </div>

      {/* Backup History */}
      <div className="bg-gray-800 rounded-lg p-4">
        <h3 className="text-lg font-semibold text-white mb-3">Automatic Backups</h3>
        <p className="text-sm text-gray-400 mb-4">
          The system automatically creates backups before each configuration change. Last 5 backups are kept.
        </p>
        {isLoading ? (
          <div className="text-gray-500 text-sm">Loading backups...</div>
        ) : backups?.backups?.length > 0 ? (
          <div className="space-y-2">
            {backups.backups.map((backup: BackupInfo) => (
              <div
                key={backup.filename}
                className="flex items-center justify-between bg-gray-700 rounded px-3 py-2 text-sm"
              >
                <div className="text-gray-300">
                  <div className="font-medium">{backup.filename}</div>
                  <div className="text-xs text-gray-400">
                    {formatDate(backup.created_at)} · {formatFileSize(backup.size_bytes)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-gray-500 text-sm">No automatic backups available</div>
        )}
      </div>
    </div>
  )
}
