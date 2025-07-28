#!/usr/bin/env python3
"""
PDF 텍스트 재포맷 스크립트
보고서와 요약본을 합쳐서 Gemini API로 재포맷팅
"""

import os
import sys
import time
import sqlite3
import logging
import traceback
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from functools import wraps
import google.generativeai as genai
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv("../.env")

@dataclass
class ReformatConfig:
    """재포맷 설정 클래스"""
    start_nttSn: Optional[int] = None
    end_nttSn: Optional[int] = None
    max_retries: int = 3
    retry_delay: int = 5
    api_delay: int = 3  # API 호출 간 대기 시간
    max_workers: int = 1  # Gemini API는 순차 처리 권장

class ReformatLogger:
    """재포맷 로거 클래스"""
    
    def __init__(self, log_dir: str = "logs", process_id: int = 0):
        self.log_dir = log_dir
        self.process_id = process_id
        self.setup_logging()
    
    def setup_logging(self):
        """로깅 설정"""
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 프로세스별 로거 생성
        logger_name = f'reformat_process_{self.process_id}'
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.INFO)
        
        # 기존 핸들러 제거
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # 파일 핸들러 (프로세스별)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_handler = logging.FileHandler(
            f"{self.log_dir}/reformat_p{self.process_id}_{timestamp}.log", 
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        
        # 콘솔 핸들러
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 포맷터 (프로세스 ID 포함)
        formatter = logging.Formatter(
            f'%(asctime)s - P{self.process_id} - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def log_success(self, message: str):
        """성공 로그"""
        self.logger.info(f"✅ {message}")
    
    def log_error(self, message: str, error: Exception = None):
        """에러 로그"""
        if error:
            self.logger.error(f"❌ {message}: {str(error)}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
        else:
            self.logger.error(f"❌ {message}")
    
    def log_warning(self, message: str):
        """경고 로그"""
        self.logger.warning(f"⚠️ {message}")
    
    def log_info(self, message: str):
        """정보 로그"""
        self.logger.info(f"ℹ️ {message}")

def retry_on_failure(max_retries: int = 3, delay: int = 5):
    """재시도 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        time.sleep(delay)
                        continue
                    else:
                        raise last_exception
        return wrapper
    return decorator

class TextReformatter:
    """텍스트 재포맷터 클래스"""
    
    def __init__(self, config: ReformatConfig):
        self.config = config
        
        # 프로세스 ID 가져오기 (환경변수에서)
        process_id = int(os.getenv('PROCESS_ID', '0'))
        self.process_id = process_id  # process_id를 인스턴스 변수로 저장
        self.logger = ReformatLogger(process_id=process_id)
        
        # API 키 설정
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다.")
        
        genai.configure(api_key=self.api_key)
        self.logger.log_success(f"✅ Gemini API 키 연결 완료 (프로세스 {self.process_id}번)")
        
        # 모델 설정
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-latest")
        self.model = genai.GenerativeModel(self.model_name)
        
        # 경로 설정
        self.db_path = "../datas/science_reports.db"
        self.prompt_file = "../prompts/prompt_reformat.txt"
        self.report_text_dir = "../datas/extracted_pdf/report"
        self.summary_text_dir = "../datas/extracted_pdf/summary"
        self.union_dir = "../datas/extracted_pdf/union"
        
        # 상위 디렉토리 생성
        os.makedirs("../datas", exist_ok=True)
        os.makedirs("../datas/extracted_pdf", exist_ok=True)
        os.makedirs(self.union_dir, exist_ok=True)
        
        # 프롬프트 로드
        self.prompt_template = self.load_prompt()
        
        # 재포맷 통계
        self.reformat_stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0
        }
    
    def load_prompt(self) -> str:
        """프롬프트 파일 로드"""
        try:
            with open(self.prompt_file, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            self.logger.log_error(f"프롬프트 파일을 찾을 수 없음: {self.prompt_file}")
            raise
        except Exception as e:
            self.logger.log_error(f"프롬프트 파일 로드 실패: {self.prompt_file}", e)
            raise
    
    def get_reformat_data(self) -> List[Dict]:
        """재포맷할 데이터 조회"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            # nttSn 범위로 직접 조회 (union_text = 0인 것만)
            if self.config.start_nttSn and self.config.end_nttSn:
                cur.execute("""
                    SELECT number, nttSn, title, file1_url, file2_url 
                    FROM joined 
                    WHERE nttSn BETWEEN ? AND ? AND (union_text = 0 OR union_text IS NULL)
                    ORDER BY nttSn ASC
                """, (self.config.start_nttSn, self.config.end_nttSn))
                
                self.logger.log_info(f"nttSn 범위: {self.config.start_nttSn} ~ {self.config.end_nttSn} (union_text = 0인 것만)")
            else:
                # 전체 데이터 조회 (union_text = 0인 것만)
                cur.execute("""
                    SELECT number, nttSn, title, file1_url, file2_url 
                    FROM joined 
                    WHERE union_text = 0 OR union_text IS NULL
                    ORDER BY nttSn ASC
                """)
            
            rows = cur.fetchall()
            conn.close()
            
            data = []
            for row in rows:
                data.append({
                    'number': row[0],
                    'nttSn': row[1],
                    'title': row[2],
                    'file1_url': row[3],
                    'file2_url': row[4]
                })
            
            self.logger.log_info(f"재포맷 대상: {len(data)}개 파일 (union_text = 0인 것만)")
            return data
            
        except Exception as e:
            self.logger.log_error("데이터베이스 조회 실패", e)
            raise
    
    def read_text_file(self, file_path: str) -> str:
        """텍스트 파일 읽기"""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"파일을 찾을 수 없음: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if not content.strip():
                self.logger.log_warning(f"빈 파일: {file_path}")
                return ""
            
            return content
            
        except Exception as e:
            self.logger.log_error(f"파일 읽기 실패: {file_path}", e)
            raise
    
    @retry_on_failure(max_retries=3, delay=5)
    def call_gemini_api(self, combined_text: str, nttSn: str) -> str:
        """Gemini API 호출"""
        try:
            # 임시 파일 생성
            temp_filename = f"{nttSn}_temp.txt"
            with open(temp_filename, 'w', encoding='utf-8') as f:
                f.write(combined_text)
            
            try:
                # 파일 업로드
                uploaded_file = genai.upload_file(path=temp_filename, display_name=temp_filename)
                
                # API 호출
                prompt_parts = [uploaded_file, self.prompt_template]
                self.logger.log_info(f"Gemini API 요청 중... (nttSn: {nttSn})")
                
                response = self.model.generate_content(prompt_parts)
                result_text = response.text.strip()
                
                if not result_text:
                    raise ValueError("API 응답이 비어있습니다.")
                
                return result_text
                
            finally:
                # 임시 파일 및 업로드된 파일 정리
                try:
                    genai.delete_file(temp_filename)
                except Exception:
                    pass
                try:
                    os.remove(temp_filename)
                except Exception:
                    pass
                
        except Exception as e:
            self.logger.log_error(f"Gemini API 호출 실패 (nttSn: {nttSn})", e)
            raise
    
    def reformat_files(self):
        """모든 파일 재포맷"""
        self.logger.log_info("=== PDF 텍스트 재포맷 시작 ===")
        
        try:
            # 재포맷 데이터 조회
            reformat_data = self.get_reformat_data()
            
            for i, item in enumerate(reformat_data):
                number = item['number']
                nttSn = item['nttSn']
                title = item['title']
                
                self.logger.log_info(f"처리 중 ({i+1}/{len(reformat_data)}): nttSn={nttSn}, number={number} - {title[:50]}...")
                
                # 파일 경로 설정
                report_txt_path = os.path.join(self.report_text_dir, f"{nttSn}_report.txt")
                summary_txt_path = os.path.join(self.summary_text_dir, f"{nttSn}_summary.txt")
                union_txt_path = os.path.join(self.union_dir, f"{nttSn}_union.txt")
                
                # 이미 처리된 파일 확인
                if os.path.exists(union_txt_path):
                    self.logger.log_info(f"재포맷 파일 이미 존재: {union_txt_path}")
                    self.reformat_stats['skipped'] += 1
                    continue
                
                # DB에서 파일 존재 여부 확인
                try:
                    conn = sqlite3.connect(self.db_path)
                    cur = conn.cursor()
                    cur.execute("""
                        SELECT saved_filename1, saved_filename2, is_pdf 
                        FROM joined WHERE nttSn = ?
                    """, (nttSn,))
                    row = cur.fetchone()
                    
                    if not row:
                        self.logger.log_warning(f"DB에서 nttSn {nttSn}을 찾을 수 없음")
                        self.reformat_stats['failed'] += 1
                        self.update_db_boolean_field(nttSn, 'union_text', False)
                        continue
                    
                    saved_filename1 = row[0]  # 보고서 파일
                    saved_filename2 = row[1]  # 요약본 파일
                    is_pdf = bool(row[2]) if row[2] is not None else False
                    conn.close()
                    
                except Exception as e:
                    self.logger.log_error(f"DB 조회 실패 (nttSn: {nttSn})", e)
                    self.reformat_stats['failed'] += 1
                    self.update_db_boolean_field(nttSn, 'union_text', False)
                    continue
                
                # 파일 존재 여부 확인
                report_exists = os.path.exists(report_txt_path) and saved_filename1 is not None
                summary_exists = os.path.exists(summary_txt_path) and saved_filename2 is not None
                
                if not report_exists and not summary_exists:
                    self.logger.log_warning(f"보고서와 요약본 파일 모두 없음: nttSn={nttSn}")
                    self.reformat_stats['failed'] += 1
                    self.update_db_boolean_field(nttSn, 'union_text', False)
                    continue
                
                # 텍스트 읽기 및 결합
                combined_text = ""
                file_type = ""
                
                if report_exists and summary_exists:
                    # 두 파일 모두 있는 경우
                    try:
                        report_text = self.read_text_file(report_txt_path)
                        summary_text = self.read_text_file(summary_txt_path)
                        
                        if is_pdf:
                            combined_text = f"[보고서 원문]\n{report_text}\n\n[요약본]\n{summary_text}"
                        else:
                            combined_text = f"[보고서 원문]\n{report_text}\n{summary_text}"
                        
                        file_type = "보고서+요약본"
                        
                    except Exception as e:
                        self.logger.log_error(f"파일 읽기 실패 (nttSn: {nttSn})", e)
                        self.reformat_stats['failed'] += 1
                        self.update_db_boolean_field(nttSn, 'union_text', False)
                        continue
                        
                elif report_exists:
                    # 보고서 파일만 있는 경우
                    try:
                        report_text = self.read_text_file(report_txt_path)
                        combined_text = f"[보고서 원문]\n{report_text}"
                        file_type = "보고서만"
                        
                    except Exception as e:
                        self.logger.log_error(f"보고서 파일 읽기 실패 (nttSn: {nttSn})", e)
                        self.reformat_stats['failed'] += 1
                        self.update_db_boolean_field(nttSn, 'union_text', False)
                        continue
                        
                elif summary_exists:
                    # 요약본 파일만 있는 경우
                    try:
                        summary_text = self.read_text_file(summary_txt_path)
                        combined_text = f"[보고서 원문]\n{summary_text}"
                        file_type = "요약본만"
                        
                    except Exception as e:
                        self.logger.log_error(f"요약본 파일 읽기 실패 (nttSn: {nttSn})", e)
                        self.reformat_stats['failed'] += 1
                        self.update_db_boolean_field(nttSn, 'union_text', False)
                        continue
                
                # 파일 타입 로그
                self.logger.log_info(f"처리할 파일 타입: {file_type} (nttSn: {nttSn})")
                
                try:
                    # Gemini API 호출
                    result_text = self.call_gemini_api(combined_text, nttSn)
                    
                    # 결과 저장
                    with open(union_txt_path, 'w', encoding='utf-8') as f:
                        f.write(result_text)
                    
                    # 성공 시 DB 업데이트
                    self.update_db_boolean_field(nttSn, 'union_text', True)
                    
                    self.logger.log_success(f"재포맷 완료 ({file_type}): {union_txt_path}")
                    self.reformat_stats['success'] += 1
                    
                except Exception as e:
                    self.logger.log_error(f"재포맷 실패 (nttSn: {nttSn})", e)
                    self.reformat_stats['failed'] += 1
                    self.update_db_boolean_field(nttSn, 'union_text', False)
                
                self.reformat_stats['total'] += 1
                
                # 진행률 표시
                if (i + 1) % 5 == 0:
                    self.logger.log_info(f"진행률: {i+1}/{len(reformat_data)}")
                
                # API 호출 간 대기
                time.sleep(self.config.api_delay)
            
            # 최종 통계 출력
            self.logger.log_success("=== PDF 텍스트 재포맷 완료 ===")
            self.logger.log_info(f"총 처리: {self.reformat_stats['total']}개")
            self.logger.log_info(f"성공: {self.reformat_stats['success']}개")
            self.logger.log_info(f"실패: {self.reformat_stats['failed']}개")
            self.logger.log_info(f"건너뛴: {self.reformat_stats['skipped']}개")
            
        except Exception as e:
            self.logger.log_error("PDF 텍스트 재포맷 프로세스 실패", e)
            raise

    def update_db_boolean_field(self, nttSn: int, field_name: str, value: bool):
        """DB에 BOOLEAN 필드 업데이트"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute(f"""
                UPDATE joined SET {field_name} = ? WHERE nttSn = ?
            """, (1 if value else 0, nttSn))
            conn.commit()
            conn.close()
            self.logger.log_success(f"DB 업데이트 완료: nttSn={nttSn}, {field_name}={value}")
        except Exception as e:
            self.logger.log_error(f"DB BOOLEAN 필드 업데이트 실패 (nttSn={nttSn}, {field_name})", e)

def main():
    """메인 함수"""
    import sys
    import os
    
    print("=== PDF 텍스트 재포맷터 ===")
    
    # 1단계: 환경변수에서 읽기
    start_nttSn = os.getenv('START_NTTSN')
    end_nttSn = os.getenv('END_NTTSN')
    
    # 2단계: 사용자 입력으로 fallback (환경변수가 없을 때만)
    if start_nttSn is None:
        start_nttSn = input("시작 nttSn (기본값: 전체): ").strip() or None
    if end_nttSn is None:
        end_nttSn = input("끝 nttSn (기본값: 전체): ").strip() or None
    
    # 3단계: 명령행 인수로 override
    if len(sys.argv) > 1:
        try:
            start_nttSn = int(sys.argv[1]) if sys.argv[1] != 'None' else None
            end_nttSn = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] != 'None' else None
        except (ValueError, IndexError):
            pass
    
    # 문자열을 정수로 변환
    if start_nttSn:
        start_nttSn = int(start_nttSn)
    if end_nttSn:
        end_nttSn = int(end_nttSn)
    
    if start_nttSn and end_nttSn:
        print(f"\n설정된 범위: nttSn {start_nttSn} ~ {end_nttSn}")
    else:
        print("\n전체 파일 재포맷")
    
    # 재포맷터 실행
    config = ReformatConfig(
        start_nttSn=start_nttSn,
        end_nttSn=end_nttSn
    )
    
    reformatter = TextReformatter(config)
    reformatter.reformat_files()

if __name__ == "__main__":
    main() 