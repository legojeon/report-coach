from pydantic import BaseModel, EmailStr
from typing import Optional

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    username: str
    affiliation: Optional[str] = None
    is_membership: Optional[bool] = False

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user_id: str  # UUID를 문자열로
    email: str
    username: Optional[str] = None
    affiliation: Optional[str] = None
    is_membership: Optional[bool] = False

class TokenData(BaseModel):
    user_id: Optional[str] = None  # UUID를 문자열로
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    is_membership: Optional[bool] = None 