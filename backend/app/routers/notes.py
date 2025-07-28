from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from ..services.note_service import NoteService
from app.dependencies import get_current_user

# Pydantic 모델 정의
class CreateNoteRequest(BaseModel):
    id: Optional[str] = None  # ← 반드시 있어야 함!
    nttsn: Optional[int] = None
    title: Optional[str] = None
    service_name: str = "chat_report"
    chat_history: Optional[List[Dict[str, str]]] = None  # 프론트엔드에서 받을 때는 리스트
    chat_summary: Optional[str] = None
    is_active: Optional[bool] = True

class NoteResponse(BaseModel):
    id: str
    user_id: str
    nttsn: Optional[int] = None
    title: Optional[str] = None
    service_name: str
    chat_history: Optional[str] = None  # JSON 문자열로 저장됨
    chat_summary: Optional[str] = None
    created_at: str
    updated_at: str
    is_active: Optional[bool] = True

router = APIRouter()

@router.post("/", response_model=NoteResponse)
async def create_note(
    request: CreateNoteRequest,
    current_user = Depends(get_current_user)
):
    """새 노트 생성"""
    try:
        note = await NoteService.create_note(
            user_id=str(current_user.id),
            nttsn=request.nttsn,
            title=request.title,
            service_name=request.service_name,
            chat_history=request.chat_history,
            chat_summary=request.chat_summary
        )
        
        if note:
            return NoteResponse(**note)
        else:
            raise HTTPException(status_code=500, detail="노트 생성에 실패했습니다.")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update_or_create", response_model=NoteResponse)
async def update_or_create_note(
    request: CreateNoteRequest,
    current_user = Depends(get_current_user)
):
    print('update_or_create_note request.id:', request.id)
    """노트 업데이트 또는 생성 (같은 nttsn과 user_id가 있으면 업데이트)"""
    try:
        note = await NoteService.update_or_create_note(
            user_id=str(current_user.id),
            nttsn=request.nttsn,
            title=request.title,
            service_name=request.service_name,
            chat_history=request.chat_history,
            chat_summary=request.chat_summary,
            id=request.id
        )
        
        if note:
            return NoteResponse(**note)
        else:
            raise HTTPException(status_code=500, detail="노트 업데이트/생성에 실패했습니다.")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[NoteResponse])
async def get_user_notes(
    current_user = Depends(get_current_user)
):
    """사용자의 모든 노트 조회"""
    try:
        notes = await NoteService.get_notes_by_user(str(current_user.id))
        return [NoteResponse(**note) for note in notes]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/report/{nttsn}", response_model=List[NoteResponse])
async def get_notes_by_report(
    nttsn: int,
    current_user = Depends(get_current_user)
):
    """특정 보고서의 노트 조회"""
    try:
        notes = await NoteService.get_notes_by_report(str(current_user.id), nttsn)
        return [NoteResponse(**note) for note in notes]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{note_id}", response_model=NoteResponse)
async def get_note_by_id(
    note_id: str,
    current_user = Depends(get_current_user)
):
    """특정 노트 조회"""
    try:
        note = await NoteService.get_note_by_id(str(current_user.id), note_id)
        
        if note:
            return NoteResponse(**note)
        else:
            raise HTTPException(status_code=404, detail="노트를 찾을 수 없습니다.")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 

@router.patch("/deactivate/{note_id}", response_model=NoteResponse)
async def deactivate_note(
    note_id: str,
    current_user = Depends(get_current_user)
):
    try:
        note = await NoteService.update_note_is_active(note_id, str(current_user.id), False)
        if note:
            return NoteResponse(**note)
        else:
            raise HTTPException(status_code=404, detail="노트를 찾을 수 없습니다.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 