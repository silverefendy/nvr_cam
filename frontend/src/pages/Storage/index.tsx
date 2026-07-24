import { useState, useEffect } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { storageApi } from "@/api/storage"
import { useAuthStore } from "@/store/auth"
import type { DriveStatus } from "@/types"

type Tab = "drives" | "cameras" | "schedule"

export default function StoragePage() {
  const [activeTab, setActiveTab]       = useState<Tab>("drives")
  const [schedHour, setSchedHour]       = useState(3)
  const [schedMinute, setSchedMinute]   = useState(0)
  const [schedEnabled, setSchedEnabled] = useState(false)
  const [message, setMessage]           = useState<{ type: "success" | "error"; text: string } | null>(null)
  const queryClient = useQueryClient()
  const { isAuthenticated } = useAuthStore()

  const { data: storage, isLoading, refetch } = useQuery({
    queryKey:        ["storage"],
    queryFn:         storageApi.getStatus,
    enabled:         isAuthenticated,   // jangan fetch sebelum token ada
    refetchInterval: 30000,
  })

  const { data: cameraStats, isLoading: statsLoading } = useQuery({
    queryKey: ["storage-camera-stats"],
    queryFn:  storageApi.getStatsByCamera,
    enabled:  isAuthenticated && activeTab === "cameras",
  })

  const { data: schedule } = useQuery({
    queryKey: ["cleanup-schedule"],
    queryFn:  storageApi.getCleanupSchedule,
    enabled:  isAuthenticated && activeTab === "schedule",
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

  const getUsageColor = (p: number) => p < 10 ? "text-red-600" : p < 25 ? "text-amber-500" : "text-emerald-600"
  const getBarColor   = (p: number) => p < 10 ? "bg-red-500"  : p < 25 ? "bg-amber-400"  : "bg-emerald-500"
  const formatGB = (gb: number) => gb >= 1000 ? `${(gb / 1024).toFixed(1)} TB` : `${gb.toFixed(0)} GB`
  const formatMB = (mb: number) => mb >= 1024  ? `${(mb / 1024).toFixed(2)} GB` : `${mb.toFixed(0)} MB`

  const tabs: { id: Tab; label: string }[] = [
    { id: "drives",   label: "Drive" },
    { id: "cameras",  label: "Per Kamera" },
    { id: "schedule", label: "Jadwal Cleanup" },
  ]

  return (
    <div className="flex flex-col h-full p-4 gap-4 bg-slate-100">

      {/* Header */}
      <div className="flex items-center gap-4 bg-white border border-slate-200 rounded-xl px-4 py-3 shadow-sm flex-shrink-0">
        <h1 className="text-sm font-semibold text-slate-700">Storage</h1>
        {message && (
          <span className={`text-xs font-medium px-3 py-1 rounded-full ${
            message.type === "success"
              ? "bg-emerald-100 text-emerald-700"
              : "bg-red-100 text-red-700"
          }`}>
            {message.text}
          </span>
        )}
        <button
          onClick={handleCleanup}
          disabled={cleanupMutation.isPending}
          className="ml-auto px-3 py-1.5 bg-red-500 hover:bg-red-600 disabled:bg-slate-300 rounded-lg text-white text-xs font-medium transition-colors"
        >
          {cleanupMutation.isPending ? "Cleaning..." : "Cleanup Sekarang"}
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 flex-shrink-0 bg-white border border-slate-200 rounded-xl p-1 shadow-sm w-fit">
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              activeTab === t.id
                ? "bg-sky-600 text-white shadow-sm"
                : "text-slate-500 hover:text-slate-700 hover:bg-slate-100"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">

        {/* Tab: Drive */}
        {activeTab === "drives" && (
          isLoading ? (
            <div className="flex items-center justify-center h-40 text-slate-400 text-sm">Memuat data storage...</div>
          ) : !storage?.drives?.length ? (
            <div className="flex items-center justify-center h-40 text-slate-400 text-sm">Tidak ada drive terkonfigurasi</div>
          ) : (
            <div className="grid gap-4">
              {/* Summary Bar */}
              <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex flex-wrap gap-6 text-sm">
                <div>
                  <p className="text-xs text-slate-400 mb-0.5">Total</p>
                  <p className="font-semibold text-slate-700">{storage.total_tb} TB</p>
                </div>
                <div>
                  <p className="text-xs text-slate-400 mb-0.5">Dipakai</p>
                  <p className="font-semibold text-slate-700">{storage.used_tb} TB</p>
                </div>
                <div>
                  <p className="text-xs text-slate-400 mb-0.5">Sisa</p>
                  <p className={`font-semibold ${storage.free_tb < 1 ? "text-red-600" : "text-emerald-600"}`}>
                    {storage.free_tb} TB
                  </p>
                </div>
                <div>
                  <p className="text-xs text-slate-400 mb-0.5">Estimasi habis</p>
                  <p className="font-semibold text-slate-700">~{storage.estimated_days_remaining} hari</p>
                </div>
              </div>

              {/* Drive Cards */}
              {storage.drives.map((drive: DriveStatus) => (
                <div key={drive.path} className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="font-semibold text-slate-700">{drive.path}</h3>
                      <p className="text-xs text-slate-400 mt-0.5">
                        {drive.cameras?.length ?? 0} kamera terdaftar
                      </p>
                    </div>
                    <div className="text-right">
                      <p className={`text-lg font-bold ${getUsageColor(drive.free_pct)}`}>
                        {drive.free_pct.toFixed(1)}% sisa
                      </p>
                      <p className="text-xs text-slate-400">{formatGB(drive.free_gb)} dari {formatGB(drive.total_gb)}</p>
                    </div>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-2.5 mb-3">
                    <div
                      className={`h-2.5 rounded-full transition-all ${getBarColor(drive.free_pct)}`}
                      style={{ width: `${drive.free_pct}%` }}
                    />
                  </div>
                  <div className="flex items-center gap-3 text-xs text-slate-400">
                    <span>Dipakai: {formatGB(drive.used_gb)}</span>
                    <span>·</span>
                    <span>Threshold: {storage.threshold_pct ?? 10}%</span>
                    {drive.free_pct < (storage.threshold_pct ?? 10) && (
                      <span className="ml-1 px-2 py-0.5 bg-red-100 text-red-600 rounded-full font-medium">
                        Di bawah threshold!
                      </span>
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
            <div className="flex items-center justify-center h-40 text-slate-400 text-sm">Memuat statistik...</div>
          ) : !cameraStats?.length ? (
            <div className="flex items-center justify-center h-40 text-slate-400 text-sm">Tidak ada data kamera</div>
          ) : (
            <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
              <div className="px-4 py-3 border-b border-slate-100">
                <p className="text-xs text-slate-400">{cameraStats.length} kamera · diurutkan dari penggunaan disk terbesar</p>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-slate-400 bg-slate-50 border-b border-slate-100">
                    <th className="px-4 py-2">#</th>
                    <th className="px-4 py-2">Kamera</th>
                    <th className="px-4 py-2">Drive</th>
                    <th className="px-4 py-2 text-right">File</th>
                    <th className="px-4 py-2 text-right">Ukuran</th>
                  </tr>
                </thead>
                <tbody>
                  {cameraStats.map((s: any, i: number) => (
                    <tr key={s.camera_id} className="border-b border-slate-50 hover:bg-slate-50 transition-colors">
                      <td className="px-4 py-2.5 text-slate-400 text-xs">{i + 1}</td>
                      <td className="px-4 py-2.5 font-medium text-slate-700">{s.camera_id}</td>
                      <td className="px-4 py-2.5 text-slate-400 text-xs">{s.drive}</td>
                      <td className="px-4 py-2.5 text-right text-slate-600">{s.file_count}</td>
                      <td className="px-4 py-2.5 text-right">
                        <span className={i < 3 ? "text-amber-600 font-semibold" : "text-slate-600"}>
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
          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm max-w-md space-y-6">
            <div>
              <h2 className="text-base font-semibold text-slate-700 mb-1">Jadwal Cleanup Otomatis</h2>
              <p className="text-xs text-slate-400">
                Cleanup terjadwal menghapus file terlama sesuai waktu yang ditentukan,
                meski disk belum kritis — agar ruang selalu tersedia.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <span className="text-sm text-slate-600">Aktifkan cleanup terjadwal</span>
              <button
                onClick={() => setSchedEnabled(!schedEnabled)}
                className={`relative w-10 h-5 rounded-full transition-colors ${schedEnabled ? "bg-sky-500" : "bg-slate-300"}`}
              >
                <span className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${schedEnabled ? "translate-x-5" : "translate-x-0.5"}`} />
              </button>
            </div>

            <div className={`space-y-4 ${!schedEnabled ? "opacity-40 pointer-events-none" : ""}`}>
              <div>
                <label className="block text-sm text-slate-600 mb-2 font-medium">Jam cleanup (HH : MM)</label>
                <div className="flex items-center gap-2">
                  <input
                    type="number" min={0} max={23} value={schedHour}
                    onChange={e => setSchedHour(Number(e.target.value))}
                    className="w-20 bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-slate-700 text-center focus:outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-200"
                  />
                  <span className="text-slate-400 font-bold">:</span>
                  <input
                    type="number" min={0} max={59} value={schedMinute}
                    onChange={e => setSchedMinute(Number(e.target.value))}
                    className="w-20 bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-slate-700 text-center focus:outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-200"
                  />
                  <span className="text-xs text-slate-400">
                    cron: {String(schedMinute).padStart(2,'0')} {String(schedHour).padStart(2,'0')} * * *
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-1">Disarankan jam 03:00 saat beban rendah</p>
              </div>
            </div>

            <button
              onClick={() => scheduleMutation.mutate({ enabled: schedEnabled, hour: schedHour, minute: schedMinute })}
              disabled={scheduleMutation.isPending}
              className="px-4 py-2 bg-sky-600 hover:bg-sky-500 disabled:bg-slate-300 rounded-lg text-white text-sm font-medium transition-colors"
            >
              {scheduleMutation.isPending ? "Menyimpan..." : "Simpan Jadwal"}
            </button>

            {schedule && (
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-xs text-slate-500 space-y-1">
                <p>Status: <span className={schedule.enabled ? "text-emerald-600 font-medium" : "text-slate-400"}>{schedule.enabled ? "Aktif" : "Nonaktif"}</span></p>
                <p>Cron: <code className="text-slate-600 bg-slate-100 px-1 rounded">{schedule.cron}</code></p>
                <p className="text-amber-500 pt-1">Berlaku setelah backend di-restart.</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
