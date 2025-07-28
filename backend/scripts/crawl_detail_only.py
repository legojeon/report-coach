# 필요한 import 생략 없이 그대로 유지
import os
import sys
import time
import sqlite3
import logging
import traceback
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass
from functools import wraps
import threading

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
from bs4 import BeautifulSoup


@dataclass
class CrawlConfig:
    start_nttSn: int = 47018
    end_nttSn: int = 46978
    max_retries: int = 3
    retry_delay: int = 5
    max_workers: int = 2
    timeout: int = 10
    page_delay: int = 2


class CrawlLogger:
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        self.setup_logging()
    
    def setup_logging(self):
        os.makedirs(self.log_dir, exist_ok=True)
        self.logger = logging.getLogger('report_crawler')
        self.logger.setLevel(logging.INFO)
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_handler = logging.FileHandler(f"{self.log_dir}/crawl_{timestamp}.log", encoding='utf-8')
        console_handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def log_success(self, message: str):
        self.logger.info(f"✅ {message}")
    
    def log_error(self, message: str, error: Exception = None):
        if error:
            self.logger.error(f"❌ {message}: {str(error)}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
        else:
            self.logger.error(f"❌ {message}")
    
    def log_warning(self, message: str):
        self.logger.warning(f"⚠️ {message}")
    
    def log_info(self, message: str):
        self.logger.info(f"ℹ️ {message}")


def retry_on_failure(max_retries: int = 3, delay: int = 5):
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
                        logger.log_warning(f"{func.__name__} 실패 (시도 {attempt + 1}/{max_retries + 1}): {str(e)}")
                        time.sleep(delay)
                    else:
                        logger = CrawlLogger()
                        logger.log_error(f"{func.__name__} 최종 실패", e)
            raise last_exception
        return wrapper
    return decorator


class ReportCrawler:
    def __init__(self, config: CrawlConfig):
        self.config = config
        self.logger = CrawlLogger()
        self.db_path = "../datas/science_reports.db"
        self.lock = threading.Lock()

    def setup_browser(self) -> tuple[Browser, BrowserContext, Page]:
        try:
            self.playwright = sync_playwright().start()
            browser = self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-blink-features=AutomationControlled'
                ]
            )
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0'
            )
            page = context.new_page()
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined })")
            self.logger.log_success("Playwright 브라우저 설정 완료")
            return browser, context, page
        except Exception as e:
            self.logger.log_error("브라우저 설정 실패", e)
            raise

    @retry_on_failure()
    def parse_report_playwright(self, page: Page, nttSn: int) -> Optional[Dict]:
        url = f"https://www.science.go.kr/mps/1079/bbs/423/moveBbsNttDetail.do?nttSn={nttSn}&"
        self.logger.log_info(f"상세 페이지 nttSn={nttSn} 크롤링 시작: {url}")
        try:
            page.goto(url, wait_until="networkidle", timeout=self.config.timeout * 1000)
            page.wait_for_timeout(2000)
            soup = BeautifulSoup(page.content(), "lxml")
            title = soup.select_one('div.tbl-view h3')
            contest = soup.select_one("div.sub-info.item4 strong")
            desc = soup.select_one("div.write-contents")
            base_url = "https://www.science.go.kr"
            files = soup.select("div.his-log")
            file1_url = base_url + files[0].find("a")["href"] if len(files) > 0 and files[0].find("a") else ""
            file2_url = base_url + files[1].find("a")["href"] if len(files) > 1 and files[1].find("a") else ""
            return {
                "nttSn": nttSn,
                "title": title.get_text(strip=True) if title else "",
                "contest": contest.get_text(strip=True) if contest else "",
                "description": desc.get_text(separator=" ", strip=True) if desc else "",
                "file1_url": file1_url,
                "file2_url": file2_url
            }
        except Exception as e:
            self.logger.log_error(f"nttSn={nttSn} 크롤링 실패", e)
            raise

    def save_single_detail_data(self, detail: Dict):
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS detail (
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
                INSERT OR REPLACE INTO detail 
                (nttSn, title, contest, description, file1_url, file2_url, reg_date, year) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                detail["nttSn"], detail["title"], detail["contest"], detail["description"],
                detail["file1_url"], detail["file2_url"],
                datetime.now().strftime("%Y-%m-%d"), datetime.now().year
            ))
            conn.commit()
            conn.close()
            self.logger.log_success(f"nttSn={detail['nttSn']} 저장 완료")
        except Exception as e:
            self.logger.log_error(f"nttSn={detail['nttSn']} 저장 실패", e)
            raise

    def crawl_detail_pages(self) -> List[Dict]:
        detail_data = []
        nttSn_list = range(self.config.start_nttSn, self.config.end_nttSn - 1, -1) \
            if self.config.start_nttSn > self.config.end_nttSn else range(self.config.start_nttSn, self.config.end_nttSn + 1)
        browser, context, page = self.setup_browser()
        try:
            for nttSn in nttSn_list:
                try:
                    detail = self.parse_report_playwright(page, nttSn)
                    if detail:
                        self.save_single_detail_data(detail)
                        detail_data.append(detail)
                    time.sleep(self.config.page_delay)
                except Exception as e:
                    self.logger.log_error(f"nttSn {nttSn} 실패", e)
        finally:
            context.close()
            browser.close()
            self.playwright.stop()
        return detail_data

    def run(self):
        self.logger.log_info("=== 상세 보고서 크롤링 시작 ===")
        try:
            detail_data = self.crawl_detail_pages()
            self.logger.log_success("=== 크롤링 완료 ===")
            self.logger.log_info(f"총 수집된 상세 데이터: {len(detail_data)}개")
        except Exception as e:
            self.logger.log_error("크롤링 실패", e)
            raise


def main():
    print("=== 과학전람회 상세 보고서 크롤러 ===")
    start_nttSn = int(os.getenv('START_NTTSN') or input("시작 nttSn (기본값: 47018): ").strip() or "47018")
    end_nttSn = int(os.getenv('END_NTTSN') or input("끝 nttSn (기본값: 46978): ").strip() or "46978")
    max_workers = int(os.getenv('MAX_WORKERS') or input("동시 처리 수 (기본값: 2): ").strip() or "2")
    print(f"nttSn: {start_nttSn} ~ {end_nttSn}, 동시 처리 수: {max_workers}")
    config = CrawlConfig(start_nttSn=start_nttSn, end_nttSn=end_nttSn, max_workers=max_workers)
    crawler = ReportCrawler(config)
    crawler.run()


if __name__ == "__main__":
    main()
