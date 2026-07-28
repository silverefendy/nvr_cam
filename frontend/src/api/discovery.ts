import { apiClient } from './client'

export interface DiscoveryRequest {
  network?: string
  timeout?: number
  ports?: number[]
  method?: 'onvif' | 'rtsp_scan'
  camera_only?: boolean
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
  dahua_sdk?: boolean
  suggested_rtsp_main?: string
  suggested_rtsp_sub?: string
  method?: string
}

export interface DiscoveryResponse {
  cameras: DiscoveredCamera[]
  count: number
  total_found: number
  filtered_out: number
  network_scanned?: string
  method_used: string
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
