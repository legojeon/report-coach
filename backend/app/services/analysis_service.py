import os
import sys
from google import genai
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from typing import List, Optional, Tuple
from .logger_service import LoggerService

# 환경 변수 로드
load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError("GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다.")
client = genai.Client(api_key=API_KEY)

# 프롬프트 템플릿 로드
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(current_dir, "..", "..", "prompts", "prompt_refine.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        PROMPT_TEMPLATE = f.read()
except FileNotFoundError:
    raise FileNotFoundError(f"프롬프트 파일을 찾을 수 없습니다: {prompt_path}")

PROMPT = PromptTemplate.from_template(PROMPT_TEMPLATE)


class AnalysisService:
    """분석 관련 비즈니스 로직을 담당하는 서비스"""
    
    @staticmethod
    async def generate_combined_answer(contents: List[str], report_numbers: List[str], user_query: str, user_id: str, logger_service: Optional[LoggerService] = None, auth_token: Optional[str] = None) -> Tuple[str, dict]:
        """Gemini API를 사용하여 여러 보고서 내용을 기반으로 통합 답변 생성"""
        generation_config = {
            "max_output_tokens": int(os.getenv("GEMINI_MAX_TOKENS", "2048")),
            "temperature": float(os.getenv("GEMINI_TEMPERATURE", "0.1")),
            "top_p": float(os.getenv("GEMINI_TOP_P", "0.9")),
            "top_k": int(os.getenv("GEMINI_TOP_K", "40"))
        }

        gemini_model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-latest")
        # model = genai.GenerativeModel(model_name=gemini_model_name, generation_config=generation_config)
        # prompt는 아래에서 생성

        # 각 보고서 내용을 구조화하여 프롬프트에 포함
        reports_content = ""
        for i, (content, number) in enumerate(zip(contents, report_numbers), 1):
            reports_content += f"\n=== 보고서 {number} ===\n{content.strip()}\n"

        # 프롬프트 템플릿에 변수 대입
        prompt = PROMPT_TEMPLATE.format(
            report_count=len(report_numbers),
            user_query=user_query,
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
                        service_name="analyze_reports",
                        request_prompt=user_query,
                        request_token_count=usage_metadata.get('prompt_token_count', 0),
                        response_token_count=usage_metadata.get('candidates_token_count', 0),
                        total_token_count=usage_metadata.get('total_token_count', 0),
                        auth_token=auth_token  # 토큰 전달
                    )
                except Exception as log_error:
                    print(f"❌ 로깅 중 오류: {log_error}")
            return response.text.strip(), usage_metadata
        except Exception as e:
            return f"응답 생성 실패: {e}", {}

    @staticmethod
    async def analyze_combined_reports(report_numbers: List[str], original_query: str, user_id: Optional[str] = None, logger_service: Optional[LoggerService] = None, auth_token: Optional[str] = None) -> Tuple[str, dict]:
        """주어진 보고서 번호들의 union.txt 파일을 읽어서 통합 분석 수행"""
        contents = []

        for i, number in enumerate(report_numbers, 1):
            current_dir = os.path.dirname(os.path.abspath(__file__))
            union_file_path = os.path.join(current_dir, "..", "..", "datas", "extracted_pdf", "union", f"{number}_union.txt")

            if not os.path.exists(union_file_path):
                return f"파일을 찾을 수 없음: {union_file_path}", {}

            try:
                with open(union_file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()

                if not content:
                    return f"파일이 비어있음: {union_file_path}", {}

                contents.append(content)

            except Exception as e:
                return f"파일 읽기 오류: {e}", {}

        if not contents:
            return "분석할 내용이 없습니다.", {}

        answer, usage_metadata = await AnalysisService.generate_combined_answer(contents, report_numbers, original_query, user_id, logger_service, auth_token)
        return answer, usage_metadata

    @staticmethod
    async def analyze_reports(query: str, report_numbers: List[str], user_id: Optional[str] = None, logger_service: Optional[LoggerService] = None, auth_token: Optional[str] = None) -> Tuple[str, dict]:
        """분석 메인 함수 - 보고서 번호 출력 후 분석 수행"""
        # 분석할 보고서 번호 출력
        print(f"📊 분석 대상 보고서: {', '.join(report_numbers)}")
        
        # 분석 수행
        result, usage_metadata = await AnalysisService.analyze_combined_reports(report_numbers, query, user_id, logger_service, auth_token)
        return result, usage_metadata

 