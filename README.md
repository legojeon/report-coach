# ReportCoach: AI 기반 리포트 작성 및 분석 플랫폼

ReportCoach는 과학전람회 보고서 데이터로 구축된 벡터 DB를 기반으로, AI를 활용하여 리포트를 검색, 분석하고 작성을 돕는 웹 애플리케이션입니다.

사용자는 AI와의 상호작용을 통해 아이디어를 발전시키고 완성도 높은 결과물을 만들 수 있습니다.

이 서비스는 2011년 이후 과학전람회 보고서 전체 데이터를 벡터화(embedding)해 구축한 DB를 기반으로 동작합니다.

서비스 바로가기: [rc.coco.io.kr](http://rc.coco.io.kr)

---

## 🌟 주요 기능

### 📝 리포트 작성 및 분석
- **AI 채팅**: 문서 내용에 기반한 심층적인 질의응답이 가능합니다.
- **리포트 작성**: AI의 가이드를 받으며 단계별로 리포트를 완성할 수 있습니다.
- **리포트 검색**: 질문을 기반으로 가장 관련도 높은 보고서를 찾아주고, 여러 보고서의 내용을 종합하여 요약 설명해줍니다.
- **RAG 기반 검색**: [과학전람회 보고서 사이트](https://www.science.go.kr/mps/1079/bbs/423/moveBbsNttList.do)에 공개된 **2011년 이후 모든 보고서 데이터를 벡터 DB(ChromaDB)에 임베딩**하고, LangChain을 활용해 검색-증강-생성(Search-Augmented Generation) 방식을 구현했습니다.
- **노트 작성**: 분석 중 발견한 중요한 내용 혹은 작성중인 보고서를 노트로 저장하고 관리합니다.

### 📊 문서 및 사용자 관리
- **PDF 뷰어**: 웹에서 바로 문서를 확인하고 분석할 수 있습니다.
- **안전한 사용자 인증**: JWT 토큰 기반의 안정적인 회원가입 및 로그인 시스템을 제공합니다.
- **프로필 및 계획 관리**: 사용자 정보를 관리하고 리포트 작성 계획을 체계적으로 수립합니다

---

## 🖼️ 실행 화면

<div align="center">

<table>
  <tr>
    <td align="center">
      <img src="https://github.com/legojeon/report-coach/blob/main/screen_shot/main_page.png" width="400px"/><br>
      <b>메인 페이지</b><br>
      사이트 접속 초기 화면
    </td>
    <td align="center">
      <img src="https://github.com/legojeon/report-coach/blob/main/screen_shot/search_page.png" width="400px"/><br>
      <b>검색 화면</b><br>
      벡터DB 기반 검색 결과
    </td>
  </tr>
  <tr>
    <td align="center">
      <img src="https://github.com/legojeon/report-coach/blob/main/screen_shot/report_page.png" width="400px"/><br>
      <b>보고서 분석 화면</b><br>
      AI와 질의응답하며 보고서 분석
    </td>
    <td align="center">
      <img src="https://github.com/legojeon/report-coach/blob/main/screen_shot/write_page.png" width="400px"/><br>
      <b>보고서 작성 화면</b><br>
      AI 가이드와 함께 보고서 작성
    </td>
  </tr>
  <tr>
    <td align="center">
      <img src="https://github.com/legojeon/report-coach/blob/main/screen_shot/note_page.png" width="400px"/><br>
      <b>노트 페이지</b><br>
      저장된 보고서 및 대화 내역 조회
    </td>
    <td align="center">
      <img src="https://github.com/legojeon/report-coach/blob/main/screen_shot/plan_page.png" width="400px"/><br>
      <b>멤버십 페이지</b><br>
      플랜 구독 및 해지
    </td>
  </tr>
</table>

</div>


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

### 🛠️ Vector DB & RAG Architecture
- [과학전람회 보고서 사이트](https://www.science.go.kr/mps/1079/bbs/423/moveBbsNttList.do)에서 **2011년 이후 모든 보고서 메타데이터 및 PDF를 수집**
- 보고서 본문을 **문단 단위로 쪼개고 임베딩(embedding)하여 ChromaDB에 저장**
- **LangChain**을 통해 벡터 검색과 문서 retrieval 파이프라인 구성
- **Google GenAI** 모델이 검색된 문서를 기반으로 자연스러운 답변을 생성 (RAG pipeline)

---

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

---

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

---

## 📄 참고 자료
- **[backend 디렉토리](https://github.com/legojeon/report-coach/tree/main/backend)** 에서 API 명세, 벡터 DB 구축 과정, 
  과학전람회 보고서 크롤링 스크립트, 데이터 전처리 코드 등을 확인할 수 있습니다.

