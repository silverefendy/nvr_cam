import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { CameraDiscovery } from './CameraDiscovery'

type SetupStep = 'welcome' | 'discovery' | 'storage' | 'notifications' | 'complete'

export default function SetupPage() {
  const [currentStep, setCurrentStep] = useState<SetupStep>('welcome')

  const { data: hasSetup } = useQuery({
    queryKey: ['setup-status'],
    queryFn: async () => {
      try {
        const response = await fetch('/api/v1/config/system')
        if (!response.ok) throw new Error('Failed to check setup status')
        const data = await response.json()
        // If we have cameras, assume setup is done
        return data.data?.cameras?.length > 0
      } catch {
        return false
      }
    },
  })

  if (hasSetup === true) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8">
        <div className="bg-gray-800 rounded-lg p-8 max-w-md text-center">
          <h1 className="text-2xl font-bold text-white mb-4">Setup Already Complete</h1>
          <p className="text-gray-400 mb-6">
            Your NVR system has already been configured. You can manage cameras and settings from the respective pages.
          </p>
          <button
            onClick={() => window.location.href = '/'}
            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded text-white"
          >
            Go to Dashboard
          </button>
        </div>
      </div>
    )
  }

  const renderStep = () => {
    switch (currentStep) {
      case 'welcome':
        return (
          <div className="bg-gray-800 rounded-lg p-8 max-w-2xl">
            <h1 className="text-3xl font-bold text-white mb-4">Welcome to NVR Cam</h1>
            <p className="text-gray-400 mb-6">
              This setup wizard will help you configure your CCTV NVR system. You'll be able to:
            </p>
            <ul className="text-gray-300 space-y-2 mb-8">
              <li>• Discover and add ONVIF cameras automatically</li>
              <li>• Configure storage drives for recordings</li>
              <li>• Set up notifications for motion events</li>
              <li>• Configure system settings</li>
            </ul>
            <button
              onClick={() => setCurrentStep('discovery')}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded text-white font-medium"
            >
              Start Setup
            </button>
          </div>
        )

      case 'discovery':
        return (
          <CameraDiscovery
            onNext={() => setCurrentStep('storage')}
            onSkip={() => setCurrentStep('storage')}
          />
        )

      case 'storage':
        return (
          <div className="bg-gray-800 rounded-lg p-8 max-w-2xl">
            <h2 className="text-2xl font-bold text-white mb-4">Storage Configuration</h2>
            <p className="text-gray-400 mb-6">
              Configure your storage drives for video recordings. You can add or remove drives later in the Settings page.
            </p>
            <div className="bg-gray-700 rounded p-4 mb-6">
              <p className="text-gray-300 text-sm">
                For now, please configure your storage drives in the Settings page after completing this wizard.
              </p>
            </div>
            <div className="flex gap-4">
              <button
                onClick={() => setCurrentStep('notifications')}
                className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded text-white"
              >
                Next
              </button>
              <button
                onClick={() => setCurrentStep('discovery')}
                className="px-6 py-2 bg-gray-600 hover:bg-gray-700 rounded text-white"
              >
                Back
              </button>
            </div>
          </div>
        )

      case 'notifications':
        return (
          <div className="bg-gray-800 rounded-lg p-8 max-w-2xl">
            <h2 className="text-2xl font-bold text-white mb-4">Notifications</h2>
            <p className="text-gray-400 mb-6">
              Configure notifications for motion events, camera offline alerts, and disk warnings.
            </p>
            <div className="bg-gray-700 rounded p-4 mb-6">
              <p className="text-gray-300 text-sm">
                For now, please configure notifications in the Settings page after completing this wizard.
              </p>
            </div>
            <div className="flex gap-4">
              <button
                onClick={() => setCurrentStep('complete')}
                className="px-6 py-2 bg-green-600 hover:bg-green-700 rounded text-white"
              >
                Complete Setup
              </button>
              <button
                onClick={() => setCurrentStep('storage')}
                className="px-6 py-2 bg-gray-600 hover:bg-gray-700 rounded text-white"
              >
                Back
              </button>
            </div>
          </div>
        )

      case 'complete':
        return (
          <div className="bg-gray-800 rounded-lg p-8 max-w-2xl text-center">
            <div className="text-green-400 text-6xl mb-4">✓</div>
            <h2 className="text-2xl font-bold text-white mb-4">Setup Complete!</h2>
            <p className="text-gray-400 mb-6">
              Your NVR system is now ready. You can add cameras, configure storage, and set up notifications from the respective pages.
            </p>
            <div className="bg-gray-700 rounded p-4 mb-6 text-left">
              <h3 className="text-white font-medium mb-2">Next Steps:</h3>
              <ul className="text-gray-300 text-sm space-y-1">
                <li>• Go to Cameras page to add or manage cameras</li>
                <li>• Configure storage drives in Settings → Storage</li>
                <li>• Set up notifications in Settings → Notifications</li>
                <li>• View live streams in Live View</li>
              </ul>
            </div>
            <button
              onClick={() => window.location.href = '/'}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded text-white font-medium"
            >
              Go to Dashboard
            </button>
          </div>
        )

      default:
        return null
    }
  }

  return (
    <div className="flex flex-col items-center justify-center h-full p-4 bg-gray-900">
      {renderStep()}
    </div>
  )
}
