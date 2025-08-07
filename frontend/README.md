# ReportCoach Frontend

ReportCoach의 프론트엔드 웹 애플리케이션입니다. React와 Vite를 기반으로 구축되었으며, 사용자 친화적인 인터페이스를 제공합니다.

## 🛠️ 기술 스택

- **React**: 사용자 인터페이스
- **Vite**: 빌드 도구
- **Tailwind CSS**: 스타일링
- **TipTap**: 리치 텍스트 에디터
- **React Router**: 라우팅
- **Axios**: HTTP 클라이언트
- **PDF.js**: PDF 뷰어

## 📁 프로젝트 구조

```
frontend/
├── src/
│   ├── features/           # 페이지 컴포넌트
│   │   ├── LoginPage.jsx   # 로그인 페이지
│   │   ├── SignupPage.jsx  # 회원가입 페이지
│   │   ├── MainPage.jsx    # 메인 페이지
│   │   ├── ChatPage.jsx    # 채팅 페이지
│   │   ├── WritePage.jsx   # 리포트 작성 페이지
│   │   ├── SearchPage.jsx  # 검색 페이지
│   │   ├── NotePage.jsx    # 노트 페이지
│   │   ├── ProfilePage.jsx # 프로필 페이지
│   │   └── HealthPage.jsx  # 헬스체크 페이지
│   ├── components/         # 재사용 컴포넌트
│   │   └── TiptapEditor.jsx # 리치 텍스트 에디터
│   ├── services/           # API 서비스
│   │   ├── api.js          # API 클라이언트
│   │   └── auth.js         # 인증 서비스
│   ├── assets/             # 정적 자산
│   ├── App.jsx             # 메인 앱 컴포넌트
│   └── main.jsx            # 앱 진입점
├── public/                 # 정적 파일
├── package.json            # Node.js 의존성
└── vite.config.js         # Vite 설정
```

## 🚀 설치 및 실행

### 1. 의존성 설치

```bash
cd frontend
npm install
```

### 2. 환경변수 설정

`.env` 파일을 생성하고 다음 환경변수를 설정하세요:

```env
# API 설정
VITE_API_URL=http://localhost:5000
VITE_API_BASE_URL=http://localhost:5000/api/v1
```

### 3. 개발 서버 실행

```bash
npm run dev
```

개발 서버는 기본적으로 `http://localhost:5173`에서 실행됩니다.

### 4. 프로덕션 빌드

```bash
npm run build
```

빌드된 파일은 `dist/` 디렉토리에 생성됩니다.

## 🔧 주요 기능

### 인증 시스템
- 로그인/회원가입 페이지
- JWT 토큰 관리
- 자동 로그인 상태 유지

### 채팅 시스템
- 실시간 AI 채팅 인터페이스
- 대화 히스토리 표시
- 메시지 전송 및 수신

### 리포트 작성
- TipTap 기반 리치 텍스트 에디터
- AI 도움을 받은 리포트 작성
- 실시간 저장 및 편집

### 문서 관리
- PDF 파일 업로드
- 내장 PDF 뷰어
- 문서 검색 및 필터링

### 노트 시스템
- 중요 내용 노트 저장
- 노트 검색 및 관리
- 노트 편집 및 삭제

### 사용자 관리
- 프로필 정보 수정
- 사용자 설정 관리
- 활동 히스토리 확인


### 환경변수 설정
배포 시 다음 환경변수를 설정하세요:

```env
VITE_API_URL=https://your-backend-domain.com
VITE_API_BASE_URL=https://your-backend-domain.com/api/v1
```

## 📱 브라우저 지원

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## 🔧 개발 가이드

### 새로운 페이지 추가
1. `src/features/` 디렉토리에 새 컴포넌트 생성
2. `src/App.jsx`에 라우트 추가
3. 필요한 API 서비스 추가

### 컴포넌트 스타일링
- Tailwind CSS 클래스 사용
- CSS 모듈 또는 styled-components 사용 가능
- 일관된 디자인 시스템 준수

### API 통신
- `src/services/api.js`에서 API 클라이언트 관리
- Axios 인터셉터를 통한 토큰 관리
- 에러 핸들링 및 로딩 상태 관리