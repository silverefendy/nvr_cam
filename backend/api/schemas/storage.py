from pydantic import BaseModel


class DriveStatus(BaseModel):
    path: str
    mount: Optional[str] = None   # alias untuk path (dari router)
    label: Optional[str] = None   # nama drive (e.g. "driveE")
    total_gb: float
    used_gb: float
    free_gb: float
    free_pct: float
    cameras: list[str]


class StorageStatus(BaseModel):
    drives: list[DriveStatus]
    total_tb: float
    used_tb: float
    free_tb: float
    estimated_days_remaining: float
