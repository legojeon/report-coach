# ReportCoach Backend

ReportCoach의 백엔드 API 서버입니다. FastAPI를 기반으로 구축되었으며, AI 기반 리포트 작성 및 분석 기능을 제공합니다.

## 🛠️ 기술 스택

- **FastAPI**: Python 웹 프레임워크
- **Supabase**: 데이터베이스 및 인증
- **LangChain**: AI 모델 통합
- **ChromaDB**: 벡터 데이터베이스
- **Google GenAI**: AI 모델 서비스
- **Uvicorn**: ASGI 서버

## 📁 프로젝트 구조

```
backend/
├── app/
│   ├── routers/          # API 라우터
│   │   ├── auth.py       # 인증 관련 API
│   │   ├── chat.py       # 채팅 관련 API
│   │   ├── notes.py      # 노트 관련 API
│   │   ├── search.py     # 검색 관련 API
│   │   ├── users.py      # 사용자 관리 API
│   │   ├── write.py      # 리포트 작성 API
│   │   └── logger.py     # 로깅 API
│   ├── services/         # 비즈니스 로직
│   ├── models/           # 데이터 모델
│   ├── schemas/          # Pydantic 스키마
│   └── dependencies.py   # 의존성 주입
├── prompts/              # AI 프롬프트
├── scripts/              # 데이터 처리 스크립트
├── main.py               # 애플리케이션 진입점
└── requirements.txt      # Python 의존성
```

## 🔧 주요 기능

### 인증 시스템
- JWT 토큰 기반 인증
- Supabase를 통한 사용자 관리
- 리프레시 토큰 지원

## 🗄️ Supabase 데이터베이스

### 주요 테이블 구조

#### 1. 핵심 테이블
- **`users`**: 사용자 정보 및 인증 관리
- **`notes`**: 사용자 노트 및 채팅 기록 저장
- **`ai_usage_logs`**: AI 서비스 사용량 추적 및 분석

#### 2. 테이블 상세 설명

**`users` 테이블**
- 사용자 기본 정보 (사용자명, 소속, 멤버십 상태)
- Supabase Auth와 연동된 인증 시스템
- 계정 활성화 상태 및 생성/수정 시간 추적

**`notes` 테이블**
- 사용자가 작성한 노트 저장
- 채팅 히스토리 및 요약 정보 포함
- 보고서 번호(nttsn)와 연동하여 특정 보고서 관련 노트 관리
- 서비스별 분류 (chat_report, write_report 등)

**`ai_usage_logs` 테이블**
- AI 서비스 사용량 상세 추적
- 요청/응답 토큰 수 개별 기록
- 세션별 사용량 분석 가능
- 서비스별 사용량 통계 제공

### Supabase 설정

