import os
import sys
import warnings
import torch
from google import genai
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from dotenv import load_dotenv
import numpy as np
import re
from typing import List, Dict, Any, Optional, Tuple
from fastapi import HTTPException
from langchain_core.prompts import PromptTemplate
from .logger_service import LoggerService

# 경고 메시지 억제
warnings.filterwarnings('ignore', category=RuntimeWarning, module='sklearn')

# .env 파일 로드
load_dotenv()

# 가중치 설정 (환경변수에서 읽어오기)
def get_weight_config():
    """환경변수에서 가중치 설정을 읽어와서 반환"""
    return {
        "alpha": float(os.getenv("SEARCH_ALPHA", "1.1")),                    # 제목 유사도 가중치 (content_score + alpha * title_score)
        "gamma": float(os.getenv("SEARCH_GAMMA", "0.05")),                   # 키워드 매칭 가중치 (gamma * matched_terms)
        "section_weights": {  # 섹션 우선순위별 가중치
            0: float(os.getenv("SEARCH_SECTION_WEIGHT_1", "0.08")),  # 1순위
            1: float(os.getenv("SEARCH_SECTION_WEIGHT_2", "0.04")),  # 2순위
            2: float(os.getenv("SEARCH_SECTION_WEIGHT_3", "0.01"))   # 3순위
        },
    "award_weights": {               # 수상도별 가중치 (높은 순위일수록 높은 가중치)
            "대통령상": float(os.getenv("SEARCH_AWARD_PRESIDENT", "0.15")),
            "국무총리상": float(os.getenv("SEARCH_AWARD_PRIME_MINISTER", "0.12")),
            "최우수상": float(os.getenv("SEARCH_AWARD_EXCELLENT", "0.10")),
            "특상": float(os.getenv("SEARCH_AWARD_SPECIAL", "0.08")),
            "우수상": float(os.getenv("SEARCH_AWARD_GOOD", "0.06")),
            "장려상": float(os.getenv("SEARCH_AWARD_ENCOURAGEMENT", "0.04"))
    },
    "metadata_weights": {
            "field": float(os.getenv("SEARCH_METADATA_FIELD", "0.06")),      # 분야 매칭 가중치
            "year": float(os.getenv("SEARCH_METADATA_YEAR", "0.05")),        # 연도 매칭 가중치
            "award": float(os.getenv("SEARCH_METADATA_AWARD", "0.08")),      # 수상내역 매칭 가중치
            "authors": float(os.getenv("SEARCH_METADATA_AUTHORS", "0.1")),   # 저자 매칭 가중치
            "teacher": float(os.getenv("SEARCH_METADATA_TEACHER", "0.1"))    # 지도교사 매칭 가중치
    }
}

# 전역 가중치 설정 변수
WEIGHT_CONFIG = get_weight_config()

# Gemini API 설정
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError("GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다.")
client = genai.Client(api_key=API_KEY)

# 임베딩 모델 및 Chroma DB 설정
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-large")

# 디바이스 설정
EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE", "cuda" if torch.cuda.is_available() else "cpu")

EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))

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
CHROMA_DIR = PATHS["chroma_db"]

# 프롬프트 템플릿 로드
try:
    prompt_path = os.path.join(PATHS["prompts"], "prompt_search.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        QUERY_ANALYSIS_PROMPT_TEMPLATE = f.read()
except FileNotFoundError:
    raise FileNotFoundError(f"프롬프트 파일을 찾을 수 없습니다: {prompt_path}")

QUERY_ANALYSIS_PROMPT = PromptTemplate.from_template(QUERY_ANALYSIS_PROMPT_TEMPLATE)

# 전역 변수
_embedding_model = None
_vectorstore = None


def cosine_similarity_numpy(vec1, vec2):
    """numpy를 사용한 cosine similarity 계산"""
    if np.allclose(vec1, 0) or np.allclose(vec2, 0):
        return 0.0
    epsilon = 1e-8
    similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2) + epsilon)
    return np.clip(similarity, -1.0, 1.0)


def get_image_path_from_db(number: str) -> str:
    """데이터베이스에서 보고서 번호에 해당하는 이미지 경로를 가져옵니다."""
    try:
        # 이미지 파일 경로 확인
        image_dir = os.path.join(PATHS["extracted_pdf"], "image")
        image_path = os.path.join(image_dir, f"{number}_image.png")
        
        if os.path.exists(image_path):
            return f"{number}_image.png"
        else:
            return ""
    except Exception as e:
        print(f"❌ 이미지 경로 확인 실패 (번호: {number}): {e}")
        return ""


