from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID

class UserBase(BaseModel):
    username: Optional[str] = None
    affiliation: Optional[str] = None

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    username: Optional[str] = None
    affiliation: Optional[str] = None
    is_active: Optional[bool] = None
    is_membership: Optional[bool] = None

class UserResponse(BaseModel):
    id: UUID
    email: Optional[str] = None  # auth.users에서 가져온 email
    username: Optional[str] = None
    affiliation: Optional[str] = None
    is_active: bool
    is_membership: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True 