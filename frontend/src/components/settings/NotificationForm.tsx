import React, { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'

interface NotificationFormData {
  telegram_bot_token?: string
  telegram_chat_id?: string
  telegram_enabled?: boolean
  email_host?: string
  email_port?: number
  email_user?: string
  email_password?: string
  email_enabled?: boolean
  notify_on_motion?: boolean
  notify_on_camera_offline?: boolean
  notify_on_disk_warning?: boolean
  disk_warning_threshold_pct?: number
}

interface Props {
  initialData?: NotificationFormData
  onSave: (data: NotificationFormData) => void
}

export const NotificationForm: React.FC<Props> = ({ initialData, onSave }) => {
  const [formData, setFormData] = useState<NotificationFormData>(
    initialData || {
      telegram_enabled: false,
      email_enabled: false,
      notify_on_motion: true,
      notify_on_camera_offline: true,
      notify_on_disk_warning: true,
      disk_warning_threshold_pct: 10,
    }
  )

  const { data: currentConfig } = useQuery({
    queryKey: ['notifications-config'],
    queryFn: async () => {
      const response = await fetch('/api/v1/config/notifications')
      if (!response.ok) throw new Error('Failed to fetch notifications config')
      return response.json()
    },
    onSuccess: (data) => {
      if (!initialData) {
        setFormData(data.data || {})
      }
    },
  })

  const updateMutation = useMutation({
    mutationFn: async (data: NotificationFormData) => {
      const response = await fetch('/api/v1/config/notifications', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      })
      if (!response.ok) throw new Error('Failed to update notifications')
      return response.json()
    },
    onSuccess: () => {
      onSave(formData)
    },
  })

  const testMutation = useMutation({
    mutationFn: async (type: 'telegram' | 'email') => {
      const response = await fetch('/api/v1/config/notifications/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          [type]: true,
          test_message: 'Test notification from NVR System',
        }),
      })
      if (!response.ok) throw new Error('Test failed')
      return response.json()
    },
  })

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault()
    updateMutation.mutate(formData)
  }

  const handleChange = (field: keyof NotificationFormData, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const handleTestTelegram = () => {
    testMutation.mutate('telegram')
  }

  const handleTestEmail = () => {
    testMutation.mutate('email')
  }

  return (
    <form onSubmit={handleSave} className="space-y-6">
      {/* Telegram Settings */}
      <div className="bg-gray-800 rounded-lg p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">Telegram</h3>
          <label className="flex items-center gap-2 text-sm text-gray-300">
            <input
              type="checkbox"
              checked={formData.telegram_enabled || false}
              onChange={e => handleChange('telegram_enabled', e.target.checked)}
              className="rounded"
            />
            Enabled
          </label>
        </div>

        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Bot Token</label>
            <input
              type="text"
              value={formData.telegram_bot_token || ''}
              onChange={e => handleChange('telegram_bot_token', e.target.value)}
              placeholder="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Chat ID</label>
            <input
              type="text"
              value={formData.telegram_chat_id || ''}
              onChange={e => handleChange('telegram_chat_id', e.target.value)}
              placeholder="-1001234567890"
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            />
          </div>
          <button
            type="button"
            onClick={handleTestTelegram}
            disabled={testMutation.isPending || !formData.telegram_bot_token || !formData.telegram_chat_id}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded text-white text-sm"
          >
            {testMutation.isPending ? 'Sending...' : 'Test Telegram'}
          </button>
        </div>
      </div>

      {/* Email Settings */}
      <div className="bg-gray-800 rounded-lg p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">Email</h3>
          <label className="flex items-center gap-2 text-sm text-gray-300">
            <input
              type="checkbox"
              checked={formData.email_enabled || false}
              onChange={e => handleChange('email_enabled', e.target.checked)}
              className="rounded"
            />
            Enabled
          </label>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">SMTP Host</label>
            <input
              type="text"
              value={formData.email_host || ''}
              onChange={e => handleChange('email_host', e.target.value)}
              placeholder="smtp.gmail.com"
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Port</label>
            <input
              type="number"
              value={formData.email_port || 587}
              onChange={e => handleChange('email_port', parseInt(e.target.value))}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Username</label>
            <input
              type="text"
              value={formData.email_user || ''}
              onChange={e => handleChange('email_user', e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Password</label>
            <input
              type="password"
              value={formData.email_password || ''}
              onChange={e => handleChange('email_password', e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            />
          </div>
        </div>
        <button
          type="button"
          onClick={handleTestEmail}
          disabled={testMutation.isPending || !formData.email_host}
          className="mt-3 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded text-white text-sm"
        >
          {testMutation.isPending ? 'Sending...' : 'Test Email'}
        </button>
      </div>

      {/* Notification Triggers */}
      <div className="bg-gray-800 rounded-lg p-4">
        <h3 className="text-lg font-semibold text-white mb-4">What to Notify</h3>

        <div className="space-y-3">
          <label className="flex items-center gap-3 text-gray-300">
            <input
              type="checkbox"
              checked={formData.notify_on_motion || false}
              onChange={e => handleChange('notify_on_motion', e.target.checked)}
              className="rounded"
            />
            <span>Motion detection events</span>
          </label>

          <label className="flex items-center gap-3 text-gray-300">
            <input
              type="checkbox"
              checked={formData.notify_on_camera_offline || false}
              onChange={e => handleChange('notify_on_camera_offline', e.target.checked)}
              className="rounded"
            />
            <span>Camera goes offline</span>
          </label>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={formData.notify_on_disk_warning || false}
              onChange={e => handleChange('notify_on_disk_warning', e.target.checked)}
              className="rounded"
            />
            <span className="text-gray-300">Disk space warning (threshold: </span>
            <input
              type="number"
              value={formData.disk_warning_threshold_pct || 10}
              onChange={e => handleChange('disk_warning_threshold_pct', parseInt(e.target.value))}
              min="1"
              max="50"
              className="w-16 bg-gray-700 border border-gray-600 rounded px-2 py-1 text-white text-sm"
            />
            <span className="text-gray-300">%)</span>
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex justify-end">
        <button
          type="submit"
          disabled={updateMutation.isPending}
          className="px-6 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 rounded text-white"
        >
          {updateMutation.isPending ? 'Saving...' : 'Save Settings'}
        </button>
      </div>

      {/* Test Result */}
      {testMutation.data && (
        <div
          className={`p-3 rounded ${
            testMutation.data.success ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'
          }`}
        >
          {testMutation.data.message}
        </div>
      )}
    </form>
  )
}
