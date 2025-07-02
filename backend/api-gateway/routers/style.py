import io
import logging
import os
import time

import httpx
from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import Optional

from urllib.parse import quote

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer(auto_error=False)  # Make auth optional for style preview

# Style Transfer Service URL (올바른 포트 8007 사용)
STYLE_TRANSFER_URL = os.getenv("STYLE_TRANSFER_URL", "http://localhost:8007")
API_BASE_URL = os.getenv("API_BASE_URL", "https://puzzle.novelike.dev")


@router.post("/preview")
async def generate_style_preview(
		file: UploadFile = File(...),
		style_type: str = Form(default="classic"),
		credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
	"""스타일 미리보기 생성"""
	logger.info(f"Generating style preview: {style_type} for file: {file.filename}")

	start_time = time.time()

	async with httpx.AsyncClient(timeout=60.0) as client:
		try:
			# 파일 내용을 읽어서 새로운 파일 객체 생성
			file_content = await file.read()
			files = {"file": (file.filename, file_content, file.content_type)}

			logger.info(f"Sending request to style-transfer service: {STYLE_TRANSFER_URL}/preview-style")
			response = await client.post(
				f"{STYLE_TRANSFER_URL}/preview-style",
				files=files,
				data={"style_type": style_type}
			)

			logger.info(f"Style-transfer service response: {response.status_code}")

			if response.status_code == 200:
				result = response.json()
				logger.info(f"Style preview successful: {result.get('success', False)}")

				# 🔧 응답 형식을 프론트엔드 기대 형식으로 변환
				if result.get('success'):
					preview_filename = result.get('preview_filename')
					processing_time = time.time() - start_time

					# API Gateway를 통한 이미지 URL 생성
					preview_url = f"{API_BASE_URL}/api/v1/style/image/{preview_filename}"

					return {
						"preview_url": preview_url,
						"style_type": result.get('style_type'),
						"processing_time": round(processing_time, 2),
						"success": True
					}
				else:
					return result
			else:
				error_detail = response.text
				logger.error(f"Style preview failed with status {response.status_code}: {error_detail}")
				raise HTTPException(
					status_code=response.status_code,
					detail=f"Style preview generation failed: {error_detail}"
				)

		except httpx.RequestError as e:
			logger.error(f"Style transfer service connection error: {str(e)}")
			raise HTTPException(
				status_code=503,
				detail=f"Style transfer service unavailable: {str(e)}"
			)
		except HTTPException:
			raise
		except Exception as e:
			logger.error(f"Unexpected error in style preview: {str(e)}")
			raise HTTPException(
				status_code=500,
				detail=f"Internal server error: {str(e)}"
			)


# 🆕 이미지 서빙을 위한 프록시 엔드포인트 추가
@router.get("/image/{filename}")
async def get_style_image(filename: str):
	"""스타일 변환된 이미지 서빙"""
	async with httpx.AsyncClient(timeout=30.0) as client:
		try:
			response = await client.get(f"{STYLE_TRANSFER_URL}/download/{filename}")

			if response.status_code == 200:
				# 파일명을 URL 인코딩하여 안전하게 처리
				safe_filename = quote(filename, safe='')
				return StreamingResponse(
					io.BytesIO(response.content),
					media_type="image/jpeg",
					headers={"Content-Disposition": f"inline; filename*=UTF-8''{safe_filename}"}
				)
			else:
				raise HTTPException(status_code=404, detail="Image not found")

		except httpx.RequestError as e:
			logger.error(f"Error fetching image from style service: {e}")
			raise HTTPException(status_code=503, detail="Style service unavailable")


@router.post("/apply")
async def apply_style(
		file: UploadFile = File(...),
		style_type: str = Form(default="classic"),
		iterations: int = Form(default=300),
		credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
	"""스타일 적용"""
	start_time = time.time()

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
				result = response.json()

				# 🔧 응답 형식을 프론트엔드 기대 형식으로 변환
				if result.get('success'):
					output_filename = os.path.basename(result.get('output_path', ''))
					processing_time = time.time() - start_time

					styled_image_url = f"{API_BASE_URL}/api/v1/style/image/{output_filename}"

					return {
						"styled_image_url": styled_image_url,
						"style_type": result.get('style_type'),
						"processing_time": round(processing_time, 2),
						"task_id": result.get('task_id')
					}
				else:
					return result
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
			response = await client.get(f"{STYLE_TRANSFER_URL}/available-styles")

			if response.status_code == 200:
				style_data = response.json()
				# Normalize the response format to match expected format
				normalized_styles = []
				for style in style_data.get('styles', []):
					normalized_style = {
						'id': style.get('name', style.get('id', '')),  # Use 'name' as 'id' if available
						'name': style.get('name', style.get('id', '')),
						'description': style.get('description', '')
					}
					normalized_styles.append(normalized_style)

				return {
					'total_styles': style_data.get('total_styles', len(normalized_styles)),
					'styles': normalized_styles,
					'style_names': style_data.get('style_names', [s['id'] for s in normalized_styles])
				}
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
	"""기본 스타일 목록 반환 (검증된 스타일만)"""
	return {
		"styles": [
			{"id": "watercolor", "name": "수채화", "description": "부드럽고 투명한 수채화 스타일"},
			{"id": "cartoon", "name": "만화", "description": "밝고 생동감 있는 만화 스타일"},
			{"id": "pixel_art", "name": "픽셀아트", "description": "레트로한 8비트 픽셀 스타일"},
			{"id": "sketch", "name": "스케치", "description": "연필로 그린 듯한 스케치 스타일"},
			{"id": "anime", "name": "애니메이션", "description": "일본 애니메이션 스타일"}
		]
	}
