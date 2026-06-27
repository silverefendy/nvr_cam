"""
Custom exception classes.
Semua error yang mungkin terjadi di aplikasi didefinisikan di sini.
"""


class CCTVBaseException(Exception):
    """Base exception untuk semua error aplikasi"""
    def __init__(self, message: str, code: str = "UNKNOWN_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class CameraNotFoundException(CCTVBaseException):
    def __init__(self, camera_id: str):
        super().__init__(f"Kamera '{camera_id}' tidak ditemukan", "CAMERA_NOT_FOUND")


class CameraConnectionError(CCTVBaseException):
    def __init__(self, camera_id: str, detail: str = ""):
        super().__init__(
            f"Gagal koneksi ke kamera '{camera_id}': {detail}",
            "CAMERA_CONNECTION_ERROR"
        )


class StorageFullError(CCTVBaseException):
    def __init__(self, drive: str, free_pct: float):
        super().__init__(
            f"Drive '{drive}' hampir penuh: {free_pct:.1f}% tersisa",
            "STORAGE_FULL"
        )


class RecordingNotFoundException(CCTVBaseException):
    def __init__(self, recording_id: int):
        super().__init__(
            f"Rekaman ID {recording_id} tidak ditemukan",
            "RECORDING_NOT_FOUND"
        )


class AuthenticationError(CCTVBaseException):
    def __init__(self):
        super().__init__("Username atau password salah", "AUTH_FAILED")


class AuthorizationError(CCTVBaseException):
    def __init__(self, resource: str = ""):
        super().__init__(
            f"Tidak punya akses ke {resource}".strip(),
            "FORBIDDEN"
        )
