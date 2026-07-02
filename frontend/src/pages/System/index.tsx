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
    return `${days}d ${hours}h ${minutes}m`
  }

  const getStatusBadge = (status: string) => {
    switch(status) {
      case "healthy": return "bg-green-600"
      case "warning": return "bg-yellow-600"
      case "error": return "bg-red-600"
      default: return "bg-gray-600"
    }
  }

  return (
    <div className="flex flex-col h-full p-4 gap-4">
      <div className="flex items-center gap-4 bg-gray-800 rounded px-4 py-3 flex-shrink-0">
        <span className="text-sm font-medium">System Health</span>
        <button onClick={() => refetch()} className="ml-auto px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded text-sm">
          Refresh
        </button>
      </div>

      <div className="flex-1 overflow-auto bg-gray-900 rounded p-4">
        {isLoading ? (
          <div className="flex items-center justify-center h-full text-gray-500">Loading...</div>
        ) : !health ? (
          <div className="flex items-center justify-center h-full text-gray-500">Unable to fetch system health</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* CPU Usage */}
            <div className="bg-gray-800 rounded p-4">
              <h3 className="font-medium mb-3">CPU Usage</h3>
              <div className="text-3xl font-bold mb-2">{health.cpu_usage.toFixed(1)}%</div>
              <div className="w-full bg-gray-700 rounded-full h-2">
                <div 
                  className={`h-2 rounded-full ${health.cpu_usage > 80 ? "bg-red-500" : health.cpu_usage > 60 ? "bg-yellow-500" : "bg-green-500"}`}
                  style={{ width: `${health.cpu_usage}%` }}
                />
              </div>
            </div>

            {/* RAM Usage */}
            <div className="bg-gray-800 rounded p-4">
              <h3 className="font-medium mb-3">RAM Usage</h3>
              <div className="text-3xl font-bold mb-2">{health.ram_usage.toFixed(1)}%</div>
              <div className="text-xs text-gray-400 mb-2">
                {health.ram_used_gb.toFixed(1)} GB / {health.ram_total_gb.toFixed(1)} GB
              </div>
              <div className="w-full bg-gray-700 rounded-full h-2">
                <div 
                  className={`h-2 rounded-full ${health.ram_usage > 80 ? "bg-red-500" : health.ram_usage > 60 ? "bg-yellow-500" : "bg-green-500"}`}
                  style={{ width: `${health.ram_usage}%` }}
                />
              </div>
            </div>

            {/* Disk Usage */}
            <div className="bg-gray-800 rounded p-4">
              <h3 className="font-medium mb-3">Disk Usage</h3>
              <div className="text-3xl font-bold mb-2">{health.disk_usage.toFixed(1)}%</div>
              <div className="text-xs text-gray-400 mb-2">
                {health.disk_used_gb.toFixed(1)} GB / {health.disk_total_gb.toFixed(1)} GB
              </div>
              <div className="w-full bg-gray-700 rounded-full h-2">
                <div 
                  className={`h-2 rounded-full ${health.disk_usage > 80 ? "bg-red-500" : health.disk_usage > 60 ? "bg-yellow-500" : "bg-green-500"}`}
                  style={{ width: `${health.disk_usage}%` }}
                />
              </div>
            </div>

            {/* System Uptime */}
            <div className="bg-gray-800 rounded p-4">
              <h3 className="font-medium mb-3">System Uptime</h3>
              <div className="text-3xl font-bold mb-2">{formatUptime(health.uptime_seconds)}</div>
              <div className="text-xs text-gray-400">Since last reboot</div>
            </div>

            {/* Camera Status */}
            <div className="bg-gray-800 rounded p-4">
              <h3 className="font-medium mb-3">Camera Status</h3>
              <div className="flex gap-4">
                <div>
                  <div className="text-2xl font-bold text-green-400">{health.cameras_online}</div>
                  <div className="text-xs text-gray-400">Online</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-red-400">{health.cameras_offline}</div>
                  <div className="text-xs text-gray-400">Offline</div>
                </div>
              </div>
            </div>

            {/* Service Status */}
            <div className="bg-gray-800 rounded p-4">
              <h3 className="font-medium mb-3">Services</h3>
              <div className="space-y-2">
                {health.services?.map((service) => (
                  <div key={service.name} className="flex items-center justify-between">
                    <span className="text-sm">{service.name}</span>
                    <span className={`px-2 py-0.5 rounded text-xs ${getStatusBadge(service.status)}`}>
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
