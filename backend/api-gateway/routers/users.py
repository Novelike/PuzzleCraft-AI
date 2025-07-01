from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter()
security = HTTPBearer()

class UserProfile(BaseModel):
    username: str
    email: str
    profile_image_url: Optional[str] = None
    level: int = 1
    total_points: int = 0

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    profile_image_url: Optional[str] = None

class UserStats(BaseModel):
    total_puzzles_completed: int
    total_play_time: int
    average_completion_time: float
    best_score: int
    current_streak: int

@router.get("/profile", response_model=UserProfile)
async def get_user_profile(token: str = Depends(security)):
    # TODO: 사용자 프로필 조회 로직 구현
    return {
        "username": "test_user",
        "email": "test@example.com",
        "profile_image_url": None,
        "level": 5,
        "total_points": 2500
    }

@router.put("/profile", response_model=UserProfile)
async def update_user_profile(
    user_data: UserUpdate,
    token: str = Depends(security)
):
    # TODO: 사용자 프로필 업데이트 로직 구현
    return {
        "username": user_data.username or "test_user",
        "email": user_data.email or "test@example.com",
        "profile_image_url": user_data.profile_image_url,
        "level": 5,
        "total_points": 2500
    }

@router.get("/stats", response_model=UserStats)
async def get_user_stats(token: str = Depends(security)):
    # TODO: 사용자 통계 조회 로직 구현
    return {
        "total_puzzles_completed": 25,
        "total_play_time": 18000,  # 5시간 (초 단위)
        "average_completion_time": 720.0,  # 12분 (초 단위)
        "best_score": 1500,
        "current_streak": 3
    }

@router.get("/achievements")
async def get_user_achievements(token: str = Depends(security)):
    # TODO: 사용자 업적 조회 로직 구현
    return [
        {
            "id": "first_puzzle",
            "name": "First Puzzle",
            "description": "Complete your first puzzle",
            "unlocked": True,
            "unlocked_at": "2024-01-01T00:00:00Z"
        },
        {
            "id": "speed_demon",
            "name": "Speed Demon",
            "description": "Complete a puzzle in under 5 minutes",
            "unlocked": False,
            "unlocked_at": None
        }
    ]

@router.get("/history")
async def get_user_history(
    skip: int = 0,
    limit: int = 10,
    token: str = Depends(security)
):
    # TODO: 사용자 게임 히스토리 조회 로직 구현
    return []

@router.delete("/account")
async def delete_user_account(token: str = Depends(security)):
    # TODO: 사용자 계정 삭제 로직 구현
    return {"message": "Account deleted successfully"}