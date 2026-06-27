"""
Konstanta yang dipakai di seluruh aplikasi.
"""

# ── User Roles ───────────────────────────────────────────────
class Role:
    SUPER_ADMIN = "super_admin"
    ADMIN       = "admin"
    OPERATOR    = "operator"
    VIEWER      = "viewer"
    SECURITY    = "security"

    ALL = [SUPER_ADMIN, ADMIN, OPERATOR, VIEWER, SECURITY]

    # Role yang bisa akses fitur tertentu
    CAN_MANAGE_CAMERAS = [SUPER_ADMIN, ADMIN]
    CAN_MANAGE_USERS   = [SUPER_ADMIN]
    CAN_VIEW_PLAYBACK  = [SUPER_ADMIN, ADMIN, OPERATOR, VIEWER]
    CAN_DELETE_RECORD  = [SUPER_ADMIN, ADMIN]


# ── Camera Status ────────────────────────────────────────────
class CameraStatus:
    ONLINE      = "online"
    OFFLINE     = "offline"
    RECONNECTING = "reconnecting"
    DISABLED    = "disabled"


# ── Motion Severity ──────────────────────────────────────────
class MotionSeverity:
    LOW    = 1
    MEDIUM = 2
    HIGH   = 3


# ── Video Codec ──────────────────────────────────────────────
class VideoCodec:
    H264 = "H264"
    H265 = "H265"
    AV1  = "AV1"


# ── Notification Type ────────────────────────────────────────
class NotifType:
    MOTION          = "motion"
    CAMERA_OFFLINE  = "camera_offline"
    CAMERA_ONLINE   = "camera_online"
    DISK_WARNING    = "disk_warning"
    DISK_CRITICAL   = "disk_critical"
    SYSTEM_START    = "system_start"
    DAILY_REPORT    = "daily_report"


# ── Notification Channel ─────────────────────────────────────
class NotifChannel:
    TELEGRAM = "telegram"
    EMAIL    = "email"


# ── File paths ───────────────────────────────────────────────
RECORDING_PATH_FORMAT = "{drive}/{camera_id}/{date}/{time}.mp4"
SNAPSHOT_PATH_FORMAT  = "{drive}/{camera_id}/snapshots/{datetime}.jpg"
HLS_PATH_FORMAT       = "{hls_dir}/{camera_id}/index.m3u8"
