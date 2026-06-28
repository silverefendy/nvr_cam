import React, { useState } from 'react'
import { useQuery } from "@tanstack/react-query"
import { camerasApi } from "@/api/cameras"
import { recordingsApi } from "@/api/recordings"

export default function PlaybackPage() {
  const [camId, setCamId] = useState("")
  const [date, setDate] = useState(new Date().toISOString().split("T")[0])
  const [playUrl, setPlayUrl] = useState<string | null>(null)
  const [selectedHour, setSelectedHour] = useState<number | null>(null)
  
  const { data: cameras } = useQuery({ queryKey: ["cameras"], queryFn: camerasApi.list })
  const { data: recs } = useQuery({
    queryKey: ["recs", camId, date],
    queryFn: () => recordingsApi.list({ camera_id: camId, date: date }),
    enabled: !!camId
  })
  const { data: timeline } = useQuery({
    queryKey: ["timeline", camId, date],
    queryFn: () => recordingsApi.getTimeline(camId, date),
    enabled: !!camId
  })

  const filteredRecs = selectedHour !== null 
    ? recs?.filter(r => new Date(r.started_at).getHours() === selectedHour)
    : recs

  return (
    <div className="flex flex-col h-full gap-2 p-2">
      <div className="flex items-center gap-2 bg-gray-800 rounded px-3 py-2 flex-shrink-0">
        <select value={camId} onChange={e => setCamId(e.target.value)} className="bg-gray-700 rounded px-3 py-1.5 border border-gray-600 text-sm">
          <option value="">-- Select Camera --</option>
          {cameras?.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <input type="date" value={date} onChange={e => setDate(e.target.value)} className="bg-gray-700 rounded px-3 py-1.5 border border-gray-600 text-sm" />
        {selectedHour !== null && (
          <button onClick={() => setSelectedHour(null)} className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded text-sm">
            Clear Filter: {selectedHour}:00
          </button>
        )}
      </div>

      {/* Timeline */}
      {timeline && (
        <div className="bg-gray-800 rounded p-2 flex-shrink-0">
          <div className="flex gap-1 overflow-x-auto">
            {timeline.timeline.map((block: any) => (
              <button
                key={block.hour}
                onClick={() => setSelectedHour(block.hour)}
                className={`flex-shrink-0 w-12 h-12 rounded flex flex-col items-center justify-center text-xs ${
                  selectedHour === block.hour ? "bg-blue-600" : "bg-gray-700 hover:bg-gray-600"
                }`}
              >
                <span>{block.hour}:00</span>
                <div className="flex gap-1 mt-1">
                  {block.has_recording && <span className="w-2 h-2 bg-green-500 rounded-full" />}
                  {block.has_motion && <span className="w-2 h-2 bg-yellow-500 rounded-full" />}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="flex-1 flex gap-2 overflow-hidden">
        {/* Recordings List */}
        <div className="w-64 flex flex-col gap-2 bg-gray-800 rounded p-2 overflow-hidden">
          <div className="text-xs text-gray-400 mb-1">
            {filteredRecs?.length || 0} recording{filteredRecs?.length !== 1 ? 's' : ''}
          </div>
          <div className="flex-1 overflow-y-auto space-y-1">
            {filteredRecs?.map(r => (
              <button
                key={r.id}
                onClick={() => setPlayUrl(recordingsApi.playUrl(r.id))}
                className="w-full text-left p-2 rounded bg-gray-700 hover:bg-gray-600 text-xs text-white"
              >
                <div className="font-medium">{new Date(r.started_at).toLocaleTimeString()}</div>
                <div className="text-gray-400">
                  {r.codec} · {r.file_size_mb?.toFixed(0)} MB
                  {r.is_protected && <span className="ml-1 text-yellow-400">🔒</span>}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Video Player */}
        <div className="flex-1 bg-black rounded overflow-hidden">
          {playUrl ? (
            <video src={playUrl} controls autoPlay className="w-full h-full" />
          ) : (
            <div className="h-full flex items-center justify-center text-gray-500 text-sm">
              Select a recording to play
            </div>
          )}
        </div>
      </div>
    </div>
  )
}