class SearchService:
    """검색 관련 비즈니스 로직을 담당하는 서비스"""
    
    @staticmethod
    def initialize_models():
        """모델들을 지연 초기화"""
        global _embedding_model, _vectorstore
        
        if _embedding_model is None:
            print(f"🔧 모델 초기화 시작...")
            
            # CUDA 사용 가능 여부 확인
            if not torch.cuda.is_available():
                print(f"❌ CUDA가 사용 불가능합니다.")
                print(f"GPU 드라이버와 PyTorch CUDA 버전을 확인해주세요.")
                raise RuntimeError("CUDA가 필요합니다.")
            
            print(f"✅ CUDA 사용 가능: {torch.cuda.get_device_name(0)}")
            
            # Gemini API 설정
            # genai.configure(api_key=API_KEY) # 이전 코드에서 이미 설정됨
            print(f"✅ Gemini API 설정 완료")
            
            # 임베딩 모델 초기화 (CUDA 필수)
            print(f"🧠 임베딩 모델 로딩 중: {EMBEDDING_MODEL_NAME}")
            try:
                _embedding_model = HuggingFaceEmbeddings(
                    model_name=EMBEDDING_MODEL_NAME,
                    model_kwargs={'device': EMBEDDING_DEVICE},
                    encode_kwargs={'batch_size': EMBEDDING_BATCH_SIZE}
                )
                print(f"✅ 임베딩 모델 로드 완료: {EMBEDDING_DEVICE}")
            except RuntimeError as e:
                print(f"❌ CUDA 디바이스 오류 발생: {e}")
                print(f"CUDA가 필요합니다. GPU 드라이버와 PyTorch CUDA 버전을 확인해주세요.")
                raise RuntimeError(f"CUDA 디바이스 오류: {e}")
            
            # Chroma DB 초기화
            print(f"💾 Chroma DB 로딩 중: {CHROMA_DIR}")
            if not os.path.exists(CHROMA_DIR):
                raise ValueError(f"Chroma DB 디렉토리 '{CHROMA_DIR}'가 존재하지 않습니다.")
            
            _vectorstore = Chroma(
                persist_directory=CHROMA_DIR, 
                embedding_function=_embedding_model,
                collection_name="my_report_collection"
            )
            print(f"✅ Chroma DB 로딩 완료")
        
        return _embedding_model, _vectorstore
    
    @staticmethod
    async def analyze_user_query(original_query: str, user_id: str, logger_service: Optional[LoggerService] = None, is_hidden: bool = False) -> Tuple[str, List[str], List[str], Dict, str, Dict]:
        """사용자 쿼리를 분석하여 요약 쿼리, 우선순위 섹션, 키워드, 메타데이터 필터, 의도, 사용량 메타데이터를 반환"""
        generation_config = {
            "max_output_tokens": int(os.getenv("GEMINI_MAX_TOKENS", "2048")),
            "temperature": float(os.getenv("GEMINI_TEMPERATURE", "0.1")),
            "top_p": float(os.getenv("GEMINI_TOP_P", "0.9")),
            "top_k": int(os.getenv("GEMINI_TOP_K", "40"))
        }
        gemini_model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-latest")
        prompt = QUERY_ANALYSIS_PROMPT_TEMPLATE.replace("{{query}}", original_query)

        try:
            response = client.models.generate_content(
                model=gemini_model_name,
                contents=prompt,
            )
            response_content = response.text
            
            # 사용량 메타데이터 추출
            usage_metadata = {}
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage_metadata = {
                    'total_token_count': response.usage_metadata.total_token_count,
                    'prompt_token_count': response.usage_metadata.prompt_token_count,
                    'candidates_token_count': response.usage_metadata.candidates_token_count
                }
            
            print(f"🔍 Gemini API 응답:")
            print(response_content)
            print(f"🔍 사용량 메타데이터: {usage_metadata}")

            summary_query = ""
            priority_sections = []
            extracted_keywords = []

            summary_match = re.search(r"요약 쿼리:\s*(.+)", response_content)
            if summary_match:
                summary_query = summary_match.group(1).strip()

            sections_match = re.search(r"우선순위 섹션:\s*(.+)", response_content)
            if sections_match:
                sections_str = sections_match.group(1).strip()
                priority_sections = [s.strip() for s in sections_str.split('>') if s.strip()]

            keywords_match = re.search(r"핵심 키워드:\s*(.+)", response_content)
            if keywords_match:
                keyword_str = keywords_match.group(1).strip()
                extracted_keywords = [kw.strip().lower() for kw in re.split(r"[,\s]+", keyword_str) if len(kw.strip()) > 1]

            metadata_filters = {}
            for key in ["field", "year", "award", "authors", "teacher"]:
                match = re.search(rf"{key}:\s*(.+)", response_content, re.IGNORECASE)
                if match:
                    metadata_filters[key] = match.group(1).strip()

            # 로깅 수행 (logger_service가 제공된 경우에만)
            if logger_service and usage_metadata:
                try:
                    await logger_service.log_ai_usage(
                        user_id=user_id,
                        service_name="query_summary",
                        request_prompt=original_query,
                        request_token_count=usage_metadata.get('prompt_token_count', 0),
                        response_token_count=usage_metadata.get('candidates_token_count', 0),
                        total_token_count=usage_metadata.get('total_token_count', 0),
                        is_hidden=is_hidden
                    )
                except Exception as log_error:
                    print(f"❌ 로깅 중 오류: {log_error}")
            
            return summary_query, priority_sections, extracted_keywords, metadata_filters, usage_metadata

        except Exception as e:
            print(f"❌ 쿼리 분석 중 오류: {e}")
            return original_query, [], [], {}, "", {}
    
    @staticmethod
    def rerank_with_weights(
        query_embedding,
        documents,
        embedding_model,
        priority_sections,
        simplified_query,
        original_query,
        keyword_match_terms,
        weight_config=WEIGHT_CONFIG,
        metadata_filters=None
    ):
        """문서를 가중치를 적용하여 재정렬"""
        alpha = weight_config["alpha"]
        gamma = weight_config["gamma"]
        section_weights = weight_config["section_weights"]
        award_weights = weight_config["award_weights"]  # 수상도별 가중치
        metadata_weight_table = weight_config["metadata_weights"]

        doc_texts = [doc.page_content for doc in documents]
        doc_titles = [doc.metadata.get("title", "") for doc in documents]

        doc_vectors = embedding_model.embed_documents(doc_texts)
        title_vectors = embedding_model.embed_documents(doc_titles)

        simplified_terms = [t.lower() for t in simplified_query.split() if len(t) > 1]
        original_terms = [t.lower() for t in original_query.split() if len(t) > 1]

        reranked_results = []

        for i, doc in enumerate(documents):
            content_score = cosine_similarity_numpy(query_embedding, doc_vectors[i])
            title_score = cosine_similarity_numpy(query_embedding, title_vectors[i]) if doc_titles[i].strip() else 0.0

            # 섹션 부스터 점수 계산 (Gemini가 분석한 우선순위 섹션과 일치할 때 가중치 적용)
            section_boost_score = 0.0
            doc_section = doc.metadata.get("section", "")
            if doc_section in priority_sections:
                try:
                    priority_index = priority_sections.index(doc_section)  # 우선순위에서의 위치 (0, 1, 2)
                    section_boost_score = section_weights.get(priority_index, 0.0)  # 1순위: 0.08, 2순위: 0.04, 3순위: 0.01
                except ValueError:
                    pass

            text_lower = doc.page_content.lower()
            title_lower = doc_titles[i].lower()

            simplified_matches = sum(1 for term in simplified_terms if term in text_lower or term in title_lower)
            original_matches = sum(1 for term in original_terms if term in text_lower or term in title_lower)
            matched_terms = simplified_matches + original_matches

            keyword_matches = sum(1 for kw in keyword_match_terms if kw in text_lower or kw in title_lower)
            keyword_boost_score = gamma * (matched_terms + keyword_matches)

            # 수상도 부스터 점수 계산 (높은 순위의 수상일수록 높은 가중치 적용)
            award_boost_score = 0.0
            doc_award = doc.metadata.get("award", "")
            if doc_award in award_weights:
                award_boost_score = award_weights[doc_award]  # 대통령상: 0.15, 국무총리상: 0.12, 최우수상: 0.10, 특상: 0.08, 우수상: 0.06, 장려상: 0.04

            metadata_boost = 0.0
            if metadata_filters:
                for key, val in metadata_filters.items():
                    doc_val = str(doc.metadata.get(key, '')).strip()
                    if doc_val == val:
                        metadata_boost += metadata_weight_table.get(key, 0.05)

            matched_terms += keyword_matches
            total_score = (
                (content_score + alpha * title_score)
                + section_boost_score
                + keyword_boost_score
                + award_boost_score  # 수상도 부스터 점수 추가
                + metadata_boost
            )

            score_info = {
                'content_score': content_score,        # 내용 유사도 점수 (0~1)
                'title_score': title_score,            # 제목 유사도 점수 (0~1)
                'alpha': alpha,                        # 제목 가중치 계수
                'section_boost_score': section_boost_score,  # 섹션 부스터 점수 (1순위: 0.08, 2순위: 0.04, 3순위: 0.01)
                'keyword_boost_score': keyword_boost_score,  # 키워드 매칭 부스터 점수
                'award_boost_score': award_boost_score,  # 수상도 부스터 점수 (대통령상: 0.15, 국무총리상: 0.12, 최우수상: 0.10, 특상: 0.08, 우수상: 0.06, 장려상: 0.04)
                'metadata_boost': metadata_boost,      # 메타데이터 매칭 부스터 점수
                'matched_terms': matched_terms,        # 매칭된 키워드 개수
                'simplified_matches': simplified_matches,  # 요약 쿼리 매칭 개수
                'original_matches': original_matches,  # 원본 쿼리 매칭 개수
                'total_score': total_score,            # 최종 점수
                'calculation': f"({content_score:.4f} + {alpha} × {title_score:.4f}) + {section_boost_score:.4f} + {keyword_boost_score:.4f} + {award_boost_score:.4f} + {metadata_boost:.4f} = {total_score:.4f}"
            }

            reranked_results.append((doc, total_score, score_info))

        reranked_results.sort(key=lambda x: x[1], reverse=True)
        return reranked_results
    
    @staticmethod
    async def search_documents(query: str, k: int = 10, user_id: Optional[str] = None, logger_service: Optional[LoggerService] = None, is_hidden: bool = False) -> Dict[str, Any]:
        """문서 검색 처리"""
        try:
            print(f"🔍 검색 요청 받음: {query}")
            query = query.strip()

            if not query:
                raise HTTPException(status_code=400, detail="검색어를 입력해주세요.")

            print(f"🔧 모델 초기화 시작...")
            # 모델 초기화
            embedding_model, vectorstore = SearchService.initialize_models()
            print(f"✅ 모델 초기화 완료")

            print(f"🧠 쿼리 분석 시작...")
            # 쿼리 분석
            summary_query, priority_sections, keyword_terms, metadata_filters, usage_metadata = await SearchService.analyze_user_query(query, user_id, logger_service, is_hidden)
            print(f"✅ 쿼리 분석 완료: {summary_query}")
            # print(f"🎯 쿼리 의도: {intent if intent else '분석 불가'}")
            
            if not summary_query:
                raise HTTPException(status_code=500, detail="요약 쿼리 생성에 실패했습니다.")

            print(f"🔍 벡터 검색 시작...")
            # 벡터 검색
            initial_search_k = k * 5
            raw_results = vectorstore.similarity_search_with_score(summary_query, k=initial_search_k)
            raw_documents = [doc for doc, _ in raw_results]
            print(f"✅ 벡터 검색 완료: {len(raw_documents)}개 문서 발견")

            # 메타데이터 필터 적용
            if metadata_filters:
                filtered_documents = [doc for doc in raw_documents if all(str(doc.metadata.get(key, '')).strip() == val.strip() for key, val in metadata_filters.items())]
                if len(filtered_documents) < k:
                    filtered_documents = raw_documents
            else:
                filtered_documents = raw_documents

            query_embedding = embedding_model.embed_query(summary_query)

            # 재정렬
            reranked = SearchService.rerank_with_weights(
                query_embedding,
                filtered_documents,
                embedding_model,
                priority_sections,
                summary_query,
                query,
                keyword_terms,
                WEIGHT_CONFIG,
                metadata_filters
            )

            # 결과 포맷팅 (중복 number 제거)
            results = []
            seen_numbers = set()
            for i, (doc, score, score_info) in enumerate(reranked, 1):
                number = str(doc.metadata.get('nttSn', 'N/A'))  # 항상 문자열로 변환
                if number in seen_numbers:
                    continue
                seen_numbers.add(number)
                
                # 이미지 경로 가져오기
                image_path = get_image_path_from_db(number)
                
                result = {
                    'rank': len(results) + 1,
                    'title': doc.metadata.get('title', 'N/A'),
                    'section': doc.metadata.get('section', 'N/A'),
                    'number': number,
                    'metadata': {
                        'field': doc.metadata.get('field', 'N/A'),
                        'year': doc.metadata.get('year', 'N/A'),
                        'award': doc.metadata.get('award', 'N/A'),
                        'authors': doc.metadata.get('authors', 'N/A'),
                        'teacher': doc.metadata.get('teacher', 'N/A'),
                        'source_type': doc.metadata.get('source_type', 'N/A')
                    },
                    'score_info': score_info,
                    'content': doc.page_content[:500] + "..." if len(doc.page_content) > 500 else doc.page_content,
                    'image_path': image_path
                }
                results.append(result)
                if len(results) >= k:
                    break

            response_data = {
                "query": query,
                "summary_query": summary_query,
                "priority_sections": priority_sections,
                "metadata_filters": metadata_filters,
                # "intent": intent,
                "total_results": len(results),
                "results": results,
                "usage_metadata": usage_metadata
            }
            
            print(f"🔍 API 응답 데이터:")
            # print(f"  - intent: '{intent}'")
            print(f"  - total_results: {len(results)}")
            print("-" * 50)
            
            return response_data

        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ 검색 중 오류: {e}")
            raise HTTPException(status_code=500, detail=f"검색 중 오류가 발생했습니다: {str(e)}") 