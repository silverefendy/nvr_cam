/**
 * CameraImportExport
 * ==================
 * Import konfigurasi kamera dari Excel (.xlsx) dan export ke Excel.
 *
 * Kolom Excel yang didukung (urutan bebas, nama kolom case-insensitive):
 *   id, name, location, ip_address, port, username, password, channel,
 *   storage_drive, motion_enabled, retention_days, segment_duration
 *
 * Dependencies: xlsx (SheetJS) — install dengan:
 *   npm install xlsx
 */

import { useState, useRef } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import * as XLSX from 'xlsx'

// ─── Types ────────────────────────────────────────────────────────────────────

interface CameraRow {
  id: string
  name: string
  location?: string
  ip_address: string
  port: number
  username: string
  password: string
  channel: number
  storage_drive: string
  motion_enabled: boolean
  retention_days: number
  segment_duration: number
  // raw RTSP override (opsional)
  rtsp_main?: string
  rtsp_sub?: string
}

interface ParseResult {
  valid: CameraRow[]
  errors: { row: number; message: string }[]
}

interface ImportResult {
  imported: number
  skipped: number
  errors: number
  created_ids: string[]
  skipped_ids: string[]
  error_details: { id: string; error: string }[]
}

interface Props {
  storageDrives: string[]
  cameras: any[]          // kamera yang sudah ada (untuk export)
  onClose: () => void
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function buildRTSP(ip: string, port: number, user: string, pass: string, channel: number, sub: boolean): string {
  const subtype = sub ? 1 : 0
  return `rtsp://${user}:${pass}@${ip}:${port}/cam/realmonitor?channel=${channel}&subtype=${subtype}`
}

function normalizeKey(k: string): string {
  return k.toLowerCase().replace(/[^a-z0-9]/g, '_')
}

function parseExcelFile(buffer: ArrayBuffer, storageDrives: string[]): ParseResult {
  const wb = XLSX.read(buffer, { type: 'array' })
  const ws = wb.Sheets[wb.SheetNames[0]]
  const raw: any[] = XLSX.utils.sheet_to_json(ws, { defval: '' })

  const valid: CameraRow[] = []
  const errors: { row: number; message: string }[] = []

  raw.forEach((rawRow, idx) => {
    const rowNum = idx + 2  // +2 karena row 1 = header

    // Normalize keys
    const row: Record<string, any> = {}
    for (const [k, v] of Object.entries(rawRow)) {
      row[normalizeKey(k)] = v
    }

    // Required fields
    const missing: string[] = []
    if (!row.id)         missing.push('id')
    if (!row.name)       missing.push('name')
    if (!row.ip_address && !row.rtsp_main) missing.push('ip_address')
    if (!row.password && !row.rtsp_main)   missing.push('password')

    if (missing.length > 0) {
      errors.push({ row: rowNum, message: `Field wajib kosong: ${missing.join(', ')}` })
      return
    }

    const ip       = String(row.ip_address || '').trim()
    const port     = Number(row.port) || 554
    const username = String(row.username || 'admin').trim()
    const password = String(row.password || '').trim()
    const channel  = Number(row.channel) || 1
    const drive    = String(row.storage_drive || storageDrives[0] || '/mnt/driveA').trim()

    const camera: CameraRow = {
      id:               String(row.id).trim(),
      name:             String(row.name).trim(),
      location:         row.location ? String(row.location).trim() : undefined,
      ip_address:       ip,
      port,
      username,
      password,
      channel,
      storage_drive:    drive,
      motion_enabled:   String(row.motion_enabled).toLowerCase() === 'true' || row.motion_enabled === 1,
      retention_days:   Number(row.retention_days) || 30,
      segment_duration: Number(row.segment_duration) || 1800,
      rtsp_main:        row.rtsp_main ? String(row.rtsp_main).trim() : undefined,
      rtsp_sub:         row.rtsp_sub  ? String(row.rtsp_sub).trim()  : undefined,
    }

    valid.push(camera)
  })

  return { valid, errors }
}

function cameraRowToApiPayload(cam: CameraRow) {
  const rtsp_main = cam.rtsp_main || buildRTSP(cam.ip_address, cam.port, cam.username, cam.password, cam.channel, false)
  const rtsp_sub  = cam.rtsp_sub  || buildRTSP(cam.ip_address, cam.port, cam.username, cam.password, cam.channel, true)
  return {
    id:               cam.id,
    name:             cam.name,
    location:         cam.location || '',
    rtsp_main,
    rtsp_sub,
    rtsp_url_main:    rtsp_main,
    rtsp_url_sub:     rtsp_sub,
    storage_drive:    cam.storage_drive,
    motion_enabled:   cam.motion_enabled,
    retention_days:   cam.retention_days,
    config_json: {
      ip_address:       cam.ip_address,
      port:             cam.port,
      username:         cam.username,
      password:         cam.password,
      channel:          cam.channel,
      segment_duration: cam.segment_duration,
    },
  }
}

function downloadTemplate(storageDrives: string[]) {
  const drive = storageDrives[0] || '/mnt/driveA'
  const example = [
    {
      id: 'cam_01',
      name: 'Pintu Masuk Utama',
      location: 'Lobby Lt.1',
      ip_address: '10.3.0.101',
      port: 554,
      username: 'admin',
      password: 'password123',
      channel: 1,
      storage_drive: drive,
      motion_enabled: false,
      retention_days: 30,
      segment_duration: 1800,
      rtsp_main: '',  // kosongkan jika ingin auto-generate
      rtsp_sub:  '',
    },
    {
      id: 'cam_02',
      name: 'Gudang Belakang',
      location: 'Gudang Lt.1',
      ip_address: '10.3.0.102',
      port: 37778,   // contoh Dahua port alternatif
      username: 'admin',
      password: 'password456',
      channel: 1,
      storage_drive: drive,
      motion_enabled: false,
      retention_days: 30,
      segment_duration: 1800,
      rtsp_main: '',
      rtsp_sub:  '',
    },
  ]

  const ws = XLSX.utils.json_to_sheet(example)

  // Set column widths
  ws['!cols'] = [
    { wch: 10 }, { wch: 25 }, { wch: 20 }, { wch: 15 }, { wch: 8 },
    { wch: 12 }, { wch: 16 }, { wch: 8 }, { wch: 20 }, { wch: 15 },
    { wch: 15 }, { wch: 16 }, { wch: 35 }, { wch: 35 },
  ]

  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, 'Kamera')
  XLSX.writeFile(wb, 'template_kamera.xlsx')
}

