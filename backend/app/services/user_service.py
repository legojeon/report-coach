from app.models.user import User
from app.schemas.user import UserUpdate
from app.supabase_client import supabase
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

class UserService:
    async def get_all_users(self) -> List[User]:
        """모든 사용자 조회"""
        try:
            response = supabase.table("users").select("*").execute()
            users = [User(**user_data) for user_data in response.data]
            return users
        except Exception as e:
            logger.error(f"Failed to get all users: {str(e)}")
            raise Exception(f"Failed to get all users: {str(e)}")
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """사용자 ID로 사용자 조회"""
        try:
            response = supabase.table("users").select("*").eq("id", user_id).execute()
            print("get user data, user_id:",user_id)
            print("response:", response)
            if response.data:
                user_data = response.data[0]
                
                # 현재 로그인한 사용자라면 email 포함
                try:
                    current_user = supabase.auth.get_user()
                    if current_user.user and str(current_user.user.id) == user_id:
                        user_data["email"] = current_user.user.email
                except:
                    # 로그인하지 않은 상태에서는 email 없이 반환
                    pass
                
                return User(**user_data)
            return None
        except Exception as e:
            logger.error(f"Failed to get user by id {user_id}: {str(e)}")
            raise Exception(f"Failed to get user by id: {str(e)}")
    
    async def update_user(self, user_id: str, user_update: UserUpdate) -> Optional[User]:
        """사용자 정보 업데이트"""
        try:
            # 현재 사용자 정보 조회
            current_user = await self.get_user_by_id(user_id)
            print("current_user:", current_user)
            if not current_user:
                return None
            
            logger.info(f"업데이트 전 사용자 정보: id={current_user.id}, is_membership={current_user.is_membership}")
            logger.info(f"업데이트할 데이터: {user_update.dict(exclude_unset=True)}")
            
            # 업데이트할 데이터 준비
            update_data = user_update.dict(exclude_unset=True)
            
            # Supabase에서 업데이트
            response = supabase.table("users").update(update_data).eq("id", user_id).execute()
            
            if response.data:
                updated_user = User(**response.data[0])
                logger.info(f"업데이트 후 사용자 정보: id={updated_user.id}, is_membership={updated_user.is_membership}")
                return updated_user
            return None
            
        except Exception as e:
            logger.error(f"Failed to update user {user_id}: {str(e)}")
            raise Exception(f"Failed to update user: {str(e)}")
    
    async def delete_user(self, user_id: str) -> bool:
        """사용자 삭제"""
        try:
            response = supabase.table("users").delete().eq("id", user_id).execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Failed to delete user {user_id}: {str(e)}")
            raise Exception(f"Failed to delete user: {str(e)}")
    
    async def deactivate_user(self, user_id: str) -> bool:
        """사용자 계정 비활성화 (is_active = False)"""
        try:
            response = supabase.table("users").update({"is_active": False}).eq("id", user_id).execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Failed to deactivate user {user_id}: {str(e)}")
            raise Exception(f"Failed to deactivate user: {str(e)}") 