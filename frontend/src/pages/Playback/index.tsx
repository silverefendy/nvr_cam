import React, { useState } from 'react'
import { useQuery } from "@tanstack/react-query"
import { camerasApi } from "@/api/cameras"
import { recordingsApi } from "@/api/recordings"
export default function PlaybackPage() {
  const [camId, setCamId] = useState("")
  const [date, setDate] = useState(new Date().toISOString().split("T")[0])
  const [playUrl, setPlayUrl] = useState<string|null>(null)
  const { data: cameras } = useQuery({ queryKey:["cameras"], queryFn: camerasApi.list })
  const { data: recs } = useQuery({ queryKey:["recs",camId,date], queryFn: () => recordingsApi.list({ camera_id:camId, date_from:`${date}T00:00:00Z`, date_to:`${date}T23:59:59Z` }), enabled:!!camId })
  return (
    <div className="flex h-full gap-2 p-2">
      <div className="w-60 flex flex-col gap-2">
        <select value={camId} onChange={e=>setCamId(e.target.value)} className="w-full p-2 rounded bg-gray-700 text-white text-sm">
          <option value="">-- Pilih Kamera --</option>
          {cameras?.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <input type="date" value={date} onChange={e=>setDate(e.target.value)} className="w-full p-2 rounded bg-gray-700 text-white text-sm" />
        <div className="flex-1 overflow-y-auto space-y-1">
          {recs?.map(r=>(
            <button key={r.id} onClick={()=>setPlayUrl(recordingsApi.playUrl(r.id))} className="w-full text-left p-2 rounded bg-gray-700 hover:bg-gray-600 text-xs text-white">
              <div>{new Date(r.started_at).toLocaleTimeString()}</div>
              <div className="text-gray-400">{r.codec} · {r.file_size_mb?.toFixed(0)} MB</div>
            </button>
          ))}
        </div>
      </div>
      <div className="flex-1 bg-black rounded overflow-hidden">
        {playUrl ? <video src={playUrl} controls autoPlay className="w-full h-full" /> : <div className="h-full flex items-center justify-center text-gray-500 text-sm">Pilih rekaman</div>}
      </div>
    </div>
  )
}