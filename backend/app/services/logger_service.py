import aiohttp
import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from app.supabase_client import supabase

load_dotenv()

class LoggerService:
    """AI 사용량 로깅을 담당하는 서비스"""
    
    def __init__(self):
        self.base_url = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
    
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
        is_hidden: bool = False
    ) -> bool:
        """AI 사용량을 로깅"""
        try:
            
            # Supabase를 통해 직접 DB에 삽입
            response = supabase.table("ai_usage_logs").insert({
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