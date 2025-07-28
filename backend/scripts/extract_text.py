#!/usr/bin/env python3
import os
import sqlite3
import fitz  # PyMuPDF
import time
import logging
import traceback
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass
from functools import wraps

@dataclass
class ExtractConfig:
    """텍스트 추출 설정 클래스"""
    start_nttSn: Optional[int] = None
    end_nttSn: Optional[int] = None
    max_retries: int = 3
    retry_delay: int = 5
    chunk_size: int = 8192

class ExtractLogger:
    """텍스트 추출 로거 클래스"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        self.setup_logging()
    
    def setup_logging(self):
        """로깅 설정"""
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 메인 로거 설정
        self.logger = logging.getLogger('extract_text')
        self.logger.setLevel(logging.INFO)
        
        # 기존 핸들러 제거
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # 파일 핸들러
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_handler = logging.FileHandler(
            f"{self.log_dir}/extract_{timestamp}.log", 
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        
        # 콘솔 핸들러
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 포맷터
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger = ExtractLogger()
                        logger.log_warning(
                            f"{func.__name__} 실패 (시도 {attempt + 1}/{max_retries + 1}): {str(e)}"
                        )
                        time.sleep(delay)
                    else:
                        logger = ExtractLogger()
                        logger.log_error(
                            f"{func.__name__} 최종 실패 (최대 시도 횟수 초과): {str(e)}",
                            e
                        )
            
            raise last_exception
        return wrapper
    return decorator

class TextExtractor:
    """PDF 텍스트 추출기"""
    
    def __init__(self, config: ExtractConfig):
        self.config = config
        self.logger = ExtractLogger()
        self.db_path = "../datas/science_reports.db"
        
        # 저장 디렉토리 설정
        self.report_pdf_dir = "../datas/pdf_reports/report"
        self.summary_pdf_dir = "../datas/pdf_reports/summary"
        self.report_text_dir = "../datas/extracted_pdf/report"
        self.summary_text_dir = "../datas/extracted_pdf/summary"
        
        # 상위 디렉토리 생성
        os.makedirs("../datas", exist_ok=True)
        os.makedirs("../datas/extracted_pdf", exist_ok=True)
        os.makedirs(self.report_text_dir, exist_ok=True)
        os.makedirs(self.summary_text_dir, exist_ok=True)
        
        self.extract_stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'hwp_empty': 0  # HWP 파일로 인한 빈 파일 생성 개수
        }
    
    def get_extract_data(self) -> List[Dict]:
        """추출할 데이터 조회 (saved_filename 필드 포함)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            # nttSn 범위로 직접 조회 (saved_filename 필드 포함)
            if self.config.start_nttSn and self.config.end_nttSn:
                cur.execute("""
                    SELECT number, nttSn, title, file1_url, file2_url, saved_filename1, saved_filename2
                    FROM joined 
                    WHERE nttSn BETWEEN ? AND ?
                    ORDER BY nttSn ASC
                """, (self.config.start_nttSn, self.config.end_nttSn))
                
                self.logger.log_info(f"nttSn 범위: {self.config.start_nttSn} ~ {self.config.end_nttSn}")
            else:
                # 전체 데이터 조회
                cur.execute("""
                    SELECT number, nttSn, title, file1_url, file2_url, saved_filename1, saved_filename2
                    FROM joined 
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
                    'file2_url': row[4],
                    'saved_filename1': row[5],
                    'saved_filename2': row[6]
                })
            
            self.logger.log_info(f"추출 대상: {len(data)}개 파일 (nttSn 기준 정렬)")
            return data
            
        except Exception as e:
            self.logger.log_error("데이터베이스 조회 실패", e)
            raise
    
    def is_pdf_file(self, filename: Optional[str]) -> bool:
        """파일이 PDF인지 확인"""
        if not filename:
            return False
        return filename.lower().endswith('.pdf')
    
    def is_hwp_file(self, filename: Optional[str]) -> bool:
        """파일이 HWP인지 확인"""
        if not filename:
            return False
        return filename.lower().endswith('.hwp')
    
    def create_empty_text_file(self, txt_path: str, file_type: str, original_filename: str):
        """빈 텍스트 파일 생성 (HWP 파일용)"""
        try:
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write("")  # 빈 내용으로 파일 생성
            
            self.logger.log_success(f"{file_type} 빈 텍스트 파일 생성 완료: {txt_path} (원본: {original_filename})")
            self.extract_stats['hwp_empty'] += 1
            
        except Exception as e:
            self.logger.log_error(f"{file_type} 빈 텍스트 파일 생성 실패: {txt_path}", e)
            raise
    
    @retry_on_failure(max_retries=3, delay=5)
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """PDF 파일에서 텍스트 추출"""
        try:
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF 파일을 찾을 수 없음: {pdf_path}")
            
            doc = fitz.open(pdf_path)
            text = "\n".join([page.get_text() for page in doc])
            doc.close()
            
            if not text.strip():
                self.logger.log_warning(f"추출된 텍스트가 없음: {pdf_path}")
                return ""
            
            return text
            
        except Exception as e:
            self.logger.log_error(f"PDF 텍스트 추출 실패: {pdf_path}", e)
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

    def extract_files(self):
        """모든 파일에서 텍스트 추출 (확장자 확인)"""
        self.logger.log_info("=== PDF 텍스트 추출 시작 ===")
        
        try:
            # 추출 데이터 조회
            extract_data = self.get_extract_data()
            
            for i, item in enumerate(extract_data):
                number = item['number']
                nttSn = item['nttSn']
                title = item['title']
                saved_filename1 = item['saved_filename1']
                saved_filename2 = item['saved_filename2']
                
                self.logger.log_info(f"처리 중 ({i+1}/{len(extract_data)}): nttSn={nttSn}, number={number} - {title[:50]}...")
                
                # 보고서 텍스트 추출
                if saved_filename1:
                    if self.is_pdf_file(saved_filename1):
                        # PDF 파일인 경우 텍스트 추출
                        report_pdf_path = os.path.join(self.report_pdf_dir, saved_filename1)
                report_txt_path = os.path.join(self.report_text_dir, f"{nttSn}_report.txt")
                
                if os.path.exists(report_pdf_path):
                    if not os.path.exists(report_txt_path):
                        try:
                            text = self.extract_text_from_pdf(report_pdf_path)
                            with open(report_txt_path, "w", encoding="utf-8") as f:
                                f.write(text)
                            self.logger.log_success(f"보고서 텍스트 추출 완료: {report_txt_path}")
                            self.extract_stats['success'] += 1
                        except Exception as e:
                            self.logger.log_error(f"보고서 텍스트 추출 실패: {report_pdf_path}", e)
                            self.extract_stats['failed'] += 1
                    else:
                        self.logger.log_info(f"보고서 텍스트 이미 존재: {report_txt_path}")
                        self.extract_stats['skipped'] += 1
                else:
                    self.logger.log_warning(f"보고서 PDF 파일 없음: {report_pdf_path}")
                    self.extract_stats['failed'] += 1
                    
                    elif self.is_hwp_file(saved_filename1):
                        # HWP 파일인 경우 빈 텍스트 파일 생성
                        report_txt_path = os.path.join(self.report_text_dir, f"{nttSn}_report.txt")
                        
                        if not os.path.exists(report_txt_path):
                            try:
                                self.create_empty_text_file(report_txt_path, "보고서", saved_filename1)
                            except Exception as e:
                                self.logger.log_error(f"보고서 빈 텍스트 파일 생성 실패: {report_txt_path}", e)
                                self.extract_stats['failed'] += 1
                        else:
                            self.logger.log_info(f"보고서 텍스트 파일 이미 존재: {report_txt_path}")
                            self.extract_stats['skipped'] += 1
                    
                    else:
                        self.logger.log_warning(f"보고서 파일 확장자 불명: {saved_filename1}")
                        self.extract_stats['failed'] += 1
                else:
                    self.logger.log_warning(f"보고서 파일명 없음: nttSn={nttSn}")
                    self.extract_stats['failed'] += 1
                
                # 요약보고서 텍스트 추출
                if saved_filename2:
                    if self.is_pdf_file(saved_filename2):
                        # PDF 파일인 경우 텍스트 추출
                        summary_pdf_path = os.path.join(self.summary_pdf_dir, saved_filename2)
                summary_txt_path = os.path.join(self.summary_text_dir, f"{nttSn}_summary.txt")
                
                if os.path.exists(summary_pdf_path):
                    if not os.path.exists(summary_txt_path):
                        try:
                            text = self.extract_text_from_pdf(summary_pdf_path)
                            with open(summary_txt_path, "w", encoding="utf-8") as f:
                                f.write(text)
                            self.logger.log_success(f"요약보고서 텍스트 추출 완료: {summary_txt_path}")
                            self.extract_stats['success'] += 1
                        except Exception as e:
                            self.logger.log_error(f"요약보고서 텍스트 추출 실패: {summary_pdf_path}", e)
                            self.extract_stats['failed'] += 1
                    else:
                        self.logger.log_info(f"요약보고서 텍스트 이미 존재: {summary_txt_path}")
                        self.extract_stats['skipped'] += 1
                else:
                    self.logger.log_warning(f"요약보고서 PDF 파일 없음: {summary_pdf_path}")
                    self.extract_stats['failed'] += 1
                    
                    elif self.is_hwp_file(saved_filename2):
                        # HWP 파일인 경우 빈 텍스트 파일 생성
                        summary_txt_path = os.path.join(self.summary_text_dir, f"{nttSn}_summary.txt")
                        
                        if not os.path.exists(summary_txt_path):
                            try:
                                self.create_empty_text_file(summary_txt_path, "요약보고서", saved_filename2)
                            except Exception as e:
                                self.logger.log_error(f"요약보고서 빈 텍스트 파일 생성 실패: {summary_txt_path}", e)
                                self.extract_stats['failed'] += 1
                        else:
                            self.logger.log_info(f"요약보고서 텍스트 파일 이미 존재: {summary_txt_path}")
                            self.extract_stats['skipped'] += 1
                    
                    else:
                        self.logger.log_warning(f"요약보고서 파일 확장자 불명: {saved_filename2}")
                        self.extract_stats['failed'] += 1
                else:
                    self.logger.log_warning(f"요약보고서 파일명 없음: nttSn={nttSn}")
                    self.extract_stats['failed'] += 1
                
                self.extract_stats['total'] += 1
                
                # 진행률 표시
                if (i + 1) % 10 == 0:
                    self.logger.log_info(f"진행률: {i+1}/{len(extract_data)}")
                
                # 요청 간 대기
                time.sleep(0.5)
            
            # 최종 통계 출력
            self.logger.log_success("=== PDF 텍스트 추출 완료 ===")
            self.logger.log_info(f"총 처리: {self.extract_stats['total']}개")
            self.logger.log_info(f"성공: {self.extract_stats['success']}개")
            self.logger.log_info(f"실패: {self.extract_stats['failed']}개")
            self.logger.log_info(f"건너뛴: {self.extract_stats['skipped']}개")
            self.logger.log_info(f"HWP 빈 파일 생성: {self.extract_stats['hwp_empty']}개")
            
        except Exception as e:
            self.logger.log_error("PDF 텍스트 추출 프로세스 실패", e)
            raise

def main():
    """메인 함수"""
    import sys
    import os
    
    print("=== PDF 텍스트 추출기 ===")
    
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
        print("\n전체 파일 추출")
    
    # 추출기 실행
    config = ExtractConfig(
        start_nttSn=start_nttSn,
        end_nttSn=end_nttSn
    )
    
    extractor = TextExtractor(config)
    extractor.extract_files()

if __name__ == "__main__":
    main() 