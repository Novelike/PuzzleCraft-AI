"""
PuzzleCraft AI - 퍼즐 생성 서비스
지능형 퍼즐 생성 엔진 FastAPI 서비스
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Union
import asyncio
import aiofiles
import logging
import json
import uuid
import os
import tempfile
from pathlib import Path
from datetime import datetime
import traceback

# 로컬 모듈 임포트
from puzzle_engine import IntelligentPuzzleEngine, PuzzleConfig, PuzzleType, DifficultyLevel
from ai_integration import AIServiceIntegrator, AIServiceType
from piece_generator import AdvancedPieceGenerator, PieceShape
from difficulty_analyzer import IntelligentDifficultyAnalyzer, ComplexityAnalysis, DifficultyProfile

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱 초기화
app = FastAPI(
    title="PuzzleCraft AI - 퍼즐 생성 서비스",
    description="지능형 AI 기반 퍼즐 생성 및 관리 시스템",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 서비스 인스턴스
puzzle_engine = IntelligentPuzzleEngine()
ai_integrator = AIServiceIntegrator()
piece_generator = AdvancedPieceGenerator()
difficulty_analyzer = IntelligentDifficultyAnalyzer()

# 임시 파일 저장 디렉토리
TEMP_DIR = Path(tempfile.gettempdir()) / "puzzlecraft_temp"
TEMP_DIR.mkdir(exist_ok=True)

# 퍼즐 생성 작업 상태 저장
puzzle_tasks = {}


# Pydantic 모델 정의
class PuzzleGenerationRequest(BaseModel):
    """퍼즐 생성 요청"""
    puzzle_type: str = Field(default="classic", description="퍼즐 타입 (classic, text, segmentation, style_enhanced, hybrid)")
    difficulty: str = Field(default="medium", description="난이도 (easy, medium, hard, expert)")
    piece_count: Optional[int] = Field(default=None, description="조각 수 (자동 계산시 None)")
    piece_shape: str = Field(default="classic", description="조각 모양 (classic, organic, geometric, irregular, curved)")
    target_audience: str = Field(default="general", description="타겟 사용자 (children, elderly, general, enthusiast, expert)")
    accessibility_requirements: List[str] = Field(default=[], description="접근성 요구사항")
    style_type: Optional[str] = Field(default=None, description="스타일 변환 타입 (watercolor, oil_painting, sketch 등)")
    enable_ai_optimization: bool = Field(default=True, description="AI 최적화 활성화")
    custom_settings: Dict[str, Any] = Field(default={}, description="사용자 정의 설정")


class UserProfile(BaseModel):
    """사용자 프로필"""
    skill_level: str = Field(default="intermediate", description="스킬 레벨")
    preferences: Dict[str, Any] = Field(default={}, description="사용자 선호도")
    accessibility_needs: List[str] = Field(default=[], description="접근성 요구사항")
    puzzle_history: List[Dict[str, Any]] = Field(default=[], description="퍼즐 이력")


class PuzzleTaskStatus(BaseModel):
    """퍼즐 작업 상태"""
    task_id: str
    status: str  # pending, processing, completed, failed
    progress: float  # 0.0 - 1.0
    current_step: str
    estimated_time_remaining: Optional[int] = None  # seconds
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# 헬스 체크 엔드포인트
@app.get("/health")
async def health_check():
    """서비스 상태 확인"""
    try:
        # AI 서비스 상태 확인
        ai_status = await ai_integrator.health_check_all_services()

        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "puzzle_engine": "active",
                "ai_integrator": "active",
                "piece_generator": "active",
                "difficulty_analyzer": "active"
            },
            "ai_services": ai_status,
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"헬스 체크 실패: {str(e)}")
        raise HTTPException(status_code=503, detail="서비스 상태 확인 실패")


# 이미지 업로드 및 복잡도 분석
@app.post("/api/v1/analyze/complexity")
async def analyze_image_complexity(file: UploadFile = File(...)):
    """이미지 복잡도 분석"""
    try:
        # 파일 검증
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="이미지 파일만 업로드 가능합니다")

        # 임시 파일 저장
        file_id = str(uuid.uuid4())
        temp_path = TEMP_DIR / f"{file_id}_{file.filename}"

        async with aiofiles.open(temp_path, 'wb') as f:
            content = await file.read()
            await f.write(content)

        # 복잡도 분석 수행
        complexity_analysis = await difficulty_analyzer.analyze_image_complexity(str(temp_path))

        # 임시 파일 정리
        os.unlink(temp_path)

        # 결과 반환 (numpy 배열은 제외)
        result = {
            "file_id": file_id,
            "filename": file.filename,
            "analysis": {
                "overall_score": complexity_analysis.overall_score,
                "edge_density": complexity_analysis.edge_density,
                "color_variance": complexity_analysis.color_variance,
                "texture_complexity": complexity_analysis.texture_complexity,
                "pattern_frequency": complexity_analysis.pattern_frequency,
                "contrast_ratio": complexity_analysis.contrast_ratio,
                "detail_level": complexity_analysis.detail_level,
                "dominant_colors": complexity_analysis.dominant_colors,
                "recommendations": complexity_analysis.recommendations
            },
            "timestamp": datetime.now().isoformat()
        }

        return result

    except Exception as e:
        logger.error(f"이미지 복잡도 분석 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"복잡도 분석 실패: {str(e)}")


# 난이도 프로필 생성
@app.post("/api/v1/analyze/difficulty-profile")
async def generate_difficulty_profile(
    complexity_analysis: Dict[str, Any],
    target_audience: str = "general",
    accessibility_requirements: List[str] = []
):
    """난이도 프로필 생성"""
    try:
        # ComplexityAnalysis 객체 재구성
        analysis = ComplexityAnalysis(
            overall_score=complexity_analysis["overall_score"],
            edge_density=complexity_analysis["edge_density"],
            color_variance=complexity_analysis["color_variance"],
            texture_complexity=complexity_analysis["texture_complexity"],
            pattern_frequency=complexity_analysis["pattern_frequency"],
            contrast_ratio=complexity_analysis["contrast_ratio"],
            detail_level=complexity_analysis["detail_level"],
            dominant_colors=complexity_analysis["dominant_colors"],
            complexity_map=None,  # 웹 API에서는 제외
            recommendations=complexity_analysis["recommendations"]
        )

        # 난이도 프로필 생성
        difficulty_profile = await difficulty_analyzer.generate_difficulty_profile(
            analysis, target_audience, accessibility_requirements
        )

        return {
            "difficulty_score": difficulty_profile.difficulty_score,
            "recommended_piece_count": difficulty_profile.recommended_piece_count,
            "estimated_solve_time": difficulty_profile.estimated_solve_time,
            "skill_level": difficulty_profile.skill_level,
            "challenge_factors": difficulty_profile.challenge_factors,
            "accessibility_score": difficulty_profile.accessibility_score,
            "adaptive_hints": difficulty_profile.adaptive_hints,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"난이도 프로필 생성 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"난이도 프로필 생성 실패: {str(e)}")


# 지능형 퍼즐 생성 (비동기)
@app.post("/api/v1/puzzles/generate-intelligent")
async def generate_intelligent_puzzle(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    request: str = None  # JSON 문자열로 전달
):
    """지능형 퍼즐 생성 (비동기)"""
    try:
        # 요청 파라미터 파싱
        if request:
            request_data = json.loads(request)
            puzzle_request = PuzzleGenerationRequest(**request_data)
        else:
            puzzle_request = PuzzleGenerationRequest()

        # 파일 검증
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="이미지 파일만 업로드 가능합니다")

        # 작업 ID 생성
        task_id = str(uuid.uuid4())

        # 임시 파일 저장
        temp_path = TEMP_DIR / f"{task_id}_{file.filename}"
        async with aiofiles.open(temp_path, 'wb') as f:
            content = await file.read()
            await f.write(content)

        # 작업 상태 초기화
        puzzle_tasks[task_id] = PuzzleTaskStatus(
            task_id=task_id,
            status="pending",
            progress=0.0,
            current_step="초기화 중",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        # 백그라운드 작업 시작
        background_tasks.add_task(
            process_puzzle_generation,
            task_id,
            str(temp_path),
            puzzle_request,
            file.filename
        )

        return {
            "task_id": task_id,
            "status": "accepted",
            "message": "퍼즐 생성 작업이 시작되었습니다",
            "check_status_url": f"/api/v1/puzzles/status/{task_id}"
        }

    except Exception as e:
        logger.error(f"퍼즐 생성 요청 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"퍼즐 생성 요청 실패: {str(e)}")


async def process_puzzle_generation(
    task_id: str,
    image_path: str,
    request: PuzzleGenerationRequest,
    filename: str
):
    """퍼즐 생성 백그라운드 처리"""
    try:
        # 작업 상태 업데이트 함수
        def update_status(progress: float, step: str, estimated_time: int = None):
            puzzle_tasks[task_id].progress = progress
            puzzle_tasks[task_id].current_step = step
            puzzle_tasks[task_id].estimated_time_remaining = estimated_time
            puzzle_tasks[task_id].updated_at = datetime.now()
            puzzle_tasks[task_id].status = "processing"

        # 1. 이미지 복잡도 분석 (20%)
        update_status(0.1, "이미지 복잡도 분석 중", 180)
        complexity_analysis = await difficulty_analyzer.analyze_image_complexity(image_path)

        # 2. 난이도 프로필 생성 (30%)
        update_status(0.2, "난이도 프로필 생성 중", 150)
        difficulty_profile = await difficulty_analyzer.generate_difficulty_profile(
            complexity_analysis,
            request.target_audience,
            request.accessibility_requirements
        )

        # 3. 퍼즐 설정 최적화 (40%)
        update_status(0.3, "퍼즐 설정 최적화 중", 120)

        # PuzzleConfig 생성
        puzzle_config = PuzzleConfig(
            puzzle_type=PuzzleType(request.puzzle_type.lower()),
            difficulty=DifficultyLevel(request.difficulty.lower()),
            piece_count=request.piece_count or difficulty_profile.recommended_piece_count,
            use_ai_enhancement=request.enable_ai_optimization,
            style_type=request.style_type
        )

        # 4. AI 서비스 통합 처리 (60%)
        update_status(0.4, "AI 서비스 처리 중", 90)

        if request.enable_ai_optimization:
            # 병렬 AI 분석 수행
            ai_results = await ai_integrator.process_parallel_ai_analysis(
                image_path,
                include_ocr=request.puzzle_type in ["text", "hybrid"],
                include_segmentation=request.puzzle_type in ["segmentation", "hybrid"],
                include_style_preview=request.style_type is not None,
                style_type=request.style_type or "watercolor"
            )

        # 5. 퍼즐 생성 (80%)
        update_status(0.6, "퍼즐 조각 생성 중", 60)
        puzzle_result = await puzzle_engine.generate_intelligent_puzzle(image_path, puzzle_config)

        # 6. 결과 최적화 및 메타데이터 생성 (100%)
        update_status(0.8, "결과 최적화 중", 30)

        # 최종 결과 구성
        final_result = {
            "puzzle_id": task_id,
            "filename": filename,
            "puzzle_data": puzzle_result,
            "complexity_analysis": {
                "overall_score": complexity_analysis.overall_score,
                "edge_density": complexity_analysis.edge_density,
                "color_variance": complexity_analysis.color_variance,
                "texture_complexity": complexity_analysis.texture_complexity,
                "recommendations": complexity_analysis.recommendations
            },
            "difficulty_profile": {
                "difficulty_score": difficulty_profile.difficulty_score,
                "recommended_piece_count": difficulty_profile.recommended_piece_count,
                "estimated_solve_time": difficulty_profile.estimated_solve_time,
                "skill_level": difficulty_profile.skill_level,
                "challenge_factors": difficulty_profile.challenge_factors,
                "adaptive_hints": difficulty_profile.adaptive_hints
            },
            "generation_config": {
                "puzzle_type": request.puzzle_type,
                "difficulty": request.difficulty,
                "piece_count": puzzle_config.piece_count,
                "piece_shape": request.piece_shape,
                "target_audience": request.target_audience,
                "ai_optimization_enabled": request.enable_ai_optimization
            },
            "created_at": datetime.now().isoformat()
        }

        # 작업 완료
        update_status(1.0, "완료")
        puzzle_tasks[task_id].status = "completed"
        puzzle_tasks[task_id].result = final_result

        # 임시 파일 정리
        try:
            os.unlink(image_path)
        except:
            pass

        logger.info(f"퍼즐 생성 완료: {task_id}")

    except Exception as e:
        logger.error(f"퍼즐 생성 처리 실패 {task_id}: {str(e)}")
        logger.error(traceback.format_exc())

        puzzle_tasks[task_id].status = "failed"
        puzzle_tasks[task_id].error_message = str(e)
        puzzle_tasks[task_id].updated_at = datetime.now()

        # 임시 파일 정리
        try:
            os.unlink(image_path)
        except:
            pass


# 퍼즐 생성 상태 확인
@app.get("/api/v1/puzzles/status/{task_id}")
async def get_puzzle_status(task_id: str):
    """퍼즐 생성 작업 상태 확인"""
    if task_id not in puzzle_tasks:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")

    task_status = puzzle_tasks[task_id]

    return {
        "task_id": task_status.task_id,
        "status": task_status.status,
        "progress": task_status.progress,
        "current_step": task_status.current_step,
        "estimated_time_remaining": task_status.estimated_time_remaining,
        "created_at": task_status.created_at.isoformat(),
        "updated_at": task_status.updated_at.isoformat(),
        "error_message": task_status.error_message
    }


# 퍼즐 결과 조회
@app.get("/api/v1/puzzles/result/{task_id}")
async def get_puzzle_result(task_id: str):
    """퍼즐 생성 결과 조회"""
    if task_id not in puzzle_tasks:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")

    task_status = puzzle_tasks[task_id]

    if task_status.status != "completed":
        raise HTTPException(status_code=400, detail="작업이 아직 완료되지 않았습니다")

    return task_status.result


# 퍼즐 미리보기 생성
@app.post("/api/v1/puzzles/preview")
async def generate_puzzle_preview(
    file: UploadFile = File(...),
    piece_count: int = 50,
    piece_shape: str = "classic"
):
    """퍼즐 미리보기 생성"""
    try:
        # 파일 검증
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="이미지 파일만 업로드 가능합니다")

        # 임시 파일 저장
        file_id = str(uuid.uuid4())
        temp_path = TEMP_DIR / f"{file_id}_{file.filename}"

        async with aiofiles.open(temp_path, 'wb') as f:
            content = await file.read()
            await f.write(content)

        # 간단한 퍼즐 설정으로 미리보기 생성
        config = PuzzleConfig(
            puzzle_type=PuzzleType.CLASSIC,
            difficulty=DifficultyLevel.MEDIUM,
            piece_count=piece_count,
            use_ai_enhancement=False
        )

        # 미리보기 생성 (AI 처리 없이)
        preview_result = await puzzle_engine.generate_intelligent_puzzle(str(temp_path), config)

        # 임시 파일 정리
        os.unlink(temp_path)

        return {
            "preview_id": file_id,
            "filename": file.filename,
            "piece_count": piece_count,
            "piece_shape": piece_shape,
            "preview_data": {
                "pieces": preview_result.get("pieces", []),
                "piece_count": len(preview_result.get("pieces", [])),
                "grid_info": preview_result.get("grid_info", {}),
                "metadata": preview_result.get("metadata", {})
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"퍼즐 미리보기 생성 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"미리보기 생성 실패: {str(e)}")


# 사용자 맞춤 최적화
@app.post("/api/v1/puzzles/optimize-for-user")
async def optimize_puzzle_for_user(
    complexity_analysis: Dict[str, Any],
    user_profile: UserProfile
):
    """사용자 맞춤 퍼즐 최적화"""
    try:
        # ComplexityAnalysis 객체 재구성
        analysis = ComplexityAnalysis(
            overall_score=complexity_analysis["overall_score"],
            edge_density=complexity_analysis["edge_density"],
            color_variance=complexity_analysis["color_variance"],
            texture_complexity=complexity_analysis["texture_complexity"],
            pattern_frequency=complexity_analysis["pattern_frequency"],
            contrast_ratio=complexity_analysis["contrast_ratio"],
            detail_level=complexity_analysis["detail_level"],
            dominant_colors=complexity_analysis["dominant_colors"],
            complexity_map=None,
            recommendations=complexity_analysis["recommendations"]
        )

        # 사용자 맞춤 최적화
        optimized_config = await difficulty_analyzer.optimize_difficulty_for_user(
            analysis, user_profile.dict()
        )

        return {
            "optimized_config": optimized_config,
            "user_profile": user_profile.dict(),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"사용자 맞춤 최적화 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"최적화 실패: {str(e)}")


# AI 서비스 상태 확인
@app.get("/api/v1/ai-services/status")
async def get_ai_services_status():
    """AI 서비스 상태 확인"""
    try:
        status = await ai_integrator.health_check_all_services()
        return {
            "ai_services": status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"AI 서비스 상태 확인 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI 서비스 상태 확인 실패: {str(e)}")


# 지원되는 기능 정보
@app.get("/api/v1/info/capabilities")
async def get_service_capabilities():
    """서비스 기능 정보"""
    return {
        "puzzle_types": [t.value.lower() for t in PuzzleType],
        "difficulty_levels": [d.value.lower() for d in DifficultyLevel],
        "piece_shapes": [s.value.lower() for s in PieceShape],
        "ai_services": [s.value for s in AIServiceType],
        "supported_formats": ["jpg", "jpeg", "png", "bmp", "tiff"],
        "max_file_size": "50MB",
        "features": {
            "intelligent_difficulty_analysis": True,
            "ai_optimization": True,
            "accessibility_support": True,
            "real_time_preview": True,
            "batch_processing": False,
            "user_customization": True
        },
        "version": "1.0.0"
    }


# 통계 정보
@app.get("/api/v1/stats/difficulty")
async def get_difficulty_statistics():
    """난이도 분석 통계"""
    return difficulty_analyzer.get_difficulty_statistics()


# 서비스 정리
@app.on_event("shutdown")
async def shutdown_event():
    """서비스 종료시 정리 작업"""
    logger.info("퍼즐 생성 서비스 종료 중...")

    # 임시 파일 정리
    try:
        for file_path in TEMP_DIR.glob("*"):
            if file_path.is_file():
                os.unlink(file_path)
    except Exception as e:
        logger.error(f"임시 파일 정리 실패: {str(e)}")

    logger.info("퍼즐 생성 서비스 종료 완료")


if __name__ == "__main__":
    import uvicorn

    # 개발 서버 실행
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8004,
        reload=True,
        log_level="info"
    )
