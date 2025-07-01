from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Request
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
import httpx
import json
import os
from datetime import datetime

router = APIRouter()
security = HTTPBearer(auto_error=False)  # Make auth optional for some endpoints

# Service URLs
PUZZLE_GENERATOR_URL = os.getenv("PUZZLE_GENERATOR_URL", "http://localhost:8004")

class PuzzleCreate(BaseModel):
    piece_count: int = 100
    difficulty_level: int = 3
    allow_rotation: bool = True
    style_type: Optional[str] = None

class PuzzleResponse(BaseModel):
    id: str
    original_image_url: str
    processed_image_url: Optional[str]
    piece_count: int
    difficulty_level: int
    style_type: Optional[str]
    created_at: str

class PuzzleGenerationRequest(BaseModel):
    puzzle_type: str = "classic"
    difficulty: str = "medium"
    piece_count: Optional[int] = None
    piece_shape: str = "classic"
    target_audience: str = "general"
    accessibility_requirements: List[str] = []
    style_type: Optional[str] = None
    enable_ai_optimization: bool = True
    custom_settings: Dict[str, Any] = {}

# Proxy endpoints to puzzle-generator service
@router.post("/analyze/complexity")
async def analyze_complexity(file: UploadFile = File(...)):
    """이미지 복잡도 분석 - puzzle-generator 서비스로 프록시"""
    try:
        # Forward the file to puzzle-generator service
        files = {"file": (file.filename, await file.read(), file.content_type)}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{PUZZLE_GENERATOR_URL}/api/v1/analyze/complexity",
                files=files
            )

            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Puzzle generator service error: {response.text}"
                )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Cannot connect to puzzle generator service: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze/difficulty-profile")
async def generate_difficulty_profile(
    complexity_analysis: Dict[str, Any],
    target_audience: str = "general",
    accessibility_requirements: List[str] = []
):
    """난이도 프로필 생성 - puzzle-generator 서비스로 프록시"""
    try:
        payload = {
            "complexity_analysis": complexity_analysis,
            "target_audience": target_audience,
            "accessibility_requirements": accessibility_requirements
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{PUZZLE_GENERATOR_URL}/api/v1/analyze/difficulty-profile",
                json=payload
            )

            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Puzzle generator service error: {response.text}"
                )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Cannot connect to puzzle generator service: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-intelligent")
async def generate_intelligent_puzzle(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    request: Optional[str] = None
):
    """지능형 퍼즐 생성 - puzzle-generator 서비스로 프록시"""
    try:
        files = {"file": (file.filename, await file.read(), file.content_type)}
        data = {"request": request} if request else {}

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{PUZZLE_GENERATOR_URL}/api/v1/puzzles/generate-intelligent",
                files=files,
                data=data
            )

            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Puzzle generator service error: {response.text}"
                )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Cannot connect to puzzle generator service: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{task_id}")
async def get_puzzle_status(task_id: str):
    """퍼즐 생성 상태 확인 - puzzle-generator 서비스로 프록시"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{PUZZLE_GENERATOR_URL}/api/v1/puzzles/status/{task_id}"
            )

            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Puzzle generator service error: {response.text}"
                )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Cannot connect to puzzle generator service: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/result/{task_id}")
async def get_puzzle_result(task_id: str):
    """퍼즐 생성 결과 조회 - puzzle-generator 서비스로 프록시"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{PUZZLE_GENERATOR_URL}/api/v1/puzzles/result/{task_id}"
            )

            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Puzzle generator service error: {response.text}"
                )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Cannot connect to puzzle generator service: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Legacy endpoints for backward compatibility
@router.post("/generate", response_model=PuzzleResponse)
async def generate_puzzle(
    file: UploadFile = File(...),
    puzzle_data: PuzzleCreate = Depends(),
    token: str = Depends(security)
):
    """레거시 퍼즐 생성 엔드포인트"""
    puzzle_id = str(uuid.uuid4())
    return {
        "id": puzzle_id,
        "original_image_url": f"uploads/{file.filename}",
        "processed_image_url": f"processed/{puzzle_id}.jpg",
        "piece_count": puzzle_data.piece_count,
        "difficulty_level": puzzle_data.difficulty_level,
        "style_type": puzzle_data.style_type,
        "created_at": datetime.now().isoformat()
    }

@router.get("/{puzzle_id}", response_model=PuzzleResponse)
async def get_puzzle(puzzle_id: str, token: str = Depends(security)):
    """퍼즐 정보 조회"""
    return {
        "id": puzzle_id,
        "original_image_url": f"uploads/sample.jpg",
        "processed_image_url": f"processed/{puzzle_id}.jpg",
        "piece_count": 100,
        "difficulty_level": 3,
        "style_type": "watercolor",
        "created_at": datetime.now().isoformat()
    }

@router.get("/", response_model=List[PuzzleResponse])
async def list_puzzles(
    skip: int = 0,
    limit: int = 10,
    token: str = Depends(security)
):
    """퍼즐 목록 조회"""
    return []

@router.delete("/{puzzle_id}")
async def delete_puzzle(puzzle_id: str, token: str = Depends(security)):
    """퍼즐 삭제"""
    return {"message": f"Puzzle {puzzle_id} deleted successfully"}
