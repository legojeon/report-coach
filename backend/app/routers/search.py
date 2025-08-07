from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Dict, Any
import os
from ..schemas.search import SearchRequest, SearchResponse
from ..services.search_service import SearchService
from ..services.analysis_service import AnalysisService
from ..services.logger_service import LoggerService
from app.dependencies import get_current_user

security = HTTPBearer()
router = APIRouter()

@router.post("/search", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    current_user = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """문서 검색 API - 인증된 사용자만 사용 가능"""
    try:
        # LoggerService 인스턴스 생성
        logger_service = LoggerService()
        
        result = await SearchService.search_documents(
            query=request.query, 
            k=request.k, 
            user_id=str(current_user.id),
            logger_service=logger_service,
            auth_token=credentials.credentials  # 토큰 전달
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze")
async def analyze_documents(
    request: SearchRequest,
    current_user = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """문서 분석 API - 인증된 사용자만 사용 가능"""
    try:
        # LoggerService 인스턴스 생성
        logger_service = LoggerService()
        
        # k 값만큼만 검색 결과를 제한
        limited_results = request.search_results[:request.k] if request.k else request.search_results
        
        # 검색 결과에서 보고서 번호들을 추출 (문자열로 변환)
        report_numbers = [str(result['number']) for result in limited_results]
        
        # 분석 서비스를 통해 분석 수행
        analysis_result, usage_metadata = await AnalysisService.analyze_reports(
            query=request.query, 
            report_numbers=report_numbers,
            user_id=str(current_user.id),
            logger_service=logger_service,
            auth_token=credentials.credentials  # 토큰 전달
        )
        
        return {
            "query": request.query,
            "analysis": analysis_result,
            "search_results": limited_results,  # 제한된 결과 반환
            "usage_metadata": usage_metadata
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/image/{report_number}")
async def get_report_image(
    report_number: str
):
    """보고서 이미지 반환 API - 인증 없이 사용 가능"""
    try:
        # 이미지 파일 경로 확인
        from ..services.search_service import PATHS
        image_dir = os.path.join(PATHS["extracted_pdf"], "image")
        image_path = os.path.join(image_dir, f"{report_number}_image.png")
        
        if os.path.exists(image_path):
            return FileResponse(image_path, media_type="image/png")
        else:
            raise HTTPException(status_code=404, detail="이미지를 찾을 수 없습니다.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이미지 로드 중 오류가 발생했습니다: {str(e)}")

# PDF 반환 라우터 완전히 제거됨

 