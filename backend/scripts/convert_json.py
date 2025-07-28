import google.generativeai as genai
import json
import os
import re
import time
from datetime import datetime
from dotenv import load_dotenv
import sqlite3

# .env 파일에서 환경 변수 로드 (API 키 등) - backend 폴더 기준
load_dotenv("../.env") 

# --- 0. 모델 설정 및 API 키 로드 ---
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    print("오류: GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다.")
    print("환경 변수를 설정하거나, 코드에 직접 API 키를 입력해주세요.")
    exit()
genai.configure(api_key=API_KEY)

# 프로세스 ID 가져오기 (환경변수에서)
PROCESS_ID = int(os.getenv('PROCESS_ID', '0'))

# 로그 설정 (프로세스별)
import logging
from datetime import datetime

def setup_logging():
    """프로세스별 로깅 설정"""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # 프로세스별 로거 생성
    logger_name = f'convert_json_process_{PROCESS_ID}'
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    
    # 기존 핸들러 제거
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 파일 핸들러 (프로세스별)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_handler = logging.FileHandler(
        f"{log_dir}/convert_json_p{PROCESS_ID}_{timestamp}.log", 
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 포맷터 (프로세스 ID 포함)
    formatter = logging.Formatter(
        f'%(asctime)s - P{PROCESS_ID} - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# 로거 초기화
logger = setup_logging()

logger.info(f"✅ Gemini API 키 연결 완료 (프로세스 {PROCESS_ID}번)")

# 프롬프트 템플릿 파일 읽기
PROMPT_FILE_PATH = '../prompts/prompt_report.txt'

try:
    with open(PROMPT_FILE_PATH, 'r', encoding='utf-8') as f:
        prompt_template = f.read()
    print(f"'{PROMPT_FILE_PATH}' 파일에서 프롬프트 템플릿을 성공적으로 읽어왔습니다.")
except FileNotFoundError:
    print(f"오류: '{PROMPT_FILE_PATH}' 파일을 찾을 수 없습니다. 기본 프롬프트를 사용합니다.")
    prompt_template = """
    ## 탐구보고서 텍스트 구조화 요청

    다음 탐구보고서 텍스트를 적절한 섹션으로 분류하여 JSON 배열 형태로 반환해 주세요.

    **중요 지침:**
    1. **원문 내용 보존**: 텍스트 내용을 임의로 요약하거나 변경하지 말고, 원문을 최대한 그대로 보존해 주세요.
    2. **최소한의 정리**: 아래 사항만 정리해 주세요:
    - 문장 중간의 불필요한 줄바꿈 제거 (단어가 끊어지지 않도록)
    - 그림, 표, 사진 캡션 제거 (예: "그림 1. xxx", "표 2. xxx" 등)
    - 깨진 텍스트나 의미 없는 문자 제거
    3. **섹션 분류**: 내용을 분석하여 다음 섹션 중 하나로 분류해 주세요:
    - 서론 (연구 동기, 연구 목적 포함)
    - 이론적 배경 (관련 이론, 선행연구 조사 포함)
    - 연구 방법 (실험 방법, 준비물, 실험 과정 포함)
    - 연구 결과 (실험 결과, 관찰 내용 포함)
    - 결론 및 고찰 (결론, 토의, 향후 계획 포함)
    - 부록 (참고문헌, 추가 자료 포함)

    **반환 형식:**
    ```json
    [
        {
            "id": "보고서번호_섹션명_청크번호",
            "text": "원문 내용을 최대한 보존한 텍스트...",
            "metadata": {
                "report_number": 보고서번호,
                "title": "보고서 제목",
                "section": "섹션명",
                "chunk_index": 청크번호
            }
        }
    ]
    ```

    **주의사항:**
    - 반드시 완전하고 유효한 JSON 배열을 반환해 주세요
    - 원문의 의미나 내용을 변경하지 마세요
    - 텍스트가 길면 적절히 나누되, 의미 단위를 유지해 주세요
    """
except Exception as e:
    print(f"오류: 프롬프트 템플릿 파일을 읽는 중 문제가 발생했습니다: {e}")
    exit()

# 사용할 Gemini 모델 선택 및 generation_config 설정
generation_config = {
    "max_output_tokens": int(os.getenv("GEMINI_MAX_TOKENS", "32768")),
    "temperature": float(os.getenv("GEMINI_TEMPERATURE", "0.1")),
    "top_p": float(os.getenv("GEMINI_TOP_P", "0.9")),
    "top_k": int(os.getenv("GEMINI_TOP_K", "40"))
}

# 모델 설정 (환경 변수에서 가져오기)
gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite-preview-06-17")
model = genai.GenerativeModel(gemini_model, generation_config=generation_config)

# --- 1. 파일 및 디렉토리 경로 설정 ---
INPUT_FOLDER = '../datas/extracted_pdf/union' 
OUTPUT_FOLDER = '../datas/json_results'
FILE_EXTENSION = '.txt'

# --- 2. 헬퍼 함수 ---

def extract_file_number(filename: str) -> str:
    """파일명에서 보고서 번호를 추출합니다."""
    match = re.match(r'(\d+)_.*\.txt', filename)
    return match.group(1) if match else "UNKNOWN"

def clean_json_string(text: str) -> str:
    """모델 응답에서 마크다운 백틱을 제거합니다."""
    cleaned_text = text.strip()
    if cleaned_text.startswith("```json") and cleaned_text.endswith("```"):
        cleaned_text = cleaned_text[len("```json"):len(cleaned_text)-len("```")].strip()
    elif cleaned_text.startswith("```") and cleaned_text.endswith("```"):
        cleaned_text = cleaned_text[len("```"):len(cleaned_text)-len("```")].strip()
    return cleaned_text

def is_valid_json(json_str: str) -> bool:
    """JSON 문자열이 유효한지 확인합니다."""
    try:
        json.loads(json_str)
        return True
    except json.JSONDecodeError:
        return False

def fix_incomplete_json(json_str: str) -> str:
    """불완전한 JSON을 수정하려고 시도합니다."""
    json_str = json_str.strip()
    
    # 마지막 쉼표 제거
    if json_str.endswith(','):
        json_str = json_str[:-1]
    
    # 미완성 객체나 배열 닫기 시도
    open_braces = json_str.count('{') - json_str.count('}')
    open_brackets = json_str.count('[') - json_str.count(']')
    
    # 열린 브레이스 닫기
    for _ in range(open_braces):
        json_str += '}'
    
    # 열린 브래킷 닫기
    for _ in range(open_brackets):
        json_str += ']'
    
    return json_str

def chunk_text(text: str, max_chars: int = 15000) -> list:
    """긴 텍스트를 청크로 나눕니다."""
    if len(text) <= max_chars:
        return [text]
    
    chunks = []
    current_chunk = ""
    lines = text.split('\n')
    
    for line in lines:
        if len(current_chunk) + len(line) + 1 <= max_chars:
            current_chunk += line + '\n'
        else:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            current_chunk = line + '\n'
    
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks

def generate_timestamp() -> str:
    """현재 시간의 timestamp를 생성합니다."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def get_report_metadata(report_number):
    db_path = "../datas/science_reports.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT year, field, contest, award, authors, teacher, title FROM joined WHERE nttSn = ?",
        (str(report_number),)
    )
    row = cur.fetchone()
    conn.close()
    if row:
        return {
            "year": row[0],
            "field": row[1],
            "contest": row[2],
            "award": row[3],
            "authors": row[4],
            "teacher": row[5],
            "title": row[6]
        }
    else:
        return {}

def update_db_boolean_field(report_number: str, field_name: str, value: bool):
    """DB에 BOOLEAN 필드 업데이트"""
    try:
        db_path = "../datas/science_reports.db"
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(f"""
            UPDATE joined SET {field_name} = ? WHERE nttSn = ?
        """, (1 if value else 0, report_number))
        conn.commit()
        conn.close()
        logger.info(f"✅ DB 업데이트 완료: nttSn={report_number}, {field_name}={value}")
    except Exception as e:
        logger.error(f"❌ DB BOOLEAN 필드 업데이트 실패 (nttSn={report_number}, {field_name}): {e}")

# --- 3. 핵심 기능 함수 ---

def analyze_file_with_stream(filepath: str, model, max_retries: int = 3):
    """
    파일을 스트림 방식으로 분석합니다.
    """
    filename = os.path.basename(filepath)
    report_number = extract_file_number(filename)
    logger.info(f"🔄 분석 시작...")
    
    uploaded_file = None
    parsing_failures = []  # 파싱 실패 목록 수집

    try:
        # 1. 파일 내용 읽기
        with open(filepath, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        logger.info(f"- 파일 크기: {len(file_content)} 문자")
        
        # 2. 텍스트가 너무 길면 청킹 처리
        if len(file_content) > 20000:
            logger.info(f"- 텍스트가 길어서 청킹 처리합니다.")
            chunks = chunk_text(file_content, max_chars=15000)
            logger.info(f"- {len(chunks)}개의 청크로 분할되었습니다.")
            
            all_results = []
            for i, chunk in enumerate(chunks):
                logger.info(f"- 청크 {i+1}/{len(chunks)} 처리 중...")
                chunk_result = process_chunk_with_stream(chunk, model, filename, report_number, i+1, parsing_failures)
                if chunk_result and isinstance(chunk_result, list):
                    all_results.extend(chunk_result)
                elif chunk_result and isinstance(chunk_result, dict):
                    all_results.append(chunk_result)
                
                # 청크 간 지연
                time.sleep(2)
            
            # 파싱 실패 목록이 있으면 마지막에 출력
            if parsing_failures:
                logger.warning(f"⚠️ 파싱 실패한 청크: {', '.join(parsing_failures)}")
            
            return all_results
        else:
            # 3. 파일 업로드
            logger.info(f"- 파일 업로드 중...")
            uploaded_file = genai.upload_file(path=filepath, display_name=filename)
            logger.info(f"- 업로드 완료: {uploaded_file.uri}")

            # 4. 스트림 방식으로 여러 번 시도
            for attempt in range(max_retries):
                logger.info(f"- 시도 {attempt + 1}/{max_retries}")
                
                try:
                    # 프롬프트 구성
                    prompt_parts = [uploaded_file, prompt_template]

                    # API 호출 (스트림 방식)
                    logger.info("Gemini API로 스트림 분석 요청 중...")
                    response_stream = model.generate_content(prompt_parts, stream=True)
                    
                    # 스트림 응답 수집
                    full_response = ""
                    logger.info("스트림 응답 수신 중...")
                    
                    chunk_count = 0
                    for chunk in response_stream:
                        if chunk.text:
                            full_response += chunk.text
                            chunk_count += 1
                            if chunk_count % 10 == 0:  # 10개 청크마다 진행 상황 표시
                                logger.info("스트림 진행 중...")
                    
                    logger.info(f"스트림 응답 완료 (총 길이: {len(full_response)} 문자)")
                    
                    if not full_response.strip():
                        logger.warning(f"경고: 빈 응답 (시도 {attempt + 1})")
                        continue

                    # JSON 파싱 시도
                    clean_response_text = clean_json_string(full_response)
                    
                    # JSON 유효성 검사
                    if not is_valid_json(clean_response_text):
                        logger.warning(f"경고: 유효하지 않은 JSON, 수정 시도 중... (시도 {attempt + 1})")
                        fixed_json = fix_incomplete_json(clean_response_text)
                        if is_valid_json(fixed_json):
                            clean_response_text = fixed_json
                            logger.info("JSON 수정 성공!")
                        else:
                            logger.warning(f"JSON 수정 실패, 다시 시도... (시도 {attempt + 1})")
                            continue

                    json_result = json.loads(clean_response_text)
                    logger.info("✅ JSON 결과 성공적으로 파싱.")

                    # 메타데이터 보정 (nttSn 설정)
                    meta_extra = get_report_metadata(report_number)
                    if isinstance(json_result, list):
                        for item in json_result:
                            if isinstance(item, dict):
                                if "metadata" not in item:
                                    item["metadata"] = {}
                                try:
                                    item["metadata"]["nttSn"] = int(report_number)
                                except ValueError:
                                    item["metadata"]["nttSn"] = report_number
                                item["metadata"].update(meta_extra)
                    elif isinstance(json_result, dict):
                        if "metadata" not in json_result:
                            json_result["metadata"] = {}
                        try:
                            json_result["metadata"]["nttSn"] = int(report_number)
                        except ValueError:
                            json_result["metadata"]["nttSn"] = report_number
                        json_result["metadata"].update(meta_extra)

                    return json_result

                except json.JSONDecodeError as e:
                    logger.warning(f"경고: JSON 파싱 오류 (시도 {attempt + 1}): {e}")
                    if attempt < max_retries - 1:
                        logger.info("3초 후 재시도...")
                        time.sleep(3)
                    continue
                except Exception as e:
                    logger.error(f"오류 발생 (시도 {attempt + 1}): {e}")
                    if attempt < max_retries - 1:
                        logger.info("3초 후 재시도...")
                        time.sleep(3)
                    continue

            # 모든 시도 실패
            logger.error(f"❌ {max_retries}번의 시도 모두 실패")
            return {
                "error_type": "MAX_RETRIES_EXCEEDED",
                "filename": filename,
                "report_number": report_number,
                "attempts": max_retries
            }

    except Exception as e:
        logger.error(f"❌ 예상치 못한 오류 발생 ({filename}): {e}")
        return {
            "error_type": "UNEXPECTED_ERROR",
            "filename": filename,
            "report_number": report_number,
            "exception_message": str(e)
        }
    finally:
        # 리소스 관리
        if uploaded_file:
            logger.info(f"- 업로드된 파일 삭제 중...")
            try:
                genai.delete_file(uploaded_file.name)
                logger.info(f"- 파일 삭제 완료.")
            except Exception as e:
                logger.warning(f"경고: 업로드된 파일 삭제 중 오류 발생: {e}")

def process_chunk_with_stream(chunk_text: str, model, filename: str, report_number: str, chunk_index: int, parsing_failures=None):
    """
    단일 청크를 스트림 방식으로 처리합니다.
    """
    if parsing_failures is None:
        parsing_failures = []
    try:
        # 청크에 대한 간소화된 프롬프트
        chunk_prompt = f"""
다음 텍스트는 탐구보고서의 일부입니다. 이 텍스트를 적절한 섹션으로 분류하여 JSON 배열로 반환해 주세요.

**중요**: 원문 내용을 최대한 보존하고, 그림/표 캡션만 제거해 주세요.

섹션: [서론, 이론적 배경, 연구 방법, 연구 결과, 결론 및 고찰, 부록] 중 선택

반환 형식:
[
    {{
        "id": "{report_number}_섹션명_{chunk_index}",
        "text": "원문을 최대한 보존한 텍스트...",
        "metadata": {{
            "report_number": {report_number},
            "title": "보고서 제목",
            "section": "섹션명",
            "chunk_index": {chunk_index}
        }}
    }}
]

텍스트:
{chunk_text}
"""
        
        # 스트림 방식으로 응답 받기
        response_stream = model.generate_content(chunk_prompt, stream=True)
        
        full_response = ""
        for chunk in response_stream:
            if chunk.text:
                full_response += chunk.text
        
        if not full_response.strip():
            return None
            
        clean_response_text = clean_json_string(full_response)
        
        if is_valid_json(clean_response_text):
            json_result = json.loads(clean_response_text)
        else:
            fixed_json = fix_incomplete_json(clean_response_text)
            if is_valid_json(fixed_json):
                json_result = json.loads(fixed_json)
            else:
                parsing_failures.append(f"청크 {chunk_index}")
                return None
        
        # 청크 결과에 대한 메타데이터 보정 (nttSn 설정)
        meta_extra = get_report_metadata(report_number)
        if isinstance(json_result, list):
            for item in json_result:
                if isinstance(item, dict):
                    if "metadata" not in item:
                        item["metadata"] = {}
                    try:
                        item["metadata"]["nttSn"] = int(report_number)
                    except ValueError:
                        item["metadata"]["nttSn"] = report_number
                    item["metadata"].update(meta_extra)
        elif isinstance(json_result, dict):
            if "metadata" not in json_result:
                json_result["metadata"] = {}
            try:
                json_result["metadata"]["nttSn"] = int(report_number)
            except ValueError:
                json_result["metadata"]["nttSn"] = report_number
            json_result["metadata"].update(meta_extra)
        
        return json_result
                
    except Exception as e:
        print(f"    오류: 청크 {chunk_index} 처리 중 오류 발생: {e}")
        return None

# --- 4. 메인 실행 로직 ---

def get_file_range_from_env():
    """환경변수에서 파일 범위를 가져옵니다."""
    start_number = os.getenv('START_NTTSN')
    end_number = os.getenv('END_NTTSN')
    
    if start_number and end_number:
        try:
            return int(start_number), int(end_number)
        except ValueError:
            print(f"오류: 잘못된 nttSn 범위 형식: {start_number} ~ {end_number}")
            return None, None
    
    return None, None

def main():
    """메인 실행 함수"""
    # 결과 저장 폴더가 없으면 생성
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
        logger.info(f"📁 출력 폴더 생성: {OUTPUT_FOLDER}")

    # 처리할 파일 목록 가져오기
    file_list = []
    if os.path.exists(INPUT_FOLDER):
        try:
            file_list = [f for f in os.listdir(INPUT_FOLDER) if f.endswith(FILE_EXTENSION)]
            # 파일명 기준으로 정렬
            file_list = sorted(file_list)
        except (FileNotFoundError, PermissionError) as e:
            logger.warning(f"⚠️  입력 폴더 '{INPUT_FOLDER}' 접근 오류: {e}")
            file_list = []
    
    if not file_list:
        logger.warning(f"⚠️  '{INPUT_FOLDER}' 폴더에 처리할 '{FILE_EXTENSION}' 파일이 없습니다.")
        logger.info("빈 파일 목록으로 처리합니다.")
        # 빈 파일 목록으로 계속 진행

    # 파일 범위 결정 (환경변수에서 가져오기)
    start_number, end_number = get_file_range_from_env()
    
    if start_number is None or end_number is None:
        logger.error("오류: 환경변수로 파일 범위를 지정해야 합니다.")
        logger.error("환경변수: START_NTTSN, END_NTTSN")
        logger.error("병렬 실행에서는 환경변수가 필수입니다.")
        return
    
    logger.info(f"환경변수로 받은 범위: {start_number} ~ {end_number}")
    
    # 범위 검증
    if start_number > end_number:
        logger.error("오류: 시작 번호가 끝 번호보다 클 수 없습니다.")
        return
    
    # DB에서 실제 파일 확인 및 필터링
    filtered_files = []
    try:
        db_path = "../datas/science_reports.db"
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # 범위 내 실제 파일 조회 (json_api = 0인 것만)
        cur.execute("""
            SELECT nttSn FROM joined 
            WHERE nttSn BETWEEN ? AND ? AND (json_api = 0 OR json_api IS NULL)
            ORDER BY nttSn ASC
        """, (start_number, end_number))
        
        db_nttSn_list = [row[0] for row in cur.fetchall()]
        conn.close()
        
        logger.info(f"DB에서 조회된 nttSn 목록: {len(db_nttSn_list)}개 (json_api = 0인 것만)")
        
        # 파일 시스템의 파일과 DB의 nttSn을 매칭
        for filename in file_list:
            report_number = extract_file_number(filename)
            if report_number != "UNKNOWN":
                try:
                    file_number = int(report_number)
                    if file_number in db_nttSn_list:
                        filtered_files.append(filename)
                except ValueError:
                    continue
                    
    except Exception as e:
        logger.error(f"DB 조회 실패: {e}")
        # DB 조회 실패 시 기존 방식으로 fallback
        for filename in file_list:
            report_number = extract_file_number(filename)
            if report_number != "UNKNOWN":
                try:
                    file_number = int(report_number)
                    if start_number <= file_number <= end_number:
                        filtered_files.append(filename)
                except ValueError:
                    continue
    
    if not filtered_files:
        logger.error(f"오류: 번호 {start_number}~{end_number} 범위에 해당하는 파일이 없습니다.")
        return
    
    logger.info(f"\n=== 처리 설정 ===")
    logger.info(f"처리 범위: {start_number} ~ {end_number}")
    logger.info(f"처리할 파일 수: {len(filtered_files)}개")
    logger.info(f"처리할 파일 목록:")
    for filename in filtered_files:
        logger.info(f"  - {filename}")
    
    # 환경변수로 실행된 경우 자동으로 진행
    logger.info(f"\n환경변수로 실행되어 자동으로 진행합니다.")
    
    logger.info(f"\n총 {len(filtered_files)}개의 파일을 처리합니다...")
    
    # 성공적으로 처리된 파일 수 카운트
    success_count = 0
    failed_count = 0
    failed_files = []  # 실패한 파일 번호 리스트

    for index, filename in enumerate(filtered_files, 1):
        input_filepath = os.path.join(INPUT_FOLDER, filename)
        
        # 파일명에서 보고서 번호 추출
        report_number = extract_file_number(filename)
        
        # 현재 처리 중인 파일 정보 출력
        logger.info(f"\n📄 [{index}/{len(filtered_files)}] 파일 처리 중: {filename}")
        logger.info(f"   보고서 번호: {report_number}")
        logger.info("-" * 60)
        
        # API 분석 실행 (스트림 방식)
        result_json = analyze_file_with_stream(input_filepath, model)

        # 결과 처리 및 개별 파일로 저장
        if result_json and not isinstance(result_json, dict) or (isinstance(result_json, dict) and 'error_type' not in result_json):
            # 개별 JSON 파일명 생성
            output_filename = f"{report_number}_union.json"
            output_filepath = os.path.join(OUTPUT_FOLDER, output_filename)
            
            try:
                # 결과를 개별 JSON 파일로 저장
                with open(output_filepath, 'w', encoding='utf-8') as f:
                    json.dump(result_json, f, ensure_ascii=False, indent=4)
                logger.info(f"  ✅ '{output_filename}' 파일로 저장 완료")
                
                # 성공 시 DB 업데이트
                update_db_boolean_field(report_number, 'json_api', True)
                
                success_count += 1
            except Exception as e:
                logger.error(f"  ❌ '{output_filename}' 저장 실패: {e}")
                # 실패 시 DB 업데이트
                update_db_boolean_field(report_number, 'json_api', False)
                failed_count += 1
                failed_files.append(report_number)
        else:
            # 에러가 발생한 경우 파일 생성하지 않음
            if isinstance(result_json, dict) and 'error_type' in result_json:
                logger.error(f"❌ API 처리 실패: {result_json.get('error_type', 'UNKNOWN_ERROR')} - {filename}")
                logger.error(f"   에러 상세: {result_json}")
            else:
                logger.warning(f"⚠️ 처리 실패 또는 건너뜀: {filename}")
            
            # 실패 시 DB 업데이트
            update_db_boolean_field(report_number, 'json_api', False)
            failed_count += 1
            failed_files.append(report_number)
        
        # API Rate Limit를 피하기 위한 지연
        time.sleep(5)

    # 처리 결과 요약
    logger.info(f"\n✨ 모든 작업이 완료되었습니다.")
    logger.info(f"📊 처리 결과:")
    logger.info(f"   - 성공: {success_count}개 파일")
    logger.info(f"   - 실패: {failed_count}개 파일")
    logger.info(f"   - 총 처리: {len(filtered_files)}개 파일")
    logger.info(f"📁 결과 파일 위치: '{OUTPUT_FOLDER}' 폴더")
    
    # 실패한 파일 번호 리스트 출력
    if failed_files:
        logger.error(f"❌ 실패한 파일 번호: {failed_files}")
        logger.error(f"   실패한 파일 수: {len(failed_files)}개")
    else:
        logger.info(f"✅ 모든 파일이 성공적으로 처리되었습니다!")

if __name__ == "__main__":
    main() 