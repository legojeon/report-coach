# ReportCoach API 명세서

## 📋 개요

ReportCoach API는 AI 기반 리포트 작성 및 분석 도구의 백엔드 API입니다.

**Base URL**: `http://localhost:5000/api/v1`

## 🔐 인증

대부분의 API는 JWT 토큰 인증이 필요합니다.
```
Authorization: Bearer <your_jwt_token>
```

## 📚 API 엔드포인트

### 🔑 인증 (Authentication)

| 메서드 | URL | 설명 |
|--------|-----|------|
| POST | `/auth/login` | 사용자 로그인 |
| POST | `/auth/register` | 사용자 회원가입 |
| GET | `/auth/me` | 현재 로그인한 사용자 정보 조회 |
| POST | `/auth/refresh` | 리프레시 토큰으로 새로운 액세스 토큰 발급 |
| POST | `/auth/logout` | 로그아웃 |

### 👥 사용자 관리 (Users)

| 메서드 | URL | 설명 |
|--------|-----|------|
| GET | `/users/` | 모든 사용자 조회 (관리자용) |
| GET | `/users/{user_id}` | 특정 사용자 조회 |
| PUT | `/users/{user_id}` | 사용자 정보 수정 |
| DELETE | `/users/{user_id}` | 사용자 계정 비활성화 |

### 💬 채팅 (Chat)

| 메서드 | URL | 설명 |
|--------|-----|------|
| POST | `/chat/chat` | 보고서와 AI 채팅 |
| GET | `/chat/history/{report_number}` | 채팅 히스토리 조회 |
| GET | `/chat/description/{report_number}` | 보고서 설명 조회 |
| GET | `/chat/title/{report_number}` | 보고서 제목 조회 |
| GET | `/chat/pdf/{pdf_type}/{report_number}` | 보고서 PDF 다운로드 |
| DELETE | `/chat/delete_file` | 업로드된 파일 삭제 |
| DELETE | `/chat/cleanup_session` | 채팅 세션 정리 |
| GET | `/chat/example/{question_number}` | 예시 질문 조회 |

### 📝 노트 (Notes)

| 메서드 | URL | 설명 |
|--------|-----|------|
| POST | `/notes/` | 새 노트 생성 |
| POST | `/notes/update_or_create` | 노트 업데이트 또는 생성 |
| GET | `/notes/` | 사용자의 모든 노트 조회 |
| GET | `/notes/report/{nttsn}` | 특정 보고서의 노트 조회 |
| GET | `/notes/{note_id}` | 특정 노트 조회 |
| PATCH | `/notes/deactivate/{note_id}` | 노트 비활성화 |

### 🔍 검색 (Search)

| 메서드 | URL | 설명 |
|--------|-----|------|
| POST | `/search/search` | 문서 검색 |
| POST | `/search/analyze` | 문서 분석 |
| GET | `/search/image/{report_number}` | 보고서 이미지 조회 |

### ✍️ 리포트 작성 (Write)

| 메서드 | URL | 설명 |
|--------|-----|------|
| POST | `/write/chat` | 리포트 작성 채팅 |
| GET | `/write/history` | 리포트 작성 채팅 히스토리 조회 |
| DELETE | `/write/session` | 리포트 작성 세션 정리 |

### 📊 로거 (Logger)

| 메서드 | URL | 설명 |
|--------|-----|------|
| GET | `/logger/ai-usage` | AI 사용량 조회 |
| GET | `/logger/history` | 사용자 검색/채팅 기록 조회 |

### 🏥 헬스체크 (Health Check)

| 메서드 | URL | 설명 |
|--------|-----|------|
| GET | `/health` | 서버 상태 확인 |
