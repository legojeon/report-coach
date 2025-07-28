from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.routers import api_router
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# 개발/운영 환경 구분
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

if ENVIRONMENT == "development":
    # 개발 환경 설정
    origins = [
        "http://localhost:5173"
    ]
    # 정적 파일 서빙 제거
else:
    # 운영 환경 설정 (도커)
    origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
    # 정적 파일 서빙 활성화

app = FastAPI(
    title="ReportCoach API",
    description="ReportCoach Backend API",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,  # Authorization 헤더 사용을 위해 True로 변경
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*", "Authorization", "Content-Type", "Accept"],
    expose_headers=["*"]
)

# API 라우터 등록
app.include_router(api_router, prefix="/api/v1")

# # ✅ 도커 기준 dist 경로로 정적 파일 mount
# DIST_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../frontend/dist"))
# print("📦 Serving static files from:", DIST_PATH)
# app.mount("/", StaticFiles(directory=DIST_PATH, html=True), name="static")

# @app.exception_handler(404)
# async def spa_fallback(request: Request, exc):
#     return FileResponse(os.path.join(DIST_PATH, "index.html"))

@app.get("/")
async def root():
    return {"message": "ReportCoach API is running!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("BACKEND_PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port) 