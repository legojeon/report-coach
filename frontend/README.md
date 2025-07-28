# ReportCoach Frontend

React + Vite + Tailwind CSS 기반의 프론트엔드 애플리케이션입니다.

## 설치 및 실행

### 1. 의존성 설치
```bash
npm install
```

### 2. 개발 서버 실행
```bash
npm run dev
```

개발 서버는 기본적으로 http://localhost:5173 에서 실행됩니다.

### 3. 빌드
```bash
npm run build
```

### 4. 빌드 결과 미리보기
```bash
npm run preview
```

## 프로젝트 구조

```
frontend/
├── public/                 # 정적 파일
├── src/
│   ├── components/         # React 컴포넌트
│   ├── pages/             # 페이지 컴포넌트
│   ├── services/          # API 서비스
│   ├── hooks/             # 커스텀 훅
│   ├── utils/             # 유틸리티 함수
│   ├── App.jsx            # 메인 앱 컴포넌트
│   ├── main.jsx           # 앱 진입점
│   ├── index.css          # 글로벌 스타일
│   └── App.css            # 앱 스타일
├── tailwind.config.js     # Tailwind CSS 설정
├── postcss.config.js      # PostCSS 설정
├── package.json           # 프로젝트 설정
└── vite.config.js         # Vite 설정
```

## 주요 기능

- **모던 UI/UX**: Tailwind CSS를 활용한 반응형 디자인
- **컴포넌트 기반**: 재사용 가능한 React 컴포넌트
- **라우팅**: React Router를 통한 SPA 라우팅
- **API 통신**: Axios를 통한 백엔드 API 연동
- **개발 환경**: Vite를 통한 빠른 개발 환경

## 기술 스택

- **React 18**: 사용자 인터페이스 라이브러리
- **Vite**: 빠른 빌드 도구
- **Tailwind CSS**: 유틸리티 우선 CSS 프레임워크
- **React Router**: 클라이언트 사이드 라우팅
- **Axios**: HTTP 클라이언트

## 개발 가이드

### 컴포넌트 작성
- 함수형 컴포넌트 사용
- Tailwind CSS 클래스 활용
- 재사용 가능한 컴포넌트 설계

### 스타일링
- Tailwind CSS 유틸리티 클래스 우선 사용
- 커스텀 CSS는 최소화
- 반응형 디자인 고려

### API 통신
- Axios를 통한 HTTP 요청
- 에러 핸들링 구현
- 로딩 상태 관리