function exportCameras(cameras: any[]) {
  const rows = cameras.map(cam => {
    const cfg = cam.config_json || {}
    return {
      id:               cam.id,
      name:             cam.name,
      location:         cam.location || '',
      ip_address:       cfg.ip_address || '',
      port:             cfg.port || 554,
      username:         cfg.username || 'admin',
      password:         cfg.password || '',
      channel:          cfg.channel || 1,
      storage_drive:    cam.storage_drive,
      motion_enabled:   cam.motion_enabled ? true : false,
      retention_days:   cam.retention_days || 30,
      segment_duration: cam.segment_duration || cfg.segment_duration || 1800,
      rtsp_main:        cam.rtsp_main || '',
      rtsp_sub:         cam.rtsp_sub || '',
    }
  })

  const ws = XLSX.utils.json_to_sheet(rows)
  ws['!cols'] = [
    { wch: 10 }, { wch: 25 }, { wch: 20 }, { wch: 15 }, { wch: 8 },
    { wch: 12 }, { wch: 16 }, { wch: 8 }, { wch: 20 }, { wch: 15 },
    { wch: 15 }, { wch: 16 }, { wch: 35 }, { wch: 35 },
  ]

  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, 'Kamera')
  const ts = new Date().toISOString().slice(0, 10)
  XLSX.writeFile(wb, `kamera_export_${ts}.xlsx`)
}

// ─── Component ────────────────────────────────────────────────────────────────

