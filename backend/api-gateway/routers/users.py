from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List
import httpx
import os

router = APIRouter()
security = HTTPBearer()

# Service URLs
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")
GAME_MANAGER_URL = os.getenv("GAME_MANAGER_URL", "http://localhost:8002")

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
async def get_user_stats(credentials: HTTPAuthorizationCredentials = Depends(security)):
	"""사용자 통계 조회"""
	async with httpx.AsyncClient() as client:
		try:
			# 먼저 현재 사용자 정보를 가져옴
			auth_response = await client.get(
				f"{AUTH_SERVICE_URL}/me",
				headers={"Authorization": f"Bearer {credentials.credentials}"},
				timeout=10.0
			)

			if auth_response.status_code != 200:
				raise HTTPException(
					status_code=status.HTTP_401_UNAUTHORIZED,
					detail="Could not validate credentials"
				)

			user_info = auth_response.json()
			user_id = user_info["id"]

			# 게임 매니저 서비스에서 사용자 통계 조회
			stats_response = await client.get(
				f"{GAME_MANAGER_URL}/stats",  # ✅ JWT 토큰으로 user_id 추출
				headers={"Authorization": f"Bearer {credentials.credentials}"},
				timeout=10.0
			)

			if stats_response.status_code == 200:
				return stats_response.json()
			elif stats_response.status_code == 404:
				# 사용자 통계가 없는 경우 기본값 반환
				return {
					"total_puzzles_completed": 0,
					"total_play_time": 0,
					"average_completion_time": 0.0,
					"best_score": 0,
					"current_streak": 0
				}
			else:
				raise HTTPException(
					status_code=stats_response.status_code,
					detail="Failed to fetch user stats"
				)

		except httpx.RequestError:
			raise HTTPException(
				status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
				detail="Service unavailable"
			)

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
