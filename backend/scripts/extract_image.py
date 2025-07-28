import os
import sqlite3
import fitz  # PyMuPDF
from PIL import Image
import io
import time
import logging
import traceback
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from functools import wraps

@dataclass
class ImageConfig:
    """이미지 추출 설정 클래스"""
    start_nttSn: Optional[int] = None
    end_nttSn: Optional[int] = None
    max_retries: int = 3
    retry_delay: int = 5
    min_image_size: int = 100
    max_pages_to_check: int = 3

class ImageLogger:
    """이미지 추출 로거 클래스"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        self.setup_logging()
    
    def setup_logging(self):
        """로깅 설정"""
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 메인 로거 설정
        self.logger = logging.getLogger('extract_image')
        self.logger.setLevel(logging.INFO)
        
        # 기존 핸들러 제거
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # 파일 핸들러
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_handler = logging.FileHandler(
            f"{self.log_dir}/extract_image_{timestamp}.log", 
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
                        logger = ImageLogger()
                        logger.log_warning(
                            f"{func.__name__} 실패 (시도 {attempt + 1}/{max_retries + 1}): {str(e)}"
                        )
                        time.sleep(delay)
                    else:
                        logger = ImageLogger()
                        logger.log_error(
                            f"{func.__name__} 최종 실패 (최대 시도 횟수 초과): {str(e)}",
                            e
                        )
            
            raise last_exception
        return wrapper
    return decorator

class ImageExtractor:
    """PDF 이미지 추출기"""
    
    def __init__(self, config: ImageConfig):
        self.config = config
        self.logger = ImageLogger()
        self.db_path = "../datas/science_reports.db"
        
        # 저장 디렉토리 설정
        self.summary_pdf_dir = "../datas/pdf_reports/summary"
        self.image_dir = "../datas/extracted_pdf/image"
        
        # 상위 디렉토리 생성
        os.makedirs("../datas", exist_ok=True)
        os.makedirs("../datas/extracted_pdf", exist_ok=True)
        os.makedirs(self.image_dir, exist_ok=True)
        
        self.extract_stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0
        }
    
    def get_extract_data(self) -> List[Dict]:
        """추출할 데이터 조회"""
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
            
            self.logger.log_info(f"이미지 추출 대상: {len(data)}개 파일 (nttSn 기준 정렬)")
            return data
            
        except Exception as e:
            self.logger.log_error("데이터베이스 조회 실패", e)
            raise
    
    @retry_on_failure(max_retries=3, delay=5)
    def extract_first_image_from_pdf(self, pdf_path: str, nttSn: str) -> Tuple[Optional[str], Optional[int], Optional[int]]:
        """PDF에서 첫 번째 이미지를 추출하여 저장"""
        try:
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF 파일을 찾을 수 없음: {pdf_path}")
            
            doc = fitz.open(pdf_path)
            
            for page_num in range(min(self.config.max_pages_to_check, len(doc))):
                page = doc.load_page(page_num)
                image_list = page.get_images()
                
                if image_list:
                    # 첫 번째 이미지 추출
                    img_index = 0
                    xref = image_list[img_index][0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    
                    # 이미지 크기 확인 및 필터링
                    img = Image.open(io.BytesIO(image_bytes))
                    width, height = img.size
                    
                    # 너무 작은 이미지는 제외
                    if width >= self.config.min_image_size and height >= self.config.min_image_size:
                        # 이미지 파일명 생성 (nttSn_image.png 형식)
                        image_filename = f"{nttSn}_image.png"
                        image_path = os.path.join(self.image_dir, image_filename)
                        
                        # 이미지 저장
                        img.save(image_path, format='PNG')
                        
                        doc.close()
                        return image_path, width, height
            
            doc.close()
            return None, None, None
            
        except Exception as e:
            self.logger.log_error(f"PDF 이미지 추출 실패: {pdf_path}", e)
            raise
    
    def update_database_with_image(self, nttSn: str, image_path: Optional[str]):
        """데이터베이스의 joined 테이블에 이미지 파일명만 업데이트"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            # joined 테이블에 image 컬럼이 있는지 확인
            cur.execute("PRAGMA table_info(joined)")
            columns = [column[1] for column in cur.fetchall()]
            
            if "image" not in columns:
                self.logger.log_info("joined 테이블에 image 컬럼을 추가합니다.")
                cur.execute("ALTER TABLE joined ADD COLUMN image TEXT")
                conn.commit()
            
            # 파일명만 저장
            image_filename = os.path.basename(image_path) if image_path else None
            # 이미지 경로 업데이트
            cur.execute("""
                UPDATE joined 
                SET image = ? 
                WHERE nttSn = ?
            """, (image_filename, nttSn))
            
            if cur.rowcount > 0:
                if image_filename:
                    self.logger.log_success(f"DB 업데이트 완료: nttSn={nttSn} -> {image_filename}")
                else:
                    self.logger.log_info(f"DB 업데이트 완료: nttSn={nttSn} -> None (이미지 없음)")
            else:
                self.logger.log_warning(f"DB에서 해당 nttSn을 찾을 수 없음: {nttSn}")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.log_error(f"DB 업데이트 실패 (nttSn={nttSn})", e)
            raise
    
    def extract_images(self):
        """모든 파일에서 이미지 추출"""
        self.logger.log_info("=== PDF 이미지 추출 시작 ===")
        
        try:
            # 추출 데이터 조회
            extract_data = self.get_extract_data()
            
            for i, item in enumerate(extract_data):
                number = item['number']
                nttSn = item['nttSn']
                title = item['title']
                file2_url = item['file2_url']
                
                self.logger.log_info(f"처리 중 ({i+1}/{len(extract_data)}): nttSn={nttSn}, number={number} - {title[:50]}...")
                
                # file2_url이 비어있거나 None이면 건너뜀
                if not file2_url or not file2_url.strip():
                    self.logger.log_warning(f"요약보고서 URL 없음, 이미지 추출 건너뜀: nttSn={nttSn}")
                    self.extract_stats['skipped'] += 1
                    self.update_database_with_image(nttSn, None)
                    self.extract_stats['total'] += 1
                    continue
                
                # 요약보고서 PDF 경로
                summary_pdf_path = os.path.join(self.summary_pdf_dir, f"{nttSn}_summary.pdf")
                image_filename = f"{nttSn}_image.png"
                image_path = os.path.join(self.image_dir, image_filename)
                
                if os.path.exists(summary_pdf_path):
                    if not os.path.exists(image_path):
                        try:
                            # PDF 파일인지 간단히 확인
                            if not summary_pdf_path.lower().endswith('.pdf'):
                                self.logger.log_warning(f"PDF 파일 아님, 이미지 추출 건너뜀: {summary_pdf_path}")
                                self.extract_stats['skipped'] += 1
                                self.update_database_with_image(nttSn, None)
                                self.extract_stats['total'] += 1
                                continue
                            extracted_image_path, width, height = self.extract_first_image_from_pdf(
                                summary_pdf_path, nttSn
                            )
                            
                            if extracted_image_path:
                                self.logger.log_success(f"이미지 추출 완료: {os.path.basename(extracted_image_path)} ({width}x{height} 픽셀)")
                                self.extract_stats['success'] += 1
                            else:
                                self.logger.log_warning(f"이미지 추출 실패: {summary_pdf_path}")
                                self.extract_stats['failed'] += 1
                            
                            # 데이터베이스 업데이트
                            self.update_database_with_image(nttSn, extracted_image_path)
                            
                        except Exception as e:
                            self.logger.log_error(f"이미지 추출 실패: {summary_pdf_path}", e)
                            self.extract_stats['failed'] += 1
                            # 데이터베이스 업데이트 (None으로)
                            self.update_database_with_image(nttSn, None)
                    else:
                        self.logger.log_info(f"이미지 이미 존재: {image_path}")
                        self.extract_stats['skipped'] += 1
                else:
                    self.logger.log_warning(f"요약보고서 PDF 파일 없음: {summary_pdf_path}")
                    self.extract_stats['failed'] += 1
                    # 데이터베이스 업데이트 (None으로)
                    self.update_database_with_image(nttSn, None)
                
                self.extract_stats['total'] += 1
                
                # 진행률 표시
                if (i + 1) % 10 == 0:
                    self.logger.log_info(f"진행률: {i+1}/{len(extract_data)}")
                
                # 요청 간 대기
                time.sleep(0.5)
            
            # 최종 통계 출력
            self.logger.log_success("=== PDF 이미지 추출 완료 ===")
            self.logger.log_info(f"총 처리: {self.extract_stats['total']}개")
            self.logger.log_info(f"성공: {self.extract_stats['success']}개")
            self.logger.log_info(f"실패: {self.extract_stats['failed']}개")
            self.logger.log_info(f"건너뛴: {self.extract_stats['skipped']}개")
            
        except Exception as e:
            self.logger.log_error("PDF 이미지 추출 프로세스 실패", e)
            raise

def main():
    """메인 함수"""
    import sys
    import os
    
    print("=== PDF 이미지 추출기 ===")
    
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
    config = ImageConfig(
        start_nttSn=start_nttSn,
        end_nttSn=end_nttSn
    )
    
    extractor = ImageExtractor(config)
    extractor.extract_images()

if __name__ == "__main__":
    main() 