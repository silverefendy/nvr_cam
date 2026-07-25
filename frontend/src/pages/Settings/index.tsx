import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { NotificationForm } from "@/components/settings/NotificationForm"
import { StorageForm } from "@/components/settings/StorageForm"
import { useTheme } from "@/store/theme"

type TabType = "general" | "notification" | "storage"

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabType>("general")
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null)
  const [formValues, setFormValues] = useState<Record<string, any>>({})
  const queryClient = useQueryClient()
  const { isDark } = useTheme()

  // ── Theme tokens ───────────────────────────────────────────────────────────
  const bg    = isDark ? '#0f1117' : '#f1f5f9'
  const card  = isDark ? '#1a1d27' : '#ffffff'
  const cardB = isDark ? '#2a2d3a' : '#e2e8f0'
  const text  = isDark ? '#e2e8f0' : '#1e293b'
  const sub   = isDark ? '#64748b' : '#94a3b8'
  const inputBg = isDark ? '#12151f' : '#f8fafc'
  const sideActive = isDark ? '#0284c7' : '#0284c7'

  const showMsg = (type: "success" | "error", msg: string) => {
    setMessage({ type, text: msg })
    setTimeout(() => setMessage(null), 3500)
  }

  // ── Query system config ────────────────────────────────────────────────────
  const { data: systemConfig, isLoading: systemLoading } = useQuery({
    queryKey: ["config-system"],
    queryFn: async () => {
      const { apiClient } = await import('@/api/client')
      try {
        const res = await apiClient.get('/config/system')
        return res.data
      } catch {
        return { data: {} }
      }
    },
    retry: false,
  })

  // Isi form ketika data datang
  useEffect(() => {
    if (systemConfig?.data) {
      setFormValues(systemConfig.data)
    }
  }, [systemConfig])

  const updateSystemMutation = useMutation({
    mutationFn: async (data: Record<string, any>) => {
      const { apiClient } = await import('@/api/client')
      const response = await apiClient.put('/config/system', data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["config-system"] })
      showMsg("success", "Pengaturan berhasil disimpan")
    },
    onError: () => showMsg("error", "Gagal menyimpan pengaturan"),
  })

  const handleFieldChange = (field: string, value: any) => {
    setFormValues(prev => ({ ...prev, [field]: value }))
  }

  const handleGeneralSave = () => {
    updateSystemMutation.mutate(formValues)
  }

  // ── Shared styles ──────────────────────────────────────────────────────────
  const cardStyle: React.CSSProperties = {
    background: card, border: `1px solid ${cardB}`,
    borderRadius: 12, padding: 20,
    boxShadow: isDark ? '0 2px 8px rgba(0,0,0,0.3)' : '0 1px 4px rgba(0,0,0,0.06)',
  }
  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '8px 12px',
    borderRadius: 8, border: `1px solid ${cardB}`,
    background: inputBg, color: text,
    fontSize: 13, outline: 'none', boxSizing: 'border-box',
  }
  const labelStyle: React.CSSProperties = {
    display: 'block', fontSize: 12, fontWeight: 600,
    color: sub, marginBottom: 6,
  }

  const Field = ({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) => (
    <div>
      <label style={labelStyle}>{label}</label>
      {children}
      {hint && <p style={{ fontSize: 11, color: sub, marginTop: 4 }}>{hint}</p>}
    </div>
  )

  // ── Render General tab ─────────────────────────────────────────────────────
  const renderGeneral = () => {
    if (systemLoading) return (
      <div style={{ color: sub, padding: 40, textAlign: 'center' }}>Memuat konfigurasi...</div>
    )

    const cfg = formValues

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

        {/* Storage */}
        <div style={cardStyle}>
          <h3 style={{ fontSize: 14, fontWeight: 700, color: text, margin: '0 0 16px', display: 'flex', alignItems: 'center', gap: 8 }}>
            💾 Storage
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <Field label="Cleanup Threshold (%)" hint="Cleanup otomatis jika free space di bawah persentase ini">
              <input type="number" style={inputStyle}
                value={cfg.storage_threshold_pct ?? 10}
                onChange={e => handleFieldChange('storage_threshold_pct', parseFloat(e.target.value))} />
            </Field>
            <Field label="Recording Segment Duration (detik)">
              <input type="number" style={inputStyle}
                value={cfg.segment_duration_s ?? 300}
                onChange={e => handleFieldChange('segment_duration_s', parseInt(e.target.value))} />
            </Field>
          </div>
        </div>

        {/* Kamera */}
        <div style={cardStyle}>
          <h3 style={{ fontSize: 14, fontWeight: 700, color: text, margin: '0 0 16px', display: 'flex', alignItems: 'center', gap: 8 }}>
            📷 Kamera & Stream
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <Field label="Reconnect Delay (detik)" hint="Jeda sebelum reconnect ke kamera yang disconnect">
              <input type="number" style={inputStyle}
                value={cfg.reconnect_delay_s ?? 5}
                onChange={e => handleFieldChange('reconnect_delay_s', parseInt(e.target.value))} />
            </Field>
            <Field label="HLS Segment Duration (detik)">
              <input type="number" style={inputStyle}
                value={cfg.hls_segment_duration_s ?? 2}
                onChange={e => handleFieldChange('hls_segment_duration_s', parseInt(e.target.value))} />
            </Field>
          </div>
        </div>

        {/* Motion */}
        <div style={cardStyle}>
          <h3 style={{ fontSize: 14, fontWeight: 700, color: text, margin: '0 0 16px', display: 'flex', alignItems: 'center', gap: 8 }}>
            🏃 Motion Detection
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
            <Field label="Frame Skip" hint="Lewati N frame antar pengecekan">
              <input type="number" style={inputStyle}
                value={cfg.motion_frame_skip ?? 1}
                onChange={e => handleFieldChange('motion_frame_skip', parseInt(e.target.value))} />
            </Field>
            <Field label="Cooldown (detik)" hint="Jeda antar deteksi motion">
              <input type="number" style={inputStyle}
                value={cfg.motion_cooldown_s ?? 30}
                onChange={e => handleFieldChange('motion_cooldown_s', parseInt(e.target.value))} />
            </Field>
            <Field label="Threshold (%)" hint="% perubahan piksel untuk dianggap motion">
              <input type="number" style={inputStyle}
                value={cfg.motion_threshold_pct ?? 5}
                onChange={e => handleFieldChange('motion_threshold_pct', parseFloat(e.target.value))} />
            </Field>
          </div>
        </div>

        {/* AV1 */}
        <div style={cardStyle}>
          <h3 style={{ fontSize: 14, fontWeight: 700, color: text, margin: '0 0 16px', display: 'flex', alignItems: 'center', gap: 8 }}>
            🎬 AV1 Encoding
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
            <Field label="CRF (0–63)" hint="Semakin kecil = kualitas lebih tinggi">
              <input type="number" min={0} max={63} style={inputStyle}
                value={cfg.av1_crf ?? 30}
                onChange={e => handleFieldChange('av1_crf', parseInt(e.target.value))} />
            </Field>
            <Field label="Preset (0–13)" hint="Semakin kecil = encoding lebih lambat tapi kecil">
              <input type="number" min={0} max={13} style={inputStyle}
                value={cfg.av1_preset ?? 6}
                onChange={e => handleFieldChange('av1_preset', parseInt(e.target.value))} />
            </Field>
            <Field label="Max Parallel Jobs">
              <input type="number" min={1} max={8} style={inputStyle}
                value={cfg.av1_max_parallel ?? 2}
                onChange={e => handleFieldChange('av1_max_parallel', parseInt(e.target.value))} />
            </Field>
            <Field label="Jadwal Mulai">
              <input type="time" style={inputStyle}
                value={cfg.av1_schedule_start ?? '01:00'}
                onChange={e => handleFieldChange('av1_schedule_start', e.target.value)} />
            </Field>
            <Field label="Jadwal Selesai">
              <input type="time" style={inputStyle}
                value={cfg.av1_schedule_stop ?? '05:00'}
                onChange={e => handleFieldChange('av1_schedule_stop', e.target.value)} />
            </Field>
          </div>
        </div>

        {/* Tombol Save */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, paddingBottom: 8 }}>
          <button
            onClick={() => setFormValues(systemConfig?.data ?? {})}
            style={{
              padding: '10px 20px', borderRadius: 8, fontSize: 13, fontWeight: 600,
              border: `1px solid ${cardB}`, background: 'transparent', color: sub, cursor: 'pointer',
            }}
          >
            Reset
          </button>
          <button
            onClick={handleGeneralSave}
            disabled={updateSystemMutation.isPending}
            style={{
              padding: '10px 24px', borderRadius: 8, fontSize: 13, fontWeight: 700,
              background: updateSystemMutation.isPending ? sub : '#0284c7',
              color: '#fff', border: 'none', cursor: 'pointer',
            }}
          >
            {updateSystemMutation.isPending ? 'Menyimpan...' : '💾 Simpan Pengaturan'}
          </button>
        </div>
      </div>
    )
  }

  const tabs: { id: TabType; label: string; icon: string }[] = [
    { id: 'general',      label: 'General',      icon: '⚙️' },
    { id: 'notification', label: 'Notifikasi',   icon: '🔔' },
    { id: 'storage',      label: 'Storage',       icon: '💾' },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: bg, padding: 16, gap: 12, overflow: 'hidden' }}>

      {/* Header */}
      <div style={{
        background: card, border: `1px solid ${cardB}`, borderRadius: 12,
        padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0,
      }}>
        <span style={{ fontSize: 16 }}>⚙️</span>
        <h1 style={{ fontSize: 15, fontWeight: 700, color: text, margin: 0 }}>Settings</h1>
        {message && (
          <span style={{
            marginLeft: 'auto', fontSize: 12, padding: '4px 12px', borderRadius: 99, fontWeight: 600,
            background: message.type === 'success' ? (isDark ? '#052e16' : '#dcfce7') : (isDark ? '#2d0a0a' : '#fee2e2'),
            color: message.type === 'success' ? '#10b981' : '#ef4444',
            border: `1px solid ${message.type === 'success' ? '#10b98140' : '#ef444440'}`,
          }}>
            {message.type === 'success' ? '✓' : '✗'} {message.text}
          </span>
        )}
      </div>

      {/* Body */}
      <div style={{ display: 'flex', gap: 12, flex: 1, minHeight: 0 }}>

        {/* Sidebar tabs */}
        <div style={{
          width: 180, background: card, border: `1px solid ${cardB}`,
          borderRadius: 12, padding: 8, display: 'flex', flexDirection: 'column', gap: 2, flexShrink: 0,
        }}>
          {tabs.map(t => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              style={{
                width: '100%', textAlign: 'left', padding: '10px 12px',
                borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: 'pointer',
                border: 'none',
                background: activeTab === t.id ? sideActive : 'transparent',
                color: activeTab === t.id ? '#fff' : sub,
                display: 'flex', alignItems: 'center', gap: 8,
                transition: 'all 0.15s',
              }}
            >
              <span>{t.icon}</span> {t.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {activeTab === 'general'      && renderGeneral()}
          {activeTab === 'notification' && (
            <NotificationForm onSave={() => showMsg("success", "Pengaturan notifikasi disimpan")} />
          )}
          {activeTab === 'storage' && (
            <StorageForm onSave={() => showMsg("success", "Konfigurasi storage disimpan")} />
          )}
        </div>
      </div>
    </div>
  )
}
