from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uvicorn
import os
import tempfile
import shutil
from pathlib import Path
import logging

from segmentation import ImageSegmentation

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="PuzzleCraft AI - Image Segmentation Service",
    description="Image segmentation service for object detection and puzzle piece generation",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize segmentation processor
try:
    segmentation_processor = ImageSegmentation()
    logger.info("Segmentation processor initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize segmentation processor: {e}")
    segmentation_processor = None

# Create uploads directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Pydantic models
class SegmentationResponse(BaseModel):
    objects_found: int
    masks: List[List]
    labels: List[int]
    scores: List[float]
    boxes: List[List[float]]
    class_names: List[str]
    segmented_objects: List[Dict]
    image_info: Dict[str, Any]
    error: Optional[str] = None

class PuzzlePiecesResponse(BaseModel):
    puzzle_type: str
    total_pieces: int
    pieces: List[Dict]
    segmentation_info: Optional[Dict] = None
    grid_info: Optional[Dict] = None
    error: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    model_loaded: bool

@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        service="Image Segmentation Service",
        version="1.0.0",
        model_loaded=segmentation_processor is not None
    )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Detailed health check"""
    return HealthResponse(
        status="healthy" if segmentation_processor is not None else "unhealthy",
        service="Image Segmentation Service",
        version="1.0.0",
        model_loaded=segmentation_processor is not None
    )

@app.post("/segment-objects", response_model=SegmentationResponse)
async def segment_objects(
    file: UploadFile = File(...),
    confidence_threshold: float = Form(0.5)
):
    """Segment objects in the uploaded image"""
    if segmentation_processor is None:
        raise HTTPException(status_code=503, detail="Segmentation model not loaded")

    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")

    if not 0.1 <= confidence_threshold <= 1.0:
        raise HTTPException(status_code=400, detail="Confidence threshold must be between 0.1 and 1.0")

    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name

        # Process with segmentation
        result = segmentation_processor.segment_objects(tmp_path, confidence_threshold)

        # Clean up temporary file
        os.unlink(tmp_path)

        return SegmentationResponse(**result)

    except Exception as e:
        logger.error(f"Object segmentation error: {e}")
        raise HTTPException(status_code=500, detail=f"Segmentation processing failed: {str(e)}")

@app.post("/create-puzzle-pieces", response_model=PuzzlePiecesResponse)
async def create_puzzle_pieces(
    file: UploadFile = File(...),
    piece_count: int = Form(20)
):
    """Create puzzle pieces from the uploaded image using segmentation"""
    if segmentation_processor is None:
        raise HTTPException(status_code=503, detail="Segmentation model not loaded")

    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")

    if not 5 <= piece_count <= 200:
        raise HTTPException(status_code=400, detail="Piece count must be between 5 and 200")

    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name

        # Create puzzle pieces
        result = segmentation_processor.create_puzzle_pieces(tmp_path, piece_count)

        # Clean up temporary file
        os.unlink(tmp_path)

        return PuzzlePiecesResponse(**result)

    except Exception as e:
        logger.error(f"Puzzle piece creation error: {e}")
        raise HTTPException(status_code=500, detail=f"Puzzle piece creation failed: {str(e)}")

@app.post("/segment-and-create-puzzle")
async def segment_and_create_puzzle(
    file: UploadFile = File(...),
    piece_count: int = Form(20),
    confidence_threshold: float = Form(0.5)
):
    """Combined endpoint: segment objects and create puzzle pieces"""
    if segmentation_processor is None:
        raise HTTPException(status_code=503, detail="Segmentation model not loaded")

    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")

    if not 5 <= piece_count <= 200:
        raise HTTPException(status_code=400, detail="Piece count must be between 5 and 200")

    if not 0.1 <= confidence_threshold <= 1.0:
        raise HTTPException(status_code=400, detail="Confidence threshold must be between 0.1 and 1.0")

    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name

        # First, segment objects
        segmentation_result = segmentation_processor.segment_objects(tmp_path, confidence_threshold)

        # Then, create puzzle pieces
        puzzle_result = segmentation_processor.create_puzzle_pieces(tmp_path, piece_count)

        # Clean up temporary file
        os.unlink(tmp_path)

        # Combine results
        combined_result = {
            "segmentation": segmentation_result,
            "puzzle": puzzle_result,
            "processing_info": {
                "confidence_threshold": confidence_threshold,
                "requested_pieces": piece_count,
                "actual_pieces": puzzle_result.get('total_pieces', 0)
            }
        }

        return JSONResponse(content=combined_result)

    except Exception as e:
        logger.error(f"Combined processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Combined processing failed: {str(e)}")

@app.get("/supported-classes")
async def get_supported_classes():
    """Get list of supported object classes"""
    if segmentation_processor is None:
        raise HTTPException(status_code=503, detail="Segmentation model not loaded")

    try:
        return {
            "total_classes": len(segmentation_processor.class_names),
            "classes": segmentation_processor.class_names,
            "model": "Mask R-CNN ResNet50 FPN",
            "dataset": "COCO"
        }
    except Exception as e:
        logger.error(f"Error getting supported classes: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get supported classes: {str(e)}")

@app.get("/model-info")
async def get_model_info():
    """Get information about the segmentation model"""
    if segmentation_processor is None:
        raise HTTPException(status_code=503, detail="Segmentation model not loaded")

    try:
        import torch
        return {
            "model_name": "Mask R-CNN ResNet50 FPN",
            "framework": "PyTorch",
            "pytorch_version": torch.__version__,
            "device": str(segmentation_processor.device),
            "cuda_available": torch.cuda.is_available(),
            "total_classes": len(segmentation_processor.class_names),
            "input_format": "RGB images",
            "output_format": "Masks, bounding boxes, labels, scores"
        }
    except Exception as e:
        logger.error(f"Error getting model info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get model info: {str(e)}")

@app.post("/analyze-image-complexity")
async def analyze_image_complexity(file: UploadFile = File(...)):
    """Analyze image complexity for puzzle difficulty estimation"""
    if segmentation_processor is None:
        raise HTTPException(status_code=503, detail="Segmentation model not loaded")

    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")

    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name

        # Segment objects to analyze complexity
        segmentation_result = segmentation_processor.segment_objects(tmp_path, 0.3)  # Lower threshold for more objects

        # Clean up temporary file
        os.unlink(tmp_path)

        # Analyze complexity
        objects_found = segmentation_result['objects_found']
        unique_classes = len(set(segmentation_result['class_names']))

        # Determine complexity level
        if objects_found >= 10 and unique_classes >= 5:
            complexity = "high"
            recommended_pieces = 50
        elif objects_found >= 5 and unique_classes >= 3:
            complexity = "medium"
            recommended_pieces = 30
        else:
            complexity = "low"
            recommended_pieces = 20

        return {
            "complexity_level": complexity,
            "objects_detected": objects_found,
            "unique_classes": unique_classes,
            "recommended_piece_count": recommended_pieces,
            "detected_classes": segmentation_result['class_names'],
            "analysis_details": {
                "high_complexity": "10+ objects, 5+ classes",
                "medium_complexity": "5+ objects, 3+ classes", 
                "low_complexity": "< 5 objects or < 3 classes"
            }
        }

    except Exception as e:
        logger.error(f"Image complexity analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"Complexity analysis failed: {str(e)}")

@app.post("/segment-subject-background")
async def segment_subject_background(
    file: UploadFile = File(...),
    confidence_threshold: float = Form(0.7)
):
    """고급 피사체/배경 분리 기능"""
    if segmentation_processor is None:
        raise HTTPException(status_code=503, detail="Segmentation model not loaded")

    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")

    if not 0.1 <= confidence_threshold <= 1.0:
        raise HTTPException(status_code=400, detail="Confidence threshold must be between 0.1 and 1.0")

    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name

        # Perform subject/background separation
        result = segmentation_processor.segment_subject_background(tmp_path, confidence_threshold)

        # Clean up temporary file
        os.unlink(tmp_path)

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"Subject/background separation error: {e}")
        raise HTTPException(status_code=500, detail=f"Subject/background separation failed: {str(e)}")

@app.post("/generate-intelligent-puzzle")
async def generate_intelligent_puzzle(
    file: UploadFile = File(...),
    piece_count: int = Form(50),
    subject_background_ratio: float = Form(0.6)
):
    """지능형 퍼즐 피스 생성 (피사체/배경 기반)"""
    if segmentation_processor is None:
        raise HTTPException(status_code=503, detail="Segmentation model not loaded")

    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")

    if not 10 <= piece_count <= 500:
        raise HTTPException(status_code=400, detail="Piece count must be between 10 and 500")

    if not 0.1 <= subject_background_ratio <= 0.9:
        raise HTTPException(status_code=400, detail="Subject/background ratio must be between 0.1 and 0.9")

    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name

        # Generate intelligent puzzle pieces
        result = segmentation_processor.generate_intelligent_puzzle_pieces(
            tmp_path, piece_count, subject_background_ratio
        )

        # Clean up temporary file
        os.unlink(tmp_path)

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"Intelligent puzzle generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Intelligent puzzle generation failed: {str(e)}")

@app.post("/analyze-subject-background")
async def analyze_subject_background(file: UploadFile = File(...)):
    """피사체/배경 분석 및 권장사항 제공"""
    if segmentation_processor is None:
        raise HTTPException(status_code=503, detail="Segmentation model not loaded")

    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")

    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name

        # Perform subject/background separation
        separation_result = segmentation_processor.segment_subject_background(tmp_path, 0.7)

        # Clean up temporary file
        os.unlink(tmp_path)

        if separation_result['success']:
            quality = separation_result['separation_quality']
            main_subject = separation_result.get('main_subject_info', {})

            # Generate recommendations
            recommendations = []

            if quality['quality_score'] < 0.5:
                recommendations.append("이미지의 피사체가 명확하지 않아 자동 분할이 어려울 수 있습니다.")

            if quality['subject_ratio'] < 0.2:
                recommendations.append("피사체가 너무 작습니다. 피사체가 더 크게 나온 이미지를 권장합니다.")
            elif quality['subject_ratio'] > 0.8:
                recommendations.append("배경이 너무 적습니다. 배경이 더 많이 보이는 이미지를 권장합니다.")

            # Puzzle difficulty estimation
            if quality['quality_score'] >= 0.8:
                puzzle_difficulty = "easy"
                recommended_pieces = 30
            elif quality['quality_score'] >= 0.6:
                puzzle_difficulty = "medium"
                recommended_pieces = 50
            else:
                puzzle_difficulty = "hard"
                recommended_pieces = 70

            return {
                "analysis_success": True,
                "separation_quality": quality,
                "main_subject": {
                    "class_name": main_subject.get('class_name', 'unknown'),
                    "confidence": main_subject.get('score', 0),
                    "center_position": main_subject.get('center', [0, 0])
                },
                "puzzle_recommendations": {
                    "difficulty": puzzle_difficulty,
                    "recommended_piece_count": recommended_pieces,
                    "subject_piece_ratio": 0.6 if quality['subject_ratio'] > 0.3 else 0.4
                },
                "optimization_tips": recommendations + quality.get('recommendations', [])
            }
        else:
            return {
                "analysis_success": False,
                "error": separation_result.get('error', 'Unknown error'),
                "fallback_recommendations": {
                    "difficulty": "medium",
                    "recommended_piece_count": 40,
                    "use_grid_based": True
                }
            }

    except Exception as e:
        logger.error(f"Subject/background analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/health-advanced")
async def health_check_advanced():
    """고급 기능 포함 헬스 체크"""
    try:
        if segmentation_processor is None:
            return {
                "status": "unhealthy",
                "message": "Segmentation model not loaded",
                "features": {
                    "basic_segmentation": False,
                    "subject_background_separation": False,
                    "intelligent_puzzle_generation": False
                }
            }

        # Test basic functionality
        import torch
        device_info = {
            "device": str(segmentation_processor.device),
            "cuda_available": torch.cuda.is_available(),
            "model_loaded": True
        }

        return {
            "status": "healthy",
            "message": "All advanced features available",
            "features": {
                "basic_segmentation": True,
                "subject_background_separation": True,
                "intelligent_puzzle_generation": True,
                "complexity_analysis": True
            },
            "device_info": device_info,
            "supported_classes": len(segmentation_processor.class_names)
        }

    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "unhealthy",
            "message": f"Health check failed: {str(e)}",
            "features": {
                "basic_segmentation": False,
                "subject_background_separation": False,
                "intelligent_puzzle_generation": False
            }
        }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8006,
        reload=True,
        log_level="info"
    )
