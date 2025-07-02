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

# 인메모리 퍼즐 저장소 추가
puzzle_storage = {}


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
				result = response.json()
				if 'puzzle_id' in result:
					puzzle_storage[result['puzzle_id']] = result
				return result
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


@router.post("/preview")
async def generate_puzzle_preview(
		file: UploadFile = File(...),
		piece_count: int = 50,
		piece_shape: str = "classic"
):
	"""퍼즐 미리보기 생성 - puzzle-generator 서비스로 프록시"""
	try:
		# Forward the file and parameters to puzzle-generator service
		files = {"file": (file.filename, await file.read(), file.content_type)}
		data = {
			"piece_count": str(piece_count),
			"piece_shape": piece_shape
		}

		async with httpx.AsyncClient(timeout=60.0) as client:
			response = await client.post(
				f"{PUZZLE_GENERATOR_URL}/api/v1/puzzles/preview",
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


@router.get("/{puzzle_id}")  # 인증 제거
async def get_puzzle(puzzle_id: str):
	"""퍼즐 정보 조회 - 실제 데이터 반환"""
	import logging
	logger = logging.getLogger(__name__)

	logger.info(f"🔍 퍼즐 조회 요청: {puzzle_id}")

	# 1. 인메모리 저장소에서 조회
	if puzzle_id in puzzle_storage:
		logger.info(f"✅ 인메모리 저장소에서 퍼즐 발견: {puzzle_id}")
		puzzle_data = puzzle_storage[puzzle_id]

		# 이미 변환된 데이터인지 확인
		if "pieces" in puzzle_data and isinstance(puzzle_data["pieces"], list):
			if len(puzzle_data["pieces"]) > 0 and "imageData" in puzzle_data["pieces"][0]:
				logger.info(f"✅ 이미 변환된 퍼즐 데이터 반환: {puzzle_id}")
				return puzzle_data

		# 변환이 필요한 경우
		logger.info(f"🔄 퍼즐 데이터 변환 중: {puzzle_id}")
		transformed_data = transform_puzzle_data(puzzle_data)
		# 변환된 데이터를 저장소에 업데이트
		puzzle_storage[puzzle_id] = transformed_data
		return transformed_data

	# 2. 퍼즐 생성기에서 직접 조회 시도 (task_id로)
	logger.info(f"🔄 퍼즐 생성기에서 조회 시도: {puzzle_id}")
	try:
		async with httpx.AsyncClient(timeout=15.0) as client:
			# result 엔드포인트로 조회
			response = await client.get(
				f"{PUZZLE_GENERATOR_URL}/api/v1/puzzles/result/{puzzle_id}"
			)

			if response.status_code == 200:
				logger.info(f"✅ 퍼즐 생성기에서 데이터 조회 성공: {puzzle_id}")
				puzzle_data = response.json()

				# 프론트엔드 형식에 맞게 변환
				transformed_data = transform_puzzle_data(puzzle_data)

				# 저장소에 캐시
				puzzle_storage[puzzle_id] = transformed_data
				logger.info(f"💾 퍼즐 데이터 저장소에 캐시됨: {puzzle_id}")

				return transformed_data
			else:
				logger.warning(f"⚠️ 퍼즐 생성기 응답 오류: {response.status_code} - {puzzle_id}")

	except httpx.RequestError as e:
		logger.error(f"❌ 퍼즐 생성기 연결 실패: {str(e)} - {puzzle_id}")
	except Exception as e:
		logger.error(f"❌ 퍼즐 조회 중 예외 발생: {str(e)} - {puzzle_id}")

	# 3. 상태 확인 엔드포인트로 조회 시도
	logger.info(f"🔄 상태 확인 엔드포인트로 조회 시도: {puzzle_id}")
	try:
		async with httpx.AsyncClient(timeout=10.0) as client:
			response = await client.get(
				f"{PUZZLE_GENERATOR_URL}/api/v1/puzzles/status/{puzzle_id}"
			)

			if response.status_code == 200:
				status_data = response.json()
				logger.info(f"📊 퍼즐 상태: {status_data.get('status', 'unknown')} - {puzzle_id}")

				# 완료된 경우 결과 조회 재시도
				if status_data.get("status") == "completed" and "result" in status_data:
					puzzle_data = status_data["result"]
					transformed_data = transform_puzzle_data(puzzle_data)
					puzzle_storage[puzzle_id] = transformed_data
					logger.info(f"✅ 상태 확인을 통한 퍼즐 데이터 조회 성공: {puzzle_id}")
					return transformed_data
				elif status_data.get("status") == "processing":
					logger.info(f"⏳ 퍼즐 생성 진행 중: {puzzle_id}")
					raise HTTPException(status_code=202, detail="Puzzle is still being generated")
				elif status_data.get("status") == "failed":
					logger.error(f"💥 퍼즐 생성 실패: {puzzle_id}")
					raise HTTPException(status_code=500, detail="Puzzle generation failed")

	except httpx.RequestError as e:
		logger.error(f"❌ 상태 확인 연결 실패: {str(e)} - {puzzle_id}")
	except HTTPException:
		raise  # HTTPException은 그대로 전파
	except Exception as e:
		logger.error(f"❌ 상태 확인 중 예외 발생: {str(e)} - {puzzle_id}")

	# 4. 모든 조회 방법 실패
	logger.error(f"❌ 퍼즐을 찾을 수 없음: {puzzle_id}")
	logger.info(f"📋 현재 저장소의 퍼즐 ID 목록: {list(puzzle_storage.keys())}")

	raise HTTPException(
		status_code=404, 
		detail=f"Puzzle not found: {puzzle_id}. Available puzzles: {len(puzzle_storage)}"
	)


def transform_puzzle_data(puzzle_result):
	"""퍼즐 생성 결과를 프론트엔드 형식으로 변환"""
	# 기본 퍼즐 데이터 추출
	pieces = puzzle_result.get("pieces", [])

	# 각 피스 데이터를 프론트엔드 형식으로 변환
	transformed_pieces = []
	for piece in pieces:
		transformed_piece = {
			"id": piece.get("id", f"piece_{len(transformed_pieces)}"),
			"x": piece.get("x", 0),
			"y": piece.get("y", 0),
			"width": piece.get("width", piece.get("piece_width", 100)),
			"height": piece.get("height", piece.get("piece_height", 100)),
			"rotation": piece.get("rotation", 0),
			"imageData": piece.get("imageData", piece.get("image_data", "")),
			"correctPosition": {
				"x": piece.get("correct_x", piece.get("x", 0)),
				"y": piece.get("correct_y", piece.get("y", 0))
			},
			"currentPosition": {
				"x": piece.get("current_x", piece.get("x", 0)),
				"y": piece.get("current_y", piece.get("y", 0))
			},
			"isPlaced": piece.get("isPlaced", piece.get("is_placed", False)),
			"isSelected": piece.get("isSelected", piece.get("is_selected", False)),
			"edges": piece.get("edges", {
				"top": "flat",
				"right": "flat", 
				"bottom": "flat",
				"left": "flat"
			}),
			"difficulty": piece.get("difficulty", "medium"),
			"region": piece.get("region", "background")
		}
		transformed_pieces.append(transformed_piece)

	# 메타데이터 변환
	metadata = puzzle_result.get("metadata", {})
	transformed_metadata = {
		"originalImageUrl": metadata.get("original_image_url", puzzle_result.get("original_image_url")),
		"styleType": metadata.get("style_type", puzzle_result.get("style_type")),
		"pieceCount": len(transformed_pieces),
		"createdAt": metadata.get("created_at", puzzle_result.get("created_at", datetime.now().isoformat()))
	}

	return {
		"pieces": transformed_pieces,
		"imageUrl": puzzle_result.get("image_url", puzzle_result.get("imageUrl", "")),
		"difficulty": puzzle_result.get("difficulty", "medium"),
		"estimatedSolveTime": puzzle_result.get("estimated_solve_time", puzzle_result.get("estimatedSolveTime", 30)),
		"metadata": transformed_metadata
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
