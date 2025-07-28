import os
import sqlite3
import requests
import time
import logging
import traceback
import re
import urllib.parse
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from functools import wraps

@dataclass
class DownloadConfig:
    """다운로드 설정 클래스"""
    start_nttSn: Optional[int] = None
    end_nttSn: Optional[int] = None
    max_retries: int = 3
    retry_delay: int = 5
    timeout: int = 30
    chunk_size: int = 8192
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

class DownloadLogger:
    """다운로드 로거 클래스"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        self.setup_logging()
    
    def setup_logging(self):
        """로깅 설정"""
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 메인 로거 설정
        self.logger = logging.getLogger('download_pdfs')
        self.logger.setLevel(logging.INFO)
        
        # 기존 핸들러 제거
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # 파일 핸들러
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_handler = logging.FileHandler(
            f"{self.log_dir}/download_{timestamp}.log", 
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
                        logger = DownloadLogger()
                        logger.log_warning(
                            f"{func.__name__} 실패 (시도 {attempt + 1}/{max_retries + 1}): {str(e)}"
                        )
                        time.sleep(delay)
                    else:
                        logger = DownloadLogger()
                        logger.log_error(
                            f"{func.__name__} 최종 실패 (최대 시도 횟수 초과): {str(e)}",
                            e
                        )
            
            raise last_exception
        return wrapper
    return decorator

def extract_original_filename(response: requests.Response, url: str) -> Optional[str]:
    """HTTP 응답에서 원본 파일명 추출"""
    original_filename = None
    
    # 1. Content-Disposition 헤더에서 파일명 추출
    content_disposition = response.headers.get('Content-Disposition', '')
    if content_disposition:
        # filename*=UTF-8''파일명.pdf 형태
        filename_match = re.search(r"filename\*=UTF-8''([^;]+)", content_disposition)
        if filename_match:
            original_filename = urllib.parse.unquote(filename_match.group(1))
        else:
            # filename="파일명.pdf" 형태
            filename_match = re.search(r'filename="([^"]+)"', content_disposition)
            if filename_match:
                original_filename = filename_match.group(1)
            else:
                # filename=파일명.pdf 형태 (따옴표 없음)
                filename_match = re.search(r'filename=([^;]+)', content_disposition)
                if filename_match:
                    original_filename = filename_match.group(1).strip()
    
    # 2. URL에서 파일명 추출 (Content-Disposition이 없는 경우)
    if not original_filename:
        parsed_url = urllib.parse.urlparse(url)
        url_filename = os.path.basename(parsed_url.path)
        if url_filename and '.' in url_filename:
            original_filename = urllib.parse.unquote(url_filename)
    
    return original_filename

def determine_file_extension(response: requests.Response, original_filename: Optional[str]) -> str:
    """파일 확장자 결정 (.pdf 또는 .hwp)"""
    # 1. 원본 파일명에서 확장자 추출
    if original_filename:
        file_extension = os.path.splitext(original_filename)[1].lower()
        if file_extension in ['.pdf', '.hwp']:
            return file_extension
    
    # 2. Content-Type에서 추정
    content_type = response.headers.get('Content-Type', '').lower()
    if 'pdf' in content_type:
        return '.pdf'
    elif 'hwp' in content_type or 'hanword' in content_type:
        return '.hwp'
    
    # 3. 응답 내용의 첫 부분으로 판단
    try:
        # 스트림에서 첫 1024바이트만 읽어서 확인
        first_chunk = next(response.iter_content(chunk_size=1024), b'')
        if first_chunk:
            if first_chunk.startswith(b'%PDF'):
                return '.pdf'
            elif b'HWP Document File' in first_chunk or first_chunk.startswith(b'\xd0\xcf\x11\xe0'):
                return '.hwp'
    except:
        pass
    
    # 4. 기본값은 .pdf
    return '.pdf'

class PDFDownloader:
    """파일 다운로더 (PDF/HWP)"""
    
    def __init__(self, config: DownloadConfig):
        self.config = config
        self.logger = DownloadLogger()
        self.db_path = "../datas/science_reports.db"
        
        # 저장 디렉토리 설정
        self.report_dir = "../datas/pdf_reports/report"
        self.summary_dir = "../datas/pdf_reports/summary"
        
        # 상위 디렉토리 생성
        os.makedirs("../datas", exist_ok=True)
        os.makedirs("../datas/pdf_reports", exist_ok=True)
        os.makedirs(self.report_dir, exist_ok=True)
        os.makedirs(self.summary_dir, exist_ok=True)
        
        self.download_stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0
        }
    
    def get_download_data(self) -> List[Dict]:
        """다운로드할 데이터 조회"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            # nttSn 범위로 직접 조회
            if self.config.start_nttSn and self.config.end_nttSn:
                cur.execute("""
                    SELECT number, nttSn, title, file1_url, file2_url 
                    FROM joined 
                    WHERE nttSn BETWEEN ? AND ?
                    ORDER BY nttSn ASC
                """, (self.config.start_nttSn, self.config.end_nttSn))
                
                self.logger.log_info(f"nttSn 범위: {self.config.start_nttSn} ~ {self.config.end_nttSn}")
            else:
                # 전체 데이터 조회
                cur.execute("""
                    SELECT number, nttSn, title, file1_url, file2_url 
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
                    'file2_url': row[4]
                })
            
            self.logger.log_info(f"다운로드 대상: {len(data)}개 파일 (nttSn 기준 정렬)")
            return data
            
        except Exception as e:
            self.logger.log_error("데이터베이스 조회 실패", e)
            raise
    
    @retry_on_failure(max_retries=3, delay=5)
    def download_file(self, url: str, nttSn: int, file_type: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """파일 다운로드 (PDF/HWP 지원)"""
        try:
            headers = {
                "User-Agent": self.config.user_agent,
                "Accept": "application/pdf,application/octet-stream,*/*",
                "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
            
            self.logger.log_info(f"{file_type} 다운로드 시작: {url}")
            
            response = requests.get(
                url, 
                headers=headers, 
                timeout=self.config.timeout,
                stream=True
            )
            
            if response.status_code != 200:
                self.logger.log_warning(f"{file_type} HTTP 오류: {response.status_code}")
                return False, None, None
            
            content_type = response.headers.get("Content-Type", "")
            content_length = response.headers.get("Content-Length", "0")
            
            # 원본 파일명 추출
            original_filename = extract_original_filename(response, url)
            
            # 파일 확장자 결정
            file_extension = determine_file_extension(response, original_filename)
            
            self.logger.log_info(f"파일 정보:")
            self.logger.log_info(f"  - HTTP 상태: {response.status_code}")
            self.logger.log_info(f"  - Content-Type: {content_type}")
            self.logger.log_info(f"  - 파일 크기: {content_length} bytes")
            self.logger.log_info(f"  - 원본 파일명: {original_filename}")
            self.logger.log_info(f"  - 결정된 확장자: {file_extension}")
            
            # 저장할 파일명 생성
            save_dir = self.report_dir if file_type == "보고서" else self.summary_dir
            file_suffix = "report" if file_type == "보고서" else "summary"
            saved_filename = f"{nttSn}_{file_suffix}{file_extension}"
            save_path = os.path.join(save_dir, saved_filename)
            
            # 파일 저장
                with open(save_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=self.config.chunk_size):
                        if chunk:
                            f.write(chunk)
                
                file_size = os.path.getsize(save_path)
                self.logger.log_success(f"{file_type} 저장 완료: {save_path} ({file_size} bytes)")
            
            return True, original_filename, saved_filename
                
        except requests.exceptions.Timeout:
            self.logger.log_error(f"{file_type} 타임아웃: {url}")
            raise
        except requests.exceptions.RequestException as e:
            self.logger.log_error(f"{file_type} 네트워크 오류: {url}", e)
            raise
        except Exception as e:
            self.logger.log_error(f"{file_type} 다운로드 오류: {url}", e)
            raise
    
    def check_existing_file(self, nttSn: int, file_type: str) -> bool:
        """이미 다운로드된 파일이 있는지 확인"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            if file_type == "보고서":
                cur.execute("SELECT saved_filename1 FROM joined WHERE nttSn = ?", (nttSn,))
                save_dir = self.report_dir
            else:  # 요약보고서
                cur.execute("SELECT saved_filename2 FROM joined WHERE nttSn = ?", (nttSn,))
                save_dir = self.summary_dir
            
            result = cur.fetchone()
            conn.close()
            
            if result and result[0]:
                saved_filename = result[0]
                full_path = os.path.join(save_dir, saved_filename)
                return os.path.exists(full_path)
            
            return False
            
        except Exception as e:
            self.logger.log_error(f"기존 파일 확인 실패 (nttSn={nttSn}, {file_type})", e)
            return False

    def update_db_filename_fields(self, nttSn: int, file_type: str, original_filename: Optional[str], saved_filename: Optional[str]):
        """DB에 파일명 정보 저장"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            if file_type == "보고서":
                cur.execute("""
                    UPDATE joined 
                    SET original_filename1 = ?, saved_filename1 = ?
                    WHERE nttSn = ?
                """, (original_filename, saved_filename, nttSn))
            else:  # 요약보고서
                cur.execute("""
                    UPDATE joined 
                    SET original_filename2 = ?, saved_filename2 = ?
                    WHERE nttSn = ?
                """, (original_filename, saved_filename, nttSn))
            
            conn.commit()
            conn.close()
            
            self.logger.log_success(f"DB 업데이트 완료: nttSn={nttSn}, {file_type} - 원본: {original_filename}, 저장: {saved_filename}")
            
        except Exception as e:
            self.logger.log_error(f"DB 업데이트 실패 (nttSn={nttSn}, {file_type})", e)
    
    def download_files(self):
        """모든 파일 다운로드"""
        self.logger.log_info("=== 파일 다운로드 시작 ===")
        
        try:
            # 다운로드 데이터 조회
            download_data = self.get_download_data()
            
            for i, item in enumerate(download_data):
                number = item['number']
                nttSn = item['nttSn']
                title = item['title']
                file1_url = item['file1_url']
                file2_url = item['file2_url']
                
                self.logger.log_info(f"처리 중 ({i+1}/{len(download_data)}): nttSn={nttSn}, number={number} - {title[:50]}...")
                
                file1_ext = None
                file2_ext = None
                
                # 보고서 다운로드
                if file1_url and file1_url.strip():
                    if self.check_existing_file(nttSn, "보고서"):
                        self.logger.log_info(f"보고서 이미 존재함, 건너뜀: nttSn={nttSn}")
                        self.download_stats['skipped'] += 1
                        # 이미 저장된 파일명에서 확장자 추출
                        conn = sqlite3.connect(self.db_path)
                        cur = conn.cursor()
                        cur.execute("SELECT saved_filename1 FROM joined WHERE nttSn = ?", (nttSn,))
                        row = cur.fetchone()
                        if row and row[0]:
                            file1_ext = os.path.splitext(row[0])[1].lower()
                        conn.close()
                    else:
                        try:
                            success, original_filename, saved_filename = self.download_file(file1_url, nttSn, "보고서")
                            if success:
                                self.download_stats['success'] += 1
                                self.update_db_filename_fields(nttSn, "보고서", original_filename, saved_filename)
                                file1_ext = os.path.splitext(saved_filename)[1].lower() if saved_filename else None
                            else:
                                self.download_stats['failed'] += 1
                                self.update_db_filename_fields(nttSn, "보고서", None, None)
                        except Exception as e:
                            self.logger.log_error(f"보고서 다운로드 실패: {file1_url}", e)
                            self.download_stats['failed'] += 1
                            self.update_db_filename_fields(nttSn, "보고서", None, None)
                else:
                    self.logger.log_warning(f"보고서 URL 없음, 건너뜀: nttSn={nttSn}")
                    self.download_stats['skipped'] += 1
                    self.update_db_filename_fields(nttSn, "보고서", None, None)
                
                # 요약보고서 다운로드
                if file2_url and file2_url.strip():
                    if self.check_existing_file(nttSn, "요약보고서"):
                        self.logger.log_info(f"요약보고서 이미 존재함, 건너뜀: nttSn={nttSn}")
                        self.download_stats['skipped'] += 1
                        # 이미 저장된 파일명에서 확장자 추출
                        conn = sqlite3.connect(self.db_path)
                        cur = conn.cursor()
                        cur.execute("SELECT saved_filename2 FROM joined WHERE nttSn = ?", (nttSn,))
                        row = cur.fetchone()
                        if row and row[0]:
                            file2_ext = os.path.splitext(row[0])[1].lower()
                        conn.close()
                    else:
                        try:
                            success, original_filename, saved_filename = self.download_file(file2_url, nttSn, "요약보고서")
                            if success:
                                self.download_stats['success'] += 1
                                self.update_db_filename_fields(nttSn, "요약보고서", original_filename, saved_filename)
                                file2_ext = os.path.splitext(saved_filename)[1].lower() if saved_filename else None
                            else:
                                self.download_stats['failed'] += 1
                                self.update_db_filename_fields(nttSn, "요약보고서", None, None)
                        except Exception as e:
                            self.logger.log_error(f"요약보고서 다운로드 실패: {file2_url}", e)
                            self.download_stats['failed'] += 1
                            self.update_db_filename_fields(nttSn, "요약보고서", None, None)
                else:
                    self.logger.log_warning(f"요약보고서 URL 없음, 건너뜀: nttSn={nttSn}")
                    self.download_stats['skipped'] += 1
                    self.update_db_filename_fields(nttSn, "요약보고서", None, None)
                
                # is_pdf 필드 업데이트
                is_pdf = 1 if file1_ext == '.pdf' and file2_ext == '.pdf' and file1_ext is not None and file2_ext is not None else 0
                try:
                    conn = sqlite3.connect(self.db_path)
                    cur = conn.cursor()
                    cur.execute("UPDATE joined SET is_pdf = ? WHERE nttSn = ?", (is_pdf, nttSn))
                    conn.commit()
                    conn.close()
                    self.logger.log_info(f"is_pdf 업데이트: nttSn={nttSn}, is_pdf={is_pdf}")
                except Exception as e:
                    self.logger.log_error(f"is_pdf 업데이트 실패: nttSn={nttSn}", e)
                
                self.download_stats['total'] += 1
                
                # 진행률 표시
                if (i + 1) % 10 == 0:
                    self.logger.log_info(f"진행률: {i+1}/{len(download_data)}")
                
                # 요청 간 대기
                time.sleep(1)
            
            # 최종 통계 출력
            self.logger.log_success("=== 파일 다운로드 완료 ===")
            self.logger.log_info(f"총 처리: {self.download_stats['total']}개")
            self.logger.log_info(f"성공: {self.download_stats['success']}개")
            self.logger.log_info(f"실패: {self.download_stats['failed']}개")
            self.logger.log_info(f"건너뛴: {self.download_stats['skipped']}개")
            
        except Exception as e:
            self.logger.log_error("파일 다운로드 프로세스 실패", e)
            raise

def main():
    """메인 함수"""
    import sys
    import os
    
    print("=== PDF 다운로더 ===")
    
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
        print("\n전체 파일 다운로드")
    
    # 다운로더 실행
    config = DownloadConfig(
        start_nttSn=start_nttSn,
        end_nttSn=end_nttSn
    )
    
    downloader = PDFDownloader(config)
    downloader.download_files()

if __name__ == "__main__":
    main() 