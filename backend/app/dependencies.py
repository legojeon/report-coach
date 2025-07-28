from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.services.auth_service import AuthService

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """현재 로그인한 사용자 확인 - 공통 의존성 함수"""
    print("get_current_user")
    try:
        auth_service = AuthService()
        user = await auth_service.get_current_user(credentials.credentials)
        print("user:",user)
        return user
    except Exception as e:
        raise HTTPException(status_code=401, detail="인증이 필요합니다. 로그인해주세요.") 