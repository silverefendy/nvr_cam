export type UserRole = 'super_admin' | 'admin' | 'operator' | 'viewer' | 'security'
export interface User {
  id: number
  username: string
  email?: string
  full_name?: string
  role: UserRole
  is_active: boolean
  last_login?: string
  created_at: string
  password?: string
}
export interface Camera { id: string; name: string; location?: string; rtsp_main: string; rtsp_sub?: string; storage_drive: string; motion_enabled: boolean; retention_days: number; is_active: boolean; sort_order: number; config_json?: CameraConfig; status: 'online' | 'offline' | 'unknown'; last_snapshot_url?: string }
export interface CameraConfig { motion_zones?: MotionZone[]; bitrate?: number }
export interface MotionZone { name: string; coords?: number[][]; sensitivity?: number }
export interface Recording { id: number; camera_id: string; file_path: string; file_size_mb?: number; started_at: string; ended_at?: string; duration_s?: number; codec: 'H264' | 'H265' | 'AV1'; is_protected: boolean; is_encoded_av1: boolean; play_url?: string }
export interface MotionEvent { id: number; camera_id: string; zone_name?: string; started_at: string; ended_at?: string; duration_s?: number; snapshot_url?: string; severity: 1|2|3; created_at: string }
export interface DriveStatus {
  path: string
  total_gb: number
  used_gb: number
  free_gb: number
  free_pct: number
  total_bytes: number
  used_bytes: number
  free_bytes: number
  camera_count: number
  cameras: string[]
}

export interface StorageStatus {
  drives: DriveStatus[]
  total_tb: number
  used_tb: number
  free_tb: number
  threshold_pct: number
  estimated_days_remaining: number
}
export interface SystemHealth {
  cpu_usage: number
  ram_usage: number
  ram_used_gb: number
  ram_total_gb: number
  disk_usage: number
  disk_used_gb: number
  disk_total_gb: number
  uptime_seconds: number
  cameras_online: number
  cameras_offline: number
  camera_total: number
  services: { name: string; status: string; uptime_s?: number }[]
}
export interface TokenResponse { access_token: string; refresh_token: string; token_type: string; role: UserRole; username: string }