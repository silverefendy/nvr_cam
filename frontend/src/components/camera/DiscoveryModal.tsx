import { useState, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { discoveryApi, type DiscoveredCamera } from '@/api/discovery'
import { apiClient } from '@/api/client'

interface Props {
  storageDrives: string[]
  onClose: () => void
}

type ScanMethod = 'onvif' | 'rtsp_scan'

const METHOD_INFO: Record<ScanMethod, { label: string; desc: string; icon: string }> = {
  onvif: {
    icon: '📡',
    label: 'ONVIF WS-Discovery',
    desc: 'Kirim broadcast UDP ke jaringan. Kamera harus support ONVIF. Mungkin tidak berfungsi di Docker/Windows.',
  },
  rtsp_scan: {
    icon: '🔎',
    label: 'IP Range Scan',
    desc: 'Scan satu per satu semua IP di subnet. Deteksi ONVIF (port 80/8080) dan Dahua (port 37777/37778). Lebih reliable di Docker.',
  },
}

export function DiscoveryModal({ storageDrives, onClose }: Props) {
  const queryClient = useQueryClient()

  // --- scan state ---
  const [method, setMethod]       = useState<ScanMethod>('rtsp_scan')
  const [network, setNetwork]     = useState('')
  const [timeout, setTimeout_]    = useState(5)
  const [results, setResults]     = useState<DiscoveredCamera[] | null>(null)
  const [scanError, setScanError] = useState('')
  const [isScanning, setIsScanning] = useState(false)
  const [networkScanned, setNetworkScanned] = useState('')

  // --- add camera state ---
  const [adding, setAdding]       = useState<Record<string, boolean>>({})
  const [added, setAdded]         = useState<Record<string, boolean>>({})
  const [addError, setAddError]   = useState<Record<string, string>>({})

  // form fields per kamera yang dipilih untuk di-add
  const [formData, setFormData]   = useState<Record<string, {
    id: string; name: string; location: string
    username: string; password: string
    storage_drive: string; retention_days: number
    use_suggested_rtsp: boolean
  }>>({})

  const abortRef = useRef<AbortController | null>(null)

  // --- Scan ---
  const handleScan = async () => {
    setScanError('')
    setResults(null)
    setAdded({})
    setAddError({})
    setFormData({})
    setNetworkScanned('')
    setIsScanning(true)
    abortRef.current = new AbortController()
    try {
      const res = await discoveryApi.scan({
        network: network.trim() || undefined,
        timeout,
        method,
        camera_only: true,
      })
      setResults(res.cameras)
      setNetworkScanned(res.network_scanned || '')
      if (res.cameras.length === 0) {
        setScanError(
          method === 'rtsp_scan'
            ? `Tidak ada kamera ditemukan di ${res.network_scanned || 'subnet lokal'}. Pastikan subnet benar dan kamera menyala.`
            : 'Tidak ada kamera ONVIF ditemukan. Coba gunakan IP Range Scan untuk hasil lebih baik.'
        )
      }
    } catch (err: any) {
      if (err?.name === 'CanceledError') return
      const detail = err?.response?.data?.detail || ''
      setScanError(
        detail || 'Scan gagal. Coba isi Network CIDR secara manual (contoh: 10.1.0.0/24).'
      )
    } finally {
      setIsScanning(false)
    }
  }

  const handleStop = () => {
    abortRef.current?.abort()
    setIsScanning(false)
  }

  // --- Init form untuk kamera yang mau di-add ---
  const initForm = (cam: DiscoveredCamera) => {
    const key = `${cam.ip}:${cam.port}`
    if (formData[key]) return
    const hasSuggestedRtsp = !!(cam.suggested_rtsp_main || cam.rtsp_url)
    setFormData(prev => ({
      ...prev,
      [key]: {
        id:            '',
        name:          cam.name || cam.model || `CAM-${cam.ip.split('.').pop()}`,
        location:      '',
        username:      'admin',
        password:      '',
        storage_drive: storageDrives[0] || '',
        retention_days: 30,
        use_suggested_rtsp: hasSuggestedRtsp,
      }
    }))
  }

  const updateForm = (key: string, field: string, value: any) => {
    setFormData(prev => ({ ...prev, [key]: { ...prev[key], [field]: value } }))
  }

  // --- Add kamera ke sistem ---
  const handleAddCamera = async (cam: DiscoveredCamera) => {
    const key = `${cam.ip}:${cam.port}`
    const f = formData[key]
    if (!f) return
    if (!f.id.trim()) { setAddError(p => ({ ...p, [key]: 'Camera ID wajib diisi.' })); return }
    if (!f.name.trim()) { setAddError(p => ({ ...p, [key]: 'Nama kamera wajib diisi.' })); return }

    setAdding(p => ({ ...p, [key]: true }))
    setAddError(p => ({ ...p, [key]: '' }))
    try {
      // Gunakan suggested RTSP dari Dahua jika tersedia, fallback ke konstruksi manual
      const rtsp_main = f.use_suggested_rtsp && (cam.suggested_rtsp_main || cam.rtsp_url)
        ? (cam.suggested_rtsp_main || cam.rtsp_url)!.replace(
            /rtsp:\/\/[^@]*@/,
            `rtsp://${f.username}:${f.password}@`
          )
        : f.username && f.password
          ? `rtsp://${f.username}:${f.password}@${cam.ip}:554/cam/realmonitor?channel=1&subtype=0`
          : `rtsp://${cam.ip}:554/stream1`

      const rtsp_sub = f.use_suggested_rtsp && cam.suggested_rtsp_sub
        ? cam.suggested_rtsp_sub.replace(
            /rtsp:\/\/[^@]*@/,
            `rtsp://${f.username}:${f.password}@`
          )
        : undefined

      await apiClient.post('/config/cameras', {
        id:             f.id.trim().toUpperCase(),
        name:           f.name.trim(),
        location:       f.location.trim() || undefined,
        rtsp_main,
        rtsp_sub,
        storage_drive:  f.storage_drive,
        retention_days: f.retention_days,
        config_json: {
          ip_address:   cam.ip,
          port:         cam.port,
          username:     f.username,
          password:     f.password,
          manufacturer: cam.manufacturer,
          model:        cam.model,
          mac_address:  cam.mac_address,
          dahua_sdk:    cam.dahua_sdk,
        }
      })

      setAdded(p => ({ ...p, [key]: true }))
      queryClient.invalidateQueries({ queryKey: ['cameras-list'] })
    } catch (err: any) {
      setAddError(p => ({
        ...p,
        [key]: err?.response?.data?.detail || 'Gagal menambahkan kamera.'
      }))
    } finally {
      setAdding(p => ({ ...p, [key]: false }))
    }
  }

  // --- Render ---
  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 50,
      background: 'rgba(0,0,0,0.7)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '16px',
    }}>
      <div style={{
        background: '#1e2535', borderRadius: 10, width: '100%', maxWidth: 780,
        maxHeight: '90vh', display: 'flex', flexDirection: 'column',
        boxShadow: '0 8px 40px rgba(0,0,0,0.6)',
        border: '1px solid #2d3a50',
      }}>
        {/* Header */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '16px 20px', borderBottom: '1px solid #2d3a50', flexShrink: 0,
        }}>
          <div>
            <div style={{ color: '#fff', fontWeight: 600, fontSize: 15 }}>🔍 Cari Kamera Otomatis</div>
            <div style={{ color: '#64748b', fontSize: 12, marginTop: 2 }}>
              Scan jaringan — ONVIF WS-Discovery atau IP Range Scan
            </div>
          </div>
          <button onClick={onClose} style={{
            background: 'none', border: 'none', color: '#64748b',
            fontSize: 20, cursor: 'pointer', padding: '4px 8px', lineHeight: 1,
          }}>✕</button>
        </div>

        {/* Method Selector */}
        <div style={{
          padding: '12px 20px', borderBottom: '1px solid #2d3a50',
          display: 'flex', gap: 10, flexShrink: 0,
        }}>
          {(Object.keys(METHOD_INFO) as ScanMethod[]).map(m => {
            const info = METHOD_INFO[m]
            const active = method === m
            return (
              <button
                key={m}
                onClick={() => setMethod(m)}
                disabled={isScanning}
                style={{
                  flex: 1, padding: '10px 12px', textAlign: 'left',
                  background: active ? 'rgba(37,99,235,0.18)' : '#0f1117',
                  border: `1px solid ${active ? '#2563eb' : '#2d3a50'}`,
                  borderRadius: 8, cursor: isScanning ? 'not-allowed' : 'pointer',
                  transition: 'all 0.15s',
                }}
              >
                <div style={{ color: active ? '#60a5fa' : '#94a3b8', fontSize: 13, fontWeight: 600 }}>
                  {info.icon} {info.label}
                  {m === 'rtsp_scan' && (
                    <span style={{
                      marginLeft: 6, fontSize: 10, background: '#166534',
                      color: '#4ade80', padding: '1px 6px', borderRadius: 4,
                    }}>Rekomendasi</span>
                  )}
                </div>
                <div style={{ color: '#475569', fontSize: 11, marginTop: 3, lineHeight: 1.4 }}>
                  {info.desc}
                </div>
              </button>
            )
          })}
        </div>

        {/* Scan Controls */}
        <div style={{
          padding: '12px 20px', borderBottom: '1px solid #2d3a50',
          display: 'flex', gap: 10, alignItems: 'flex-end', flexShrink: 0, flexWrap: 'wrap',
        }}>
          <div style={{ flex: 1, minWidth: 200 }}>
            <label style={{ color: '#94a3b8', fontSize: 11, display: 'block', marginBottom: 4 }}>
              Network CIDR
              {method === 'rtsp_scan' && (
                <span style={{ color: '#f59e0b', marginLeft: 4 }}>
                  ⚠ Wajib diisi untuk IP Range Scan
                </span>
              )}
            </label>
            <input
              type="text"
              placeholder={method === 'rtsp_scan' ? 'cth: 10.1.0.0/24 atau 192.168.1.0/24' : 'cth: 192.168.1.0/24 (opsional)'}
              value={network}
              onChange={e => setNetwork(e.target.value)}
              disabled={isScanning}
              style={{
                width: '100%', background: '#0f1117',
                border: `1px solid ${method === 'rtsp_scan' && !network ? '#92400e' : '#2d3a50'}`,
                borderRadius: 6, padding: '6px 10px', color: '#e2e8f0', fontSize: 13,
                outline: 'none', boxSizing: 'border-box',
              }}
            />
            {method === 'rtsp_scan' && !network && (
              <div style={{ color: '#f59e0b', fontSize: 10, marginTop: 3 }}>
                Kosongkan untuk auto-detect subnet host (via host.docker.internal)
              </div>
            )}
          </div>
          <div style={{ minWidth: 110 }}>
            <label style={{ color: '#94a3b8', fontSize: 11, display: 'block', marginBottom: 4 }}>
              Timeout (detik)
            </label>
            <input
              type="number"
              min={1} max={30}
              value={timeout}
              onChange={e => setTimeout_(Number(e.target.value))}
              disabled={isScanning}
              style={{
                width: '100%', background: '#0f1117', border: '1px solid #2d3a50',
                borderRadius: 6, padding: '6px 10px', color: '#e2e8f0', fontSize: 13,
                outline: 'none', boxSizing: 'border-box',
              }}
            />
          </div>
          {!isScanning ? (
            <button onClick={handleScan} style={{
              padding: '7px 22px', background: '#2563eb', color: '#fff',
              border: 'none', borderRadius: 6, fontSize: 13, cursor: 'pointer', fontWeight: 500,
            }}>
              Mulai Scan
            </button>
          ) : (
            <button onClick={handleStop} style={{
              padding: '7px 22px', background: '#dc2626', color: '#fff',
              border: 'none', borderRadius: 6, fontSize: 13, cursor: 'pointer', fontWeight: 500,
            }}>
              Stop
            </button>
          )}
        </div>

        {/* Body — Results */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px' }}>
          {isScanning && (
            <div style={{ textAlign: 'center', color: '#60a5fa', padding: '32px 0' }}>
              <div style={{ fontSize: 28, marginBottom: 8 }}>
                {method === 'rtsp_scan' ? '🔎' : '📡'}
              </div>
              <div style={{ fontSize: 13 }}>
                {method === 'rtsp_scan' ? 'Memindai IP satu per satu…' : 'Mengirim broadcast ONVIF…'}
              </div>
              <div style={{ fontSize: 11, color: '#475569', marginTop: 4 }}>
                {network || 'auto-detect subnet'} • timeout {timeout}s
              </div>
            </div>
          )}

          {!isScanning && scanError && (
            <div style={{
              background: '#2d1515', border: '1px solid #7f1d1d',
              borderRadius: 6, padding: '10px 14px', color: '#fca5a5', fontSize: 13,
            }}>
              ⚠️ {scanError}
              {method === 'onvif' && (
                <div style={{ marginTop: 8, color: '#94a3b8', fontSize: 12 }}>
                  💡 Coba ganti ke <strong style={{ color: '#60a5fa' }}>IP Range Scan</strong> — lebih reliable di Docker/Windows.
                </div>
              )}
            </div>
          )}

          {!isScanning && results && results.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ color: '#22c55e', fontSize: 12, marginBottom: 4 }}>
                ✅ {results.length} kamera ditemukan
                {networkScanned && (
                  <span style={{ color: '#475569', marginLeft: 8 }}>di {networkScanned}</span>
                )}
              </div>
              {results.map(cam => {
                const key = `${cam.ip}:${cam.port}`
                const isAdded   = added[key]
                const isAdding  = adding[key]
                const err       = addError[key]
                const form      = formData[key]
                const showForm  = !!form && !isAdded

                return (
                  <div key={key} style={{
                    background: '#0f1117', border: `1px solid ${isAdded ? '#166534' : '#2d3a50'}`,
                    borderRadius: 8, padding: '12px 16px',
                  }}>
                    {/* Info kamera */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 8 }}>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span style={{ color: '#e2e8f0', fontWeight: 500, fontSize: 13 }}>
                            {cam.manufacturer || 'Unknown'} {cam.model || ''}
                          </span>
                          {cam.dahua_sdk && (
                            <span style={{
                              fontSize: 10, background: '#1e3a5f', color: '#60a5fa',
                              padding: '1px 6px', borderRadius: 4,
                            }}>Dahua SDK</span>
                          )}
                          <span style={{
                            fontSize: 10, background: '#1a2a1a', color: '#4ade80',
                            padding: '1px 6px', borderRadius: 4,
                          }}>{cam.method || 'onvif'}</span>
                        </div>
                        <div style={{ color: '#60a5fa', fontSize: 12, fontFamily: 'monospace', marginTop: 2 }}>
                          {cam.ip}:{cam.port}
                        </div>
                        {cam.mac_address && (
                          <div style={{ color: '#475569', fontSize: 11, marginTop: 1 }}>
                            MAC: {cam.mac_address}
                          </div>
                        )}
                        {(cam.suggested_rtsp_main || cam.rtsp_url) && (
                          <div style={{ color: '#475569', fontSize: 11, marginTop: 1, fontFamily: 'monospace' }}>
                            RTSP: {cam.suggested_rtsp_main || cam.rtsp_url}
                          </div>
                        )}
                      </div>
                      <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                        {isAdded ? (
                          <span style={{ color: '#22c55e', fontSize: 12, padding: '4px 10px' }}>✓ Ditambahkan</span>
                        ) : !form ? (
                          <button
                            onClick={() => initForm(cam)}
                            style={{
                              padding: '5px 14px', background: '#1d4ed8', color: '#fff',
                              border: 'none', borderRadius: 5, fontSize: 12, cursor: 'pointer',
                            }}
                          >+ Tambah</button>
                        ) : null}
                      </div>
                    </div>

                    {/* Mini form tambah kamera */}
                    {showForm && (
                      <div style={{ marginTop: 12, borderTop: '1px solid #2d3a50', paddingTop: 12 }}>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                          {[
                            { label: 'Camera ID *', field: 'id', placeholder: 'cth: CAM01', width: 100 },
                            { label: 'Nama *', field: 'name', placeholder: 'Nama kamera', width: 160 },
                            { label: 'Lokasi', field: 'location', placeholder: 'cth: Pintu Masuk', width: 140 },
                            { label: 'Username', field: 'username', placeholder: 'admin', width: 100 },
                            { label: 'Password', field: 'password', placeholder: '••••••', width: 100, type: 'password' },
                          ].map(({ label, field, placeholder, width, type }) => (
                            <div key={field} style={{ minWidth: width }}>
                              <label style={{ color: '#94a3b8', fontSize: 10, display: 'block', marginBottom: 3 }}>
                                {label}
                              </label>
                              <input
                                type={type || 'text'}
                                placeholder={placeholder}
                                value={(form as any)[field]}
                                onChange={e => updateForm(key, field, e.target.value)}
                                style={{
                                  width: '100%', background: '#1e2535', border: '1px solid #334155',
                                  borderRadius: 5, padding: '5px 8px', color: '#e2e8f0', fontSize: 12,
                                  outline: 'none', boxSizing: 'border-box',
                                }}
                              />
                            </div>
                          ))}
                          <div style={{ minWidth: 120 }}>
                            <label style={{ color: '#94a3b8', fontSize: 10, display: 'block', marginBottom: 3 }}>Storage</label>
                            <select
                              value={form.storage_drive}
                              onChange={e => updateForm(key, 'storage_drive', e.target.value)}
                              style={{
                                width: '100%', background: '#1e2535', border: '1px solid #334155',
                                borderRadius: 5, padding: '5px 8px', color: '#e2e8f0', fontSize: 12,
                                outline: 'none', boxSizing: 'border-box',
                              }}
                            >
                              {storageDrives.map(d => <option key={d} value={d}>{d}</option>)}
                            </select>
                          </div>
                          <div style={{ minWidth: 80 }}>
                            <label style={{ color: '#94a3b8', fontSize: 10, display: 'block', marginBottom: 3 }}>Retensi (hari)</label>
                            <input
                              type="number" min={1} max={365}
                              value={form.retention_days}
                              onChange={e => updateForm(key, 'retention_days', Number(e.target.value))}
                              style={{
                                width: '100%', background: '#1e2535', border: '1px solid #334155',
                                borderRadius: 5, padding: '5px 8px', color: '#e2e8f0', fontSize: 12,
                                outline: 'none', boxSizing: 'border-box',
                              }}
                            />
                          </div>
                        </div>

                        {/* Opsi RTSP Dahua jika tersedia */}
                        {(cam.suggested_rtsp_main || cam.rtsp_url) && (
                          <div style={{ marginTop: 8 }}>
                            <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
                              <input
                                type="checkbox"
                                checked={form.use_suggested_rtsp}
                                onChange={e => updateForm(key, 'use_suggested_rtsp', e.target.checked)}
                              />
                              <span style={{ color: '#94a3b8', fontSize: 11 }}>
                                Gunakan RTSP URL format Dahua
                                <span style={{ color: '#475569', marginLeft: 4, fontFamily: 'monospace', fontSize: 10 }}>
                                  {cam.suggested_rtsp_main || cam.rtsp_url}
                                </span>
                              </span>
                            </label>
                          </div>
                        )}

                        {err && (
                          <div style={{ color: '#f87171', fontSize: 11, marginTop: 6 }}>⚠️ {err}</div>
                        )}

                        <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
                          <button
                            onClick={() => handleAddCamera(cam)}
                            disabled={isAdding}
                            style={{
                              padding: '5px 16px', background: isAdding ? '#1e3a5f' : '#2563eb',
                              color: '#fff', border: 'none', borderRadius: 5, fontSize: 12,
                              cursor: isAdding ? 'not-allowed' : 'pointer',
                            }}
                          >{isAdding ? 'Menyimpan…' : 'Simpan Kamera'}</button>
                          <button
                            onClick={() => setFormData(p => { const n = { ...p }; delete n[key]; return n })}
                            style={{
                              padding: '5px 12px', background: 'none', color: '#64748b',
                              border: '1px solid #334155', borderRadius: 5, fontSize: 12, cursor: 'pointer',
                            }}
                          >Batal</button>
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}

          {!isScanning && results === null && !scanError && (
            <div style={{ textAlign: 'center', color: '#475569', padding: '32px 0', fontSize: 13 }}>
              <div style={{ marginBottom: 8, fontSize: 22 }}>🔎</div>
              Pilih metode scan di atas, isi Network CIDR jika perlu, lalu klik{' '}
              <strong style={{ color: '#94a3b8' }}>Mulai Scan</strong>.
              <div style={{ marginTop: 10, fontSize: 11, color: '#334155' }}>
                Untuk Docker/Windows, gunakan <strong style={{ color: '#60a5fa' }}>IP Range Scan</strong>{' '}
                dan isi subnet kamera (cth: <code style={{ color: '#4ade80' }}>10.1.0.0/24</code>).
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{
          padding: '12px 20px', borderTop: '1px solid #2d3a50',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0,
        }}>
          <div style={{ fontSize: 11, color: '#334155' }}>
            💡 Docker/Windows: IP Range Scan lebih reliable dari ONVIF WS-Discovery
          </div>
          <button onClick={onClose} style={{
            padding: '6px 18px', background: '#1e2535', color: '#94a3b8',
            border: '1px solid #334155', borderRadius: 6, fontSize: 13, cursor: 'pointer',
          }}>Tutup</button>
        </div>
      </div>
    </div>
  )
}
