import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useAuthStore } from "@/store/auth"
import { ThemeProvider, useTheme } from "@/store/theme"
import { Sidebar } from "@/components/layout/Sidebar"
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
  defaultOptions: {
    queries: {
      retry: 0,
      staleTime: 60_000,
      gcTime: 300_000,
      refetchOnWindowFocus: false,
    }
  }
})

function ProtectedLayout() {
  const { isAuthenticated } = useAuthStore()
  const { isDark } = useTheme()
  if (!isAuthenticated) return <Navigate to="/login" replace />

  return (
    <div style={{
      display: 'flex',
      width: '100vw',
      height: '100dvh',
      overflow: 'hidden',
      background: isDark ? '#0f1117' : '#f1f5f9',
    }}>
      <Sidebar />
      <main style={{
        flex: 1,
        height: '100%',
        overflow: 'hidden',
        minWidth: 0,
        display: 'flex',
        flexDirection: 'column',
        background: isDark ? '#0f1117' : '#f1f5f9',
      }}>
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
          <Route path="*"         element={<Navigate to="/cameras" replace />} />
        </Routes>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/*"     element={<ProtectedLayout />} />
          </Routes>
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  )
}
