import { useState } from 'react'
import { useQuery } from "@tanstack/react-query"
import { camerasApi } from "@/api/cameras"
import { recordingsApi } from "@/api/recordings"

export default function PlaybackPage() {
  const [camId, setCamId]               = useState("")
  const [date, setDate]                 = useState(new Date().toISOString().split("T")[0])
  const [playUrl, setPlayUrl]           = useState<string | null>(null)
  const [selectedRec, setSelectedRec]   = useState<any | null>(null)
  const [selectedHour, setSelectedHour] = useState<number | null>(null)

  const { data: cameras } = useQuery({ queryKey: ["cameras"], queryFn: camerasApi.list })
  const { data: recs }    = useQuery({
    queryKey: ["recs", camId, date],
    queryFn:  () => recordingsApi.list({ camera_id: camId, date_from: date, date_to: date }),
    enabled:  !!camId,
  })

  const filteredRecs = selectedHour !== null
    ? recs?.filter((r: any) => new Date(r.started_at).getHours() === selectedHour)
    : recs

  const handlePlay = (r: any) => {
    setSelectedRec(r)
    setPlayUrl(recordingsApi.playUrl(r.id))
  }

  const handleDownload = (r: any) => {
    const url = recordingsApi.downloadUrl(r.id)
    const a   = document.createElement('a')
    a.href    = url
    a.download = ''
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }

  const formatSize = (mb: number) =>
    mb >= 1024 ? `${(mb / 1024).toFixed(1)} GB` : `${mb?.toFixed(0)} MB`

  return (
    <div className="flex flex-col h-full gap-2 p-2">
      {/* Toolbar */}
      <div className="flex items-center gap-2 bg-gray-800 rounded px-3 py-2 flex-shrink-0">
        <select
          value={camId}
          onChange={e => { setCamId(e.target.value); setPlayUrl(null); setSelectedRec(null) }}
          className="bg-gray-700 rounded px-3 py-1.5 border border-gray-600 text-sm"
        >
          <option value="">-- Pilih Kamera --</option>
          {cameras?.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <input
          type="date"
          value={date}
          onChange={e => { setDate(e.target.value); setPlayUrl(null); setSelectedRec(null) }}
          className="bg-gray-700 rounded px-3 py-1.5 border border-gray-600 text-sm"
        />
        {selectedHour !== null && (
          <button
            onClick={() => setSelectedHour(null)}
            className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded text-sm"
          >
            ✕ Filter: {String(selectedHour).padStart(2,'0')}:00
          </button>
        )}
      </div>

      <div className="flex-1 flex gap-2 overflow-hidden">
        {/* Daftar Rekaman */}
        <div className="w-64 flex flex-col gap-1 bg-gray-800 rounded p-2 overflow-hidden">
          <div className="text-xs text-gray-400 px-1 mb-1">
            {filteredRecs?.length || 0} rekaman
            {selectedHour !== null ? ` · jam ${String(selectedHour).padStart(2,'0')}:00` : ''}
          </div>
          <div className="flex-1 overflow-y-auto space-y-1">
            {filteredRecs?.length === 0 && (
              <div className="text-center text-gray-500 text-xs py-4">Tidak ada rekaman</div>
            )}
            {filteredRecs?.map((r: any) => (
              <div
                key={r.id}
                className={`rounded border text-xs ${
                  selectedRec?.id === r.id
                    ? 'border-blue-500 bg-blue-900/30'
                    : 'border-transparent bg-gray-700 hover:bg-gray-600'
                }`}
              >
                <button onClick={() => handlePlay(r)} className="w-full text-left p-2">
                  <div className="font-medium text-white">
                    {new Date(r.started_at).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    {r.is_protected && <span className="ml-1 text-yellow-400">🔒</span>}
                  </div>
                  <div className="text-gray-400 mt-0.5">
                    {r.codec ?? 'mp4'} · {formatSize(r.file_size_mb ?? 0)}
                  </div>
                </button>
                <div className="flex border-t border-gray-600">
                  <button
                    onClick={() => handlePlay(r)}
                    className="flex-1 py-1 text-center text-gray-400 hover:text-white hover:bg-gray-600 text-xs rounded-bl"
                  >
                    ▶ Putar
                  </button>
                  <button
                    onClick={() => handleDownload(r)}
                    className="flex-1 py-1 text-center text-blue-400 hover:text-blue-200 hover:bg-gray-600 text-xs rounded-br border-l border-gray-600"
                  >
                    ⬇ Download
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Video Player */}
        <div className="flex-1 flex flex-col gap-2 overflow-hidden">
          <div className="flex-1 bg-black rounded overflow-hidden">
            {playUrl ? (
              <video key={playUrl} src={playUrl} controls autoPlay className="w-full h-full" />
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-gray-500 text-sm gap-2">
                <span className="text-3xl">🎬</span>
                <span>Pilih rekaman untuk diputar</span>
              </div>
            )}
          </div>
          {selectedRec && (
            <div className="bg-gray-800 rounded px-3 py-2 flex items-center gap-4 text-xs text-gray-300 flex-shrink-0">
              <span className="font-medium text-white">
                {new Date(selectedRec.started_at).toLocaleString('id-ID')}
              </span>
              <span>{selectedRec.codec ?? 'mp4'}</span>
              <span>{formatSize(selectedRec.file_size_mb ?? 0)}</span>
              {selectedRec.is_protected && <span className="text-yellow-400">🔒 Dilindungi</span>}
              <button
                onClick={() => handleDownload(selectedRec)}
                className="ml-auto px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs"
              >
                ⬇ Download
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}