import os
import sys
import time
import sqlite3
import logging
import traceback
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import wraps
import threading

# Playwright imports
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
import asyncio

# BeautifulSoup import
from bs4 import BeautifulSoup

@dataclass
class CrawlConfig:
    """크롤링 설정 클래스"""
    start_page: int = 1
    end_page: int = 3
    start_nttSn: int = 47018
    end_nttSn: int = 46978
    max_retries: int = 3
    retry_delay: int = 5
    max_workers: int = 2
    timeout: int = 10
    page_delay: int = 2

class CrawlLogger:
    """크롤링 로거 클래스"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        self.setup_logging()
    
    def setup_logging(self):
        """로깅 설정"""
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 메인 로거 설정
        self.logger = logging.getLogger('report_crawler')
        self.logger.setLevel(logging.INFO)
        
        # 기존 핸들러 제거
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # 파일 핸들러
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_handler = logging.FileHandler(
            f"{self.log_dir}/crawl_{timestamp}.log", 
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        
        # 콘솔 핸들러
        console_handler = logging.StreamHandler(sys.stdout)
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
                        logger = CrawlLogger()
                        logger.log_warning(
                            f"{func.__name__} 실패 (시도 {attempt + 1}/{max_retries + 1}): {str(e)}"
                        )
                        time.sleep(delay)
                    else:
                        logger = CrawlLogger()
                        logger.log_error(
                            f"{func.__name__} 최종 실패 (최대 시도 횟수 초과): {str(e)}",
                            e
                        )
            
            raise last_exception
        return wrapper
    return decorator

class ReportCrawler:
    """과학전람회 보고서 크롤러"""
    
    def __init__(self, config: CrawlConfig):
        self.config = config
        self.logger = CrawlLogger()
        self.db_path = "../datas/science_reports.db"
        self.lock = threading.Lock()
        
    def setup_browser(self) -> tuple[Browser, BrowserContext, Page]:
        """Playwright 브라우저 설정"""
        try:
            self.playwright = sync_playwright().start()
            
            # 브라우저 설정
            browser = self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-extensions',
                    '--disable-plugins',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--disable-features=TranslateUI',
                    '--disable-ipc-flooding-protection'
                ]
            )
            
            # 컨텍스트 설정
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                ignore_https_errors=True,
                extra_http_headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                }
            )
            
            # 페이지 생성
            page = context.new_page()
            
            # 웹드라이버 감지 방지
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['ko-KR', 'ko', 'en'],
                });
            """)
            
            self.logger.log_success("Playwright 브라우저 설정 완료")
            return browser, context, page
        except Exception as e:
            self.logger.log_error("Playwright 브라우저 설정 실패", e)
            raise
    
    def init_database(self):
        """데이터베이스 초기화"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            # 기존 테이블 삭제
            cur.execute("DROP TABLE IF EXISTS summary")
            cur.execute("DROP TABLE IF EXISTS detail")
            cur.execute("DROP TABLE IF EXISTS joined")
            cur.execute("DROP TABLE IF EXISTS crawl_log")
            
            # 테이블 생성
            cur.execute("""
            CREATE TABLE summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                number TEXT,
                year TEXT,
                field TEXT,
                title TEXT,
                award TEXT,
                authors TEXT,
                teacher TEXT,
                image TEXT,
                nttSn INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            cur.execute("""
            CREATE TABLE detail (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nttSn INTEGER UNIQUE,
                title TEXT,
                contest TEXT,
                description TEXT,
                file1_url TEXT,
                file2_url TEXT,
                reg_date TEXT,
                year TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            cur.execute("""
            CREATE TABLE joined (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                number TEXT,
                nttSn INTEGER,
                year TEXT,
                field TEXT,
                title TEXT,
                contest TEXT,
                award TEXT,
                authors TEXT,
                teacher TEXT,
                description TEXT,
                file1_url TEXT,
                file2_url TEXT,
                reg_date TEXT,
                original_filename1 TEXT DEFAULT NULL,
                original_filename2 TEXT DEFAULT NULL,
                saved_filename1 TEXT DEFAULT NULL,
                saved_filename2 TEXT DEFAULT NULL,
                union_text BOOLEAN DEFAULT 0,
                json_api BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            cur.execute("""
            CREATE TABLE crawl_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation TEXT,
                status TEXT,
                message TEXT,
                retry_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            conn.commit()
            conn.close()
            self.logger.log_success("데이터베이스 초기화 완료")
            
        except Exception as e:
            self.logger.log_error("데이터베이스 초기화 실패", e)
            raise
    
    @retry_on_failure(max_retries=3, delay=5)
    def get_summary_from_list_playwright(self, page: Page, page_num: int) -> List[Dict]:
        """Playwright를 사용한 리스트 페이지 크롤링"""
        url = f"https://www.science.go.kr/mps/1079/bbs/423/moveBbsNttList.do?page={page_num}&searchCnd=&aditfield10=&aditfield4=&searchKrwd=#n"
        
        self.logger.log_info(f"리스트 페이지 {page_num} 크롤링 시작: {url}")
        
        try:
            # 페이지가 닫혔는지 확인
            if page.is_closed():
                raise Exception("페이지가 닫혔습니다")
            
            # 페이지 이동
            page.goto(url, wait_until="networkidle", timeout=self.config.timeout * 1000)
            
            # 페이지가 닫혔는지 다시 확인
            if page.is_closed():
                raise Exception("페이지 이동 후 페이지가 닫혔습니다")
            
            # 테이블이 로드될 때까지 대기 (여러 선택자 시도)
            table_loaded = False
            selectors = ["#bbsNttTable", "table.tbl-list", "table"]
            
            for selector in selectors:
                try:
                    if page.is_closed():
                        raise Exception("페이지가 닫혔습니다")
                    page.wait_for_selector(selector, timeout=5000)
                    self.logger.log_info(f"페이지 {page_num}: {selector} 로드 완료")
                    table_loaded = True
                    break
                except Exception:
                    continue
            
            if not table_loaded:
                self.logger.log_warning(f"페이지 {page_num}: 테이블 로딩 타임아웃, 계속 진행")
            
            # 페이지가 완전히 로드될 때까지 대기
            if not page.is_closed():
                page.wait_for_timeout(3000)
            
            # 페이지 소스 가져오기
            if page.is_closed():
                raise Exception("페이지 소스 가져오기 전에 페이지가 닫혔습니다")
            
            page_source = page.content()
            soup = BeautifulSoup(page_source, "lxml")
            
            # 디버깅: 페이지 소스 일부 출력
            self.logger.log_info(f"페이지 {page_num} 소스 길이: {len(page_source)}")
            
            # 테이블에서 데이터 행 찾기 (tbody.singlerow 기준)
            table = soup.find("table", {"id": "bbsNttTable"})
            if not table:
                # 다른 테이블 ID 시도
                table = soup.find("table", {"class": "tbl-list"})
                if not table:
                    # 모든 테이블 찾기
                    tables = soup.find_all("table")
                    self.logger.log_warning(f"페이지 {page_num}: bbsNttTable을 찾을 수 없음. 발견된 테이블 수: {len(tables)}")
                    if tables:
                        table = tables[0]  # 첫 번째 테이블 사용
                    else:
                        raise Exception(f"페이지 {page_num}: 테이블을 찾을 수 없음")
            
            tbodies = table.find_all("tbody", class_="singlerow")
            data = []
            for i, tbody in enumerate(tbodies):
                onclick = tbody.get("onclick", "")
                import re
                match = re.search(r"fn_moveBbsNttDetail\('([0-9]+)'", onclick)
                nttSn = int(match.group(1)) if match else None

                cols = tbody.find_all("td")
                if len(cols) < 7:
                    self.logger.log_warning(f"페이지 {page_num} 행 {i}: 열 개수 부족 ({len(cols)})")
                    continue

                try:
                    number = cols[0].get_text(strip=True)
                    year = cols[1].get_text(strip=True)
                    field = cols[2].get_text(strip=True)
                    title = cols[3].get_text(strip=True)
                    award = cols[4].get_text(strip=True)
                    teacher = cols[5].get_text(strip=True)
                    authors = cols[6].get_text(strip=True)

                    data.append({
                        "number": number,
                        "year": year,
                        "field": field,
                        "title": title,
                        "award": award,
                        "teacher": teacher,
                        "authors": authors,
                        "nttSn": nttSn
                    })
                except Exception as e:
                    self.logger.log_warning(f"페이지 {page_num} 행 {i} 데이터 파싱 실패: {str(e)}")
                    continue

            self.logger.log_success(f"페이지 {page_num} 크롤링 완료: {len(data)}개 데이터 수집")
            return data
            
        except Exception as e:
            self.logger.log_error(f"페이지 {page_num} 크롤링 실패", e)
            raise
    
    @retry_on_failure(max_retries=3, delay=5)
    def parse_report_playwright(self, page: Page, nttSn: int) -> Optional[Dict]:
        """Playwright를 사용한 상세 페이지 크롤링"""
        url = f"https://www.science.go.kr/mps/1079/bbs/423/moveBbsNttDetail.do?nttSn={nttSn}&"
        
        self.logger.log_info(f"상세 페이지 nttSn={nttSn} 크롤링 시작: {url}")
        
        try:
            # 페이지가 닫혔는지 확인
            if page.is_closed():
                raise Exception("페이지가 닫혔습니다")
            
            # 페이지 이동
            page.goto(url, wait_until="networkidle", timeout=self.config.timeout * 1000)
            
            # 페이지가 닫혔는지 다시 확인
            if page.is_closed():
                raise Exception("페이지 이동 후 페이지가 닫혔습니다")
            
            # 페이지가 완전히 로드될 때까지 대기
            if not page.is_closed():
                page.wait_for_timeout(2000)
            
            # 페이지 소스 가져오기
            if page.is_closed():
                raise Exception("페이지 소스 가져오기 전에 페이지가 닫혔습니다")
            
            page_source = page.content()
            soup = BeautifulSoup(page_source, "lxml")

            # 제목 추출
            title = ""
            title_tag = soup.select_one('div.tbl-view h3')
            if title_tag:
                title = title_tag.get_text(strip=True)

            # 대회명 추출
            contest = ""
            strong_tag = soup.select_one("div.sub-info.item4 strong")
            if strong_tag:
                contest = strong_tag.get_text(strip=True)

            # 요약설명 추출
            desc = ""
            cont_div = soup.select_one("div.write-contents")
            if cont_div:
                desc = cont_div.get_text(separator=" ", strip=True)
            
            # 파일 링크 추출
            base_url = "https://www.science.go.kr"
            file1_url, file2_url = "", ""
            his_logs = soup.select("div.his-log")
            
            if len(his_logs) > 0:
                a1 = his_logs[0].find("a", href=True)
                if a1:
                    file1_url = base_url + a1["href"]
            if len(his_logs) > 1:
                a2 = his_logs[1].find("a", href=True)
                if a2:
                    file2_url = base_url + a2["href"]

            result = {
                "nttSn": nttSn,
                "title": title,
                "contest": contest,
                "description": desc,
                "file1_url": file1_url,
                "file2_url": file2_url
            }
            
            self.logger.log_success(f"nttSn={nttSn} 상세 정보 추출 완료")
            return result
            
        except Exception as e:
            self.logger.log_error(f"nttSn={nttSn} 상세 페이지 크롤링 실패", e)
            raise
    
    def save_summary_data(self, summary_data: List[Dict]):
        """요약 데이터를 DB에 저장"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            for i, row in enumerate(summary_data):
                cur.execute("""
                    INSERT INTO summary (number, year, field, title, award, authors, teacher, image, nttSn)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row["number"], row["year"], row["field"], row["title"],
                    row["award"], row["authors"], row["teacher"], None, row.get("nttSn")
                ))
                
                if (i + 1) % 10 == 0:
                    self.logger.log_info(f"요약 데이터 저장 진행률: {i + 1}/{len(summary_data)}")
            
            conn.commit()
            conn.close()
            self.logger.log_success(f"요약 데이터 {len(summary_data)}개 저장 완료")
            
        except Exception as e:
            self.logger.log_error("요약 데이터 저장 실패", e)
            raise
    
    def save_single_summary_data(self, summary_data: List[Dict]):
        """단일 페이지 요약 데이터를 DB에 저장 (중복 nttSn 건너뛰기)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            saved_count = 0
            skipped_count = 0
            
            for row in summary_data:
                nttSn = row.get("nttSn")
                if nttSn is None:
                    self.logger.log_warning(f"nttSn이 없는 데이터 건너뜀: {row}")
                    continue
                
                # 이미 존재하는지 확인
                cur.execute("SELECT 1 FROM summary WHERE nttSn = ?", (nttSn,))
                if cur.fetchone():
                    self.logger.log_info(f"nttSn {nttSn}은 이미 존재함 → 건너뜀")
                    skipped_count += 1
                    continue
                
                # 새 데이터 저장
                cur.execute("""
                    INSERT INTO summary (number, year, field, title, award, authors, teacher, image, nttSn)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row["number"], row["year"], row["field"], row["title"],
                    row["award"], row["authors"], row["teacher"], None, nttSn
                ))
                saved_count += 1
            
            conn.commit()
            conn.close()
            self.logger.log_success(f"페이지 요약 데이터 저장 완료: {saved_count}개 저장, {skipped_count}개 건너뜀")
            
        except Exception as e:
            self.logger.log_error("페이지 요약 데이터 저장 실패", e)
            raise
    
    def save_detail_data(self, detail_data: List[Dict]):
        """상세 데이터를 DB에 저장"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            for i, detail in enumerate(detail_data):
                cur.execute("""
                    INSERT OR REPLACE INTO detail (nttSn, title, contest, description, file1_url, file2_url, reg_date, year)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    detail["nttSn"], detail["title"], detail["contest"],
                    detail["description"], detail["file1_url"], detail["file2_url"],
                    datetime.now().strftime("%Y-%m-%d"), datetime.now().year
                ))
                
                if (i + 1) % 10 == 0:
                    self.logger.log_info(f"상세 데이터 저장 진행률: {i + 1}/{len(detail_data)}")
            
            conn.commit()
            conn.close()
            self.logger.log_success(f"상세 데이터 {len(detail_data)}개 저장 완료")
            
        except Exception as e:
            self.logger.log_error("상세 데이터 저장 실패", e)
            raise
    
    def save_single_detail_data(self, detail: Dict):
        """단일 상세 데이터를 DB에 저장"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            cur.execute("""
                INSERT OR REPLACE INTO detail (nttSn, title, contest, description, file1_url, file2_url, reg_date, year)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                detail["nttSn"], detail["title"], detail["contest"],
                detail["description"], detail["file1_url"], detail["file2_url"],
                datetime.now().strftime("%Y-%m-%d"), datetime.now().year
            ))
            
            conn.commit()
            conn.close()
            self.logger.log_success(f"nttSn={detail['nttSn']} 상세 데이터 즉시 저장 완료")
            
        except Exception as e:
            self.logger.log_error(f"nttSn={detail['nttSn']} 상세 데이터 저장 실패", e)
            raise
    
    def join_data(self):
        """데이터 JOIN 처리 - nttSn 기준 (DB 테이블 간 JOIN)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            # 기존 joined 데이터 삭제 (중복 방지)
            cur.execute("DELETE FROM joined")
            self.logger.log_info("기존 joined 데이터 삭제 완료")
            
            # SQL JOIN을 사용하여 summary와 detail 테이블을 nttSn으로 연결
            cur.execute("""
                INSERT INTO joined (
                    number, nttSn, year, field, title, contest, award, 
                    authors, teacher, description, file1_url, file2_url, 
                    reg_date, report_pdf, summary_pdf, union_text, json_api
                )
                SELECT 
                    s.number, s.nttSn, s.year, s.field, s.title, 
                    d.contest, s.award, s.authors, s.teacher, d.description,
                    d.file1_url, d.file2_url, ?, 0, 0, 0, 0
                FROM summary s
                INNER JOIN detail d ON s.nttSn = d.nttSn
                WHERE s.nttSn IS NOT NULL AND s.nttSn != ''
            """, (datetime.now().strftime("%Y-%m-%d"),))
            
            join_count = cur.rowcount
            conn.commit()
            conn.close()
            
            self.logger.log_success(f"데이터 JOIN 완료: {join_count}개 매칭 (nttSn 기준)")
            
        except Exception as e:
            self.logger.log_error("데이터 JOIN 실패", e)
            raise
    
    def crawl_list_pages(self) -> List[Dict]:
        """리스트 페이지 크롤링 (Playwright 사용) - 페이지별 즉시 저장"""
        summary_data = []
        
        # 브라우저 재시작 함수
        def restart_browser():
            if hasattr(self, 'playwright'):
                try:
                    context.close()
                    browser.close()
                    self.playwright.stop()
                except:
                    pass
            self.logger.log_info("브라우저 재시작")
            return self.setup_browser()
        
        # 초기 브라우저 설정
        browser, context, page = self.setup_browser()
        
        try:
            for page_num in range(self.config.start_page, self.config.end_page + 1):
                retry_count = 0
                max_retries = 3
                
                while retry_count <= max_retries:
                    try:
                        page_data = self.get_summary_from_list_playwright(page, page_num)
                        
                        # 페이지별로 즉시 DB에 저장
                        if page_data:
                            self.save_single_summary_data(page_data)
                            summary_data.extend(page_data)
                            self.logger.log_success(f"페이지 {page_num} 처리 및 저장 완료: {len(page_data)}개 데이터")
                        else:
                            self.logger.log_warning(f"페이지 {page_num}: 데이터가 없음")
                        
                        # 페이지 간 대기
                        if page_num < self.config.end_page:
                            time.sleep(self.config.page_delay)
                        
                        break  # 성공했으면 while 탈출
                        
                    except Exception as e:
                        retry_count += 1
                        self.logger.log_warning(f"페이지 {page_num} 재시도 {retry_count}/{max_retries + 1}: {str(e)}")
                        
                        if retry_count <= max_retries:
                            # 브라우저 재시작
                            try:
                                browser, context, page = restart_browser()
                                time.sleep(self.config.retry_delay)
                            except Exception as restart_error:
                                self.logger.log_error(f"브라우저 재시작 실패: {str(restart_error)}")
                                break
                        else:
                            self.logger.log_error(f"페이지 {page_num} 최종 실패 (최대 시도 횟수 초과)", e)
                            break
                            
        finally:
            try:
                context.close()
                browser.close()
                self.playwright.stop()
            except:
                pass
        
        return summary_data
    
    def crawl_detail_pages(self) -> List[Dict]:
        """상세 페이지 크롤링 (Playwright 사용) - 개별 즉시 저장"""
        detail_data = []
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        # nttSn 범위 설정
        if self.config.start_nttSn > self.config.end_nttSn:
            nttSn_list = range(self.config.start_nttSn, self.config.end_nttSn - 1, -1)
        else:
            nttSn_list = range(self.config.start_nttSn, self.config.end_nttSn + 1)

        # 브라우저 설정 함수
        def restart_browser():
            if hasattr(self, 'playwright'):
                try:
                    context.close()
                    browser.close()
                    self.playwright.stop()
                except:
                    pass
            self.logger.log_info("브라우저 재시작")
            return self.setup_browser()

        # 초기 브라우저 설정
        browser, context, page = self.setup_browser()

        try:
            for nttSn in nttSn_list:
                cur.execute("SELECT 1 FROM detail WHERE nttSn = ?", (nttSn,))
                if cur.fetchone():
                    self.logger.log_info(f"nttSn {nttSn}은 이미 존재함 → 건너뜀")
                    continue
                retry = 0
                while retry <= self.config.max_retries:
                    try:
                        detail = self.parse_report_playwright(page, nttSn)
                        if detail:
                            self.save_single_detail_data(detail)
                            detail_data.append(detail)
                        self.logger.log_success(f"nttSn {nttSn} 처리 및 저장 완료")
                        time.sleep(self.config.page_delay)
                        break  # 성공했으면 while 탈출
                    except Exception as e:
                        retry += 1
                        self.logger.log_warning(f"nttSn {nttSn} 재시도 {retry}/{self.config.max_retries}")
                        browser, context, page = restart_browser()
                        time.sleep(self.config.retry_delay)
        finally:
            context.close()
            browser.close()
            self.playwright.stop()
            conn.close()

        return detail_data


    
    def run(self):
        """메인 실행 함수"""
        self.logger.log_info("=== 과학전람회 보고서 크롤링 시작 ===")
        
        try:
            # 데이터베이스 초기화
            # self.init_database()
            
            # 상세 페이지 크롤링 (개별 즉시 저장) 33078부터해야함
            # self.logger.log_info("=== 상세 페이지 크롤링 시작 (개별 즉시 저장) ===")
            # detail_data = self.crawl_detail_pages()

            # 리스트 페이지 크롤링 (페이지별 즉시 저장)
            self.logger.log_info("=== 리스트 페이지 크롤링 시작 (페이지별 즉시 저장) ===")
            summary_data = self.crawl_list_pages()
            
            # 데이터 JOIN (DB 테이블 직접 JOIN)
            self.logger.log_info("=== 데이터 JOIN 처리 시작 ===")
            self.join_data()
            
            # 최종 결과 출력
            self.logger.log_success("=== 크롤링 완료! ===")
            self.logger.log_info(f"요약 데이터: {len(summary_data)}개")
            # 상세 데이터 개수는 DB에서 직접 조회 필요
                
        except Exception as e:
            self.logger.log_error("크롤링 프로세스 실패", e)
            raise

def main():
    """메인 함수"""
    import sys
    import os
    
    print("=== 과학전람회 보고서 크롤러 ===")
    
    # 환경변수에서 설정 가져오기 (main.py에서 전달받은 값)
    start_page = os.getenv('START_PAGE')
    end_page = os.getenv('END_PAGE')
    start_nttSn = os.getenv('START_NTTSN')
    end_nttSn = os.getenv('END_NTTSN')
    max_workers = os.getenv('MAX_WORKERS')
    
    # 환경변수가 없으면 사용자 입력 받기
    if not start_page:
        start_page = input("시작 페이지 번호 (기본값: 1): ").strip() or "1"
    if not end_page:
        end_page = input("끝 페이지 번호 (기본값: 3): ").strip() or "3"
    if not start_nttSn:
        start_nttSn = input("시작 nttSn (기본값: 47018): ").strip() or "47018"
    if not end_nttSn:
        end_nttSn = input("끝 nttSn (기본값: 46978): ").strip() or "46978"
    if not max_workers:
        max_workers = input("동시 처리 수 (기본값: 2): ").strip() or "2"
    
    # 문자열을 정수로 변환
    start_page = int(start_page)
    end_page = int(end_page)
    start_nttSn = int(start_nttSn)
    end_nttSn = int(end_nttSn)
    max_workers = int(max_workers)
    
    # 명령행 인수 처리 (환경변수보다 우선)
    if len(sys.argv) > 1:
        try:
            start_page = int(sys.argv[1])
            end_page = int(sys.argv[2]) if len(sys.argv) > 2 else end_page
            start_nttSn = int(sys.argv[3]) if len(sys.argv) > 3 else start_nttSn
            end_nttSn = int(sys.argv[4]) if len(sys.argv) > 4 else end_nttSn
        except (ValueError, IndexError):
            pass
    
    # 설정 출력
    print(f"\n설정된 범위:")
    print(f"페이지: {start_page} ~ {end_page}")
    print(f"nttSn: {start_nttSn} ~ {end_nttSn}")
    print(f"동시 처리 수: {max_workers}")
    
    # 크롤러 실행
    config = CrawlConfig(
        start_page=start_page,
        end_page=end_page,
        start_nttSn=start_nttSn,
        end_nttSn=end_nttSn,
        max_workers=max_workers
    )
    
    crawler = ReportCrawler(config)
    crawler.run()

if __name__ == "__main__":
    main() 