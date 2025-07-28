from fastapi import APIRouter, HTTPException, Depends
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, RegisterRequest
from app.services.auth_service import AuthService
from app.schemas.user import UserResponse
from app.dependencies import get_current_user

router = APIRouter()

@router.post("/login", response_model=LoginResponse)
async def login(login_data: LoginRequest):
    """사용자 로그인"""
    try:
        auth_service = AuthService()
        result = await auth_service.login(login_data.email, login_data.password)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/register", response_model=LoginResponse)
async def register(register_data: RegisterRequest):
    """사용자 회원가입"""
    try:
        auth_service = AuthService()
        result = await auth_service.register(
            email=register_data.email,
            password=register_data.password,
            username=register_data.username,
            affiliation=register_data.affiliation,
            is_membership=register_data.is_membership
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/me", response_model=UserResponse)
async def get_current_user_endpoint(current_user = Depends(get_current_user)):
    """현재 로그인한 사용자 정보 조회 (항상 DB에서 최신값 반환)"""
    return current_user

@router.post("/refresh")
async def refresh_token(refresh_token: str):
    """리프레시 토큰으로 새로운 액세스 토큰 발급"""
    try:
        auth_service = AuthService()
        result = await auth_service.refresh_token(refresh_token)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/logout")
async def logout():
    """로그아웃"""
    try:
        auth_service = AuthService()
        result = await auth_service.logout()
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) 