#!/usr/bin/env python3
"""
Playwright 브라우저 설치 스크립트
"""

import subprocess
import sys

def install_playwright_browsers():
    """Playwright 브라우저 설치"""
    print("=== Playwright 브라우저 설치 시작 ===")
    
    try:
        # Playwright 브라우저 설치
        result = subprocess.run([
            sys.executable, "-m", "playwright", "install", "chromium"
        ], capture_output=True, text=True, check=True)
        
        print("✅ Playwright Chromium 브라우저 설치 완료")
        print(result.stdout)
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Playwright 브라우저 설치 실패: {e}")
        print(f"에러 출력: {e.stderr}")
        return False
    
    print("=== Playwright 브라우저 설치 완료 ===")
    return True

if __name__ == "__main__":
    install_playwright_browsers() 