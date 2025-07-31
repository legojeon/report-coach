# ReportCoach

ReportCoach는 AI 기반 리포트 작성 및 분석 도구입니다. 사용자가 문서를 업로드하고 AI와 대화하며 리포트를 작성하고 분석할 수 있는 웹 애플리케이션입니다.

## 🚀 주요 기능

### 📝 리포트 작성 및 분석
- **AI 채팅**: 문서 내용에 대한 질문과 답변
- **리포트 작성**: AI 도움을 받아 리포트 작성
- **문서 검색**: 업로드된 문서에서 정보 검색
- **노트 작성**: 중요 내용을 노트로 저장

### 📊 문서 관리
- **PDF 뷰어**: 내장 PDF 뷰어로 문서 확인
- **문서 업로드**: PDF 파일 업로드 및 처리
- **문서 분석**: AI를 통한 문서 내용 분석

### 👤 사용자 관리
- **회원가입/로그인**: 사용자 인증 시스템
- **프로필 관리**: 사용자 정보 및 설정 관리
- **계획 관리**: 리포트 작성 계획 수립

## 🛠️ 기술 스택

### Backend
- **FastAPI**: Python 웹 프레임워크
- **Supabase**: 데이터베이스 및 인증
- **LangChain**: AI 모델 통합
- **ChromaDB**: 벡터 데이터베이스
- **Google GenAI**: AI 모델 서비스
- **Uvicorn**: ASGI 서버

### Frontend
- **React**: 사용자 인터페이스
- **Vite**: 빌드 도구
- **Tailwind CSS**: 스타일링
- **TipTap**: 리치 텍스트 에디터
- **React Router**: 라우팅
- **Axios**: HTTP 클라이언트

## 📁 프로젝트 구조

```
report-app/
├── backend/                 # FastAPI 백엔드
│   ├── app/
│   │   ├── routers/        # API 라우터
│   │   ├── services/       # 비즈니스 로직
│   │   ├── models/         # 데이터 모델
│   │   └── schemas/        # Pydantic 스키마
│   ├── prompts/            # AI 프롬프트
│   ├── scripts/            # 유틸리티 스크립트
│   └── main.py             # 애플리케이션 진입점
├── frontend/               # React 프론트엔드
│   ├── src/
│   │   ├── features/       # 페이지 컴포넌트
│   │   ├── components/     # 재사용 컴포넌트
│   │   └── services/       # API 서비스
│   └── public/             # 정적 파일
└── docker-compose.yml      # Docker 설정
```

## 🚀 설치 및 실행

### 1. 저장소 클론
```bash
git clone <repository-url>
cd report-app
```

### 2. Backend 설정

#### Python 가상환경 생성
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate     # Windows
```

#### 의존성 설치
```bash
pip install -r requirements.txt
```

#### 환경변수 설정
```bash
# backend/.env 파일 생성
cp .env.example .env
# .env 파일에 필요한 환경변수 설정
```

### 3. Frontend 설정

#### 의존성 설치
```bash
cd frontend
npm install
```

#### 환경변수 설정
```bash
# frontend/.env 파일 생성
cp .env.example .env
# .env 파일에 필요한 환경변수 설정
```

### 4. 데이터베이스 설정

#### Supabase 설정
1. Supabase 프로젝트 생성
2. 환경변수에 Supabase URL과 API 키 설정
3. 데이터베이스 스키마 설정

### 5. AI 모델 설정

#### Google GenAI 설정
1. Google AI Studio에서 API 키 생성
2. 환경변수에 API 키 설정

### 6. 애플리케이션 실행

#### 개발 모드
```bash
# Backend 실행
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 5000

# Frontend 실행 (새 터미널)
cd frontend
npm run dev
```

#### Docker를 사용한 실행
```bash
docker-compose up --build
```

## 📖 사용법

### 1. 회원가입/로그인
- 웹 애플리케이션에 접속하여 계정 생성
- 로그인 후 대시보드 접근

### 2. 문서 업로드
- PDF 파일을 업로드하여 문서 관리
- 업로드된 문서는 자동으로 분석됨

### 3. AI 채팅
- 문서에 대한 질문을 AI에게 물어보기
- 실시간으로 답변 받기

### 4. 리포트 작성
- AI 도움을 받아 리포트 작성
- TipTap 에디터를 사용한 리치 텍스트 편집

### 5. 노트 관리
- 중요 내용을 노트로 저장
- 노트 검색 및 관리

## 🔧 환경변수

### Backend (.env)
```env
# Supabase 설정
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# Google GenAI 설정
GOOGLE_GENAI_API_KEY=your_google_genai_key

# 서버 설정
BACKEND_PORT=5000
```

### Frontend (.env)
```env
# API 설정
VITE_API_URL=http://localhost:5000
```

## 🐳 Docker 배포

### Docker Compose로 실행
```bash
docker-compose up --build
```

### 개별 컨테이너 실행
```bash
# Backend
docker build -t reportcoach-backend ./backend
docker run -p 5000:5000 reportcoach-backend

# Frontend
docker build -t reportcoach-frontend ./frontend
docker run -p 3000:3000 reportcoach-frontend
```
