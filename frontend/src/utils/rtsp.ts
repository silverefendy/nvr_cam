/**
 * RTSP URL builder utilities for different camera brands.
 */

export type CameraBrand = 'dahua' | 'hikvision' | 'generic'

export interface RTSPConfig {
  ip: string
  port: number
  username: string
  password: string
  channel?: number
  subtype?: 0 | 1
}

/**
 * Build Dahua RTSP URL
 * Main stream: rtsp://{user}:{pass}@{ip}:{port}/cam/realmonitor?channel={ch}&subtype=0
 * Sub stream:  rtsp://{user}:{pass}@{ip}:{port}/cam/realmonitor?channel={ch}&subtype=1
 */
export function buildDahuaRTSP(
  ip: string,
  port: number,
  user: string,
  pass: string,
  channel: number = 1,
  subtype: 0 | 1 = 0
): string {
  return `rtsp://${user}:${pass}@${ip}:${port}/cam/realmonitor?channel=${channel}&subtype=${subtype}`
}

/**
 * Build Hikvision RTSP URL
 * Main stream: rtsp://{user}:{pass}@{ip}:{port}/Streaming/Channels/{channel}01
 * Sub stream:  rtsp://{user}:{pass}@{ip}:{port}/Streaming/Channels/{channel}02
 */
export function buildHikvisionRTSP(
  ip: string,
  port: number,
  user: string,
  pass: string,
  channel: number = 1,
  subtype: 1 | 2 = 1
): string {
  return `rtsp://${user}:${pass}@${ip}:${port}/Streaming/Channels/${channel}0${subtype}`
}

/**
 * Build generic RTSP URL
 */
export function buildGenericRTSP(
  ip: string,
  port: number,
  user: string,
  pass: string,
  path: string = '/stream1'
): string {
  return `rtsp://${user}:${pass}@${ip}:${port}${path}`
}

/**
 * Build RTSP URL based on camera brand
 */
export function buildRTSPURL(
  brand: CameraBrand,
  config: RTSPConfig
): string {
  const { ip, port, username, password, channel = 1, subtype = 0 } = config

  switch (brand) {
    case 'dahua':
      return buildDahuaRTSP(ip, port, username, password, channel, subtype as 0 | 1)
    case 'hikvision':
      return buildHikvisionRTSP(ip, port, username, password, channel, (subtype + 1) as 1 | 2)
    case 'generic':
    default:
      return buildGenericRTSP(ip, port, username, password)
  }
}

/**
 * Mask password in RTSP URL for display
 */
export function maskRTSPPassword(url: string): string {
  return url.replace(/rtsp:\/\/([^:]+):([^@]+)@/, 'rtsp://$1:***@')
}

/**
 * Validate RTSP URL format
 */
export function isValidRTSPURL(url: string): boolean {
  return /^rtsp:\/\/[^\s:@]+:[^\s@]+@[^\s:]+:[0-9]+/.test(url)
}

/**
 * Extract IP from RTSP URL
 */
export function extractIPFromRTSP(url: string): string | null {
  const match = url.match(/@([^:]+):/)
  return match ? match[1] : null
}

/**
 * Extract port from RTSP URL
 */
export function extractPortFromRTSP(url: string): number | null {
  const match = url.match(/:(\d+)/)
  return match ? parseInt(match[1], 10) : null
}
