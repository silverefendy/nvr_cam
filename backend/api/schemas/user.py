from datetime import datetime
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    username: str
    password: str
    email: EmailStr | None = None
    full_name: str | None = None
    role: str = "viewer"


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    role: str | None = None
    is_active: bool | None = None
    password: str | None = None


class UserResponse(BaseModel):
    id: str
    username: str
    email: str | None
    full_name: str | None
    role: str
    is_active: bool
    last_login: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True
