import React, { useState } from 'react'
import { useQuery } from "@tanstack/react-query"
import { eventsApi } from "@/api/events"
import { camerasApi } from "@/api/cameras"
import type { MotionEvent, Camera } from "@/types"

export default function EventsPage() {
  const [selectedCamera, setSelectedCamera] = useState<string>("")
  const [selectedDate, setSelectedDate] = useState<string>(new Date().toISOString().split('T')[0])
  
  const { data: cameras } = useQuery({ queryKey: ["cameras"], queryFn: camerasApi.list })
  const { data: events, isLoading } = useQuery({
    queryKey: ["events", selectedCamera, selectedDate],
    queryFn: () => eventsApi.list({ camera_id: selectedCamera || undefined, date_from: selectedDate, date_to: selectedDate })
  })

  const filteredEvents = events?.filter(e => 
    !selectedCamera || e.camera_id === selectedCamera
  ) || []

  const getCameraName = (cameraId: string) => {
    return cameras?.find(c => c.id === cameraId)?.name || cameraId
  }

  const getSeverityColor = (severity: number) => {
    switch(severity) {
      case 3: return "bg-red-500"
      case 2: return "bg-yellow-500"
      default: return "bg-blue-500"
    }
  }

  return (
    <div className="flex flex-col h-full p-4 gap-4">
      <div className="flex items-center gap-4 bg-gray-800 rounded px-4 py-3 flex-shrink-0">
        <span className="text-sm font-medium">Motion Events</span>
        <select 
          value={selectedCamera}
          onChange={(e) => setSelectedCamera(e.target.value)}
          className="bg-gray-700 text-sm rounded px-3 py-1.5 border border-gray-600"
        >
          <option value="">All Cameras</option>
          {cameras?.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <input 
          type="date"
          value={selectedDate}
          onChange={(e) => setSelectedDate(e.target.value)}
          className="bg-gray-700 text-sm rounded px-3 py-1.5 border border-gray-600"
        />
        <span className="text-xs text-gray-400 ml-auto">{filteredEvents.length} events</span>
      </div>

      <div className="flex-1 overflow-auto bg-gray-900 rounded">
        {isLoading ? (
          <div className="flex items-center justify-center h-full text-gray-500">Loading...</div>
        ) : filteredEvents.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-500">No motion events found</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-800 sticky top-0">
              <tr>
                <th className="text-left px-4 py-2">Camera</th>
                <th className="text-left px-4 py-2">Zone</th>
                <th className="text-left px-4 py-2">Time</th>
                <th className="text-left px-4 py-2">Duration</th>
                <th className="text-left px-4 py-2">Severity</th>
                <th className="text-left px-4 py-2">Snapshot</th>
              </tr>
            </thead>
            <tbody>
              {filteredEvents.map((event) => (
                <tr key={event.id} className="border-b border-gray-800 hover:bg-gray-800/50">
                  <td className="px-4 py-2">{getCameraName(event.camera_id)}</td>
                  <td className="px-4 py-2">{event.zone_name || "-"}</td>
                  <td className="px-4 py-2">{new Date(event.started_at).toLocaleString()}</td>
                  <td className="px-4 py-2">{event.duration_s ? `${event.duration_s}s` : "-"}</td>
                  <td className="px-4 py-2">
                    <span className={`inline-block w-2 h-2 rounded-full ${getSeverityColor(event.severity)}`}></span>
                  </td>
                  <td className="px-4 py-2">
                    {event.snapshot_url ? (
                      <a href={event.snapshot_url} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">View</a>
                    ) : "-"}
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
