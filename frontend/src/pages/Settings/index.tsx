import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { NotificationForm } from "@/components/settings/NotificationForm"
import { StorageForm } from "@/components/settings/StorageForm"

type TabType = "general" | "notification" | "storage"

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabType>("general")
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null)
  const queryClient = useQueryClient()

  const { data: systemConfig, isLoading: systemLoading } = useQuery({
    queryKey: ["config-system"],
    queryFn: async () => {
      const response = await fetch('/api/v1/config/system')
      if (!response.ok) throw new Error('Failed to fetch system config')
      return response.json()
    },
  })

  const updateSystemMutation = useMutation({
    mutationFn: async (data: Record<string, any>) => {
      const response = await fetch('/api/v1/config/system', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      })
      if (!response.ok) throw new Error('Failed to update system config')
      return response.json()
    },
  })

  const handleSystemSave = (data: Record<string, any>) => {
    updateSystemMutation.mutate(data)
  }

  // Handle mutation success/error
  useEffect(() => {
    if (updateSystemMutation.isSuccess) {
      queryClient.invalidateQueries({ queryKey: ["config-system"] })
      setMessage({ type: "success", text: "System settings saved successfully" })
      setTimeout(() => setMessage(null), 3000)
    }
    if (updateSystemMutation.isError) {
      setMessage({ type: "error", text: "Failed to save system settings" })
      setTimeout(() => setMessage(null), 3000)
    }
  }, [updateSystemMutation.isSuccess, updateSystemMutation.isError, queryClient])

  const renderGeneralSettings = () => {
    if (systemLoading) {
      return <div className="flex items-center justify-center h-full text-gray-500">Loading...</div>
    }

    const config = systemConfig?.data || {}

    return (
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Storage Cleanup Threshold (%)</label>
          <input
            type="number"
            defaultValue={config.storage_threshold_pct || 10}
            onChange={(e) => {
              const data = { storage_threshold_pct: parseFloat(e.target.value) }
              handleSystemSave(data)
            }}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
          />
          <p className="text-xs text-gray-400 mt-1">Cleanup will trigger when free space falls below this percentage</p>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Recording Segment Duration (seconds)</label>
          <input
            type="number"
            defaultValue={config.segment_duration_s || 300}
            onChange={(e) => {
              const data = { segment_duration_s: parseInt(e.target.value) }
              handleSystemSave(data)
            }}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Reconnect Delay (seconds)</label>
          <input
            type="number"
            defaultValue={config.reconnect_delay_s || 5}
            onChange={(e) => {
              const data = { reconnect_delay_s: parseInt(e.target.value) }
              handleSystemSave(data)
            }}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">HLS Segment Duration (seconds)</label>
          <input
            type="number"
            defaultValue={config.hls_segment_duration_s || 2}
            onChange={(e) => {
              const data = { hls_segment_duration_s: parseInt(e.target.value) }
              handleSystemSave(data)
            }}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Motion Frame Skip</label>
          <input
            type="number"
            defaultValue={config.motion_frame_skip || 1}
            onChange={(e) => {
              const data = { motion_frame_skip: parseInt(e.target.value) }
              handleSystemSave(data)
            }}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Motion Cooldown (seconds)</label>
          <input
            type="number"
            defaultValue={config.motion_cooldown_s || 30}
            onChange={(e) => {
              const data = { motion_cooldown_s: parseInt(e.target.value) }
              handleSystemSave(data)
            }}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Motion Threshold (%)</label>
          <input
            type="number"
            defaultValue={config.motion_threshold_pct || 5}
            onChange={(e) => {
              const data = { motion_threshold_pct: parseFloat(e.target.value) }
              handleSystemSave(data)
            }}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
          />
        </div>
        <div className="border-t border-gray-700 pt-4">
          <h3 className="text-lg font-semibold text-white mb-3">AV1 Encoding</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">CRF</label>
              <input
                type="number"
                defaultValue={config.av1_crf || 30}
                onChange={(e) => {
                  const data = { av1_crf: parseInt(e.target.value) }
                  handleSystemSave(data)
                }}
                min="0"
                max="63"
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Preset</label>
              <input
                type="number"
                defaultValue={config.av1_preset || 6}
                onChange={(e) => {
                  const data = { av1_preset: parseInt(e.target.value) }
                  handleSystemSave(data)
                }}
                min="0"
                max="13"
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Schedule Start</label>
              <input
                type="time"
                defaultValue={config.av1_schedule_start || "01:00"}
                onChange={(e) => {
                  const data = { av1_schedule_start: e.target.value }
                  handleSystemSave(data)
                }}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Schedule Stop</label>
              <input
                type="time"
                defaultValue={config.av1_schedule_stop || "05:00"}
                onChange={(e) => {
                  const data = { av1_schedule_stop: e.target.value }
                  handleSystemSave(data)
                }}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Max Parallel Jobs</label>
              <input
                type="number"
                defaultValue={config.av1_max_parallel || 2}
                onChange={(e) => {
                  const data = { av1_max_parallel: parseInt(e.target.value) }
                  handleSystemSave(data)
                }}
                min="1"
                max="8"
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
              />
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full p-4 gap-4">
      <div className="flex items-center gap-4 bg-gray-800 rounded px-4 py-3 flex-shrink-0">
        <span className="text-sm font-medium text-white">Settings</span>
        {message && (
          <span className={`ml-auto text-xs ${message.type === "success" ? "text-green-400" : "text-red-400"}`}>
            {message.text}
          </span>
        )}
      </div>

      <div className="flex gap-4 flex-1 overflow-hidden">
        <div className="w-48 bg-gray-800 rounded p-2 flex-shrink-0">
          <button
            onClick={() => setActiveTab("general")}
            className={`w-full text-left px-3 py-2 rounded text-sm ${activeTab === "general" ? "bg-blue-600" : "hover:bg-gray-700"}`}
          >
            General
          </button>
          <button
            onClick={() => setActiveTab("notification")}
            className={`w-full text-left px-3 py-2 rounded text-sm ${activeTab === "notification" ? "bg-blue-600" : "hover:bg-gray-700"}`}
          >
            Notifications
          </button>
          <button
            onClick={() => setActiveTab("storage")}
            className={`w-full text-left px-3 py-2 rounded text-sm ${activeTab === "storage" ? "bg-blue-600" : "hover:bg-gray-700"}`}
          >
            Storage
          </button>
        </div>

        <div className="flex-1 bg-gray-900 rounded p-4 overflow-auto">
          {activeTab === "general" && renderGeneralSettings()}
          {activeTab === "notification" && <NotificationForm onSave={() => setMessage({ type: "success", text: "Notification settings saved" })} />}
          {activeTab === "storage" && <StorageForm onSave={() => setMessage({ type: "success", text: "Storage configuration saved" })} />}
        </div>
      </div>
    </div>
  )
}
