import os
import sys
from dotenv import load_dotenv
from google import genai
from google.genai import types
import traceback
import sqlite3
import uuid
from typing import Optional
from .logger_service import LoggerService

# 경로 설정 (환경변수에서 읽어오기)
def get_paths():
    """환경변수에서 경로 설정을 읽어와서 반환"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(os.path.dirname(current_dir))
    return {
        "chroma_db": os.path.join(base_dir, os.getenv("CHROMA_DB_PATH", "datas/chroma_db")),
        "extracted_pdf": os.path.join(base_dir, os.getenv("EXTRACTED_PDF_PATH", "datas/extracted_pdf")),
        "pdf_reports": os.path.join(base_dir, os.getenv("PDF_REPORTS_PATH", "datas/pdf_reports")),
        "json_results": os.path.join(base_dir, os.getenv("JSON_RESULTS_PATH", "datas/json_results")),
        "science_reports_db": os.path.join(base_dir, os.getenv("SCIENCE_REPORTS_DB_PATH", "datas/science_reports.db")),
        "prompts": os.path.join(base_dir, os.getenv("PROMPTS_PATH", "prompts"))
    }

# 전역 경로 설정
PATHS = get_paths()

API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise RuntimeError("GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다.")

CHAT_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
client = genai.Client(api_key=API_KEY)

# ChatSession(대화 context) 관리를 위한 전역 변수
chat_sessions = {}  # key: session_id, value: chat 객체

# 프롬프트 템플릿 로드
try:
    prompt_path = os.path.join(PATHS["prompts"], "prompt_chat.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        CHAT_PROMPT_TEMPLATE = f.read()
except FileNotFoundError:
    raise FileNotFoundError(f"프롬프트 파일을 찾을 수 없습니다: {prompt_path}")

class ChatService:
    @staticmethod
    def get_union_content(number: int) -> str:
        """보고서 union 파일의 내용을 반환"""
        union_path = os.path.join(
            PATHS["extracted_pdf"], "union", f'{number}_union.txt'
        )
        union_path = os.path.abspath(union_path)
        if not os.path.exists(union_path):
            print(f"[UNION][FAIL] Union txt 파일을 찾을 수 없습니다: {union_path}")
            raise FileNotFoundError(f"Union txt 파일을 찾을 수 없습니다: {union_path}")
        with open(union_path, 'r', encoding='utf-8') as f:
            return f.read()

    @staticmethod
    def create_system_message(report_content: str) -> str:
        """프롬프트 템플릿을 사용하여 system message 생성"""
        try:
            # {report_content} 부분을 실제 보고서 내용으로 치환
            system_message = CHAT_PROMPT_TEMPLATE.replace("{report_content}", report_content)
            return system_message
        except Exception as e:
            print(f"[PROMPT][ERROR] 프롬프트 템플릿 처리 중 오류: {e}")
            # 오류 발생 시 기본 메시지 사용
            return f"다음은 연구 보고서 내용입니다. 이 내용을 기반으로 제가 묻는 질문에 답해주세요.\n\n보고서 내용:\n{report_content}"

    @staticmethod
    def get_report_description(report_number: str) -> str:
        db_path = PATHS["science_reports_db"]
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT description FROM joined WHERE nttSn = ?", (report_number,))
            row = cursor.fetchone()
            conn.close()
            if row and row[0]:
                return row[0]
            return ""
        except Exception as e:
            print(f"[DB][ERROR] description 조회 실패: {e}")
            return ""

    @staticmethod
    def get_report_title(report_number: str) -> str:
        db_path = PATHS["science_reports_db"]
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT title FROM joined WHERE nttSn = ?", (report_number,))
            row = cursor.fetchone()
            conn.close()
            if row and row[0]:
                return row[0]
            return ""
        except Exception as e:
            print(f"[DB][ERROR] title 조회 실패: {e}")
            return ""

    @staticmethod
    async def chat_with_gemini(report_number: str, query: str, user_id: Optional[str] = None, logger_service: Optional[LoggerService] = None, session_id: Optional[str] = None, history: Optional[list] = None, is_hidden: bool = False, origin_query: Optional[str] = None, auth_token: Optional[str] = None):
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-001")
        print(f"[CHAT] 모델: {model_name}")
        print(f"[CHAT] report_number: {report_number}")
        print(f"[CHAT] query: {query}")
        print(f"[CHAT] user_id: {user_id}, session_id: {session_id}")
        print(f"[CHAT] history: {history}")
        try:
            # 세션ID 생성 (user_id + report_number 조합)
            if not session_id and user_id:
                session_id = f"{user_id}_{report_number}"
            if not session_id:
                session_id = f"anonymous_{report_number}"

            if session_id in chat_sessions:
                # 기존 세션 사용
                chat = chat_sessions[session_id]
                print(f"[CHAT] 기존 ChatSession 사용: {session_id}")
                response = await chat.send_message(query)
            else:
                # 새로운 세션 생성
                chat = client.aio.chats.create(model=CHAT_MODEL_NAME)
                print(f"[CHAT] 새로운 ChatSession 생성: {session_id}")
                
                # union 파일 내용을 프롬프트 템플릿을 사용하여 system message 생성
                report_content = ChatService.get_union_content(report_number)
                system_message = ChatService.create_system_message(report_content)
                print(f"[CHAT] 프롬프트 템플릿 기반 system message 생성 완료")
                await chat.send_message(system_message)
                
                # 히스토리가 있으면 추가
                if history:
                    for item in history:
                        for part in item.get("parts", []):
                            role = item.get('role', '')
                            text = part.get('text', '')
                            if role == 'user':
                                await chat.send_message(text)
                            elif role == 'model':
                                # assistant 응답은 자동으로 처리됨
                                pass
                
                # 현재 쿼리 전송
                response = await chat.send_message(query)
                chat_sessions[session_id] = chat

            result = response.text.strip()
            print(f"[CHAT] 응답 성공 (길이: {len(result)})")

            # 사용량 메타데이터 추출 (gemini-1.5-pro는 usage_metadata 미지원일 수 있음)
            usage_metadata = {}
            print(f"[DEBUG] Gemini 응답 usage_metadata: {getattr(response, 'usage_metadata', None)}")
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage_metadata = {
                    'total_token_count': response.usage_metadata.total_token_count,
                    'prompt_token_count': response.usage_metadata.prompt_token_count,
                    'candidates_token_count': response.usage_metadata.candidates_token_count
                }
                print(f"[CHAT] 사용량 메타데이터: {usage_metadata}")

            # nttSn은 report_number를 int로 직접 설정
            nttsn = int(report_number)

            # 로깅 수행 (logger_service가 제공된 경우에만)
            if logger_service and user_id:
                try:
                    session_string = f"{report_number}-{user_id}"
                    log_session_id = str(uuid.uuid5(uuid.NAMESPACE_OID, session_string))
                    await logger_service.log_ai_usage(
                        user_id=user_id,
                        service_name="chat_report",
                        request_prompt=origin_query if origin_query is not None else query,
                        request_token_count=usage_metadata.get('prompt_token_count', 0),
                        response_token_count=usage_metadata.get('candidates_token_count', 0),
                        total_token_count=usage_metadata.get('total_token_count', 0),
                        session_id=log_session_id,
                        nttsn=nttsn,
                        is_hidden=is_hidden,
                        auth_token=auth_token  # 토큰 전달
                    )
                    print(f"✅ 세션 ID로 로깅: {log_session_id} (from {session_string}), nttSn: {nttsn}, is_hidden: {is_hidden}")
                except Exception as log_error:
                    print(f"❌ AI 사용량 로깅 중 오류: {log_error}")

            return result, usage_metadata
        except Exception as e:
            print(f"[CHAT] Gemini API 호출 중 오류 발생: {e}")
            print(f"[CHAT] 전체 에러 정보:")
            print(traceback.format_exc())
            raise Exception(f"Gemini API 호출 중 오류 발생: {e}")

    @staticmethod
    def cleanup_session(session_id: str):
        """세션 종료: ChatSession 삭제"""
        if session_id in chat_sessions:
            del chat_sessions[session_id]
            print(f"[CLEANUP] ChatSession 삭제됨: {session_id}") 