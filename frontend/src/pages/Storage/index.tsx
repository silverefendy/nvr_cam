import { useState, useEffect } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { storageApi } from "@/api/storage"
import type { DriveStatus } from "@/types"

type Tab = "drives" | "cameras" | "schedule"

export default function StoragePage() {
  const [activeTab, setActiveTab]       = useState<Tab>("drives")
  const [schedHour, setSchedHour]       = useState(3)
  const [schedMinute, setSchedMinute]   = useState(0)
  const [schedEnabled, setSchedEnabled] = useState(false)
  const [message, setMessage]           = useState<{ type: "success" | "error"; text: string } | null>(null)
  const queryClient = useQueryClient()

  const { data: storage, isLoading, refetch } = useQuery({
    queryKey:        ["storage"],
    queryFn:         storageApi.getStatus,
    refetchInterval: 30000,
  })

  const { data: cameraStats, isLoading: statsLoading } = useQuery({
    queryKey: ["storage-camera-stats"],
    queryFn:  storageApi.getStatsByCamera,
    enabled:  activeTab === "cameras",
  })

  const { data: schedule } = useQuery({
    queryKey: ["cleanup-schedule"],
    queryFn:  storageApi.getCleanupSchedule,
    enabled:  activeTab === "schedule",
  })

  useEffect(() => {
    if (schedule) {
      setSchedEnabled(schedule.enabled ?? false)
      setSchedHour(schedule.hour ?? 3)
      setSchedMinute(schedule.minute ?? 0)
    }
  }, [schedule])

  const showMsg = (type: "success" | "error", text: string) => {
    setMessage({ type, text })
    setTimeout(() => setMessage(null), 3000)
  }

  const cleanupMutation = useMutation({
    mutationFn: storageApi.manualCleanup,
    onSuccess:  () => { refetch(); showMsg("success", "Cleanup selesai dijalankan") },
    onError:    () => showMsg("error", "Cleanup gagal"),
  })

  const scheduleMutation = useMutation({
    mutationFn: storageApi.saveCleanupSchedule,
    onSuccess:  () => {
      queryClient.invalidateQueries({ queryKey: ["cleanup-schedule"] })
      showMsg("success", "Jadwal cleanup disimpan")
    },
    onError: () => showMsg("error", "Gagal menyimpan jadwal"),
  })

  const handleCleanup = () => {
    if (confirm("Jalankan cleanup sekarang? File terlama yang tidak diprotect akan dihapus.")) {
      cleanupMutation.mutate()
    }
  }

  const getUsageColor = (p: number) => p < 10 ? "text-red-500" : p < 20 ? "text-yellow-500" : "text-green-500"
  const getBarColor   = (p: number) => p < 10 ? "bg-red-500"  : p < 20 ? "bg-yellow-500"  : "bg-green-500"
  const formatGB = (gb: number) => gb >= 1000 ? `${(gb / 1024).toFixed(1)} TB` : `${gb.toFixed(0)} GB`
  const formatMB = (mb: number) => mb >= 1024  ? `${(mb / 1024).toFixed(2)} GB` : `${mb.toFixed(0)} MB`

  const tabs: { id: Tab; label: string }[] = [
    { id: "drives",   label: "📀 Drive" },
    { id: "cameras",  label: "📷 Per Kamera" },
    { id: "schedule", label: "⏰ Jadwal Cleanup" },
  ]

  return (
    <div className="flex flex-col h-full p-4 gap-4">
      <div className="flex items-center gap-4 bg-gray-800 rounded px-4 py-3 flex-shrink-0">
        <span className="text-sm font-medium">Storage</span>
        {message && (
          <span className={`text-xs ${message.type === "success" ? "text-green-400" : "text-red-400"}`}>
            {message.text}
          </span>
        )}
        <button
          onClick={handleCleanup}
          disabled={cleanupMutation.isPending}
          className="ml-auto px-3 py-1 bg-red-600 hover:bg-red-700 disabled:bg-gray-600 rounded text-sm"
        >
          {cleanupMutation.isPending ? "Cleaning..." : "🧹 Cleanup Sekarang"}
        </button>
      </div>

      <div className="flex gap-1 flex-shrink-0">
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={`px-4 py-2 rounded text-sm ${activeTab === t.id ? "bg-blue-600 text-white" : "bg-gray-800 hover:bg-gray-700 text-gray-300"}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-auto bg-gray-900 rounded p-4">

        {/* Tab: Drive */}
        {activeTab === "drives" && (
          isLoading ? (
            <div className="flex items-center justify-center h-full text-gray-500">Loading...</div>
          ) : !storage?.drives?.length ? (
            <div className="flex items-center justify-center h-full text-gray-500">Tidak ada drive terkonfigurasi</div>
          ) : (
            <div className="grid gap-4">
              <div className="bg-gray-800 rounded p-3 flex gap-6 text-sm">
                <span>Total: <b>{storage.total_tb} TB</b></span>
                <span>Dipakai: <b>{storage.used_tb} TB</b></span>
                <span className={storage.free_tb < 1 ? "text-red-400" : "text-green-400"}>
                  Sisa: <b>{storage.free_tb} TB</b>
                </span>
                <span className="text-gray-400">Est. habis: ~{storage.estimated_days_remaining} hari</span>
              </div>
              {storage.drives.map((drive: DriveStatus) => (
                <div key={drive.path} className="bg-gray-800 rounded p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <h3 className="font-medium">{drive.path}</h3>
                      <p className="text-xs text-gray-400">{drive.camera_count ?? drive.cameras?.length ?? 0} kamera</p>
                    </div>
                    <div className="text-right">
                      <p className={`text-lg font-medium ${getUsageColor(drive.free_pct)}`}>
                        {drive.free_pct.toFixed(1)}% sisa
                      </p>
                      <p className="text-xs text-gray-400">{formatGB(drive.free_gb)} / {formatGB(drive.total_gb)}</p>
                    </div>
                  </div>
                  <div className="w-full bg-gray-700 rounded-full h-2 mb-3">
                    <div className={`h-2 rounded-full transition-all ${getBarColor(drive.free_pct)}`} style={{ width: `${drive.free_pct}%` }} />
                  </div>
                  <div className="text-xs text-gray-400">
                    Dipakai: {formatGB(drive.used_gb)} · Threshold: {storage.threshold_pct ?? 10}%
                    {drive.free_pct < (storage.threshold_pct ?? 10) && (
                      <span className="ml-2 text-red-400 font-medium">⚠ Di bawah threshold!</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )
        )}

        {/* Tab: Per Kamera */}
        {activeTab === "cameras" && (
          statsLoading ? (
            <div className="flex items-center justify-center h-full text-gray-500">Loading...</div>
          ) : !cameraStats?.length ? (
            <div className="flex items-center justify-center h-full text-gray-500">Tidak ada data</div>
          ) : (
            <div>
              <p className="text-xs text-gray-400 mb-3">
                {cameraStats.length} kamera · diurutkan dari penggunaan disk terbesar
              </p>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-gray-400 border-b border-gray-700">
                    <th className="pb-2 pr-4">#</th>
                    <th className="pb-2 pr-4">Kamera</th>
                    <th className="pb-2 pr-4">Drive</th>
                    <th className="pb-2 pr-4 text-right">File</th>
                    <th className="pb-2 text-right">Ukuran</th>
                  </tr>
                </thead>
                <tbody>
                  {cameraStats.map((s: any, i: number) => (
                    <tr key={s.camera_id} className="border-b border-gray-800 hover:bg-gray-800/50">
                      <td className="py-2 pr-4 text-gray-500">{i + 1}</td>
                      <td className="py-2 pr-4 font-medium">{s.camera_id}</td>
                      <td className="py-2 pr-4 text-gray-400 text-xs">{s.drive}</td>
                      <td className="py-2 pr-4 text-right text-gray-300">{s.file_count}</td>
                      <td className="py-2 text-right">
                        <span className={i < 3 ? "text-yellow-400 font-medium" : "text-gray-300"}>
                          {formatMB(s.total_mb)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        )}

        {/* Tab: Jadwal Cleanup */}
        {activeTab === "schedule" && (
          <div className="max-w-md space-y-6">
            <div>
              <h2 className="text-base font-semibold text-white mb-1">Jadwal Cleanup Otomatis</h2>
              <p className="text-xs text-gray-400">
                Cleanup terjadwal menghapus file terlama sesuai waktu yang ditentukan,
                meski disk belum kritis — agar ruang selalu tersedia.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-300">Aktifkan cleanup terjadwal</span>
              <button
                onClick={() => setSchedEnabled(!schedEnabled)}
                className={`relative w-10 h-5 rounded-full transition-colors ${schedEnabled ? "bg-blue-600" : "bg-gray-600"}`}
              >
                <span className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${schedEnabled ? "translate-x-5" : "translate-x-0.5"}`} />
              </button>
            </div>

            <div className={`space-y-4 ${!schedEnabled ? "opacity-40 pointer-events-none" : ""}`}>
              <div>
                <label className="block text-sm text-gray-300 mb-1">Jam cleanup (HH : MM)</label>
                <div className="flex items-center gap-2">
                  <input
                    type="number" min={0} max={23} value={schedHour}
                    onChange={e => setSchedHour(Number(e.target.value))}
                    className="w-20 bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-center"
                  />
                  <span className="text-gray-400 font-bold">:</span>
                  <input
                    type="number" min={0} max={59} value={schedMinute}
                    onChange={e => setSchedMinute(Number(e.target.value))}
                    className="w-20 bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-center"
                  />
                  <span className="text-xs text-gray-500">
                    cron: {String(schedMinute).padStart(2,'0')} {String(schedHour).padStart(2,'0')} * * *
                  </span>
                </div>
                <p className="text-xs text-gray-500 mt-1">Disarankan jam 03:00 saat beban rendah</p>
              </div>
            </div>

            <button
              onClick={() => scheduleMutation.mutate({ enabled: schedEnabled, hour: schedHour, minute: schedMinute })}
              disabled={scheduleMutation.isPending}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded text-sm"
            >
              {scheduleMutation.isPending ? "Menyimpan..." : "Simpan Jadwal"}
            </button>

            {schedule && (
              <div className="bg-gray-800 rounded p-3 text-xs text-gray-400 space-y-1">
                <p>Status: <span className={schedule.enabled ? "text-green-400" : "text-gray-500"}>{schedule.enabled ? "✅ Aktif" : "⏸ Nonaktif"}</span></p>
                <p>Cron: <code className="text-gray-300">{schedule.cron}</code></p>
                <p className="text-yellow-400/70 pt-1">⚠ Berlaku setelah backend di-restart.</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}