from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.routers import api_router
import os
import time
from datetime import datetime
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse


origins = [
    "http://localhost:5173"
]

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

# API 라우터 등록 (정적 파일보다 먼저)
app.include_router(api_router, prefix="/api/v1")

# API 엔드포인트들 (정적 파일보다 먼저)
@app.get("/health")
async def health_check():
    """서버 상태 체크 API"""
    try:
        # 기본 정보
        health_info = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "ReportCoach",
            "version": "1.0.0",
        }
        return health_info
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# 정적 파일 마운트 (API 라우트 이후에)
DIST_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../frontend/dist"))
print("📦 Serving static files from:", DIST_PATH)
app.mount("/", StaticFiles(directory=DIST_PATH, html=True), name="static")

@app.exception_handler(404)
async def spa_fallback(request: Request, exc):
    return FileResponse(os.path.join(DIST_PATH, "index.html"))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("BACKEND_PORT", "5000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port) 