path = "frontend/src/pages/Settings/index.tsx"
content = open(path, encoding="utf-8").read()

old1 = """  const { data: systemConfig, isLoading: systemLoading } = useQuery({
    queryKey: ["config-system"],
    queryFn: async () => {
      const response = await fetch('/api/v1/config/system', {
        headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
      })
      if (!response.ok) return { data: {} }
      return response.json()
    },
    retry: false,
  })"""

new1 = """  const { data: systemConfig, isLoading: systemLoading } = useQuery({
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
  })"""

old2 = """  const updateSystemMutation = useMutation({
    mutationFn: async (data: Record<string, any>) => {
      const response = await fetch('/api/v1/config/system', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify(data),
      })
      if (!response.ok) throw new Error('Gagal menyimpan')
      return response.json()
    },"""

new2 = """  const updateSystemMutation = useMutation({
    mutationFn: async (data: Record<string, any>) => {
      const { apiClient } = await import('@/api/client')
      const response = await apiClient.put('/config/system', data)
      return response.data
    },"""

if old1 not in content: print("ERROR: patch1 tidak ditemukan - cek manual")
elif old2 not in content: print("ERROR: patch2 tidak ditemukan - cek manual")
else:
    content = content.replace(old1, new1, 1).replace(old2, new2, 1)
    open(path, "w", encoding="utf-8").write(content)
    print("OK Settings/index.tsx")