#### 1. 프로젝트 생성
1. [Supabase](https://supabase.com)에서 새 프로젝트 생성
2. 프로젝트 URL과 API 키 확인

#### 2. 환경변수 설정
```env
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
```

#### 3. 데이터베이스 스키마

데이터베이스 테이블 구조는 `schema.sql` 파일에 정의되어 있습니다. Supabase의 SQL Editor에 해당 파일의 내용을 복사하여 실행하면 필요한 테이블이 생성됩니다.

**주요 특징:**
- **Row Level Security (RLS)**: 사용자별 데이터 접근 제어
- **인덱스**: 성능 최적화를 위한 인덱스 설정
- **트리거**: `updated_at` 자동 업데이트
- **외래 키 제약**: 데이터 무결성 보장

### Supabase 기능 활용

#### 1. 실시간 데이터베이스
- 사용자 활동 실시간 추적
- 채팅 히스토리 동기화
- 노트 실시간 업데이트

#### 2. Row Level Security (RLS)
- 사용자별 데이터 접근 제어
- 보안 강화 및 데이터 격리

#### 3. 자동 백업
- Supabase 자동 백업 기능 활용
- 데이터 손실 방지

### AI 통합
- Google GenAI를 통한 AI 모델 연동
- LangChain을 통한 프롬프트 관리
- ChromaDB를 통한 벡터 검색

### 문서 처리
- PDF 파일 업로드 및 처리
- 텍스트 추출 및 분석
- 이미지 추출

### 채팅 시스템
- 실시간 AI 채팅
- 대화 히스토리 관리
- 토큰 사용량 추적

## 📊 벡터 데이터베이스 구성

### 데이터 처리 파이프라인
ReportCoach는 과학 탐구 보고서를 수집하고 벡터 데이터베이스로 구성하는 자동화된 파이프라인을 제공합니다.

#### 1. 데이터 수집 (`scripts/`)
- **`report_crawler.py`**: 과학 탐구 보고서 크롤링
- **`download_pdfs.py`**: PDF 파일 다운로드
- **`extract_text.py`**: PDF에서 텍스트 추출
- **`extract_image.py`**: PDF에서 이미지 추출
- **`reformat_text.py`**: 텍스트 전처리 및 재구성
- **`convert_json.py`**: 데이터를 JSON 형식으로 변환
- **`build_chromadb.py`**: 변환된 JSON 데이터로 ChromaDB 벡터 데이터베이스 구축

#### 2. 실행 방법
```bash
cd backend/scripts
python main.py  # 전체 파이프라인 실행
```

#### 3. 데이터 구조
```
datas/
├── pdf_reports/      # 원본 PDF 파일
├── extracted_pdf/    # 추출된 텍스트/이미지
├── json_results/     # JSON 변환 결과
└── chroma_db/        # ChromaDB 벡터 DB
```

## 🤖 AI 프롬프트 시스템

### 프롬프트 역할별 설명

#### 1. 채팅 프롬프트 (`prompt_chat.txt`)
- **역할**: 보고서 분석 및 발전 컨설턴트
- **기능**: 
  - 보고서 내용 기반 사실 확인
  - 개선점 및 발전 아이디어 제안
  - 두 가지 모드 전환 (사실 확인 / 컨설팅)

#### 2. 검색 프롬프트 (`prompt_search.txt`)
- **역할**: 쿼리 분석 전문가
- **기능**:
  - 사용자 질문을 검색 쿼리로 변환
  - 우선순위 섹션 분석
  - 핵심 키워드 추출
  - 메타데이터 조건 파싱

#### 3. 리포트 작성 프롬프트 (`prompt_write.txt`)
- **역할**: 보고서 작성 컨설턴트
- **기능**:
  - 단계별 보고서 작성 가이드
  - 관련 보고서 정보 활용
  - 자연스러운 대화형 작성 지원

#### 4. 예시 질문 프롬프트 (`example_questions/`)
- **역할**: 사용자에게 제안할 예시 질문들의 프롬프트
- **기능**: 
  - 다양한 관점에서 보고서를 분석하는 질문들
  - 초등학생도 이해할 수 있는 쉬운 설명 (question_1.txt)
  - 실험 도구 및 재료 분석 (question_5.txt)
  - 총 12개의 다양한 예시 질문 프롬프트 제공

#### 5. 벡터 DB 구축용 프롬프트
- **`prompt_summary.txt`**: 요약보고서 json 생성
- **`prompt_report.txt`**: 상세보고서 json 생성
- **`prompt_reformat.txt`**: 텍스트 재구성

## 📚 API 문서

자세한 API 명세는 [API_SPECIFICATION.md](./API_SPECIFICATION.md)를 참조하세요.

## 📊 모니터링

### 로깅
- AI 사용량 로깅
- 사용자 활동 추적
- 에러 로깅

### 헬스체크
```bash
curl http://localhost:5000/health
```

## 🔍 디버깅

### 로그 확인
```bash
# 실시간 로그 확인
tail -f logs/app.log
```

### 데이터베이스 연결 확인
```bash
python -c "from app.supabase_client import supabase; print('DB 연결 성공')"
```

### 벡터 DB 상태 확인
```bash
python -c "from app.services.search_service import SearchService; print('ChromaDB 연결 성공')"
```

### 환경변수 설정
배포 시 다음 환경변수를 설정하세요:

```env
SUPABASE_URL=your_production_supabase_url
SUPABASE_KEY=your_production_supabase_key
GOOGLE_GENAI_API_KEY=your_production_google_genai_key
BACKEND_PORT=5000
```

