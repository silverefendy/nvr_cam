import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { buildDahuaRTSP, maskRTSPPassword } from '@/utils/rtsp'
import { RTSPTestButton } from './RTSPTestButton'
import { apiClient } from '@/api/client'

interface CameraFormData {
  id?: string
  name: string
  location?: string
  ip_address: string
  port: number
  username: string
  password: string
  channel: number
  rtsp_main_custom?: string
  rtsp_sub_custom?: string
  storage_drive: string
  motion_enabled: boolean
  retention_days: number
}

interface Props {
  initialData?: CameraFormData
  storageDrives: string[]
  onSave: (data: CameraFormData) => void
  onCancel: () => void
}

const inputCls = "w-full px-3 py-2.5 rounded-xl bg-slate-50 border border-slate-300 text-slate-800 text-sm placeholder-slate-400 focus:outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-100 transition"
const labelCls = "block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5"

export const CameraForm: React.FC<Props> = ({ initialData, storageDrives, onSave, onCancel }) => {
  const [formData, setFormData] = useState<CameraFormData>(
    initialData || {
      name: '', location: '', ip_address: '', port: 554,
      username: 'admin', password: '', channel: 1,
      storage_drive: storageDrives[0] || '',
      motion_enabled: false, retention_days: 30,
    }
  )
  const [useCustomRTSP, setUseCustomRTSP] = useState(false)

  const saveMutation = useMutation({
    mutationFn: async (data: CameraFormData) => {
      const isEdit = !!data.id
      const url = isEdit ? `/config/cameras/${data.id}` : '/config/cameras'
      const res = await apiClient({ method: isEdit ? 'PUT' : 'POST', url, data })
      return res.data
    },
    onSuccess: () => onSave(formData),
  })

  const set = (field: keyof CameraFormData, value: any) =>
    setFormData(prev => ({ ...prev, [field]: value }))

  const rtspMain = useCustomRTSP ? (formData.rtsp_main_custom || '') :
    buildDahuaRTSP(formData.ip_address, formData.port, formData.username, formData.password, formData.channel, 0)
  const rtspSub = useCustomRTSP ? (formData.rtsp_sub_custom || '') :
    buildDahuaRTSP(formData.ip_address, formData.port, formData.username, formData.password, formData.channel, 1)

  return (
    <div className="bg-white border border-slate-200 rounded-2xl shadow-sm max-w-2xl mx-auto overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
        <h2 className="text-base font-bold text-slate-800">
          {formData.id ? '✏️ Edit Kamera' : '➕ Tambah Kamera Baru'}
        </h2>
        <p className="text-xs text-slate-400 mt-0.5">Isi informasi koneksi dan penyimpanan kamera</p>
      </div>

      <div className="p-6 space-y-6">
        {/* Identitas Kamera */}
        <div>
          <div className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3 flex items-center gap-2">
            <span className="flex-1 h-px bg-slate-200" />
            <span>Identitas</span>
            <span className="flex-1 h-px bg-slate-200" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelCls}>Nama Kamera *</label>
              <input type="text" value={formData.name} onChange={e => set('name', e.target.value)}
                placeholder="Pintu Masuk Utama" className={inputCls} required />
            </div>
            <div>
              <label className={labelCls}>Lokasi</label>
              <input type="text" value={formData.location || ''} onChange={e => set('location', e.target.value)}
                placeholder="Lantai 1, Lobby" className={inputCls} />
            </div>
          </div>
        </div>

        {/* Koneksi Jaringan */}
        <div>
          <div className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3 flex items-center gap-2">
            <span className="flex-1 h-px bg-slate-200" />
            <span>Jaringan & Autentikasi</span>
            <span className="flex-1 h-px bg-slate-200" />
          </div>
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div className="col-span-2">
              <label className={labelCls}>IP Address *</label>
              <input type="text" value={formData.ip_address} onChange={e => set('ip_address', e.target.value)}
                placeholder="192.168.1.101" className={inputCls} required />
            </div>
            <div>
              <label className={labelCls}>Port</label>
              <input type="number" value={formData.port} onChange={e => set('port', parseInt(e.target.value))}
                className={inputCls} />
            </div>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className={labelCls}>Username</label>
              <input type="text" value={formData.username} onChange={e => set('username', e.target.value)}
                className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Password *</label>
              <input type="password" value={formData.password} onChange={e => set('password', e.target.value)}
                className={inputCls} required />
            </div>
            <div>
              <label className={labelCls}>Channel</label>
              <input type="number" value={formData.channel} onChange={e => set('channel', parseInt(e.target.value))}
                min="1" max="16" className={inputCls} />
            </div>
          </div>
        </div>

        {/* RTSP */}
        <div>
          <div className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3 flex items-center gap-2">
            <span className="flex-1 h-px bg-slate-200" />
            <span>RTSP Stream</span>
            <span className="flex-1 h-px bg-slate-200" />
          </div>
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-medium text-slate-500">URL Preview</span>
              <label className="flex items-center gap-2 text-xs text-slate-500 cursor-pointer">
                <div className={`w-8 h-4 rounded-full transition-colors relative ${useCustomRTSP ? 'bg-sky-500' : 'bg-slate-300'}`}
                  onClick={() => setUseCustomRTSP(v => !v)}>
                  <div className={`absolute top-0.5 w-3 h-3 bg-white rounded-full shadow transition-transform ${useCustomRTSP ? 'translate-x-4' : 'translate-x-0.5'}`} />
                </div>
                Custom URL
              </label>
            </div>
            {useCustomRTSP ? (
              <div className="space-y-2">
                <input type="text" value={formData.rtsp_main_custom || ''} onChange={e => set('rtsp_main_custom', e.target.value)}
                  placeholder="rtsp://... (main stream)" className={inputCls} />
                <input type="text" value={formData.rtsp_sub_custom || ''} onChange={e => set('rtsp_sub_custom', e.target.value)}
                  placeholder="rtsp://... (sub stream)" className={inputCls} />
              </div>
            ) : (
              <div className="space-y-1.5 mb-3">
                <div className="font-mono text-xs bg-white border border-slate-200 rounded-lg px-3 py-2 text-slate-600 break-all">
                  <span className="text-slate-400 mr-1">Main:</span>{maskRTSPPassword(rtspMain)}
                </div>
                <div className="font-mono text-xs bg-white border border-slate-200 rounded-lg px-3 py-2 text-slate-600 break-all">
                  <span className="text-slate-400 mr-1">Sub:</span>{maskRTSPPassword(rtspSub)}
                </div>
              </div>
            )}
            <RTSPTestButton rtspUrl={rtspMain || rtspSub} />
          </div>
        </div>

        {/* Storage */}
        <div>
          <div className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3 flex items-center gap-2">
            <span className="flex-1 h-px bg-slate-200" />
            <span>Penyimpanan & Rekaman</span>
            <span className="flex-1 h-px bg-slate-200" />
          </div>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className={labelCls}>Storage Drive *</label>
              <select value={formData.storage_drive} onChange={e => set('storage_drive', e.target.value)}
                className={inputCls} required>
                {storageDrives.length === 0 && <option value="">— Belum ada drive —</option>}
                {storageDrives.map(d => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>
            <div>
              <label className={labelCls}>Retensi (hari)</label>
              <input type="number" value={formData.retention_days} onChange={e => set('retention_days', parseInt(e.target.value))}
                min="1" max="365" className={inputCls} />
            </div>
          </div>
          <label className="flex items-center gap-3 cursor-pointer group">
            <div className={`w-10 h-5 rounded-full transition-colors relative flex-shrink-0 ${formData.motion_enabled ? 'bg-sky-500' : 'bg-slate-300'}`}
              onClick={() => set('motion_enabled', !formData.motion_enabled)}>
              <div className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${formData.motion_enabled ? 'translate-x-5' : 'translate-x-0.5'}`} />
            </div>
            <div>
              <div className="text-sm font-medium text-slate-700">Deteksi Gerakan</div>
              <div className="text-xs text-slate-400">Rekam otomatis saat ada gerakan terdeteksi</div>
            </div>
          </label>
        </div>
      </div>

      {/* Footer Actions */}
      <div className="px-6 py-4 border-t border-slate-200 bg-slate-50 flex justify-end gap-3">
        <button type="button" onClick={onCancel}
          className="px-5 py-2.5 rounded-xl text-sm font-medium text-slate-600 bg-white border border-slate-300 hover:bg-slate-100 transition-colors">
          Batal
        </button>
        <button
          onClick={() => saveMutation.mutate(formData)}
          disabled={saveMutation.isPending}
          className="px-5 py-2.5 rounded-xl text-sm font-medium text-white bg-sky-600 hover:bg-sky-500 disabled:opacity-50 transition-colors shadow-sm">
          {saveMutation.isPending ? 'Menyimpan...' : formData.id ? '💾 Update Kamera' : '➕ Tambah Kamera'}
        </button>
      </div>
    </div>
  )
}
