# Scripts 폴더 설치 및 실행 가이드

## 가상환경 설정

### 1. 가상환경 생성
```bash
# Python 3.8 이상 권장
python3 -m venv venv

# 가상환경 활성화 (macOS/Linux)
source venv/bin/activate

# 가상환경 활성화 (Windows)
venv\Scripts\activate
```

### 2. 의존성 설치
```bash
sudo apt update
sudo apt install libsqlite3-dev
pip install -r requirements.txt
```

### 3. Playwright 브라우저 설치
```bash
playwright install
```

## 환경변수 설정

### .env 파일 생성
`backend` 폴더에 `.env` 파일을 생성하고 다음 내용을 추가:

```env
# Google Gemini API
GOOGLE_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash-lite-preview-06-17
GEMINI_MAX_TOKENS=32768
GEMINI_TEMPERATURE=0.1
GEMINI_TOP_P=0.9
GEMINI_TOP_K=40

# Embedding Model
EMBEDDING_MODEL=jhgan/ko-sroberta-multitask
EMBEDDING_DEVICE=mps  # macOS: mps, Linux: cuda, CPU: cpu
EMBEDDING_BATCH_SIZE=32
```

## 실행 방법

### 1. 전체 프로세스 실행
```bash
python main.py
```

### 2. 개별 스크립트 실행
```bash
# 크롤링
python report_crawler.py

# PDF 다운로드
python download_pdfs.py

# 텍스트 추출
python extract_text.py

# 이미지 추출
python extract_image.py

# 텍스트 재포맷
python reformat_text.py

# JSON 변환
python convert_json.py

# ChromaDB 구축
python build_chromadb.py
```

## 폴더 구조

```
backend/
├── .env                    # 환경변수 파일
├── scripts/
│   ├── requirements.txt    # 의존성 목록
│   ├── main.py           # 메인 실행 스크립트
│   ├── report_crawler.py # 크롤링
│   ├── download_pdfs.py  # PDF 다운로드
│   ├── extract_text.py   # 텍스트 추출
│   ├── extract_image.py  # 이미지 추출
│   ├── reformat_text.py  # 텍스트 재포맷
│   ├── convert_json.py   # JSON 변환
│   └── build_chromadb.py # ChromaDB 구축
├── datas/                 # 데이터 저장 폴더 (자동 생성)
│   ├── pdf_reports/      # 다운로드된 PDF
│   ├── extracted_pdf/    # 추출된 텍스트/이미지
│   ├── json_results/     # JSON 변환 결과
│   └── chroma_db/        # ChromaDB
└── prompts/              # 프롬프트 파일들
```

## 주의사항

1. **API 키**: Google Gemini API 키가 필요합니다
2. **메모리**: 대용량 데이터 처리 시 충분한 메모리 확보
3. **네트워크**: PDF 다운로드 시 안정적인 인터넷 연결
4. **저장공간**: PDF와 이미지 파일로 인한 충분한 디스크 공간

## 문제 해결

### 일반적인 오류

1. **ModuleNotFoundError**: `pip install -r requirements.txt` 재실행
2. **API 키 오류**: `.env` 파일의 API 키 확인
3. **Playwright 오류**: `playwright install` 재실행
4. **메모리 부족**: 배치 크기 조정 또는 더 작은 범위로 실행

### 로그 확인
```bash
# 로그 폴더 확인
ls logs/

# 최신 로그 확인
tail -f logs/main_*.log
``` 