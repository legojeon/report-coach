from fastapi import APIRouter, HTTPException, Depends
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from app.services.user_service import UserService
from uuid import UUID
from app.dependencies import get_current_user

router = APIRouter()

@router.get("/", response_model=list[UserResponse])
async def get_users():
    """모든 사용자 조회"""
    try:
        user_service = UserService()
        users = await user_service.get_all_users()
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """특정 사용자 조회"""
    try:
        user_service = UserService()
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str, 
    user_update: UserUpdate,
    current_user = Depends(get_current_user)
):
    """사용자 정보 수정"""
    try:
        # 본인의 정보만 수정 가능하도록 검증
        if str(current_user.id) != user_id:
            raise HTTPException(status_code=403, detail="Can only update own user information")
        
        print("now, edit the user data")
        update_data = user_update.dict(exclude_unset=True)
        print('update_data:', update_data)  # ← 추가
        user_service = UserService()
        user = await user_service.update_user(user_id, user_update)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user = Depends(get_current_user)
):
    """사용자 삭제 (비활성화)"""
    try:
        # 본인의 계정만 삭제 가능하도록 검증
        if str(current_user.id) != user_id:
            raise HTTPException(status_code=403, detail="Can only delete own account")
        
        user_service = UserService()
        success = await user_service.deactivate_user(user_id)
        if not success:
            raise HTTPException(status_code=404, detail="User not found")
        return {"message": "Account deactivated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 