from fastapi import APIRouter
from .auth import router as auth_router
from .users import router as users_router
from .search import router as search_router
from .chat import router as chat_router
from .logger import router as logger_router
from .notes import router as notes_router
from .write import router as write_router

api_router = APIRouter()

# 라우터 등록
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(search_router, prefix="/search", tags=["search"])
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
api_router.include_router(logger_router, prefix="/logger", tags=["logger"])
api_router.include_router(notes_router, prefix="/notes", tags=["notes"])
api_router.include_router(write_router, prefix="/write", tags=["write"]) 