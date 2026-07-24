import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'

interface BackupItem {
  filename: string
  size_mb: number
  created_at: string
}

export const BackupRestore: React.FC = () => {
  const [restoreFile, setRestoreFile] = useState<File | null>(null)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  // Ambil daftar backup yang tersedia
  const { data: backupsData, isLoading, refetch } = useQuery({
    queryKey: ['backups-list'],
    queryFn: async () => {
      const res = await apiClient.get('/config/backups')
      return res.data
    },
  })

  // Buat backup baru
  const createBackupMutation = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post('/config/backup')
      return res.data
    },
    onSuccess: (data) => {
      setMessage({ type: 'success', text: data.message || 'Backup berhasil dibuat.' })
      refetch()
    },
    onError: (error: any) => {
      setMessage({ type: 'error', text: error?.response?.data?.detail || 'Gagal membuat backup.' })
    },
  })

  // Restore dari file upload
  const restoreMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData()
      formData.append('file', file)
      const res = await apiClient.post('/config/restore', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return res.data
    },
    onSuccess: (data) => {
      setMessage({ type: 'success', text: data.message || 'Restore berhasil.' })
      setRestoreFile(null)
    },
    onError: (error: any) => {
      setMessage({ type: 'error', text: error?.response?.data?.detail || 'Gagal melakukan restore.' })
    },
  })

  const handleRestore = () => {
    if (!restoreFile) return
    restoreMutation.mutate(restoreFile)
  }

  const backups: BackupItem[] = backupsData?.data || []

  return (
    <div className="space-y-6">
      {/* Status Message */}
      {message && (
        <div className={`p-3 rounded text-sm ${
          message.type === 'success' ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'
        }`}>
          {message.text}
        </div>
      )}

      {/* Buat Backup */}
      <div className="bg-gray-800 rounded-lg p-4">
        <h3 className="text-lg font-semibold text-white mb-3">Buat Backup</h3>
        <p className="text-sm text-gray-400 mb-4">
          Backup mencakup konfigurasi kamera, pengaturan sistem, dan data notifikasi.
        </p>
        <button
          type="button"
          onClick={() => createBackupMutation.mutate()}
          disabled={createBackupMutation.isPending}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded text-white text-sm"
        >
          {createBackupMutation.isPending ? 'Membuat backup...' : '💾 Buat Backup Sekarang'}
        </button>
      </div>

      {/* Daftar Backup */}
      <div className="bg-gray-800 rounded-lg p-4">
        <h3 className="text-lg font-semibold text-white mb-3">Riwayat Backup</h3>
        {isLoading ? (
          <p className="text-gray-400 text-sm">Memuat daftar backup...</p>
        ) : backups.length === 0 ? (
          <p className="text-gray-500 text-sm italic">Belum ada backup tersedia.</p>
        ) : (
          <div className="space-y-2">
            {backups.map((b) => (
              <div key={b.filename} className="flex items-center justify-between bg-gray-700 rounded px-3 py-2 text-sm">
                <div>
                  <div className="text-white font-mono">{b.filename}</div>
                  <div className="text-gray-400 text-xs">{b.size_mb.toFixed(2)} MB · {new Date(b.created_at).toLocaleString('id-ID')}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Restore */}
      <div className="bg-gray-800 rounded-lg p-4">
        <h3 className="text-lg font-semibold text-white mb-3">Restore dari File</h3>
        <p className="text-sm text-gray-400 mb-4">
          Upload file backup (.zip) untuk mengembalikan konfigurasi sistem.
        </p>
        <div className="flex items-center gap-3">
          <input
            type="file"
            accept=".zip,.tar.gz"
            onChange={(e) => setRestoreFile(e.target.files?.[0] || null)}
            className="text-sm text-gray-300 file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0
              file:text-sm file:font-medium file:bg-gray-600 file:text-white hover:file:bg-gray-500"
          />
          <button
            type="button"
            onClick={handleRestore}
            disabled={!restoreFile || restoreMutation.isPending}
            className="px-4 py-2 bg-orange-600 hover:bg-orange-700 disabled:bg-gray-600 rounded text-white text-sm whitespace-nowrap"
          >
            {restoreMutation.isPending ? 'Merestore...' : '♻️ Restore'}
          </button>
        </div>
      </div>
    </div>
  )
}
