# 베이스 이미지
FROM python:3.10-slim

# 작업 디렉토리 설정 (컨테이너 내에서 사용할 디렉토리)
WORKDIR /app

# backend 전체 복사 (requirements.txt 포함)
COPY backend/ ./backend

# frontend build된 dist 폴더만 복사
COPY frontend/dist ./frontend/dist

# requirements 설치
# pip 자체를 최신 버전으로 업그레이드하는 것이 좋습니다.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r backend/requirements.txt

# PYTHONPATH 설정
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/backend

# FastAPI 실행 (app 모듈 인식되게끔 backend.main 지정)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]