import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { usersApi } from "@/api/users"
import type { User } from "@/types"
import { useEffect } from 'react'

export default function UsersPage() {
  const [editingId, setEditingId] = useState<number | null>(null)
  const [formData, setFormData] = useState<Partial<User>>({})
  const [showAddForm, setShowAddForm] = useState(false)
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null)
  const queryClient = useQueryClient()

  const { data: users, isLoading } = useQuery({ queryKey: ["users"], queryFn: usersApi.list })

  const createMutation = useMutation({
    mutationFn: usersApi.create,
  })

  useEffect(() => {
    if (createMutation.isSuccess) {
      queryClient.invalidateQueries({ queryKey: ["users"] })
      setShowAddForm(false)
      setFormData({})
      setMessage({ type: "success", text: "User created successfully" })
      setTimeout(() => setMessage(null), 3000)
    }
    if (createMutation.isError) {
      setMessage({ type: "error", text: "Failed to create user" })
      setTimeout(() => setMessage(null), 3000)
    }
  }, [createMutation.isSuccess, createMutation.isError, queryClient])

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<User> }) => usersApi.update(id, data),
  })

  useEffect(() => {
    if (updateMutation.isSuccess) {
      queryClient.invalidateQueries({ queryKey: ["users"] })
      setEditingId(null)
      setFormData({})
      setMessage({ type: "success", text: "User updated successfully" })
      setTimeout(() => setMessage(null), 3000)
    }
    if (updateMutation.isError) {
      setMessage({ type: "error", text: "Failed to update user" })
      setTimeout(() => setMessage(null), 3000)
    }
  }, [updateMutation.isSuccess, updateMutation.isError, queryClient])

  const deleteMutation = useMutation({
    mutationFn: usersApi.delete,
  })

  useEffect(() => {
    if (deleteMutation.isSuccess) {
      queryClient.invalidateQueries({ queryKey: ["users"] })
      setMessage({ type: "success", text: "User deleted successfully" })
      setTimeout(() => setMessage(null), 3000)
    }
    if (deleteMutation.isError) {
      setMessage({ type: "error", text: "Failed to delete user" })
      setTimeout(() => setMessage(null), 3000)
    }
  }, [deleteMutation.isSuccess, deleteMutation.isError, queryClient])

  const handleEdit = (user: User) => {
    setEditingId(user.id)
    setFormData(user)
  }

  const handleSave = (id: number) => {
    updateMutation.mutate({ id, data: formData })
  }

  const handleDelete = (id: number) => {
    if (confirm("Are you sure you want to delete this user?")) {
      deleteMutation.mutate(id)
    }
  }

  const handleCancel = () => {
    setEditingId(null)
    setFormData({})
    setShowAddForm(false)
  }

  const handleChange = (field: keyof User, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const handleCreate = () => {
    createMutation.mutate(formData as User)
  }

  return (
    <div className="flex flex-col h-full p-4 gap-4">
      <div className="flex items-center gap-4 bg-gray-800 rounded px-4 py-3 flex-shrink-0">
        <span className="text-sm font-medium">Users</span>
        <button
          onClick={() => setShowAddForm(true)}
          className="ml-auto px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-sm"
        >
          Add User
        </button>
        {message && (
          <span className={`text-xs ${message.type === "success" ? "text-green-400" : "text-red-400"}`}>
            {message.text}
          </span>
        )}
      </div>

      {showAddForm && (
        <div className="bg-gray-800 rounded p-4">
          <h3 className="font-medium mb-3">Add New User</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm mb-1">Username</label>
              <input
                type="text"
                value={formData.username || ""}
                onChange={(e) => handleChange("username", e.target.value)}
                className="w-full bg-gray-700 rounded px-3 py-2 border border-gray-600"
              />
            </div>
            <div>
              <label className="block text-sm mb-1">Email</label>
              <input
                type="email"
                value={formData.email || ""}
                onChange={(e) => handleChange("email", e.target.value)}
                className="w-full bg-gray-700 rounded px-3 py-2 border border-gray-600"
              />
            </div>
            <div>
              <label className="block text-sm mb-1">Password</label>
              <input
                type="password"
                value={formData.password || ""}
                onChange={(e) => handleChange("password", e.target.value)}
                className="w-full bg-gray-700 rounded px-3 py-2 border border-gray-600"
              />
            </div>
            <div>
              <label className="block text-sm mb-1">Role</label>
              <select
                value={formData.role || "viewer"}
                onChange={(e) => handleChange("role", e.target.value)}
                className="w-full bg-gray-700 rounded px-3 py-2 border border-gray-600"
              >
                <option value="admin">Admin</option>
                <option value="operator">Operator</option>
                <option value="viewer">Viewer</option>
              </select>
            </div>
          </div>
          <div className="mt-3 flex gap-2">
            <button
              onClick={handleCreate}
              disabled={createMutation.isPending}
              className="px-3 py-1 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 rounded text-sm"
            >
              {createMutation.isPending ? "Creating..." : "Create"}
            </button>
            <button onClick={handleCancel} className="px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded text-sm">
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="flex-1 overflow-auto bg-gray-900 rounded">
        {isLoading ? (
          <div className="flex items-center justify-center h-full text-gray-500">Loading...</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-800 sticky top-0">
              <tr>
                <th className="text-left px-4 py-2">Username</th>
                <th className="text-left px-4 py-2">Email</th>
                <th className="text-left px-4 py-2">Role</th>
                <th className="text-left px-4 py-2">Active</th>
                <th className="text-left px-4 py-2">Last Login</th>
                <th className="text-left px-4 py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users?.map((user) => (
                <tr key={user.id} className="border-b border-gray-800 hover:bg-gray-800/50">
                  {editingId === user.id ? (
                    <>
                      <td className="px-4 py-2">
                        <input
                          value={formData.username || ""}
                          onChange={(e) => handleChange("username", e.target.value)}
                          className="bg-gray-700 rounded px-2 py-1 w-full"
                        />
                      </td>
                      <td className="px-4 py-2">
                        <input
                          value={formData.email || ""}
                          onChange={(e) => handleChange("email", e.target.value)}
                          className="bg-gray-700 rounded px-2 py-1 w-full"
                        />
                      </td>
                      <td className="px-4 py-2">
                        <select
                          value={formData.role || "viewer"}
                          onChange={(e) => handleChange("role", e.target.value)}
                          className="bg-gray-700 rounded px-2 py-1 w-full"
                        >
                          <option value="admin">Admin</option>
                          <option value="operator">Operator</option>
                          <option value="viewer">Viewer</option>
                        </select>
                      </td>
                      <td className="px-4 py-2">
                        <input
                          type="checkbox"
                          checked={formData.is_active || false}
                          onChange={(e) => handleChange("is_active", e.target.checked)}
                        />
                      </td>
                      <td className="px-4 py-2">-</td>
                      <td className="px-4 py-2">
                        <button onClick={() => handleSave(user.id)} className="text-green-400 hover:underline mr-2">Save</button>
                        <button onClick={handleCancel} className="text-gray-400 hover:underline">Cancel</button>
                      </td>
                    </>
                  ) : (
                    <>
                      <td className="px-4 py-2">{user.username}</td>
                      <td className="px-4 py-2">{user.email || "-"}</td>
                      <td className="px-4 py-2">
                        <span className={
                          user.role === "admin" ? "text-yellow-400" :
                          user.role === "operator" ? "text-blue-400" : "text-gray-400"
                        }>
                          {user.role}
                        </span>
                      </td>
                      <td className="px-4 py-2">
                        <span className={user.is_active ? "text-green-400" : "text-red-400"}>
                          {user.is_active ? "Yes" : "No"}
                        </span>
                      </td>
                      <td className="px-4 py-2">
                        {user.last_login ? new Date(user.last_login).toLocaleString() : "-"}
                      </td>
                      <td className="px-4 py-2">
                        <button onClick={() => handleEdit(user)} className="text-blue-400 hover:underline mr-2">Edit</button>
                        {user.username !== "admin" && (
                          <button onClick={() => handleDelete(user.id)} className="text-red-400 hover:underline">Delete</button>
                        )}
                      </td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
