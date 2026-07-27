import { apiClient } from './client'

export interface DiscoveryRequest {
  network?: string
  timeout?: number
  ports?: number[]
}

export interface DiscoveredCamera {
  ip: string
  port: number
  manufacturer?: string
  model?: string
  name?: string
  rtsp_url?: string
  onvif_url?: string
  mac_address?: string
}

export interface DiscoveryResponse {
  cameras: DiscoveredCamera[]
  count: number
  network_scanned?: string
}

export interface DiscoveryStatus {
  is_running: boolean
  cameras_found: number
}

export const discoveryApi = {
  scan: (req: DiscoveryRequest = {}) =>
    apiClient.post<DiscoveryResponse>('/discovery/cameras', req).then(r => r.data),

  status: () =>
    apiClient.get<DiscoveryStatus>('/discovery/status').then(r => r.data),

  testCamera: (ip: string, port = 554, username?: string, password?: string) =>
    apiClient
      .post(`/discovery/cameras/${ip}/test`, null, {
        params: { port, username, password },
      })
      .then(r => r.data),
}
