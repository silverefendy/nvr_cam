path = "frontend/src/pages/Cameras/index.tsx"
with open(path, encoding="utf-8-sig") as f:
    content = f.read()

# Fix 1: tambah import apiClient
old1 = "import { useState } from 'react'\nimport { useQuery, useMutation, useQueryClient } from \"@tanstack/react-query\""
new1 = "import { useState } from 'react'\nimport { useQuery, useMutation, useQueryClient } from \"@tanstack/react-query\"\nimport { apiClient } from '@/api/client'"

# Fix 2: fetch cameras → apiClient
old2 = """      queryFn: async () => {
      const response = await fetch('/api/v1/config/cameras')
      if (!response.ok) throw new Error('Failed to fetch cameras')
      const data = await response.json()
      return data.data?.cameras || []
    }"""
new2 = """      queryFn: async () => {
      const res = await apiClient.get('/config/cameras')
      return res.data?.data?.cameras || []
    }"""

# Fix 3: fetch storage → apiClient
old3 = """    queryFn: async () => {
      const response = await fetch('/api/v1/storage/status')
      if (!response.ok) throw new Error('Failed to fetch storage drives')
      const data = await response.json()
      return data.drives?.map((d: any) => d.path) || []
    },"""
new3 = """    queryFn: async () => {
      const res = await apiClient.get('/storage/status')
      return res.data?.drives?.map((d: any) => d.path) || []
    },"""

# Fix 4: fetch DELETE → apiClient
old4 = """    mutationFn: async (id: string) => {
      const response = await fetch(`/api/v1/config/cameras/${id}`, {
        method: 'DELETE',
      })
      if (!response.ok) throw new Error('Failed to delete camera')
      return response.json()
    },"""
new4 = """    mutationFn: async (id: string) => {
      const res = await apiClient.delete(`/config/cameras/${id}`)
      return res.data
    },"""

result = content
for old, new in [(old1,new1),(old2,new2),(old3,new3),(old4,new4)]:
    if old in result:
        result = result.replace(old, new)
        print(f"PATCHED: {old[:40].strip()}")
    else:
        print(f"NOT FOUND: {old[:40].strip()}")

with open(path, "w", encoding="utf-8") as f:
    f.write(result)
