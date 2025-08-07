from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from ..services.analysis_service import AnalysisService
from ..services.chat_service import ChatService
from ..services.logger_service import LoggerService
from ..services.note_service import NoteService
from app.dependencies import get_current_user
import os
import json
from fastapi.responses import FileResponse

security = HTTPBearer()

class ChatPart(BaseModel):
    text: str

class ChatHistoryItem(BaseModel):
    role: str
    parts: List[ChatPart]

class ChatRequest(BaseModel):
    query: str
    report_number: str
    history: Optional[List[ChatHistoryItem]] = None
    is_hidden: Optional[bool] = False
    origin_query: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    usage_metadata: dict = None

class ChatHistoryResponse(BaseModel):
    history: List[Dict[str, Any]]
    report_number: int

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_with_report(
    request: ChatRequest,
    current_user = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """보고서와 채팅 API - 캐시를 활용한 Gemini API 호출"""
    try:
        # 요청 데이터 로깅
        if request.history:
            pass # Removed print statements
        
        # LoggerService 인스턴스 생성
        logger_service = LoggerService()
        
        # 히스토리를 딕셔너리 형태로 변환
        history_dict = None
        if request.history:
            history_dict = []
            for item in request.history:
                # role을 Gemini API 형식으로 변환
                gemini_role = "model" if item.role == "assistant" else item.role
                history_dict.append({
                    "role": gemini_role,
                    "parts": [{"text": part.text} for part in item.parts]
                })
        
        # Gemini API를 사용하여 채팅
        # origin_query가 있으면 ChatService에 넘김
        result, usage_metadata = await ChatService.chat_with_gemini(
            report_number=request.report_number, 
            query=request.query,
            user_id=str(current_user.id),
            logger_service=logger_service,
            history=history_dict,
            is_hidden=request.is_hidden,
            origin_query=request.origin_query,
            auth_token=credentials.credentials  # 토큰 전달
        )
        
        return ChatResponse(
            response=result,
            usage_metadata=usage_metadata
        )
    except Exception as e:
        print(f"[CHAT API] 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete_file")
async def delete_file(
    file_id: str,
    current_user = Depends(get_current_user)
):
    """업로드된 파일 삭제"""
    try:
        success = ChatService.delete_uploaded_file(file_id)
        if success:
            return {"message": "파일이 성공적으로 삭제되었습니다."}
        else:
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/cleanup_session")
async def cleanup_session(
    session_id: str,
    current_user = Depends(get_current_user)
):
    """채팅 세션 종료: 참조 카운트 감소 및 필요시 파일 삭제"""
    try:
        ChatService.cleanup_session(session_id)
        return {"message": f"세션 {session_id}이(가) 성공적으로 정리되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/description/{report_number}")
async def get_report_description(report_number: str):
    """science_reports.db의 joined 테이블에서 description 반환"""
    desc = ChatService.get_report_description(report_number)
    return {"description": desc}

@router.get("/title/{report_number}")
async def get_report_title(report_number: str):
    title = ChatService.get_report_title(report_number)
    return {"title": title}

@router.get("/pdf/{pdf_type}/{report_number}")
async def get_report_pdf(
    pdf_type: str,
    report_number: str
):
    try:
        # 경로 설정 가져오기
        from ..services.chat_service import PATHS
        pdf_dir = os.path.join(PATHS["pdf_reports"], pdf_type)
        
        possible_extensions = ['.pdf', '.hwp']
        pdf_path = None
        
        if pdf_type == "report":
            for ext in possible_extensions:
                temp_path = os.path.join(pdf_dir, f"{report_number}_report{ext}")
                if os.path.exists(temp_path):
                    pdf_path = temp_path
                    break
        elif pdf_type == "summary":
            for ext in possible_extensions:
                temp_path = os.path.join(pdf_dir, f"{report_number}_summary{ext}")
                if os.path.exists(temp_path):
                    pdf_path = temp_path
                    break
        else:
            raise HTTPException(status_code=400, detail="pdf_type은 report 또는 summary만 허용됩니다.")
        
        if not pdf_path or not os.path.exists(pdf_path):
            raise HTTPException(status_code=404, detail="PDF를 찾을 수 없습니다.")
        
        file_ext = os.path.splitext(pdf_path)[1].lower()
        if file_ext == '.pdf':
            media_type = "application/pdf"
        elif file_ext == '.hwp':
            media_type = "application/x-hwp"
        else:
            media_type = "application/octet-stream"
        
        response = FileResponse(pdf_path, media_type=media_type)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, HEAD, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF 로드 중 오류가 발생했습니다: {str(e)}")

@router.head("/pdf/{pdf_type}/{report_number}")
async def head_report_pdf(
    pdf_type: str,
    report_number: str
):
    import os
    from fastapi import HTTPException, Response
    # 경로 설정 가져오기
    from ..services.chat_service import PATHS
    pdf_dir = os.path.join(PATHS["pdf_reports"], pdf_type)
    
    possible_extensions = ['.pdf', '.hwp']
    pdf_path = None
    
    if pdf_type == "report":
        for ext in possible_extensions:
            temp_path = os.path.join(pdf_dir, f"{report_number}_report{ext}")
            if os.path.exists(temp_path):
                pdf_path = temp_path
                break
    elif pdf_type == "summary":
        for ext in possible_extensions:
            temp_path = os.path.join(pdf_dir, f"{report_number}_summary{ext}")
            if os.path.exists(temp_path):
                pdf_path = temp_path
                break
    else:
        raise HTTPException(status_code=400, detail="pdf_type은 report 또는 summary만 허용됩니다.")
    
    if not pdf_path or not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF를 찾을 수 없습니다.")
    
    response = Response(status_code=200)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, HEAD, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

@router.get("/history/{report_number}", response_model=ChatHistoryResponse)
async def get_chat_history(
    report_number: int,
    current_user = Depends(get_current_user)
):
    """특정 보고서의 채팅 히스토리 조회"""
    try:
        # 사용자의 해당 보고서 노트 조회
        notes = await NoteService.get_notes_by_report(str(current_user.id), report_number)
        
        if not notes:
            raise HTTPException(status_code=404, detail="채팅 히스토리를 찾을 수 없습니다.")
        
        # 가장 최근 노트의 chat_history 사용
        latest_note = notes[0]  # 이미 created_at desc로 정렬됨
        
        if not latest_note.get('chat_history'):
            raise HTTPException(status_code=404, detail="채팅 히스토리가 없습니다.")
        
        # JSON 문자열을 파싱하여 히스토리 복원
        try:
            chat_history = json.loads(latest_note['chat_history'])
            
            # Gemini API 형식으로 변환
            gemini_history = []
            for msg in chat_history:
                # role을 Gemini API 형식으로 변환
                gemini_role = "model" if msg['role'] == "assistant" else msg['role']
                gemini_history.append({
                    "role": gemini_role,
                    "parts": [{"text": msg['content']}]
                })
            
            return ChatHistoryResponse(
                history=gemini_history,
                report_number=report_number
            )
            
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="채팅 히스토리 형식이 올바르지 않습니다.")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 

@router.get("/example/{question_number}")
async def get_example_question(
    question_number: int,
    current_user = Depends(get_current_user)
):
    """예시 질문에 대한 프롬프트 반환"""
    try:
        # 프롬프트 파일 경로
        from ..services.chat_service import PATHS
        prompt_path = os.path.join(PATHS["prompts"], "example_questions", f"question_{question_number}.txt")
        
        if not os.path.exists(prompt_path):
            raise HTTPException(status_code=404, detail="프롬프트 파일을 찾을 수 없습니다.")
        
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_content = f.read()
        
        return {
            "question_number": question_number,
            "prompt": prompt_content
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"예시 질문 처리 중 오류가 발생했습니다: {str(e)}") 