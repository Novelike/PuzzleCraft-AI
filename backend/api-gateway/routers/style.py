from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import Optional
import httpx
import os

router = APIRouter()
security = HTTPBearer()

# Style Transfer Service URL (올바른 포트 8007 사용)
STYLE_TRANSFER_URL = os.getenv("STYLE_TRANSFER_URL", "http://localhost:8007")

@router.post("/preview")
async def generate_style_preview(
    file: UploadFile = File(...),
    style_type: str = Form(default="classic"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """스타일 미리보기 생성"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            # 파일 내용을 읽어서 새로운 파일 객체 생성
            file_content = await file.read()
            files = {"file": (file.filename, file_content, file.content_type)}
            data = {"style_type": style_type, "preview_only": True}

            response = await client.post(
                f"{STYLE_TRANSFER_URL}/apply-style",
                files=files,
                data=data
            )

            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Style preview generation failed: {response.text}"
                )

        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Style transfer service unavailable: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Internal server error: {str(e)}"
            )

@router.post("/apply")
async def apply_style(
    file: UploadFile = File(...),
    style_type: str = Form(default="classic"),
    iterations: int = Form(default=300),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """스타일 적용"""
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            # 파일 내용을 읽어서 새로운 파일 객체 생성
            file_content = await file.read()
            files = {"file": (file.filename, file_content, file.content_type)}
            data = {"style_type": style_type, "iterations": iterations}

            response = await client.post(
                f"{STYLE_TRANSFER_URL}/apply-style",
                files=files,
                data=data
            )

            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Style application failed: {response.text}"
                )

        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Style transfer service unavailable: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Internal server error: {str(e)}"
            )

@router.get("/styles")
async def get_available_styles():
    """사용 가능한 스타일 목록 조회"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{STYLE_TRANSFER_URL}/styles")

            if response.status_code == 200:
                return response.json()
            else:
                # 서비스가 응답하지만 에러인 경우 기본 스타일 목록 반환
                return _get_default_styles()

        except httpx.RequestError:
            # 서비스가 없는 경우 기본 스타일 목록 반환
            return _get_default_styles()
        except Exception:
            # 기타 예외 발생 시 기본 스타일 목록 반환
            return _get_default_styles()

def _get_default_styles():
    """기본 스타일 목록 반환"""
    return {
        "styles": [
            {"id": "watercolor", "name": "수채화", "description": "부드럽고 투명한 수채화 스타일"},
            {"id": "cartoon", "name": "만화", "description": "밝고 생동감 있는 만화 스타일"},
            {"id": "pixel", "name": "픽셀아트", "description": "레트로한 8비트 픽셀 스타일"},
            {"id": "oil_painting", "name": "유화", "description": "클래식한 유화 스타일"},
            {"id": "sketch", "name": "스케치", "description": "연필로 그린 듯한 스케치 스타일"},
            {"id": "anime", "name": "애니메이션", "description": "일본 애니메이션 스타일"},
            {"id": "original", "name": "원본", "description": "스타일 변환 없이 원본 이미지 사용"}
        ]
    }
