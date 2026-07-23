import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query'
import { useAuthStore } from "@/store/auth"
import { Sidebar } from "@/components/layout/Sidebar"
import { camerasApi } from "@/api/cameras"
import LoginPage    from "@/pages/Login"
import LiveViewPage from "@/pages/LiveView"
import PlaybackPage from "@/pages/Playback"
import EventsPage   from "@/pages/Events"
import CamerasPage  from "@/pages/Cameras"
import StoragePage  from "@/pages/Storage"
import UsersPage    from "@/pages/Users"
import SettingsPage from "@/pages/Settings"
import SystemPage   from "@/pages/System"
import SetupPage    from "@/pages/Setup"

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000 } }
})

function ProtectedLayout() {
  const { isAuthenticated } = useAuthStore()
  const location = useLocation()

  const { data: cameras } = useQuery({
    queryKey: ['cameras'],
    queryFn: camerasApi.list,
    enabled: isAuthenticated,
  })

  if (!isAuthenticated) return <Navigate to="/login" replace />

  if (cameras !== undefined && cameras.length === 0 && location.pathname !== '/setup') {
    return <Navigate to="/setup" replace />
  }

  return (
    <div className="flex h-screen bg-slate-100 text-slate-800 overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-hidden">
        <Routes>
          <Route path="/live"     element={<LiveViewPage />} />
          <Route path="/playback" element={<PlaybackPage />} />
          <Route path="/events"   element={<EventsPage />} />
          <Route path="/cameras"  element={<CamerasPage />} />
          <Route path="/storage"  element={<StoragePage />} />
          <Route path="/users"    element={<UsersPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/system"   element={<SystemPage />} />
          <Route path="/setup"    element={<SetupPage />} />
          <Route path="*"         element={<Navigate to="/live" replace />} />
        </Routes>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/*"     element={<ProtectedLayout />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
