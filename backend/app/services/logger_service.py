import aiohttp
import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from app.supabase_client import get_client

load_dotenv()

class LoggerService:
    """AI 사용량 로깅을 담당하는 서비스"""
    
    def __init__(self):
        pass  # BACKEND_BASE_URL 제거 - 사용되지 않음
    
    async def log_ai_usage(
        self,
        user_id: str,
        service_name: str,
        request_prompt: str,
        request_token_count: int,
        response_token_count: int,
        total_token_count: int,
        session_id: Optional[str] = None,
        nttsn: Optional[int] = None,
        is_hidden: bool = False,
        auth_token: Optional[str] = None  # 추가: 인증 토큰
    ) -> bool:
        """AI 사용량을 로깅"""
        try:
            # 독립적인 Supabase 클라이언트 생성
            client = get_client(auth_token)
            
            # 토큰 검증 (인증된 클라이언트인 경우)
            if auth_token:
                from app.services.auth_service import AuthService
                auth_service = AuthService()
                user = await auth_service.get_current_user(auth_token)
                
                if str(user.id) != user_id:
                    print(f"❌ 사용자 ID 불일치: 토큰 사용자={user.id}, 요청 사용자={user_id}")
                    return False
            
            # 독립적인 클라이언트로 DB 접근
            response = client.table("ai_usage_logs").insert({
                "user_id": user_id,
                "session_id": session_id,
                "service_name": service_name,
                "nttsn": nttsn,
                "request_prompt": request_prompt,
                "request_token_count": request_token_count,
                "response_token_count": response_token_count,
                "total_token_count": total_token_count,
                "is_hidden": is_hidden
            }).execute()
            
            print(f"[AI_USAGE_LOG] user_id={user_id}, service_name={service_name}, request_token_count={request_token_count}, response_token_count={response_token_count}, total_token_count={total_token_count}, is_hidden={is_hidden}")
            if response.data:
                print(f"✅ AI 사용량 로깅 성공: {service_name}")
                return True
            else:
                print(f"❌ AI 사용량 로깅 실패")
                return False
                        
        except Exception as e:
            print(f"❌ AI 사용량 로깅 중 오류: {e}")
            return False 