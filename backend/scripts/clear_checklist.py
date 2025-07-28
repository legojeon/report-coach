#!/usr/bin/env python3
"""
clear_checklist.py
science_reports.db의 joined 테이블에서 특정 필드들을 초기화하는 스크립트
"""

import os
import sqlite3
import sys
from datetime import datetime

def clear_checklist_fields():
    """joined 테이블의 체크리스트 필드들을 초기화"""
    
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
        print("=== 현재 상태 확인 ===")
        cur.execute("""
            SELECT 
                COUNT(*) as total_rows,
                COUNT(CASE WHEN original_filename1 IS NOT NULL THEN 1 END) as has_original1,
                COUNT(CASE WHEN original_filename2 IS NOT NULL THEN 1 END) as has_original2,
                COUNT(CASE WHEN saved_filename1 IS NOT NULL THEN 1 END) as has_saved1,
                COUNT(CASE WHEN saved_filename2 IS NOT NULL THEN 1 END) as has_saved2,
                COUNT(CASE WHEN union_text = 1 THEN 1 END) as has_union_text,
                COUNT(CASE WHEN json_api = 1 THEN 1 END) as has_json_api,
                COUNT(CASE WHEN is_pdf = 1 THEN 1 END) as has_is_pdf
            FROM joined
        """)
        
        result = cur.fetchone()
        total_rows, has_original1, has_original2, has_saved1, has_saved2, has_union_text, has_json_api, has_is_pdf = result
        
        print(f"총 행 수: {total_rows}")
        print(f"original_filename1 설정된 행: {has_original1}")
        print(f"original_filename2 설정된 행: {has_original2}")
        print(f"saved_filename1 설정된 행: {has_saved1}")
        print(f"saved_filename2 설정된 행: {has_saved2}")
        print(f"union_text = 1인 행: {has_union_text}")
        print(f"json_api = 1인 행: {has_json_api}")
        print(f"is_pdf = 1인 행: {has_is_pdf}")
        
        # 사용자 확인
        if total_rows == 0:
            print("⚠️ 테이블에 데이터가 없습니다.")
            return False
        
        print(f"\n=== 초기화 작업 ===")
        print("다음 필드들을 초기화합니다:")
        print("- original_filename1 → NULL")
        print("- original_filename2 → NULL")
        print("- saved_filename1 → NULL")
        print("- saved_filename2 → NULL")
        print("- union_text → 0")
        print("- json_api → 0")
        print("- is_pdf → 0")
        
        # 명령행 인수로 --yes가 전달되지 않았다면 사용자 확인
        if len(sys.argv) < 2 or sys.argv[1] != "--yes":
            confirm = input(f"\n{total_rows}개 행의 필드를 초기화하시겠습니까? (y/N): ").strip().lower()
            if confirm != 'y' and confirm != 'yes':
                print("❌ 작업이 취소되었습니다.")
                return False
        
        # 필드 초기화 실행
        print("\n🔄 필드 초기화 중...")
        cur.execute("""
            UPDATE joined 
            SET 
                original_filename1 = NULL,
                original_filename2 = NULL,
                saved_filename1 = NULL,
                saved_filename2 = NULL,
                union_text = 0,
                json_api = 0,
                is_pdf = 0
        """)
        
        updated_rows = cur.rowcount
        conn.commit()
        
        # 결과 확인
        print("\n=== 초기화 완료 ===")
        print(f"✅ {updated_rows}개 행이 초기화되었습니다.")
        
        # 초기화 후 상태 확인
        cur.execute("""
            SELECT 
                COUNT(CASE WHEN original_filename1 IS NOT NULL THEN 1 END) as has_original1,
                COUNT(CASE WHEN original_filename2 IS NOT NULL THEN 1 END) as has_original2,
                COUNT(CASE WHEN saved_filename1 IS NOT NULL THEN 1 END) as has_saved1,
                COUNT(CASE WHEN saved_filename2 IS NOT NULL THEN 1 END) as has_saved2,
                COUNT(CASE WHEN union_text = 1 THEN 1 END) as has_union_text,
                COUNT(CASE WHEN json_api = 1 THEN 1 END) as has_json_api,
                COUNT(CASE WHEN is_pdf = 1 THEN 1 END) as has_is_pdf
            FROM joined
        """)
        
        result = cur.fetchone()
        has_original1, has_original2, has_saved1, has_saved2, has_union_text, has_json_api, has_is_pdf = result
        
        print(f"\n=== 초기화 후 상태 ===")
        print(f"original_filename1 설정된 행: {has_original1}")
        print(f"original_filename2 설정된 행: {has_original2}")
        print(f"saved_filename1 설정된 행: {has_saved1}")
        print(f"saved_filename2 설정된 행: {has_saved2}")
        print(f"union_text = 1인 행: {has_union_text}")
        print(f"json_api = 1인 행: {has_json_api}")
        print(f"is_pdf = 1인 행: {has_is_pdf}")
        
        if has_original1 == 0 and has_original2 == 0 and has_saved1 == 0 and has_saved2 == 0 and has_union_text == 0 and has_json_api == 0 and has_is_pdf == 0:
            print("✅ 모든 필드가 성공적으로 초기화되었습니다!")
        else:
            print("⚠️ 일부 필드가 완전히 초기화되지 않았습니다.")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        return False

def main():
    """메인 함수"""
    print("=== joined 테이블 체크리스트 필드 초기화 ===")
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    success = clear_checklist_fields()
    
    if success:
        print("\n🎉 초기화 작업이 완료되었습니다!")
        sys.exit(0)
    else:
        print("\n💥 초기화 작업이 실패했습니다.")
        sys.exit(1)

if __name__ == "__main__":
    main() 