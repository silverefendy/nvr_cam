from pydantic import BaseModel, Field
from datetime import datetime


class CameraGroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=255)
    color: str | None = Field(None, max_length=50)


class CameraGroupResponse(BaseModel):
    id: int
    name: str
    description: str | None
    color: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class CameraAssignGroupRequest(BaseModel):
    group_id: int | None = None
