import { useQuery, useMutation } from "@tanstack/react-query"
import { storageApi } from "@/api/storage"
import type { DriveStatus } from "@/types"
import { useEffect } from 'react'

export default function StoragePage() {
  const { data: storage, isLoading, refetch } = useQuery({
    queryKey: ["storage"],
    queryFn: storageApi.getStatus,
    refetchInterval: 30000
  })

  const cleanupMutation = useMutation({
    mutationFn: storageApi.manualCleanup,
  })

  useEffect(() => {
    if (cleanupMutation.isSuccess) {
      refetch()
    }
  }, [cleanupMutation.isSuccess, refetch])

  const handleCleanup = (drive: string) => {
    if (confirm(`Run cleanup on ${drive}? This will delete old unprotected recordings.`)) {
      cleanupMutation.mutate()
    }
  }

  const getUsageColor = (freePct: number) => {
    if (freePct < 10) return "text-red-500"
    if (freePct < 20) return "text-yellow-500"
    return "text-green-500"
  }

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 B"
    const k = 1024
    const sizes = ["B", "KB", "MB", "GB", "TB"]
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i]
  }

  return (
    <div className="flex flex-col h-full p-4 gap-4">
      <div className="flex items-center gap-4 bg-gray-800 rounded px-4 py-3 flex-shrink-0">
        <span className="text-sm font-medium">Storage Status</span>
        <button 
          onClick={() => cleanupMutation.mutate()}
          disabled={cleanupMutation.isPending}
          className="ml-auto px-3 py-1 bg-red-600 hover:bg-red-700 disabled:bg-gray-600 rounded text-sm"
        >
          {cleanupMutation.isPending ? "Cleaning..." : "Run Cleanup All"}
        </button>
      </div>

      <div className="flex-1 overflow-auto bg-gray-900 rounded">
        {isLoading ? (
          <div className="flex items-center justify-center h-full text-gray-500">Loading...</div>
        ) : !storage?.drives || storage.drives.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-500">No drives configured</div>
        ) : (
          <div className="p-4 grid gap-4">
            {storage.drives.map((drive: DriveStatus) => (
              <div key={drive.path} className="bg-gray-800 rounded p-4">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h3 className="font-medium">{drive.path}</h3>
                    <p className="text-xs text-gray-400">{drive.camera_count} cameras</p>
                  </div>
                  <div className="text-right">
                    <p className={`text-lg font-medium ${getUsageColor(drive.free_pct)}`}>
                      {drive.free_pct.toFixed(1)}% free
                    </p>
                    <p className="text-xs text-gray-400">
                      {formatBytes(drive.free_bytes)} / {formatBytes(drive.total_bytes)}
                    </p>
                  </div>
                </div>
                
                <div className="w-full bg-gray-700 rounded-full h-2 mb-3">
                  <div 
                    className={`h-2 rounded-full ${drive.free_pct < 10 ? "bg-red-500" : drive.free_pct < 20 ? "bg-yellow-500" : "bg-green-500"}`}
                    style={{ width: `${drive.free_pct}%` }}
                  />
                </div>

                <div className="flex gap-4 text-xs text-gray-400">
                  <span>Used: {formatBytes(drive.used_bytes)}</span>
                  <span>Threshold: {storage.threshold_pct}%</span>
                </div>

                <button 
                  onClick={() => handleCleanup(drive.path)}
                  className="mt-3 px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded text-xs"
                >
                  Cleanup {drive.path}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
