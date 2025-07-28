#!/usr/bin/env python3
"""
reset_json_api.py
joined 테이블의 json_api 필드만 초기화하는 스크립트
"""

import os
import sqlite3
import sys
from datetime import datetime

def reset_json_api():
    """joined 테이블의 json_api 필드만 초기화"""
    
    # 데이터베이스 경로
    db_path = "../datas/science_reports.db"
    
    # 데이터베이스 파일 존재 확인
    if not os.path.exists(db_path):
        print(f"❌ 데이터베이스 파일을 찾을 수 없습니다: {db_path}")
        return False
    
    try:
        # 데이터베이스 연결
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # 현재 상태 확인
        print("=== 현재 json_api 상태 확인 ===")
        cur.execute("""
            SELECT 
                COUNT(*) as total_rows,
                COUNT(CASE WHEN json_api = 1 THEN 1 END) as has_json_api_1,
                COUNT(CASE WHEN json_api = 0 THEN 1 END) as has_json_api_0,
                COUNT(CASE WHEN json_api IS NULL THEN 1 END) as has_json_api_null
            FROM joined
        """)
        
        result = cur.fetchone()
        total_rows, has_json_api_1, has_json_api_0, has_json_api_null = result
        
        print(f"총 행 수: {total_rows}")
        print(f"json_api = 1인 행: {has_json_api_1}")
        print(f"json_api = 0인 행: {has_json_api_0}")
        print(f"json_api = NULL인 행: {has_json_api_null}")
        
        if total_rows == 0:
            print("⚠️ 테이블에 데이터가 없습니다.")
            return False
        
        # 사용자 확인
        if len(sys.argv) < 2 or sys.argv[1] != "--yes":
            confirm = input(f"\n{total_rows}개 행의 json_api 필드를 0으로 초기화하시겠습니까? (y/N): ").strip().lower()
            if confirm != 'y' and confirm != 'yes':
                print("❌ 작업이 취소되었습니다.")
                return False
        
        # json_api 필드 초기화 실행
        print("\n🔄 json_api 필드 초기화 중...")
        cur.execute("UPDATE joined SET json_api = 0")
        
        updated_rows = cur.rowcount
        conn.commit()
        
        # 결과 확인
        print("\n=== 초기화 완료 ===")
        print(f"✅ {updated_rows}개 행의 json_api 필드가 초기화되었습니다.")
        
        # 초기화 후 상태 확인
        cur.execute("""
            SELECT 
                COUNT(CASE WHEN json_api = 1 THEN 1 END) as has_json_api_1,
                COUNT(CASE WHEN json_api = 0 THEN 1 END) as has_json_api_0,
                COUNT(CASE WHEN json_api IS NULL THEN 1 END) as has_json_api_null
            FROM joined
        """)
        
        result = cur.fetchone()
        has_json_api_1, has_json_api_0, has_json_api_null = result
        
        print(f"\n=== 초기화 후 상태 ===")
        print(f"json_api = 1인 행: {has_json_api_1}")
        print(f"json_api = 0인 행: {has_json_api_0}")
        print(f"json_api = NULL인 행: {has_json_api_null}")
        
        if has_json_api_1 == 0:
            print("✅ json_api 필드가 성공적으로 초기화되었습니다!")
        else:
            print("⚠️ json_api 필드가 완전히 초기화되지 않았습니다.")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        return False

def main():
    """메인 함수"""
    print("=== joined 테이블 json_api 필드 초기화 ===")
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    success = reset_json_api()
    
    if success:
        print("\n🎉 json_api 초기화 작업이 완료되었습니다!")
        sys.exit(0)
    else:
        print("\n💥 json_api 초기화 작업이 실패했습니다.")
        sys.exit(1)

if __name__ == "__main__":
    main() 