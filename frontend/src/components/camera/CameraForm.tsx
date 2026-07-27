import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
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
  segment_duration: number
}

interface Props {
  initialData?: CameraFormData
  storageDrives: string[]
  onSave: (data: CameraFormData) => void
  onCancel: () => void
}

const inputCls = "w-full px-3 py-2.5 rounded-xl bg-slate-50 border border-slate-300 text-slate-800 text-sm placeholder-slate-400 focus:outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-100 transition"
const labelCls = "block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5"
const dividerCls = "text-xs font-bold text-slate-400 uppercase tracking-widest mb-3 flex items-center gap-2"

// Tab type
type FormTab = 'basic' | 'onvif'

// ONVIF settings state
interface ONVIFState {
  fps: number
  bitrate_kbps: number
  width: number
  height: number
  codec: string
  loading: boolean
  saving: boolean
  loaded: boolean
  error: string | null
  success: string | null
}

export const CameraForm: React.FC<Props> = ({ initialData, storageDrives, onSave, onCancel }) => {
  const [formData, setFormData] = useState<CameraFormData>(
    initialData || {
      name: '', location: '', ip_address: '', port: 554,
      username: 'admin', password: '', channel: 1,
      storage_drive: storageDrives[0] || '',
      motion_enabled: false, retention_days: 30,
      segment_duration: 1800,
    }
  )
  const [useCustomRTSP, setUseCustomRTSP] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<FormTab>('basic')
  const [onvif, setOnvif] = useState<ONVIFState>({
    fps: 15, bitrate_kbps: 2048, width: 1920, height: 1080,
    codec: 'H265', loading: false, saving: false, loaded: false,
    error: null, success: null,
  })

  const isEdit = !!formData.id

  const saveMutation = useMutation({
    mutationFn: async (data: CameraFormData) => {
      setErrorMsg(null)
      // Kirim segment_duration sebagai bagian dari body
      // Backend akan menyimpannya ke config_json
      if (data.id) {
        const res = await apiClient.put(`/config/cameras/${data.id}`, data)
        return res.data
      } else {
        const res = await apiClient.post('/config/cameras', data)
        return res.data
      }
    },
    onSuccess: () => onSave(formData),
    onError: (err: any) => {
      const detail = err?.response?.data?.detail
      if (typeof detail === 'string') {
        setErrorMsg(detail)
      } else if (Array.isArray(detail)) {
        setErrorMsg(detail.map((d: any) => `${d.loc?.slice(1).join('.')} — ${d.msg}`).join('\n'))
      } else {
        setErrorMsg('Gagal menyimpan kamera. Periksa log untuk detail.')
      }
    },
  })

  const set = (field: keyof CameraFormData, value: any) =>
    setFormData(prev => ({ ...prev, [field]: value }))

  const rtspMain = useCustomRTSP ? (formData.rtsp_main_custom || '') :
    buildDahuaRTSP(formData.ip_address, formData.port, formData.username, formData.password, formData.channel, 0)
  const rtspSub = useCustomRTSP ? (formData.rtsp_sub_custom || '') :
    buildDahuaRTSP(formData.ip_address, formData.port, formData.username, formData.password, formData.channel, 1)

  const validate = () => {
    if (!formData.name.trim()) { setErrorMsg('Nama kamera wajib diisi.'); return false }
    if (!formData.ip_address.trim() && !formData.rtsp_main_custom?.trim()) {
      setErrorMsg('IP Address wajib diisi (atau gunakan Custom RTSP URL).')
      return false
    }
    if (!formData.storage_drive) { setErrorMsg('Storage drive wajib dipilih.'); return false }
    return true
  }

  const handleSubmit = () => {
    if (!validate()) return
    saveMutation.mutate(formData)
  }

  // ONVIF: baca setting dari kamera
  const loadOnvifSettings = async () => {
    if (!formData.id) return
    setOnvif(s => ({ ...s, loading: true, error: null, success: null }))
    try {
      const res = await apiClient.get(`/cameras/${formData.id}/onvif-settings`)
      const d = res.data
      setOnvif(s => ({
        ...s,
        fps: d.fps ?? s.fps,
        bitrate_kbps: d.bitrate_kbps ?? s.bitrate_kbps,
        width: d.width ?? s.width,
        height: d.height ?? s.height,
        codec: d.codec ?? s.codec,
        loading: false, loaded: true,
      }))
    } catch (e: any) {
      setOnvif(s => ({ ...s, loading: false, error: e?.response?.data?.detail || 'Gagal membaca setting ONVIF' }))
    }
  }

  // ONVIF: kirim setting ke kamera
  const saveOnvifSettings = async () => {
    if (!formData.id) return
    setOnvif(s => ({ ...s, saving: true, error: null, success: null }))
    try {
      await apiClient.put(`/cameras/${formData.id}/onvif-settings`, {
        fps: onvif.fps,
        bitrate_kbps: onvif.bitrate_kbps,
        width: onvif.width,
        height: onvif.height,
        codec: onvif.codec,
        username: formData.username,
        password: formData.password,
      })
      setOnvif(s => ({ ...s, saving: false, success: 'Setting ONVIF berhasil diterapkan ke kamera!' }))
    } catch (e: any) {
      setOnvif(s => ({ ...s, saving: false, error: e?.response?.data?.detail || 'Gagal mengirim setting ONVIF' }))
    }
  }

  const RESOLUTIONS = [
    { label: '1080p (1920×1080)', w: 1920, h: 1080 },
    { label: '720p (1280×720)', w: 1280, h: 720 },
    { label: '4MP (2560×1440)', w: 2560, h: 1440 },
    { label: '4K (3840×2160)', w: 3840, h: 2160 },
    { label: 'D1 (704×576)', w: 704, h: 576 },
  ]

  return (
    <div className="bg-white border border-slate-200 rounded-2xl shadow-sm max-w-2xl mx-auto overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
        <h2 className="text-base font-bold text-slate-800">
          {formData.id ? '✏️ Edit Kamera' : '➕ Tambah Kamera Baru'}
        </h2>
        <p className="text-xs text-slate-400 mt-0.5">Isi informasi koneksi dan penyimpanan kamera</p>
      </div>

      {/* Tab bar — hanya tampilkan ONVIF tab jika edit */}
      {isEdit && (
        <div className="flex border-b border-slate-200 bg-slate-50">
          {(['basic', 'onvif'] as FormTab[]).map(tab => (
            <button
              key={tab}
              onClick={() => { setActiveTab(tab); if (tab === 'onvif' && !onvif.loaded) loadOnvifSettings() }}
              className={`px-6 py-3 text-xs font-semibold uppercase tracking-wider transition-colors ${
                activeTab === tab
                  ? 'border-b-2 border-sky-500 text-sky-600 bg-white'
                  : 'text-slate-400 hover:text-slate-600'
              }`}
            >
              {tab === 'basic' ? '⚙️ Konfigurasi' : '📡 Setting Kamera (ONVIF)'}
            </button>
          ))}
        </div>
      )}

      {/* ─── TAB: Basic ─────────────────────────────────────────── */}
      {activeTab === 'basic' && (
        <div className="p-6 space-y-6">
          {errorMsg && (
            <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 flex items-start gap-2">
              <span className="text-red-500 text-sm mt-0.5 flex-shrink-0">⚠️</span>
              <pre className="text-red-700 text-xs whitespace-pre-wrap font-sans">{errorMsg}</pre>
              <button onClick={() => setErrorMsg(null)} className="ml-auto text-red-400 hover:text-red-600 text-xs flex-shrink-0">✕</button>
            </div>
          )}

          {/* Identitas */}
          <div>
            <div className={dividerCls}>
              <span className="flex-1 h-px bg-slate-200" /><span>Identitas</span><span className="flex-1 h-px bg-slate-200" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className={labelCls}>Nama Kamera *</label>
                <input type="text" value={formData.name} onChange={e => set('name', e.target.value)}
                  placeholder="Pintu Masuk Utama" className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Lokasi</label>
                <input type="text" value={formData.location || ''} onChange={e => set('location', e.target.value)}
                  placeholder="Lantai 1, Lobby" className={inputCls} />
              </div>
            </div>
          </div>

          {/* Jaringan */}
          <div>
            <div className={dividerCls}>
              <span className="flex-1 h-px bg-slate-200" /><span>Jaringan &amp; Autentikasi</span><span className="flex-1 h-px bg-slate-200" />
            </div>
            <div className="grid grid-cols-3 gap-4 mb-4">
              <div className="col-span-2">
                <label className={labelCls}>IP Address *</label>
                <input type="text" value={formData.ip_address} onChange={e => set('ip_address', e.target.value)}
                  placeholder="192.168.1.101" className={inputCls} />
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
                  placeholder="••••••••" className={inputCls} />
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
            <div className={dividerCls}>
              <span className="flex-1 h-px bg-slate-200" /><span>RTSP Stream</span><span className="flex-1 h-px bg-slate-200" />
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

          {/* Storage & rekaman */}
          <div>
            <div className={dividerCls}>
              <span className="flex-1 h-px bg-slate-200" /><span>Penyimpanan &amp; Rekaman</span><span className="flex-1 h-px bg-slate-200" />
            </div>
            <div className="grid grid-cols-3 gap-4 mb-4">
              <div>
                <label className={labelCls}>Storage Drive *</label>
                <select value={formData.storage_drive} onChange={e => set('storage_drive', e.target.value)}
                  className={inputCls}>
                  {storageDrives.length === 0 && <option value="">— Belum ada drive —</option>}
                  {storageDrives.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
              </div>
              <div>
                <label className={labelCls}>Retensi (hari)</label>
                <input type="number" value={formData.retention_days} onChange={e => set('retention_days', parseInt(e.target.value))}
                  min="1" max="365" className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Durasi Segmen</label>
                <select
                  value={formData.segment_duration}
                  onChange={e => set('segment_duration', parseInt(e.target.value))}
                  className={inputCls}
                >
                  <option value={900}>15 menit</option>
                  <option value={1800}>30 menit</option>
                  <option value={3600}>1 jam</option>
                  <option value={7200}>2 jam</option>
                </select>
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
      )}

      {/* ─── TAB: ONVIF Settings ────────────────────────────────── */}
      {activeTab === 'onvif' && isEdit && (
        <div className="p-6 space-y-5">
          <div className="bg-sky-50 border border-sky-200 rounded-xl px-4 py-3 text-xs text-sky-700">
            ℹ️ Setting ini dikirim langsung ke kamera via ONVIF. Pastikan kamera mendukung ONVIF Profile S.
            Tidak semua kamera expose semua field — field yang tidak didukung akan diabaikan kamera.
          </div>

          {onvif.error && (
            <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-600">
              ❌ {onvif.error}
            </div>
          )}
          {onvif.success && (
            <div className="bg-green-50 border border-green-200 rounded-xl px-4 py-3 text-sm text-green-700">
              ✅ {onvif.success}
            </div>
          )}

          {onvif.loading ? (
            <div className="text-center py-8 text-slate-400 text-sm">Membaca setting dari kamera...</div>
          ) : (
            <>
              {/* Resolusi */}
              <div>
                <label className={labelCls}>Resolusi</label>
                <select
                  className={inputCls}
                  value={`${onvif.width}x${onvif.height}`}
                  onChange={e => {
                    const [w, h] = e.target.value.split('x').map(Number)
                    setOnvif(s => ({ ...s, width: w, height: h }))
                  }}
                >
                  {RESOLUTIONS.map(r => (
                    <option key={r.label} value={`${r.w}x${r.h}`}>{r.label}</option>
                  ))}
                </select>
              </div>

              {/* FPS */}
              <div>
                <label className={labelCls}>Frame Rate (FPS): {onvif.fps} fps</label>
                <input
                  type="range" min={1} max={30} step={1}
                  value={onvif.fps}
                  onChange={e => setOnvif(s => ({ ...s, fps: Number(e.target.value) }))}
                  className="w-full accent-sky-500"
                />
                <div className="flex justify-between text-xs text-slate-400 mt-1">
                  <span>1 fps</span><span>15 fps</span><span>30 fps</span>
                </div>
              </div>

              {/* Bitrate */}
              <div>
                <label className={labelCls}>Bitrate: {onvif.bitrate_kbps} Kbps ({(onvif.bitrate_kbps / 1024).toFixed(1)} Mbps)</label>
                <input
                  type="range" min={256} max={16384} step={256}
                  value={onvif.bitrate_kbps}
                  onChange={e => setOnvif(s => ({ ...s, bitrate_kbps: Number(e.target.value) }))}
                  className="w-full accent-sky-500"
                />
                <div className="flex justify-between text-xs text-slate-400 mt-1">
                  <span>256 Kbps</span><span>4 Mbps</span><span>16 Mbps</span>
                </div>
              </div>

              {/* Codec */}
              <div>
                <label className={labelCls}>Codec Video</label>
                <div className="flex gap-3">
                  {['H264', 'H265'].map(c => (
                    <label key={c} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio" name="codec" value={c}
                        checked={onvif.codec === c}
                        onChange={() => setOnvif(s => ({ ...s, codec: c }))}
                        className="accent-sky-500"
                      />
                      <span className="text-sm font-medium text-slate-700">{c}</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Estimasi bandwidth */}
              <div className="bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-xs text-slate-500">
                <div className="font-semibold text-slate-600 mb-1">📊 Estimasi penggunaan bandwidth & storage</div>
                <div>• Bitrate: <strong>{(onvif.bitrate_kbps / 1024).toFixed(2)} Mbps</strong> per kamera</div>
                <div>• Per jam: <strong>{((onvif.bitrate_kbps / 8) * 3600 / (1024 * 1024)).toFixed(1)} GB</strong></div>
                <div>• Per hari (24 jam): <strong>{((onvif.bitrate_kbps / 8) * 86400 / (1024 * 1024)).toFixed(1)} GB</strong></div>
                <div>• Per bulan: <strong>{((onvif.bitrate_kbps / 8) * 86400 * 30 / (1024 * 1024 * 1024)).toFixed(1)} GB</strong></div>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={loadOnvifSettings}
                  disabled={onvif.loading}
                  className="flex-1 px-4 py-2.5 rounded-xl text-sm font-medium text-slate-600 bg-white border border-slate-300 hover:bg-slate-100 transition-colors"
                >
                  🔄 Baca Ulang dari Kamera
                </button>
                <button
                  onClick={saveOnvifSettings}
                  disabled={onvif.saving}
                  className="flex-1 px-4 py-2.5 rounded-xl text-sm font-medium text-white bg-sky-600 hover:bg-sky-500 disabled:opacity-50 transition-colors"
                >
                  {onvif.saving ? 'Mengirim...' : '📡 Terapkan ke Kamera'}
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {/* Footer — hanya tampilkan di tab basic */}
      {activeTab === 'basic' && (
        <div className="px-6 py-4 border-t border-slate-200 bg-slate-50 flex justify-end gap-3">
          <button type="button" onClick={onCancel}
            className="px-5 py-2.5 rounded-xl text-sm font-medium text-slate-600 bg-white border border-slate-300 hover:bg-slate-100 transition-colors">
            Batal
          </button>
          <button
            onClick={handleSubmit}
            disabled={saveMutation.isPending}
            className="px-5 py-2.5 rounded-xl text-sm font-medium text-white bg-sky-600 hover:bg-sky-500 disabled:opacity-50 transition-colors shadow-sm">
            {saveMutation.isPending ? 'Menyimpan...' : formData.id ? '💾 Update Kamera' : '➕ Tambah Kamera'}
          </button>
        </div>
      )}
    </div>
  )
}
