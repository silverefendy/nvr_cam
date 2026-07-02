import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { buildDahuaRTSP, maskRTSPPassword } from '@/utils/rtsp'
import { RTSPTestButton } from './RTSPTestButton'

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

export const CameraForm: React.FC<Props> = ({ initialData, storageDrives, onSave, onCancel }) => {
  const [formData, setFormData] = useState<CameraFormData>(
    initialData || {
      name: '',
      location: '',
      ip_address: '',
      port: 554,
      username: 'admin',
      password: '',
      channel: 1,
      storage_drive: storageDrives[0] || '',
      motion_enabled: false,
      retention_days: 30,
    }
  )

  const [useCustomRTSP, setUseCustomRTSP] = useState(false)

  const createMutation = useMutation({
    mutationFn: async (data: CameraFormData) => {
      const response = await fetch('/api/v1/config/cameras', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      })
      if (!response.ok) throw new Error('Failed to create camera')
      return response.json()
    },
    onSuccess: () => {
      onSave(formData)
    },
  })

  const updateMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: CameraFormData }) => {
      const response = await fetch(`/api/v1/config/cameras/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      })
      if (!response.ok) throw new Error('Failed to update camera')
      return response.json()
    },
    onSuccess: () => {
      onSave(formData)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (formData.id) {
      updateMutation.mutate({ id: formData.id, data: formData })
    } else {
      createMutation.mutate(formData)
    }
  }

  const handleChange = (field: keyof CameraFormData, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  // Generate RTSP URL preview
  const rtspMainPreview = useCustomRTSP
    ? formData.rtsp_main_custom || ''
    : buildDahuaRTSP(
        formData.ip_address,
        formData.port,
        formData.username,
        formData.password,
        formData.channel,
        0
      )

  const rtspSubPreview = useCustomRTSP
    ? formData.rtsp_sub_custom || ''
    : buildDahuaRTSP(
        formData.ip_address,
        formData.port,
        formData.username,
        formData.password,
        formData.channel,
        1
      )

  const testUrl = rtspMainPreview || rtspSubPreview

  return (
    <div className="bg-gray-800 rounded-lg p-6 max-w-2xl mx-auto">
      <h2 className="text-xl font-bold mb-4 text-white">
        {formData.id ? 'Edit Camera' : 'Add New Camera'}
      </h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Basic Info */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Camera Name *</label>
            <input
              type="text"
              value={formData.name}
              onChange={e => handleChange('name', e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Location</label>
            <input
              type="text"
              value={formData.location || ''}
              onChange={e => handleChange('location', e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            />
          </div>
        </div>

        {/* Network Settings */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">IP Address *</label>
            <input
              type="text"
              value={formData.ip_address}
              onChange={e => handleChange('ip_address', e.target.value)}
              placeholder="192.168.1.101"
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Port</label>
            <input
              type="number"
              value={formData.port}
              onChange={e => handleChange('port', parseInt(e.target.value))}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Username</label>
            <input
              type="text"
              value={formData.username}
              onChange={e => handleChange('username', e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Password *</label>
            <input
              type="password"
              value={formData.password}
              onChange={e => handleChange('password', e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
              required
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Channel</label>
          <input
            type="number"
            value={formData.channel}
            onChange={e => handleChange('channel', parseInt(e.target.value))}
            min="1"
            max="16"
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
          />
        </div>

        {/* RTSP URL Preview */}
        <div className="bg-gray-900 rounded p-3">
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium text-gray-300">RTSP URL</label>
            <label className="flex items-center gap-2 text-sm text-gray-400">
              <input
                type="checkbox"
                checked={useCustomRTSP}
                onChange={e => setUseCustomRTSP(e.target.checked)}
                className="rounded"
              />
              Custom URL
            </label>
          </div>

          {useCustomRTSP ? (
            <div className="space-y-2">
              <input
                type="text"
                value={formData.rtsp_main_custom || ''}
                onChange={e => handleChange('rtsp_main_custom', e.target.value)}
                placeholder="Custom main stream RTSP URL"
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
              />
              <input
                type="text"
                value={formData.rtsp_sub_custom || ''}
                onChange={e => handleChange('rtsp_sub_custom', e.target.value)}
                placeholder="Custom substream RTSP URL"
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
              />
            </div>
          ) : (
            <div className="space-y-1 text-sm">
              <div className="text-gray-400 font-mono break-all">
                Main: {maskRTSPPassword(rtspMainPreview)}
              </div>
              <div className="text-gray-400 font-mono break-all">
                Sub: {maskRTSPPassword(rtspSubPreview)}
              </div>
            </div>
          )}

          <div className="mt-3">
            <RTSPTestButton rtspUrl={testUrl} />
          </div>
        </div>

        {/* Storage & Recording */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Storage Drive *</label>
            <select
              value={formData.storage_drive}
              onChange={e => handleChange('storage_drive', e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
              required
            >
              {storageDrives.map(drive => (
                <option key={drive} value={drive}>
                  {drive}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Retention (days)</label>
            <input
              type="number"
              value={formData.retention_days}
              onChange={e => handleChange('retention_days', parseInt(e.target.value))}
              min="1"
              max="365"
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            />
          </div>
        </div>

        {/* Motion Detection */}
        <div className="flex items-center gap-3">
          <input
            type="checkbox"
            id="motion_enabled"
            checked={formData.motion_enabled}
            onChange={e => handleChange('motion_enabled', e.target.checked)}
            className="rounded"
          />
          <label htmlFor="motion_enabled" className="text-sm font-medium text-gray-300">
            Enable Motion Detection
          </label>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3 pt-4 border-t border-gray-700">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded text-white"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={createMutation.isPending || updateMutation.isPending}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded text-white"
          >
            {createMutation.isPending || updateMutation.isPending
              ? 'Saving...'
              : formData.id
              ? 'Update Camera'
              : 'Add Camera'}
          </button>
        </div>
      </form>
    </div>
  )
}
