from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID

class User(BaseModel):
    """
    사용자 모델 (Supabase Auth용)
    - id: UUID (auth.users 참조)
    - email: 이메일 (auth.users에서 가져옴, Optional)
    - username: 사용자명 (중복 허용)
    - affiliation: 소속
    - is_membership: 멤버쉽 여부
    - is_active: 활성화 여부
    - created_at: 생성일
    - updated_at: 수정일
    """
    id: UUID
    email: Optional[str] = None  # auth.users에서 가져온 email
    username: Optional[str] = None
    affiliation: Optional[str] = None
    is_membership: bool = False
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        # 추가 필드 허용 (email이 없어도 에러 안나게)
        extra = "ignore" 