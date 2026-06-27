import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { authApi } from "@/api/auth"
import { useAuthStore } from "@/store/auth"
export default function LoginPage() {
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)
  const { setAuth } = useAuthStore()
  const navigate = useNavigate()
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); setLoading(true); setError("")
    try {
      const token = await authApi.login(username, password)
      const user = await authApi.me()
      setAuth(user, token.access_token)
      navigate("/live")
    } catch { setError("Username atau password salah") }
    finally { setLoading(false) }
  }
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900">
      <div className="w-80 bg-gray-800 rounded-lg p-6">
        <h1 className="text-xl font-semibold text-white mb-6 text-center">📹 CCTV NVR</h1>
        <form onSubmit={handleSubmit} className="space-y-4">
          <input value={username} onChange={e=>setUsername(e.target.value)} placeholder="Username" required className="w-full p-2 rounded bg-gray-700 text-white text-sm" />
          <input type="password" value={password} onChange={e=>setPassword(e.target.value)} placeholder="Password" required className="w-full p-2 rounded bg-gray-700 text-white text-sm" />
          {error && <p className="text-red-400 text-xs">{error}</p>}
          <button type="submit" disabled={loading} className="w-full p-2 rounded bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium disabled:opacity-50">{loading?"Masuk...":"Login"}</button>
        </form>
      </div>
    </div>
  )
}