from datetime import datetime, timedelta
from typing import Optional
from app.models.user import User
from app.supabase_client import supabase
import os
from dotenv import load_dotenv
import logging

# .env 파일 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self):
        pass
    
    async def login(self, email: str, password: str):
        """
        Supabase Auth를 사용한 로그인
        """
        try:
            # Supabase Auth로 로그인
            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            user = response.user
            session = response.session
            
            if not user:
                raise Exception("Invalid email or password")
            
            # users 테이블에서 추가 정보 조회
            profile_response = supabase.table("users").select("*").eq("id", user.id).execute()
            
            profile_data = profile_response.data[0] if profile_response.data else {
                "id": user.id,
                "username": None,
                "affiliation": None,
                "is_membership": False,
                "is_active": True
            }
            
            # 계정 활성화 상태 확인
            if not profile_data.get("is_active", True):
                raise Exception("Account is deactivated. Please contact support.")
            
            # auth.users에서 email 추가
            profile_data["email"] = user.email
            
            return {
                "access_token": session.access_token,
                "refresh_token": session.refresh_token,
                "token_type": "bearer",
                "user_id": str(user.id),
                "email": user.email,  # auth.users에서 가져온 email
                "username": profile_data.get("username"),
                "affiliation": profile_data.get("affiliation"),
                "is_membership": profile_data.get("is_membership", False)
            }
            
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            raise Exception(f"Login failed: {str(e)}")
    
    async def register(self, email: str, password: str, username: str, affiliation: Optional[str] = None, is_membership: Optional[bool] = False):
        """
        Supabase Auth를 사용한 회원가입
        """
        try:
            logger.info(f"Starting registration for email: {email}")
            
            # Supabase Auth로 회원가입
            logger.info("Calling Supabase auth.sign_up...")
            response = supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            
            logger.info(f"Auth sign_up response: {response}")
            user = response.user
            
            if not user:
                logger.error("No user returned from auth.sign_up")
                raise Exception("Failed to create user")
            
            logger.info(f"User created with ID: {user.id}")
            
            # 먼저 로그인해서 인증된 세션 생성
            logger.info("Signing in to create authenticated session...")
            login_response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            session = login_response.session
            
            # 인증된 세션으로 users 테이블에 추가 정보 저장
            profile_data = {
                "id": user.id,
                "username": username,
                "affiliation": affiliation,
                "is_membership": is_membership,
                "is_active": True
            }
            
            logger.info(f"Inserting profile data with authenticated session: {profile_data}")
            
            # 인증된 세션으로 insert
            profile_response = supabase.table("users").insert(profile_data).execute()
            logger.info(f"Profile insert response: {profile_response}")
            
            return {
                "access_token": session.access_token,
                "refresh_token": session.refresh_token,
                "token_type": "bearer",
                "user_id": str(user.id),
                "email": user.email,  # auth.users에서 가져온 email
                "username": username,
                "affiliation": affiliation,
                "is_membership": is_membership
            }
            
        except Exception as e:
            logger.error(f"Registration failed: {str(e)}")
            logger.error(f"Exception type: {type(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise Exception(f"Registration failed: {str(e)}")
    
    async def get_current_user(self, token: str):
        """
        토큰으로 현재 사용자 정보 조회
        """
        try:
            # Supabase Auth로 사용자 정보 조회
            user = supabase.auth.get_user(token)
            
            if not user.user:
                raise Exception("Could not validate credentials")
            
            # users 테이블에서 추가 정보 조회
            profile_response = supabase.table("users").select("*").eq("id", user.user.id).execute()
            
            profile_data = profile_response.data[0] if profile_response.data else {
                "id": user.user.id,
                "username": None,
                "affiliation": None,
                "is_membership": False,
                "is_active": True
            }
            
            # auth.users에서 email 추가
            if hasattr(user.user, 'email') and user.user.email:
                profile_data["email"] = user.user.email
            
            return User(**profile_data)
            
        except Exception as e:
            logger.error(f"get_current_user failed: {str(e)}")
            raise Exception("Could not validate credentials")
    
    async def refresh_token(self, refresh_token: str):
        """
        리프레시 토큰으로 새로운 액세스 토큰 발급
        """
        try:
            response = supabase.auth.refresh_session(refresh_token)
            return {
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
                "token_type": "bearer"
            }
        except Exception as e:
            raise Exception(f"Token refresh failed: {str(e)}")
    
    async def logout(self):
        """
        로그아웃
        """
        try:
            supabase.auth.sign_out()
            return {"message": "Successfully logged out"}
        except Exception as e:
            raise Exception(f"Logout failed: {str(e)}") 