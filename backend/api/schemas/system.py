from pydantic import BaseModel


class ServiceStatus(BaseModel):
    name: str
    status: str   # running | stopped | error
    uptime_s: int | None


class SystemHealth(BaseModel):
    cpu_pct: float
    ram_pct: float
    ram_used_gb: float
    ram_total_gb: float
    uptime_s: int
    services: list[ServiceStatus]
    camera_online: int
    camera_offline: int
    camera_total: int
