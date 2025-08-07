import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.supabase_client import get_client

class NoteService:
    """노트 관련 비즈니스 로직을 담당하는 서비스"""
    
    @staticmethod
    async def create_note(
        user_id: str,
        nttsn: Optional[int] = None,  # null 허용
        title: Optional[str] = None,
        service_name: str = "chat_report",
        chat_history: Optional[List[Dict[str, str]]] = None,
        chat_summary: Optional[str] = None,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """새 노트 생성"""
        try:
            # 독립적인 클라이언트 사용
            supabase = get_client(auth_token)
            
            # chat_history를 JSON 문자열로 변환
            chat_history_json = json.dumps(chat_history or [], ensure_ascii=False) if chat_history else "[]"
            
            note_data = {
                "user_id": user_id,
                "nttsn": nttsn,
                "title": title,
                "service_name": service_name,
                "chat_history": chat_history_json,
                "chat_summary": chat_summary,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "is_active": True
            }
            
            response = supabase.table("notes").insert(note_data).execute()
            
            if response.data:
                print(f"✅ 노트 생성 성공: {response.data[0]['id']}")
                return response.data[0]
            else:
                print(f"❌ 노트 생성 실패")
                return None
                
        except Exception as e:
            print(f"❌ 노트 생성 중 오류: {e}")
            return None
    
    @staticmethod
    async def get_notes_by_user(user_id: str, auth_token: Optional[str] = None) -> List[Dict[str, Any]]:
        """사용자의 모든 노트 조회"""
        try:
            # 독립적인 클라이언트 사용
            supabase = get_client(auth_token)
            
            response = supabase.table("notes").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
            
            if response.data:
                print(f"✅ 사용자 노트 조회 성공: {len(response.data)}개")
                return response.data
            else:
                print(f"✅ 사용자 노트 없음")
                return []
                
        except Exception as e:
            print(f"❌ 노트 조회 중 오류: {e}")
            return []
    
    @staticmethod
    async def get_notes_by_report(user_id: str, nttsn: Optional[int] = None, auth_token: Optional[str] = None) -> List[Dict[str, Any]]:
        """특정 보고서의 노트 조회"""
        try:
            # 독립적인 클라이언트 사용
            supabase = get_client(auth_token)
            
            if nttsn is None:
                # nttsn이 null인 경우 (write_report 등)
                response = supabase.table("notes").select("*").eq("user_id", user_id).is_("nttsn", "null").order("created_at", desc=True).execute()
            else:
                response = supabase.table("notes").select("*").eq("user_id", user_id).eq("nttsn", nttsn).order("created_at", desc=True).execute()
            
            if response.data:
                print(f"✅ 보고서 노트 조회 성공: {len(response.data)}개")
                return response.data
            else:
                print(f"✅ 보고서 노트 없음")
                return []
                
        except Exception as e:
            print(f"❌ 보고서 노트 조회 중 오류: {e}")
            return []
    
    @staticmethod
    async def get_note_by_id(user_id: str, note_id: str, auth_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """특정 노트 조회"""
        try:
            # 독립적인 클라이언트 사용
            supabase = get_client(auth_token)
            
            response = supabase.table("notes").select("*").eq("id", note_id).eq("user_id", user_id).execute()
            
            if response.data:
                print(f"✅ 노트 조회 성공: {note_id}")
                return response.data[0]
            else:
                print(f"✅ 노트 없음: {note_id}")
                return None
                
        except Exception as e:
            print(f"❌ 노트 조회 중 오류: {e}")
            return None

    @staticmethod
    async def update_or_create_note(
        user_id: str,
        nttsn: Optional[int] = None,  # null 허용
        title: Optional[str] = None,
        service_name: str = "chat_report",
        chat_history: Optional[List[Dict[str, str]]] = None,
        chat_summary: Optional[str] = None,
        id: Optional[str] = None,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """노트 업데이트 또는 생성 (같은 nttsn과 user_id가 있으면 업데이트)"""
        try:
            # 독립적인 클라이언트 사용
            supabase = get_client(auth_token)
            
            # chat_history를 JSON 문자열로 변환
            chat_history_json = json.dumps(chat_history or [], ensure_ascii=False) if chat_history else "[]"

            if id:
                # id로 update
                update_data = {
                    "title": title,
                    "service_name": service_name,
                    "chat_history": chat_history_json,
                    "chat_summary": chat_summary,
                    "updated_at": datetime.utcnow().isoformat(),
                    "is_active": True
                }
                print(f"Updating note with id: {id}, user_id: {user_id}")
                response = supabase.table("notes").update(update_data).eq("id", id).eq("user_id", user_id).execute()
                if response.data:
                    print(f"✅ 노트 id로 업데이트 성공: {id}")
                    print('update response:', response.data)
                    return response.data[0]
                else:
                    print(f"❌ 노트 id로 업데이트 실패")
                    return None

            # 기존 노트가 있는지 확인
            if nttsn is None:
                # nttsn이 null인 경우 (write_report) - 항상 새로 생성
                note_data = {
                    "user_id": user_id,
                    "nttsn": nttsn,
                    "title": title,
                    "service_name": service_name,
                    "chat_history": chat_history_json,
                    "chat_summary": chat_summary,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                    "is_active": True
                }
                
                response = supabase.table("notes").insert(note_data).execute()
                
                if response.data:
                    print(f"✅ 새 write_report 노트 생성 성공: {response.data[0]['id']}")
                    return response.data[0]
                else:
                    print(f"❌ 새 write_report 노트 생성 실패")
                    return None
            else:
                # nttsn이 있는 경우 (chat_report) - 기존 노트 확인 후 업데이트 또는 생성
                response = supabase.table("notes").select("*").eq("user_id", user_id).eq("nttsn", nttsn).order("created_at", desc=True).execute()
                existing_notes = response.data if response.data else []
                
                if existing_notes:
                    # 기존 노트 업데이트
                    latest_note = existing_notes[0]  # 가장 최근 노트
                    note_id = latest_note['id']
                    
                    update_data = {
                        "title": title,
                        "service_name": service_name,
                        "chat_history": chat_history_json,
                        "chat_summary": chat_summary,
                        "updated_at": datetime.utcnow().isoformat(),
                        "is_active": True
                    }
                    
                    response = supabase.table("notes").update(update_data).eq("id", note_id).execute()
                    
                    if response.data:
                        print(f"✅ 노트 업데이트 성공: {note_id}")
                        return response.data[0]
                    else:
                        print(f"❌ 노트 업데이트 실패")
                        return None
                else:
                    # 새 노트 생성
                    note_data = {
                        "user_id": user_id,
                        "nttsn": nttsn,
                        "title": title,
                        "service_name": service_name,
                        "chat_history": chat_history_json,
                        "chat_summary": chat_summary,
                        "created_at": datetime.utcnow().isoformat(),
                        "updated_at": datetime.utcnow().isoformat(),
                        "is_active": True
                    }
                    
                    response = supabase.table("notes").insert(note_data).execute()
                    
                    if response.data:
                        print(f"✅ 새 노트 생성 성공: {response.data[0]['id']}")
                        return response.data[0]
                    else:
                        print(f"❌ 새 노트 생성 실패")
                        return None
                
        except Exception as e:
            print(f"❌ 노트 업데이트/생성 중 오류: {e}")
            return None 

    @staticmethod
    async def update_note_is_active(note_id: str, user_id: str, is_active: bool, auth_token: Optional[str] = None):
        try:
            # 독립적인 클라이언트 사용
            supabase = get_client(auth_token)
            
            response = supabase.table("notes").update({"is_active": is_active}).eq("id", note_id).eq("user_id", user_id).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            print(f"❌ 노트 is_active 업데이트 오류: {e}")
            return None 