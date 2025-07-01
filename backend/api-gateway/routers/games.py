from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import httpx
import os

router = APIRouter()
security = HTTPBearer()

# Game Manager Service URL
GAME_MANAGER_URL = os.getenv("GAME_MANAGER_URL", "http://game-manager:8002")

class GameSession(BaseModel):
    puzzle_id: str
    game_mode: str  # 'single', 'challenge', 'multiplayer'

class GameSessionResponse(BaseModel):
    id: str
    puzzle_id: str
    game_mode: str
    status: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    completion_time: Optional[int]
    score: Optional[int]
    moves_count: int
    hints_used: int

class GameMove(BaseModel):
    piece_id: str
    x: float
    y: float
    rotation: Optional[float] = 0

class GameMoveResponse(BaseModel):
    id: int
    piece_id: str
    x: float
    y: float
    rotation: float
    is_correct: bool
    timestamp: datetime

class GameCompletion(BaseModel):
    completion_time: int
    final_score: int

class LeaderboardEntry(BaseModel):
    username: str
    score: int
    completion_time: int
    game_mode: str
    created_at: datetime

@router.post("/sessions", response_model=GameSessionResponse)
async def create_game_session(
    session_data: GameSession,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """게임 세션 생성"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{GAME_MANAGER_URL}/sessions",
                json=session_data.dict(),
                headers={"Authorization": f"Bearer {credentials.credentials}"},
                timeout=10.0
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not validate credentials"
                )
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Game service error"
                )
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Game service unavailable"
            )

@router.get("/sessions/{session_id}", response_model=GameSessionResponse)
async def get_game_session(
    session_id: str, 
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """게임 세션 조회"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{GAME_MANAGER_URL}/sessions/{session_id}",
                headers={"Authorization": f"Bearer {credentials.credentials}"},
                timeout=10.0
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not validate credentials"
                )
            elif response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Game session not found"
                )
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Game service error"
                )
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Game service unavailable"
            )

@router.post("/sessions/{session_id}/moves", response_model=GameMoveResponse)
async def make_move(
    session_id: str,
    move: GameMove,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """퍼즐 조각 이동 처리"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{GAME_MANAGER_URL}/sessions/{session_id}/moves",
                json=move.dict(),
                headers={"Authorization": f"Bearer {credentials.credentials}"},
                timeout=10.0
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not validate credentials"
                )
            elif response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Game session not found"
                )
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Game service error"
                )
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Game service unavailable"
            )

@router.post("/sessions/{session_id}/complete")
async def complete_game(
    session_id: str, 
    completion: GameCompletion,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """게임 완료 처리"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{GAME_MANAGER_URL}/sessions/{session_id}/complete",
                json=completion.dict(),
                headers={"Authorization": f"Bearer {credentials.credentials}"},
                timeout=10.0
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not validate credentials"
                )
            elif response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Game session not found"
                )
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Game service error"
                )
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Game service unavailable"
            )

@router.get("/leaderboard", response_model=List[LeaderboardEntry])
async def get_leaderboard(
    puzzle_id: Optional[str] = None,
    game_mode: Optional[str] = None,
    limit: int = 10
):
    """리더보드 조회"""
    async with httpx.AsyncClient() as client:
        try:
            params = {"limit": limit}
            if puzzle_id:
                params["puzzle_id"] = puzzle_id
            if game_mode:
                params["game_mode"] = game_mode

            response = await client.get(
                f"{GAME_MANAGER_URL}/leaderboard",
                params=params,
                timeout=10.0
            )

            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Game service error"
                )
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Game service unavailable"
            )

@router.get("/sessions", response_model=List[GameSessionResponse])
async def list_game_sessions(
    skip: int = 0,
    limit: int = 10,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """게임 세션 목록 조회"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{GAME_MANAGER_URL}/sessions",
                params={"skip": skip, "limit": limit},
                headers={"Authorization": f"Bearer {credentials.credentials}"},
                timeout=10.0
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not validate credentials"
                )
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Game service error"
                )
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Game service unavailable"
            )
