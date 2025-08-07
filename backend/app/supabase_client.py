import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# 환경 변수
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

# 기본 클라이언트 (서비스 계정용)
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

def get_client(auth_token: str = None) -> Client:
    """토큰이 있으면 인증된 클라이언트, 없으면 기본 클라이언트 반환"""
    if auth_token:
        # 인증된 클라이언트 생성
        client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        # 토큰을 클라이언트에 설정 (올바른 방법)
        try:
            # access_token과 refresh_token을 동일하게 설정
            client.auth.set_session(auth_token, auth_token)
        except Exception as e:
            print(f"⚠️ 토큰 설정 실패: {e}")
            # 토큰 설정 실패시 기본 클라이언트 반환
            return supabase
        return client
    return supabase 