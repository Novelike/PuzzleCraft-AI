from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from typing import Optional
import httpx
import os

router = APIRouter()

# Style Transfer Service URL
STYLE_TRANSFER_URL = os.getenv("STYLE_TRANSFER_URL", "http://style-transfer:8005")

@router.post("/preview")
async def generate_style_preview(
    file: UploadFile = File(...),
    style_type: str = Form(default="classic")
):
    """스타일 미리보기 생성"""
    async with httpx.AsyncClient() as client:
        try:
            files = {"file": (file.filename, file.file, file.content_type)}
            data = {"style_type": style_type, "preview_only": True}
            
            response = await client.post(
                f"{STYLE_TRANSFER_URL}/apply-style",
                files=files,
                data=data,
                timeout=30.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Style preview generation failed"
                )
                
        except httpx.RequestError:
            raise HTTPException(
                status_code=503,
                detail="Style transfer service unavailable"
            )

@router.post("/apply")
async def apply_style(
    file: UploadFile = File(...),
    style_type: str = Form(default="classic")
):
    """스타일 적용"""
    async with httpx.AsyncClient() as client:
        try:
            files = {"file": (file.filename, file.file, file.content_type)}
            data = {"style_type": style_type}
            
            response = await client.post(
                f"{STYLE_TRANSFER_URL}/apply-style",
                files=files,
                data=data,
                timeout=60.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Style application failed"
                )
                
        except httpx.RequestError:
            raise HTTPException(
                status_code=503,
                detail="Style transfer service unavailable"
            )

@router.get("/styles")
async def get_available_styles():
    """사용 가능한 스타일 목록 조회"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{STYLE_TRANSFER_URL}/styles",
                timeout=10.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                # 서비스가 없는 경우 기본 스타일 목록 반환
                return {
                    "styles": [
                        {"id": "classic", "name": "Classic", "description": "Classic art style"},
                        {"id": "modern", "name": "Modern", "description": "Modern art style"},
                        {"id": "abstract", "name": "Abstract", "description": "Abstract art style"},
                        {"id": "vintage", "name": "Vintage", "description": "Vintage art style"}
                    ]
                }
                
        except httpx.RequestError:
            # 서비스가 없는 경우 기본 스타일 목록 반환
            return {
                "styles": [
                    {"id": "classic", "name": "Classic", "description": "Classic art style"},
                    {"id": "modern", "name": "Modern", "description": "Modern art style"},
                    {"id": "abstract", "name": "Abstract", "description": "Abstract art style"},
                    {"id": "vintage", "name": "Vintage", "description": "Vintage art style"}
                ]
            }