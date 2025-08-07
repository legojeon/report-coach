from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, Dict, Any, List
from datetime import datetime, date
from app.dependencies import get_current_user
from app.supabase_client import get_client
from app.models.user import User
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter()
security = HTTPBearer()

@router.get("/ai-usage")
async def get_ai_usage(
    current_user: User = Depends(get_current_user),
    service_name: Optional[str] = Query(None, description="서비스 이름 (query_summary, analyze_reports, chat_report)"),
    start_date: Optional[date] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="종료 날짜 (YYYY-MM-DD)"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """사용자의 AI 토큰 사용량 조회"""
    try:
        # 독립적인 클라이언트 사용
        supabase = get_client(credentials.credentials)
        
        # 기본 쿼리
        query = supabase.table("ai_usage_logs").select("*").eq("user_id", current_user.id)
        
        # 서비스 이름 필터
        if service_name:
            query = query.eq("service_name", service_name)
        
        # 날짜 필터
        if start_date:
            query = query.gte("timestamp", start_date.isoformat())
        if end_date:
            # 종료 날짜는 해당 날짜의 23:59:59까지 포함
            end_datetime = f"{end_date.isoformat()}T23:59:59"
            query = query.lte("timestamp", end_datetime)
        
        # 일단 정렬 없이 조회 (프론트엔드에서 정렬)
        # query = query.order("timestamp", desc=True)
        
        response = query.execute()
        
        if not response.data:
            return {
                "logs": [],
                "summary": {
                    "total_requests": 0,
                    "total_tokens": 0,
                    "total_request_tokens": 0,
                    "total_response_tokens": 0
                },
                "by_service": {}
            }
        
        logs = response.data
        
        # 전체 통계 계산
        total_requests = len(logs)
        total_tokens = sum(log.get("total_token_count", 0) for log in logs)
        total_request_tokens = sum(log.get("request_token_count", 0) for log in logs)
        total_response_tokens = sum(log.get("response_token_count", 0) for log in logs)
        
        # 서비스별 통계 계산
        by_service = {}
        for log in logs:
            service = log.get("service_name", "unknown")
            if service not in by_service:
                by_service[service] = {
                    "requests": 0,
                    "total_tokens": 0,
                    "request_tokens": 0,
                    "response_tokens": 0
                }
            
            by_service[service]["requests"] += 1
            by_service[service]["total_tokens"] += log.get("total_token_count", 0)
            by_service[service]["request_tokens"] += log.get("request_token_count", 0)
            by_service[service]["response_tokens"] += log.get("response_token_count", 0)
        
        return {
            "logs": logs,
            "summary": {
                "total_requests": total_requests,
                "total_tokens": total_tokens,
                "total_request_tokens": total_request_tokens,
                "total_response_tokens": total_response_tokens
            },
            "by_service": by_service
        }
        
    except Exception as e:
        import traceback
        print(f"❌ 토큰 사용량 조회 중 오류: {e}")
        print(f"❌ 상세 오류: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"토큰 사용량 조회 중 오류가 발생했습니다: {str(e)}")

@router.get("/history")
async def get_user_history(
    current_user: User = Depends(get_current_user),
    service_type: Optional[str] = Query(None, description="서비스 타입 (search, chat, all)"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """사용자의 검색/채팅 기록 조회"""
    try:
        # 독립적인 클라이언트 사용
        supabase = get_client(credentials.credentials)
        
        # 기본 쿼리 - is_hidden이 false인 것만 조회
        query = supabase.table("ai_usage_logs").select("*").eq("user_id", current_user.id).eq("is_hidden", False)
        
        # 서비스 타입 필터
        if service_type == "search":
            query = query.eq("service_name", "query_summary")
        elif service_type == "chat":
            query = query.in_("service_name", ["chat_report", "write_chat"])
        else:
            # all 또는 기본값: query_summary, chat_report, write_chat 모두
            query = query.in_("service_name", ["query_summary", "chat_report", "write_chat"])
        
        response = query.execute()
        
        if not response.data:
            return {
                "history": [],
                "summary": {
                    "total_records": 0,
                    "search_count": 0,
                    "chat_count": 0
                }
            }
        
        logs = response.data
        
        # 서비스별 개수 계산
        search_count = sum(1 for log in logs if log.get("service_name") == "query_summary")
        chat_count = sum(1 for log in logs if log.get("service_name") in ["chat_report", "write_chat"])
        
        return {
            "history": logs,
            "summary": {
                "total_records": len(logs),
                "search_count": search_count,
                "chat_count": chat_count
            }
        }
        
    except Exception as e:
        import traceback
        print(f"❌ 기록 조회 중 오류: {e}")
        print(f"❌ 상세 오류: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"기록 조회 중 오류가 발생했습니다: {str(e)}") 