export const CameraImportExport: React.FC<Props> = ({ storageDrives, cameras, onClose }) => {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [tab, setTab] = useState<'import' | 'export'>('import')
  const [parseResult, setParseResult] = useState<ParseResult | null>(null)
  const [importResult, setImportResult] = useState<ImportResult | null>(null)
  const [importing, setImporting] = useState(false)
  const [fileName, setFileName] = useState('')
  const queryClient = useQueryClient()

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setFileName(file.name)
    setParseResult(null)
    setImportResult(null)

    const reader = new FileReader()
    reader.onload = (ev) => {
      const buffer = ev.target?.result as ArrayBuffer
      try {
        const result = parseExcelFile(buffer, storageDrives)
        setParseResult(result)
      } catch (err: any) {
        setParseResult({ valid: [], errors: [{ row: 0, message: `Gagal membaca file: ${err.message}` }] })
      }
    }
    reader.readAsArrayBuffer(file)
  }

  const handleImport = async () => {
    if (!parseResult || parseResult.valid.length === 0) return
    setImporting(true)
    setImportResult(null)

    try {
      const payload = parseResult.valid.map(cameraRowToApiPayload)
      const res = await apiClient.post('/cameras/import', payload)
      setImportResult(res.data)
      queryClient.invalidateQueries({ queryKey: ['cameras-list'] })
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err.message
      setImportResult({
        imported: 0, skipped: 0, errors: parseResult.valid.length,
        created_ids: [], skipped_ids: [],
        error_details: [{ id: '-', error: typeof detail === 'string' ? detail : JSON.stringify(detail) }],
      })
    } finally {
      setImporting(false)
    }
  }

  const overlayStyle: React.CSSProperties = {
    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    zIndex: 50, padding: '1rem',
  }
  const modalStyle: React.CSSProperties = {
    background: '#1e293b', borderRadius: 16, width: '100%', maxWidth: 640,
    maxHeight: '90vh', display: 'flex', flexDirection: 'column',
    boxShadow: '0 25px 50px rgba(0,0,0,0.5)',
  }

  return (
    <div style={overlayStyle} onClick={onClose}>
      <div style={modalStyle} onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div style={{ padding: '20px 24px 0', borderBottom: '1px solid #334155' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h2 style={{ color: '#f1f5f9', fontWeight: 700, fontSize: 16, margin: 0 }}>📋 Import / Export Kamera</h2>
            <button onClick={onClose} style={{ color: '#94a3b8', background: 'none', border: 'none', cursor: 'pointer', fontSize: 18 }}>✕</button>
          </div>
          {/* Tabs */}
          <div style={{ display: 'flex', gap: 0 }}>
            {(['import', 'export'] as const).map(t => (
              <button
                key={t}
                onClick={() => { setTab(t); setParseResult(null); setImportResult(null) }}
                style={{
                  padding: '8px 20px', fontSize: 13, fontWeight: 600,
                  background: 'none', border: 'none', cursor: 'pointer',
                  color: tab === t ? '#60a5fa' : '#64748b',
                  borderBottom: tab === t ? '2px solid #60a5fa' : '2px solid transparent',
                  textTransform: 'capitalize',
                }}
              >{t === 'import' ? '⬆ Import dari Excel' : '⬇ Export ke Excel'}</button>
            ))}
          </div>
        </div>

        {/* Body */}
        <div style={{ padding: 24, overflowY: 'auto', flex: 1 }}>

          {/* ── TAB IMPORT ───────────────────────────────────────────── */}
          {tab === 'import' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {/* Info */}
              <div style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 10, padding: '12px 16px' }}>
                <div style={{ color: '#94a3b8', fontSize: 12, lineHeight: 1.6 }}>
                  <strong style={{ color: '#cbd5e1' }}>Kolom Excel yang didukung:</strong><br />
                  <code style={{ color: '#7dd3fc' }}>id, name, location, ip_address, port, username, password, channel, storage_drive, motion_enabled, retention_days, segment_duration</code><br />
                  Field <code style={{ color: '#fbbf24' }}>id, name, ip_address, password</code> wajib diisi.
                  Kolom <code style={{ color: '#7dd3fc' }}>rtsp_main / rtsp_sub</code> opsional — jika kosong, URL dibuat otomatis dari ip+port+username+password.
                </div>
              </div>

              {/* Template download */}
              <button
                onClick={() => downloadTemplate(storageDrives)}
                style={{
                  padding: '8px 16px', background: '#1e3a5f', border: '1px solid #2563eb',
                  borderRadius: 8, color: '#93c5fd', fontSize: 12, cursor: 'pointer', textAlign: 'left',
                }}
              >
                📥 Download Template Excel (dengan contoh isi)
              </button>

              {/* File picker */}
              <div
                onClick={() => fileInputRef.current?.click()}
                style={{
                  border: '2px dashed #475569', borderRadius: 10, padding: '24px',
                  textAlign: 'center', cursor: 'pointer', color: '#94a3b8', fontSize: 13,
                  background: '#0f172a',
                }}
              >
                {fileName
                  ? <span style={{ color: '#e2e8f0' }}>📄 {fileName}</span>
                  : <span>Klik untuk pilih file Excel (.xlsx)<br /><span style={{ fontSize: 11 }}>atau drag &amp; drop di sini</span></span>
                }
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".xlsx,.xls"
                style={{ display: 'none' }}
                onChange={handleFileChange}
              />

              {/* Parse result preview */}
              {parseResult && (
                <div>
                  {/* Summary */}
                  <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
                    <div style={{ flex: 1, background: '#064e3b', borderRadius: 8, padding: '10px 14px' }}>
                      <div style={{ color: '#6ee7b7', fontWeight: 700, fontSize: 20 }}>{parseResult.valid.length}</div>
                      <div style={{ color: '#a7f3d0', fontSize: 11 }}>Baris valid</div>
                    </div>
                    <div style={{ flex: 1, background: parseResult.errors.length > 0 ? '#7f1d1d' : '#1e293b', borderRadius: 8, padding: '10px 14px' }}>
                      <div style={{ color: parseResult.errors.length > 0 ? '#fca5a5' : '#64748b', fontWeight: 700, fontSize: 20 }}>{parseResult.errors.length}</div>
                      <div style={{ color: parseResult.errors.length > 0 ? '#fca5a5' : '#64748b', fontSize: 11 }}>Baris error</div>
                    </div>
                  </div>

                  {/* Error list */}
                  {parseResult.errors.length > 0 && (
                    <div style={{ background: '#450a0a', border: '1px solid #b91c1c', borderRadius: 8, padding: 12, marginBottom: 12, maxHeight: 120, overflowY: 'auto' }}>
                      {parseResult.errors.map((e, i) => (
                        <div key={i} style={{ color: '#fca5a5', fontSize: 12, marginBottom: 4 }}>
                          Row {e.row}: {e.message}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Valid preview table */}
                  {parseResult.valid.length > 0 && (
                    <div style={{ overflowX: 'auto', borderRadius: 8, border: '1px solid #334155', marginBottom: 12 }}>
                      <table style={{ width: '100%', fontSize: 11, borderCollapse: 'collapse' }}>
                        <thead>
                          <tr style={{ background: '#334155' }}>
                            {['ID', 'Nama', 'IP', 'Port', 'User', 'Channel', 'Drive'].map(h => (
                              <th key={h} style={{ padding: '6px 10px', color: '#94a3b8', textAlign: 'left', fontWeight: 600, whiteSpace: 'nowrap' }}>{h}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {parseResult.valid.slice(0, 10).map((r, i) => (
                            <tr key={i} style={{ borderBottom: '1px solid #1e293b' }}>
                              <td style={{ padding: '5px 10px', color: '#a5b4fc', fontFamily: 'monospace' }}>{r.id}</td>
                              <td style={{ padding: '5px 10px', color: '#e2e8f0' }}>{r.name}</td>
                              <td style={{ padding: '5px 10px', color: '#7dd3fc', fontFamily: 'monospace' }}>{r.ip_address}</td>
                              <td style={{ padding: '5px 10px', color: '#cbd5e1' }}>{r.port}</td>
                              <td style={{ padding: '5px 10px', color: '#cbd5e1' }}>{r.username}</td>
                              <td style={{ padding: '5px 10px', color: '#cbd5e1' }}>{r.channel}</td>
                              <td style={{ padding: '5px 10px', color: '#94a3b8', fontSize: 10 }}>{r.storage_drive}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      {parseResult.valid.length > 10 && (
                        <div style={{ padding: '6px 10px', color: '#64748b', fontSize: 11 }}>...dan {parseResult.valid.length - 10} kamera lainnya</div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Import result */}
              {importResult && (
                <div style={{
                  background: importResult.errors > 0 ? '#451a03' : '#052e16',
                  border: `1px solid ${importResult.errors > 0 ? '#c2410c' : '#15803d'}`,
                  borderRadius: 8, padding: 14,
                }}>
                  <div style={{ color: '#f1f5f9', fontWeight: 600, marginBottom: 8 }}>
                    {importResult.imported > 0 ? '✅' : '⚠️'} Hasil Import
                  </div>
                  <div style={{ display: 'flex', gap: 16, fontSize: 13 }}>
                    <span style={{ color: '#86efac' }}>✓ Imported: <strong>{importResult.imported}</strong></span>
                    <span style={{ color: '#fcd34d' }}>⏭ Skipped: <strong>{importResult.skipped}</strong></span>
                    <span style={{ color: '#fca5a5' }}>✗ Error: <strong>{importResult.errors}</strong></span>
                  </div>
                  {importResult.skipped_ids.length > 0 && (
                    <div style={{ marginTop: 8, fontSize: 11, color: '#fcd34d' }}>Sudah ada: {importResult.skipped_ids.join(', ')}</div>
                  )}
                  {importResult.error_details.length > 0 && (
                    <div style={{ marginTop: 8, maxHeight: 80, overflowY: 'auto' }}>
                      {importResult.error_details.map((e, i) => (
                        <div key={i} style={{ fontSize: 11, color: '#fca5a5' }}>{e.id}: {e.error}</div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* ── TAB EXPORT ────────────────────────────────────────────── */}
          {tab === 'export' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 10, padding: '12px 16px' }}>
                <div style={{ color: '#94a3b8', fontSize: 12, lineHeight: 1.6 }}>
                  Export semua kamera yang ada ke file Excel. File dapat diedit dan diimport kembali.
                  <br /><span style={{ color: '#fbbf24' }}>⚠️ Password tersimpan dalam config_json — pastikan file dijaga keamanannya.</span>
                </div>
              </div>
              <div style={{ background: '#1e293b', borderRadius: 10, padding: 16, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ color: '#e2e8f0', fontWeight: 600 }}>{cameras.length} kamera</div>
                  <div style={{ color: '#64748b', fontSize: 12 }}>Akan diekspor ke Excel</div>
                </div>
                <button
                  onClick={() => exportCameras(cameras)}
                  disabled={cameras.length === 0}
                  style={{
                    padding: '10px 20px', background: cameras.length > 0 ? '#15803d' : '#374151',
                    border: 'none', borderRadius: 8, color: cameras.length > 0 ? '#dcfce7' : '#9ca3af',
                    fontSize: 13, fontWeight: 600, cursor: cameras.length > 0 ? 'pointer' : 'not-allowed',
                  }}
                >
                  ⬇ Download Excel
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{ padding: '16px 24px', borderTop: '1px solid #334155', display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
          {tab === 'import' && parseResult && parseResult.valid.length > 0 && !importResult && (
            <button
              onClick={handleImport}
              disabled={importing}
              style={{
                padding: '9px 20px', background: importing ? '#374151' : '#1d4ed8',
                border: 'none', borderRadius: 8, color: '#dbeafe',
                fontSize: 13, fontWeight: 600, cursor: importing ? 'not-allowed' : 'pointer',
              }}
            >
              {importing ? 'Mengimpor...' : `⬆ Import ${parseResult.valid.length} Kamera`}
            </button>
          )}
          <button
            onClick={onClose}
            style={{
              padding: '9px 20px', background: '#334155',
              border: 'none', borderRadius: 8, color: '#cbd5e1',
              fontSize: 13, cursor: 'pointer',
            }}
          >
            Tutup
          </button>
        </div>
      </div>
    </div>
  )
}
