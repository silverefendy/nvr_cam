import { useQuery } from "@tanstack/react-query"
import { systemApi } from "@/api/system"

export default function SystemPage() {
  const { data: health, isLoading, refetch } = useQuery({
    queryKey: ["system-health"],
    queryFn: systemApi.getHealth,
    refetchInterval: 5000
  })

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400)
    const hours = Math.floor((seconds % 86400) / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return `${days}h ${hours}j ${minutes}m`
  }

  const barColor = (pct: number) =>
    pct > 80 ? "bg-red-500" : pct > 60 ? "bg-amber-400" : "bg-emerald-500"

  const badgeColor = (status: string) => {
    switch(status) {
      case "healthy": case "running": return "bg-emerald-100 text-emerald-700 border border-emerald-300"
      case "warning": return "bg-amber-100 text-amber-700 border border-amber-300"
      default: return "bg-red-100 text-red-700 border border-red-300"
    }
  }

  return (
    <div className="flex flex-col h-full p-4 gap-4 bg-slate-100">
      {/* Header */}
      <div className="flex items-center gap-3 bg-white border border-slate-200 rounded-xl px-5 py-3 shadow-sm flex-shrink-0">
        <span className="text-lg">📊</span>
        <span className="text-sm font-semibold text-slate-700">System Health</span>
        <div className="flex-1" />
        <button
          onClick={() => refetch()}
          className="px-4 py-1.5 bg-sky-600 hover:bg-sky-500 text-white rounded-lg text-xs font-medium transition-colors shadow-sm"
        >
          🔄 Refresh
        </button>
      </div>

      <div className="flex-1 overflow-auto">
        {isLoading ? (
          <div className="flex items-center justify-center h-full text-slate-400">
            <div className="text-center">
              <div className="text-3xl mb-2">⏳</div>
              <div className="text-sm">Memuat data sistem...</div>
            </div>
          </div>
        ) : !health ? (
          <div className="flex items-center justify-center h-full text-slate-400">
            <div className="text-center">
              <div className="text-3xl mb-2">⚠️</div>
              <div className="text-sm">Tidak dapat mengambil data sistem</div>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* CPU */}
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-slate-600">🖥️ CPU Usage</h3>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${health.cpu_usage > 80 ? "bg-red-100 text-red-600" : "bg-emerald-100 text-emerald-600"}`}>
                  {health.cpu_usage > 80 ? "Tinggi" : "Normal"}
                </span>
              </div>
              <div className="text-4xl font-bold text-slate-800 mb-3">{health.cpu_usage?.toFixed(1)}%</div>
              <div className="w-full bg-slate-200 rounded-full h-2.5">
                <div className={`h-2.5 rounded-full transition-all ${barColor(health.cpu_usage)}`}
                  style={{ width: `${health.cpu_usage}%` }} />
              </div>
            </div>

            {/* RAM */}
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-slate-600">🧠 RAM Usage</h3>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${health.ram_usage > 80 ? "bg-red-100 text-red-600" : "bg-emerald-100 text-emerald-600"}`}>
                  {health.ram_usage > 80 ? "Tinggi" : "Normal"}
                </span>
              </div>
              <div className="text-4xl font-bold text-slate-800 mb-1">{health.ram_usage?.toFixed(1)}%</div>
              <div className="text-xs text-slate-400 mb-3">
                {health.ram_used_gb?.toFixed(1)} GB / {health.ram_total_gb?.toFixed(1)} GB
              </div>
              <div className="w-full bg-slate-200 rounded-full h-2.5">
                <div className={`h-2.5 rounded-full transition-all ${barColor(health.ram_usage)}`}
                  style={{ width: `${health.ram_usage}%` }} />
              </div>
            </div>

            {/* Disk */}
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-slate-600">💾 Disk Usage</h3>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${health.disk_usage > 80 ? "bg-red-100 text-red-600" : "bg-emerald-100 text-emerald-600"}`}>
                  {health.disk_usage > 80 ? "Penuh" : "Normal"}
                </span>
              </div>
              <div className="text-4xl font-bold text-slate-800 mb-1">{health.disk_usage?.toFixed(1)}%</div>
              <div className="text-xs text-slate-400 mb-3">
                {health.disk_used_gb?.toFixed(1)} GB / {health.disk_total_gb?.toFixed(1)} GB
              </div>
              <div className="w-full bg-slate-200 rounded-full h-2.5">
                <div className={`h-2.5 rounded-full transition-all ${barColor(health.disk_usage)}`}
                  style={{ width: `${health.disk_usage}%` }} />
              </div>
            </div>

            {/* Uptime */}
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
              <h3 className="text-sm font-semibold text-slate-600 mb-3">⏱️ System Uptime</h3>
              <div className="text-4xl font-bold text-slate-800 mb-1">{formatUptime(health.uptime_seconds)}</div>
              <div className="text-xs text-slate-400">Sejak terakhir restart</div>
            </div>

            {/* Kamera */}
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
              <h3 className="text-sm font-semibold text-slate-600 mb-4">📷 Status Kamera</h3>
              <div className="flex gap-6">
                <div className="text-center">
                  <div className="text-3xl font-bold text-emerald-600">{health.cameras_online}</div>
                  <div className="text-xs text-slate-400 mt-1">Online</div>
                </div>
                <div className="w-px bg-slate-200" />
                <div className="text-center">
                  <div className="text-3xl font-bold text-red-500">{health.cameras_offline}</div>
                  <div className="text-xs text-slate-400 mt-1">Offline</div>
                </div>
              </div>
            </div>

            {/* Services */}
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
              <h3 className="text-sm font-semibold text-slate-600 mb-4">⚙️ Services</h3>
              <div className="space-y-2.5">
                {health.services?.map((service: { name: string; status: string }) => (
                  <div key={service.name} className="flex items-center justify-between">
                    <span className="text-sm text-slate-600">{service.name}</span>
                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${badgeColor(service.status)}`}>
                      {service.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
