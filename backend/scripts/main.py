#!/usr/bin/env python3
"""
과학전람회 보고서 크롤링 메인 프로세스
전체 워크플로우를 관리하는 통합 스크립트
"""

import os
import sys
import time
import subprocess
import logging
import traceback
import multiprocessing as mp
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv("../.env")

@dataclass
class ProcessConfig:
    """프로세스 설정 클래스"""
    start_page: int = 1
    end_page: int = 1800
    start_nttSn: int = 47018
    end_nttSn: int = 13176
    max_workers: int = 2
    skip_crawl: bool = False
    skip_download: bool = False
    skip_extract: bool = False
    skip_image: bool = False
    skip_reformat: bool = False
    skip_convert_json: bool = False
    skip_chromadb: bool = False
    reformat_processes: int = 4  # reformat용 프로세스 수 추가

    def __post_init__(self):
        # nttSn 범위 자동 정렬
        if self.start_nttSn > self.end_nttSn:
            self.start_nttSn, self.end_nttSn = self.end_nttSn, self.start_nttSn

class ProcessLogger:
    """프로세스 로거 클래스"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        self.setup_logging()
    
    def setup_logging(self):
        """로깅 설정"""
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 메인 로거 설정
        self.logger = logging.getLogger('main_process')
        self.logger.setLevel(logging.INFO)
        
        # 기존 핸들러 제거
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # 파일 핸들러
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_handler = logging.FileHandler(
            f"{self.log_dir}/main_{timestamp}.log", 
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

def get_nttSn_ranges_from_db(start_nttSn: int, end_nttSn: int, num_processes: int) -> List[Tuple[int, int]]:
    """DB에서 실제 파일 개수를 기준으로 nttSn 범위를 균등 분할"""
    try:
        # DB 연결
        db_path = "../datas/science_reports.db"
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # 범위 내 실제 파일 개수 조회
        cur.execute("""
            SELECT COUNT(*) FROM joined 
            WHERE nttSn BETWEEN ? AND ?
        """, (start_nttSn, end_nttSn))
        
        total_files = cur.fetchone()[0]
        
        if total_files == 0:
            print(f"경고: nttSn {start_nttSn}~{end_nttSn} 범위에 파일이 없습니다.")
            conn.close()
            return []
        
        print(f"총 파일 수: {total_files}개")
        
        # 각 프로세스별 분할점 계산
        split_points = []
        for i in range(1, num_processes):
            split_index = (total_files * i) // num_processes
            split_points.append(split_index)
        
        # nttSn 순서로 정렬된 파일 목록 가져오기
        cur.execute("""
            SELECT nttSn FROM joined 
            WHERE nttSn BETWEEN ? AND ?
            ORDER BY nttSn ASC
        """, (start_nttSn, end_nttSn))
        
        nttSn_list = [row[0] for row in cur.fetchall()]
        
        # nttSn 범위 계산
        ranges = []
        start_index = 0
        
        for i in range(num_processes):
            if i == num_processes - 1:
                # 마지막 프로세스는 끝까지
                range_start = nttSn_list[start_index]
                range_end = nttSn_list[-1]
            else:
                # 분할점까지
                end_index = split_points[i] - 1
                range_start = nttSn_list[start_index]
                range_end = nttSn_list[end_index]
                start_index = end_index + 1
            
            file_count = (split_points[i] if i < num_processes - 1 else total_files) - (split_points[i-1] if i > 0 else 0)
            ranges.append((range_start, range_end))
            print(f"프로세스 {i}: nttSn {range_start}~{range_end} ({file_count}개 파일)")
        
        conn.close()
        return ranges
        
    except Exception as e:
        print(f"DB 분할 오류: {e}")
        # 오류 시 기존 방식으로 fallback
        return get_nttSn_ranges_fallback(start_nttSn, end_nttSn, num_processes)

def get_nttSn_ranges_fallback(start_nttSn: int, end_nttSn: int, num_processes: int) -> List[Tuple[int, int]]:
    """기존 수학적 분할 방식 (fallback용)"""
    total_range = end_nttSn - start_nttSn + 1
    chunk_size = total_range // num_processes
    
    ranges = []
    for i in range(num_processes):
        range_start = start_nttSn + (i * chunk_size)
        if i == num_processes - 1:  # 마지막 프로세스는 남은 모든 것을 처리
            range_end = end_nttSn
        else:
            range_end = range_start + chunk_size - 1
        
        ranges.append((range_start, range_end))
    
    return ranges

def get_nttSn_ranges(start_nttSn: int, end_nttSn: int, num_processes: int) -> List[Tuple[int, int]]:
    """nttSn 범위를 DB 기준으로 분할 (기본 함수)"""
    return get_nttSn_ranges_from_db(start_nttSn, end_nttSn, num_processes)

def run_reformat_process(process_id: int, start_nttSn: int, end_nttSn: int, script_dir: str) -> bool:
    """개별 reformat 프로세스 실행 함수"""
    try:
        # 환경변수 설정
        env = os.environ.copy()
        env['START_NTTSN'] = str(start_nttSn)
        env['END_NTTSN'] = str(end_nttSn)
        env['PROCESS_ID'] = str(process_id)  # 프로세스 ID를 환경변수로 전달
        
        # 방법 1: 환경변수에서 여러 API 키 선택
        api_keys = [
            os.getenv('GOOGLE_API_KEY_1', os.getenv('GOOGLE_API_KEY')),  # 프로세스 0
            os.getenv('GOOGLE_API_KEY_2', os.getenv('GOOGLE_API_KEY')),  # 프로세스 1
            os.getenv('GOOGLE_API_KEY_3', os.getenv('GOOGLE_API_KEY')),  # 프로세스 2
            os.getenv('GOOGLE_API_KEY_4', os.getenv('GOOGLE_API_KEY')),  # 프로세스 3
        ]
        
        # 방법 2: 프로세스별 .env 파일 사용 (선택사항)
        env_file = f"../.env.process{process_id}" if os.path.exists(f"../.env.process{process_id}") else "../.env"
        if env_file != "../.env":
            print(f"프로세스 {process_id}: {env_file} 사용")
        
        # 프로세스 ID에 따라 API 키 선택
        selected_api_key = api_keys[process_id % len(api_keys)]
        
        # API 키가 None이면 기본 키 사용
        if selected_api_key is None:
            selected_api_key = os.getenv('GOOGLE_API_KEY')
        
        # API 키가 여전히 None이면 오류
        if selected_api_key is None:
            print(f"프로세스 {process_id} 오류: GOOGLE_API_KEY가 설정되지 않았습니다.")
            return False
            
        env['GOOGLE_API_KEY'] = selected_api_key
        
        # 스크립트 실행
        cmd = [sys.executable, 'reformat_text.py']
        
        print(f"프로세스 {process_id} 시작: nttSn {start_nttSn} ~ {end_nttSn} (API Key: {selected_api_key[:10]}...)")
        
        result = subprocess.run(
            cmd,
            capture_output=False,
            text=True,
            cwd=script_dir,
            env=env
        )
        
        if result.returncode == 0:
            print(f"프로세스 {process_id} 완료: nttSn {start_nttSn} ~ {end_nttSn}")
            return True
        else:
            print(f"프로세스 {process_id} 실패: nttSn {start_nttSn} ~ {end_nttSn}")
            return False
            
    except Exception as e:
        print(f"프로세스 {process_id} 실행 오류: {e}")
        return False

def run_convert_json_process(process_id: int, start_nttSn: int, end_nttSn: int, script_dir: str) -> bool:
    """개별 convert_json 프로세스 실행 함수"""
    try:
        # 환경변수 설정
        env = os.environ.copy()
        env['START_NTTSN'] = str(start_nttSn)
        env['END_NTTSN'] = str(end_nttSn)
        env['PROCESS_ID'] = str(process_id)  # 프로세스 ID를 환경변수로 전달
        
        # 방법 1: 환경변수에서 여러 API 키 선택
        api_keys = [
            os.getenv('GOOGLE_API_KEY_1', os.getenv('GOOGLE_API_KEY')),  # 프로세스 0
            os.getenv('GOOGLE_API_KEY_2', os.getenv('GOOGLE_API_KEY')),  # 프로세스 1
            os.getenv('GOOGLE_API_KEY_3', os.getenv('GOOGLE_API_KEY')),  # 프로세스 2
            os.getenv('GOOGLE_API_KEY_4', os.getenv('GOOGLE_API_KEY')),  # 프로세스 3
        ]
        
        # 방법 2: 프로세스별 .env 파일 사용 (선택사항)
        env_file = f"../.env.process{process_id}" if os.path.exists(f"../.env.process{process_id}") else "../.env"
        if env_file != "../.env":
            print(f"프로세스 {process_id}: {env_file} 사용")
        
        # 프로세스 ID에 따라 API 키 선택
        selected_api_key = api_keys[process_id % len(api_keys)]
        
        # API 키가 None이면 기본 키 사용
        if selected_api_key is None:
            selected_api_key = os.getenv('GOOGLE_API_KEY')
        
        # API 키가 여전히 None이면 오류
        if selected_api_key is None:
            print(f"프로세스 {process_id} 오류: GOOGLE_API_KEY가 설정되지 않았습니다.")
            return False
            
        env['GOOGLE_API_KEY'] = selected_api_key
        
        # 스크립트 실행
        cmd = [sys.executable, 'convert_json.py']
        
        print(f"프로세스 {process_id} 시작: nttSn {start_nttSn} ~ {end_nttSn} (API Key: {selected_api_key[:10]}...)")
        
        result = subprocess.run(
            cmd,
            capture_output=False,
            text=True,
            cwd=script_dir,
            env=env
        )
        
        if result.returncode == 0:
            print(f"프로세스 {process_id} 완료: nttSn {start_nttSn} ~ {end_nttSn}")
            return True
        else:
            print(f"프로세스 {process_id} 실패: nttSn {start_nttSn} ~ {end_nttSn}")
            return False
            
    except Exception as e:
        print(f"프로세스 {process_id} 실행 오류: {e}")
        return False

class ProcessManager:
    """프로세스 관리자"""
    
    def __init__(self, config: ProcessConfig):
        self.config = config
        self.logger = ProcessLogger()
        self.process_stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0
        }
        
        # 실행할 스크립트 목록
        self.scripts = [
            # {
            #     'name': 'report_crawler.py',
            #     'description': '보고서 크롤링',
            #     'skip': config.skip_crawl,
            #     'args': []
            # },
            # {
            #     'name': 'download_pdfs.py',
            #     'description': 'PDF 다운로드',
            #     'skip': config.skip_download,
            #     'args': []
            # },
            # {
            #     'name': 'extract_text.py',
            #     'description': '텍스트 추출',
            #     'skip': config.skip_extract,
            #     'args': []
            # },
            # {
            #     'name': 'extract_image.py',
            #     'description': '이미지 추출',
            #     'skip': config.skip_image,
            #     'args': []
            # },
            {
                'name': 'reformat_text_parallel',  # 특별한 이름으로 변경
                'description': '텍스트 재포맷 (병렬)',
                'skip': config.skip_reformat,
                'args': []
            },
            {
                'name': 'convert_json_parallel',  # 병렬 처리용 이름으로 변경
                'description': 'JSON 변환 (병렬)',
                'skip': config.skip_convert_json,
                'args': []
            }
            # {
            #     'name': 'build_chromadb.py',
            #     'description': 'ChromaDB 구축',
            #     'skip': config.skip_chromadb,
            #     'args': []
            # }
        ]
    
    def run_script(self, script_info: Dict) -> bool:
        """개별 스크립트 실행"""
        script_name = script_info['name']
        description = script_info['description']
        
        self.logger.log_info(f"=== {description} 시작 ===")
        self.logger.log_info(f"스크립트: {script_name}")
        
        try:
            # reformat_text_parallel 특별 처리
            if script_name == 'reformat_text_parallel':
                return self.run_reformat_parallel()
            
            # convert_json_parallel 특별 처리
            if script_name == 'convert_json_parallel':
                return self.run_convert_json_parallel()
            
            # 환경변수 설정
            env = os.environ.copy()
            
            # 크롤링 설정
            if script_name == 'report_crawler.py':
                env['START_PAGE'] = str(self.config.start_page)
                env['END_PAGE'] = str(self.config.end_page)
                env['START_NTTSN'] = str(self.config.start_nttSn)
                env['END_NTTSN'] = str(self.config.end_nttSn)
                env['MAX_WORKERS'] = str(self.config.max_workers)
            
            # 다운로드 설정 - nttSn 범위 직접 사용
            elif script_name == 'download_pdfs.py':
                env['START_NTTSN'] = str(self.config.start_nttSn)
                env['END_NTTSN'] = str(self.config.end_nttSn)
            
            # 텍스트 추출 설정 - nttSn 범위 직접 사용
            elif script_name == 'extract_text.py':
                env['START_NTTSN'] = str(self.config.start_nttSn)
                env['END_NTTSN'] = str(self.config.end_nttSn)
            
            # 이미지 추출 설정 - nttSn 범위 직접 사용
            elif script_name == 'extract_image.py':
                env['START_NTTSN'] = str(self.config.start_nttSn)
                env['END_NTTSN'] = str(self.config.end_nttSn)
            
            # 스크립트 실행
            cmd = [sys.executable, script_name] + script_info['args']
            self.logger.log_info(f"실행 명령: {' '.join(cmd)}")
            
            # 스크립트 디렉토리로 작업 디렉토리 변경
            script_dir = os.path.dirname(os.path.abspath(__file__))
            
            self.logger.log_info(f"작업 디렉토리: {script_dir}")
            self.logger.log_info(f"환경변수: {dict(env)}")
            
            # 실시간 출력을 위해 capture_output=False로 변경
            result = subprocess.run(
                cmd,
                capture_output=False,
                text=True,
                cwd=script_dir,
                env=env
            )
            
            if result.returncode == 0:
                self.logger.log_success(f"{description} 완료")
                self.process_stats['success'] += 1
                return True
            else:
                self.logger.log_error(f"{description} 실패 (종료 코드: {result.returncode})")
                self.logger.log_error(f"에러 출력: {result.stderr}")
                self.process_stats['failed'] += 1
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.log_error(f"{description} 타임아웃 (1시간 초과)")
            self.process_stats['failed'] += 1
            return False
        except Exception as e:
            self.logger.log_error(f"{description} 실행 오류", e)
            self.process_stats['failed'] += 1
            return False
    
    def run_reformat_parallel(self) -> bool:
        """reformat_text.py를 병렬로 실행"""
        self.logger.log_info(f"=== 텍스트 재포맷 병렬 실행 시작 ===")
        self.logger.log_info(f"프로세스 수: {self.config.reformat_processes}")
        
        try:
            # nttSn 범위 분할
            ranges = get_nttSn_ranges(
                self.config.start_nttSn, 
                self.config.end_nttSn, 
                self.config.reformat_processes
            )
            
            self.logger.log_info("분할된 범위:")
            for i, (start, end) in enumerate(ranges):
                self.logger.log_info(f"프로세스 {i}: nttSn {start} ~ {end}")
            
            # 스크립트 디렉토리
            script_dir = os.path.dirname(os.path.abspath(__file__))
            
            # 병렬 프로세스 시작
            processes = []
            for i, (start, end) in enumerate(ranges):
                p = mp.Process(
                    target=run_reformat_process,
                    args=(i, start, end, script_dir)
                )
                processes.append(p)
                p.start()
                self.logger.log_info(f"프로세스 {i} 시작됨")
            
            # 모든 프로세스 완료 대기
            self.logger.log_info("모든 프로세스 완료 대기 중...")
            for i, p in enumerate(processes):
                p.join()
                if p.exitcode == 0:
                    self.logger.log_success(f"프로세스 {i} 정상 완료")
                else:
                    self.logger.log_error(f"프로세스 {i} 실패 (종료 코드: {p.exitcode})")
            
            # 성공 여부 확인
            success_count = sum(1 for p in processes if p.exitcode == 0)
            total_count = len(processes)
            
            self.logger.log_info(f"병렬 재포맷 완료: {success_count}/{total_count} 성공")
            
            if success_count == total_count:
                self.logger.log_success("모든 reformat 프로세스 성공")
                return True
            else:
                self.logger.log_warning(f"일부 reformat 프로세스 실패 ({success_count}/{total_count})")
                return False
                
        except Exception as e:
            self.logger.log_error("병렬 reformat 실행 오류", e)
            return False
    
    def run_convert_json_parallel(self) -> bool:
        """convert_json.py를 병렬로 실행"""
        self.logger.log_info(f"=== JSON 변환 병렬 실행 시작 ===")
        self.logger.log_info(f"프로세스 수: {self.config.reformat_processes}")
        
        try:
            # nttSn 범위 분할
            ranges = get_nttSn_ranges(
                self.config.start_nttSn, 
                self.config.end_nttSn, 
                self.config.reformat_processes
            )
            
            self.logger.log_info("분할된 범위:")
            for i, (start, end) in enumerate(ranges):
                self.logger.log_info(f"프로세스 {i}: nttSn {start} ~ {end}")
            
            # 스크립트 디렉토리
            script_dir = os.path.dirname(os.path.abspath(__file__))
            
            # 병렬 프로세스 시작
            processes = []
            for i, (start, end) in enumerate(ranges):
                p = mp.Process(
                    target=run_convert_json_process,
                    args=(i, start, end, script_dir)
                )
                processes.append(p)
                p.start()
                self.logger.log_info(f"프로세스 {i} 시작됨")
            
            # 모든 프로세스 완료 대기
            self.logger.log_info("모든 프로세스 완료 대기 중...")
            for i, p in enumerate(processes):
                p.join()
                if p.exitcode == 0:
                    self.logger.log_success(f"프로세스 {i} 정상 완료")
                else:
                    self.logger.log_error(f"프로세스 {i} 실패 (종료 코드: {p.exitcode})")
            
            # 성공 여부 확인
            success_count = sum(1 for p in processes if p.exitcode == 0)
            total_count = len(processes)
            
            self.logger.log_info(f"병렬 JSON 변환 완료: {success_count}/{total_count} 성공")
            
            if success_count == total_count:
                self.logger.log_success("모든 convert_json 프로세스 성공")
                return True
            else:
                self.logger.log_warning(f"일부 convert_json 프로세스 실패 ({success_count}/{total_count})")
                return False
                
        except Exception as e:
            self.logger.log_error("병렬 convert_json 실행 오류", e)
            return False
    
    def run_all_processes(self):
        """모든 프로세스 실행"""
        self.logger.log_info("=== 과학전람회 보고서 크롤링 프로세스 시작 ===")
        self.logger.log_info(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        start_time = time.time()
        
        try:
            for i, script_info in enumerate(self.scripts):
                self.process_stats['total'] += 1
                
                if script_info['skip']:
                    self.logger.log_warning(f"건너뛰기: {script_info['description']}")
                    self.process_stats['skipped'] += 1
                    continue
                
                self.logger.log_info(f"진행률: {i+1}/{len(self.scripts)} - {script_info['description']}")
                
                success = self.run_script(script_info)
                
                if not success:
                    self.logger.log_warning(f"{script_info['description']} 실패로 인한 프로세스 중단")
                    break
                
                # 스크립트 간 대기
                if i < len(self.scripts) - 1:
                    self.logger.log_info("다음 스크립트 준비 중... (5초 대기)")
                    time.sleep(5)
            
            # 최종 통계
            end_time = time.time()
            duration = end_time - start_time
            
            self.logger.log_success("=== 전체 프로세스 완료 ===")
            self.logger.log_info(f"총 소요 시간: {duration:.2f}초 ({duration/60:.2f}분)")
            self.logger.log_info(f"총 스크립트: {self.process_stats['total']}개")
            self.logger.log_info(f"성공: {self.process_stats['success']}개")
            self.logger.log_info(f"실패: {self.process_stats['failed']}개")
            self.logger.log_info(f"건너뛴: {self.process_stats['skipped']}개")
            
        except KeyboardInterrupt:
            self.logger.log_warning("사용자에 의한 프로세스 중단")
        except Exception as e:
            self.logger.log_error("프로세스 실행 중 오류 발생", e)
            raise

def get_user_input() -> ProcessConfig:
    """사용자 입력 받기 - 하드코딩된 설정 사용"""
    print("=== 과학전람회 보고서 크롤링 메인 프로세스 ===")
    print("\n=== 크롤링 설정 (하드코딩됨) ===")
    
    # 하드코딩된 설정
    start_page = 1
    end_page = 567
    start_nttSn = 47018
    end_nttSn = 25514
    reformat_processes = 4  # reformat용 프로세스 수
    
    # 스킵 옵션 - 모두 False로 설정 (전체 실행)
    skip_crawl = False
    skip_download = False
    skip_extract = False
    skip_image = False
    skip_reformat = False
    skip_convert_json = False
    skip_chromadb = False
    
    # 설정 출력
    print(f"페이지: {start_page} ~ {end_page}")
    print(f"nttSn: {start_nttSn} ~ {end_nttSn}")
    print(f"Reformat 프로세스 수: {reformat_processes}")
    print("모든 프로세스 실행 (스킵 없음)")
    
    return ProcessConfig(
        start_page=start_page,
        end_page=end_page,
        start_nttSn=start_nttSn,
        end_nttSn=end_nttSn,
        reformat_processes=reformat_processes,
        skip_crawl=skip_crawl,
        skip_download=skip_download,
        skip_extract=skip_extract,
        skip_image=skip_image,
        skip_reformat=skip_reformat,
        skip_convert_json=skip_convert_json,
        skip_chromadb=skip_chromadb
    )

def main():
    """메인 함수"""
    try:
        # 사용자 입력 받기 (하드코딩된 설정)
        config = get_user_input()
        
        # 프로세스 실행 (확인 없이 바로 실행)
        print(f"\n=== 프로세스 시작 ===")
        manager = ProcessManager(config)
        manager.run_all_processes()
        
    except KeyboardInterrupt:
        print("\n프로세스가 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n프로세스 실행 중 오류 발생: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main() 