import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useAuthStore } from "@/store/auth"
import { Sidebar } from "@/components/layout/Sidebar"
import LoginPage   from "@/pages/Login"
import LiveViewPage from "@/pages/LiveView"
import PlaybackPage from "@/pages/Playback"
const queryClient = new QueryClient({ defaultOptions:{ queries:{ retry:1, staleTime:30_000 } } })
function ProtectedLayout() {
  const { isAuthenticated } = useAuthStore()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return (
    <div className="flex h-screen bg-gray-950 text-white overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-hidden">
        <Routes>
          <Route path="/live"     element={<LiveViewPage />} />
          <Route path="/playback" element={<PlaybackPage />} />
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