import os
import sys
from typing import List, Dict, Any, Optional, Tuple
from fastapi import HTTPException
from .search_service import SearchService
from .analysis_service import AnalysisService
from .logger_service import LoggerService
from google import genai
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
import traceback
import uuid

# 환경 변수 로드
load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError("GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다.")
client = genai.Client(api_key=API_KEY)

# 프롬프트 템플릿 로드
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(current_dir, "..", "..", "prompts", "prompt_write.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        PROMPT_TEMPLATE = f.read()
except FileNotFoundError:
    raise FileNotFoundError(f"프롬프트 파일을 찾을 수 없습니다: {prompt_path}")

PROMPT = PromptTemplate.from_template(PROMPT_TEMPLATE)

# Write 채팅 히스토리 관리를 위한 전역 변수
write_chat_histories = {}  # key: user_id, value: List[Dict] (채팅 히스토리)
write_user_reports = {}  # key: user_id, value: user_report 내용

def get_write_history_key(user_id: str) -> str:
    """사용자별 Write 채팅 히스토리 키 생성"""
    return f"write_{user_id}"

def cleanup_write_history(user_id: str):
    """Write 히스토리 정리"""
    history_key = get_write_history_key(user_id)
    if history_key in write_chat_histories:
        del write_chat_histories[history_key]
        print(f"[WRITE_CLEANUP] Write 채팅 히스토리 삭제됨: {history_key}")
    
    if user_id in write_user_reports:
        del write_user_reports[user_id]
        print(f"[WRITE_CLEANUP] Write 사용자 보고서 정보 삭제됨: {user_id}")


class WriteService:
    """WritePage 채팅 기능을 담당하는 서비스"""
    
    @staticmethod
    async def analyze_for_write(
        user_query: str,
        user_report: str,
        report_numbers: List[str],
        user_id: str,
        logger_service: Optional[LoggerService] = None,
        auth_token: Optional[str] = None
    ) -> Tuple[str, dict]:
        """사용자 보고서 내용을 참고하여 분석 및 답변 생성"""
        generation_config = {
            "max_output_tokens": int(os.getenv("GEMINI_MAX_TOKENS", "2048")),
            "temperature": float(os.getenv("GEMINI_TEMPERATURE", "0.1")),
            "top_p": float(os.getenv("GEMINI_TOP_P", "0.9")),
            "top_k": int(os.getenv("GEMINI_TOP_K", "40"))
        }

        gemini_model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-latest")
        # model = genai.GenerativeModel(model_name=gemini_model_name, generation_config=generation_config)

        # 각 보고서 내용을 읽어서 결합
        reports_content = ""
        for i, number in enumerate(report_numbers, 1):
            current_dir = os.path.dirname(os.path.abspath(__file__))
            union_file_path = os.path.join(current_dir, "..", "..", "datas", "extracted_pdf", "union", f"{number}_union.txt")

            if os.path.exists(union_file_path):
                try:
                    with open(union_file_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                    if content:
                        reports_content += f"\n=== 보고서 {number} ===\n{content}\n"
                except Exception as e:
                    print(f"파일 읽기 오류 (보고서 {number}): {e}")

        # 프롬프트 템플릿에 변수 대입
        prompt = PROMPT_TEMPLATE.format(
            user_query=user_query,
            user_report=user_report,
            reports_content=reports_content
        )

        try:
            response = client.models.generate_content(
                model=gemini_model_name,
                contents=prompt,
            )
            
            # 사용량 메타데이터 추출
            usage_metadata = {}
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage_metadata = {
                    'total_token_count': response.usage_metadata.total_token_count,
                    'prompt_token_count': response.usage_metadata.prompt_token_count,
                    'candidates_token_count': response.usage_metadata.candidates_token_count
                }

            if logger_service and usage_metadata:
                try:
                    await logger_service.log_ai_usage(
                        user_id=user_id,
                        service_name="write_chat",
                        request_prompt=user_query,
                        request_token_count=usage_metadata.get('prompt_token_count', 0),
                        response_token_count=usage_metadata.get('candidates_token_count', 0),
                        total_token_count=usage_metadata.get('total_token_count', 0),
                        auth_token=auth_token  # 토큰 전달
                    )
                except Exception as log_error:
                    print(f"❌ 로깅 중 오류: {log_error}")
            
            return response.text, usage_metadata
        except Exception as e:
            return f"답변 생성 실패: {e}", {}
    
    @staticmethod
    async def chat_with_write(
        query: str, 
        user_id: str, 
        user_report: str = "",
        history: Optional[List[Dict[str, Any]]] = None,
        logger_service: Optional[LoggerService] = None,
        auth_token: Optional[str] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """analyze_for_write()를 활용한 채팅 메시지에 대한 답변 생성"""
        try:
            print(f"✍️ Write 채팅 요청: {query}")
            print(f"✍️ user_id: {user_id}")
            print(f"✍️ history: {history}")
            
            # 히스토리 키 생성
            history_key = get_write_history_key(user_id)
            print(f"✍️ history_key: {history_key}")
            
            # 1. 검색을 통해 관련 보고서 찾기
            search_result = await SearchService.search_documents(
                query=query,
                k=5,  # 상위 5개 보고서 사용
                user_id=user_id,
                logger_service=logger_service,
                is_hidden=True,  # write_chat에서 호출하는 검색은 숨김 처리
                auth_token=auth_token  # 토큰 전달
            )
            
            if not search_result.get('results'):
                return "관련된 보고서를 찾을 수 없습니다. 다른 질문을 해보세요.", {}
            
            # 2. 검색된 보고서 번호들 추출
            report_numbers = [str(result['number']) for result in search_result['results']]
            print(f"📊 관련 보고서: {report_numbers}")
            
            # 3. analyze_for_write()를 통해 답변 생성
            analysis_result, usage_metadata = await WriteService.analyze_for_write(
                user_query=query,
                user_report=user_report,
                report_numbers=report_numbers,
                user_id=user_id,
                logger_service=logger_service,
                auth_token=auth_token  # 토큰 전달
            )
            
            # 4. 히스토리 관리
            if history_key not in write_chat_histories:
                write_chat_histories[history_key] = []
            
            # 사용자 메시지와 AI 응답을 히스토리에 추가
            write_chat_histories[history_key].append({
                "role": "user",
                "content": query,
                "timestamp": str(uuid.uuid4())
            })
            
            write_chat_histories[history_key].append({
                "role": "assistant",
                "content": analysis_result,
                "timestamp": str(uuid.uuid4())
            })
            
            # 사용자 보고서 정보 저장
            write_user_reports[user_id] = user_report
            
            print(f"✍️ 히스토리에 메시지 추가됨. 총 {len(write_chat_histories[history_key])}개 메시지")
            
            # 5. 사용량 메타데이터에 검색 결과 정보 추가
            if usage_metadata:
                usage_metadata['search_results'] = search_result.get('results', [])
                usage_metadata['report_numbers'] = report_numbers
            
            print(f"✅ Write 채팅 응답 생성 완료")
            return analysis_result, usage_metadata
            
        except Exception as e:
            print(f"❌ Write 채팅 중 오류: {e}")
            print(f"❌ 전체 에러 정보:")
            print(traceback.format_exc())
            return f"답변 생성 중 오류가 발생했습니다: {str(e)}", {}
    
    @staticmethod
    async def get_write_chat_history(user_id: str) -> Dict[str, Any]:
        """사용자의 Write 채팅 히스토리 조회"""
        history_key = get_write_history_key(user_id)
        if history_key in write_chat_histories:
            return {
                'session_id': history_key,
                'has_session': True,
                'history': write_chat_histories[history_key],
                'report_numbers': [],  # 현재는 빈 배열, 필요시 구현
                'user_report': write_user_reports.get(user_id, "")
            }
        return {
            'session_id': history_key,
            'has_session': False,
            'history': [],
            'report_numbers': [],
            'user_report': ""
        }
    
    @staticmethod
    async def cleanup_write_session(user_id: str) -> bool:
        """사용자의 Write 채팅 히스토리 정리"""
        try:
            cleanup_write_history(user_id)
            return True
        except Exception as e:
            print(f"❌ Write 히스토리 정리 중 오류: {e}")
            return False
    
    @staticmethod
    async def save_chat_message(
        user_id: str, 
        message: str, 
        response: str, 
        report_numbers: List[str]
    ) -> bool:
        """채팅 메시지 저장 (향후 구현)"""
        # 현재는 True 반환, 필요시 DB 저장 구현
        return True 