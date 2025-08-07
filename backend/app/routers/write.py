from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from ..services.write_service import WriteService
from ..services.logger_service import LoggerService
from app.dependencies import get_current_user

# Pydantic 모델 정의
class ChatRequest(BaseModel):
    message: str
    user_report: str = ""  # 사용자 보고서 내용 추가
    history: Optional[List[Dict[str, Any]]] = None  # 채팅 히스토리 추가

class ChatResponse(BaseModel):
    response: str
    usage_metadata: Optional[Dict[str, Any]] = None

class ChatHistoryResponse(BaseModel):
    session_id: str
    has_session: bool
    history: List[Dict[str, Any]]
    report_numbers: List[str]
    user_report: str

class SessionCleanupResponse(BaseModel):
    success: bool
    message: str

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_with_write(
    request: ChatRequest,
    current_user = Depends(get_current_user)
):
    """WritePage analyze_for_write() 기반 채팅 API"""
    try:
        # LoggerService 인스턴스 생성
        logger_service = LoggerService()
        
        # WriteService를 통해 analyze_for_write() 기반 채팅 응답 생성
        response, usage_metadata = await WriteService.chat_with_write(
            query=request.message,
            user_id=str(current_user.id),
            user_report=request.user_report,  # 사용자 보고서 내용 전달
            history=request.history,  # 채팅 히스토리 전달
            logger_service=logger_service,
            auth_token=credentials.credentials  # 토큰 전달
        )
        
        return ChatResponse(
            response=response,
            usage_metadata=usage_metadata
        )
        
    except Exception as e:
        print(f"[WRITE API] 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history", response_model=ChatHistoryResponse)
async def get_write_chat_history(
    current_user = Depends(get_current_user)
):
    """WritePage 채팅 히스토리 조회"""
    try:
        # 히스토리 기반 조회
        history_info = await WriteService.get_write_chat_history(str(current_user.id))
        
        return ChatHistoryResponse(**history_info)
        
    except Exception as e:
        print(f"[WRITE API] 히스토리 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/session", response_model=SessionCleanupResponse)
async def cleanup_write_session(
    current_user = Depends(get_current_user)
):
    """WritePage 채팅 히스토리 정리"""
    try:
        success = await WriteService.cleanup_write_session(str(current_user.id))
        
        if success:
            return SessionCleanupResponse(
                success=True,
                message="채팅 히스토리가 성공적으로 정리되었습니다."
            )
        else:
            return SessionCleanupResponse(
                success=False,
                message="채팅 히스토리 정리에 실패했습니다."
            )
        
    except Exception as e:
        print(f"[WRITE API] 히스토리 정리 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 