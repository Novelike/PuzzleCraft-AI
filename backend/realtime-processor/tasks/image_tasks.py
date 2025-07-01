"""
이미지 처리 관련 Celery 태스크
이미지 리사이징, 압축, 썸네일 생성, 포맷 변환 등의 작업을 처리
"""

import asyncio
import json
import logging
import time
import uuid
import base64
import io
import os
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime
import requests
from PIL import Image, ImageFilter, ImageEnhance, ImageOps
import numpy as np

from ..celery_app import image_task, celery_app
from ..progress_tracker import ProgressTracker
from ..notification_service import NotificationService

logger = logging.getLogger(__name__)

# 이미지 처리 설정
IMAGE_CONFIG = {
    "max_file_size": int(os.getenv("MAX_IMAGE_SIZE", "10485760")),  # 10MB
    "supported_formats": ["JPEG", "PNG", "GIF", "BMP", "TIFF", "WEBP"],
    "thumbnail_sizes": {
        "small": (150, 150),
        "medium": (300, 300),
        "large": (600, 600)
    },
    "quality_levels": {
        "low": 60,
        "medium": 80,
        "high": 95
    }
}

# 서비스 URL 설정
API_GATEWAY_URL = "http://api-gateway:8000"
STORAGE_SERVICE_URL = "http://storage-service:8000"


@image_task(name="process_image_task")
def process_image_task(
    self,
    image_data: Union[str, bytes],
    operations: List[Dict[str, Any]],
    user_id: str,
    session_id: str,
    output_format: Optional[str] = None,
    quality: Optional[int] = None
) -> Dict[str, Any]:
    """
    이미지 처리 태스크
    
    Args:
        image_data: 이미지 데이터 (base64 또는 bytes)
        operations: 처리 작업 목록
        user_id: 사용자 ID
        session_id: 세션 ID
        output_format: 출력 포맷
        quality: 출력 품질
    
    Returns:
        처리된 이미지 결과
    """
    task_id = self.request.id
    logger.info(f"Starting image processing: {task_id}, operations: {len(operations)}")
    
    try:
        # 진행률 추적 시작
        progress_tracker = ProgressTracker()
        asyncio.run(progress_tracker.start_task(
            task_id,
            "image_processing",
            {
                "operations_count": len(operations),
                "user_id": user_id,
                "session_id": session_id
            }
        ))
        
        # 1단계: 이미지 로드 및 검증
        asyncio.run(progress_tracker.update_step(
            task_id, "image_loading", 10, "Loading and validating image"
        ))
        
        image = _load_and_validate_image(image_data)
        
        # 2단계: 이미지 처리 작업 실행
        processed_image = image
        total_operations = len(operations)
        
        for i, operation in enumerate(operations):
            progress = 20 + (60 * (i + 1) / total_operations)
            asyncio.run(progress_tracker.update_step(
                task_id, f"operation_{i}", progress, f"Executing {operation['type']}"
            ))
            
            processed_image = _execute_image_operation(processed_image, operation)
        
        # 3단계: 출력 포맷 변환
        asyncio.run(progress_tracker.update_step(
            task_id, "format_conversion", 85, "Converting output format"
        ))
        
        output_image = _convert_output_format(
            processed_image, output_format, quality
        )
        
        # 4단계: 결과 저장
        asyncio.run(progress_tracker.update_step(
            task_id, "result_saving", 95, "Saving processed image"
        ))
        
        save_result = _save_processed_image(
            output_image, user_id, session_id, task_id
        )
        
        # 최종 결과 준비
        final_result = {
            "processing_id": str(uuid.uuid4()),
            "task_id": task_id,
            "original_info": {
                "size": image.size,
                "format": image.format,
                "mode": image.mode
            },
            "processed_info": {
                "size": output_image.size,
                "format": output_image.format,
                "mode": output_image.mode
            },
            "operations_applied": operations,
            "save_location": save_result["location"],
            "metadata": {
                "user_id": user_id,
                "session_id": session_id,
                "processed_at": datetime.utcnow().isoformat(),
                "processing_time": time.time() - self.request.called_directly
            }
        }
        
        # 완료
        asyncio.run(progress_tracker.complete_step(
            task_id, "image_processing", {"processing_id": final_result["processing_id"]}
        ))
        
        # 알림 발송
        notification_service = NotificationService()
        asyncio.run(notification_service.send_notification(
            user_id,
            "image_processed",
            {
                "processing_id": final_result["processing_id"],
                "operations_count": len(operations)
            }
        ))
        
        logger.info(f"Image processing completed: {task_id}")
        return final_result
        
    except Exception as e:
        logger.error(f"Image processing failed: {task_id}, {e}")
        
        # 실패 처리
        if 'progress_tracker' in locals():
            asyncio.run(progress_tracker.fail_step(
                task_id, "image_processing", str(e)
            ))
        
        raise


@image_task(name="resize_image_task")
def resize_image_task(
    self,
    image_data: Union[str, bytes],
    target_size: Tuple[int, int],
    resize_method: str = "lanczos",
    maintain_aspect_ratio: bool = True,
    user_id: str,
    session_id: str
) -> Dict[str, Any]:
    """
    이미지 리사이징 태스크
    
    Args:
        image_data: 이미지 데이터
        target_size: 목표 크기 (width, height)
        resize_method: 리사이징 방법 (lanczos, bilinear, bicubic, nearest)
        maintain_aspect_ratio: 종횡비 유지 여부
        user_id: 사용자 ID
        session_id: 세션 ID
    
    Returns:
        리사이징된 이미지 결과
    """
    task_id = self.request.id
    logger.info(f"Starting image resize: {task_id}, target: {target_size}")
    
    try:
        # 이미지 로드
        image = _load_and_validate_image(image_data)
        
        # 리사이징 실행
        resized_image = _resize_image(
            image, target_size, resize_method, maintain_aspect_ratio
        )
        
        # 결과 저장
        save_result = _save_processed_image(
            resized_image, user_id, session_id, task_id
        )
        
        result = {
            "resize_id": str(uuid.uuid4()),
            "task_id": task_id,
            "original_size": image.size,
            "target_size": target_size,
            "final_size": resized_image.size,
            "resize_method": resize_method,
            "aspect_ratio_maintained": maintain_aspect_ratio,
            "save_location": save_result["location"],
            "resized_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Image resize completed: {task_id}")
        return result
        
    except Exception as e:
        logger.error(f"Image resize failed: {task_id}, {e}")
        raise


@image_task(name="compress_image_task")
def compress_image_task(
    self,
    image_data: Union[str, bytes],
    quality: int = 85,
    optimize: bool = True,
    progressive: bool = True,
    user_id: str,
    session_id: str
) -> Dict[str, Any]:
    """
    이미지 압축 태스크
    
    Args:
        image_data: 이미지 데이터
        quality: 압축 품질 (1-100)
        optimize: 최적화 여부
        progressive: 프로그레시브 JPEG 여부
        user_id: 사용자 ID
        session_id: 세션 ID
    
    Returns:
        압축된 이미지 결과
    """
    task_id = self.request.id
    logger.info(f"Starting image compression: {task_id}, quality: {quality}")
    
    try:
        # 이미지 로드
        image = _load_and_validate_image(image_data)
        
        # 원본 크기 계산
        original_size = _calculate_image_size(image)
        
        # 압축 실행
        compressed_image = _compress_image(image, quality, optimize, progressive)
        
        # 압축된 크기 계산
        compressed_size = _calculate_image_size(compressed_image)
        
        # 결과 저장
        save_result = _save_processed_image(
            compressed_image, user_id, session_id, task_id
        )
        
        result = {
            "compression_id": str(uuid.uuid4()),
            "task_id": task_id,
            "original_size_bytes": original_size,
            "compressed_size_bytes": compressed_size,
            "compression_ratio": round((1 - compressed_size / original_size) * 100, 2),
            "quality": quality,
            "optimize": optimize,
            "progressive": progressive,
            "save_location": save_result["location"],
            "compressed_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Image compression completed: {task_id}")
        return result
        
    except Exception as e:
        logger.error(f"Image compression failed: {task_id}, {e}")
        raise


@image_task(name="generate_thumbnail_task")
def generate_thumbnail_task(
    self,
    image_data: Union[str, bytes],
    thumbnail_sizes: Optional[List[str]] = None,
    user_id: str,
    session_id: str
) -> Dict[str, Any]:
    """
    썸네일 생성 태스크
    
    Args:
        image_data: 이미지 데이터
        thumbnail_sizes: 썸네일 크기 목록 (small, medium, large)
        user_id: 사용자 ID
        session_id: 세션 ID
    
    Returns:
        생성된 썸네일 결과
    """
    task_id = self.request.id
    logger.info(f"Starting thumbnail generation: {task_id}")
    
    try:
        # 기본 썸네일 크기 설정
        if thumbnail_sizes is None:
            thumbnail_sizes = ["small", "medium", "large"]
        
        # 이미지 로드
        image = _load_and_validate_image(image_data)
        
        thumbnails = {}
        
        # 각 크기별 썸네일 생성
        for size_name in thumbnail_sizes:
            if size_name in IMAGE_CONFIG["thumbnail_sizes"]:
                size = IMAGE_CONFIG["thumbnail_sizes"][size_name]
                thumbnail = _generate_thumbnail(image, size)
                
                # 썸네일 저장
                save_result = _save_processed_image(
                    thumbnail, user_id, session_id, f"{task_id}_{size_name}"
                )
                
                thumbnails[size_name] = {
                    "size": thumbnail.size,
                    "location": save_result["location"]
                }
        
        result = {
            "thumbnail_id": str(uuid.uuid4()),
            "task_id": task_id,
            "original_size": image.size,
            "thumbnails": thumbnails,
            "generated_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Thumbnail generation completed: {task_id}")
        return result
        
    except Exception as e:
        logger.error(f"Thumbnail generation failed: {task_id}, {e}")
        raise


@image_task(name="apply_filter_task")
def apply_filter_task(
    self,
    image_data: Union[str, bytes],
    filter_type: str,
    filter_params: Optional[Dict[str, Any]] = None,
    user_id: str,
    session_id: str
) -> Dict[str, Any]:
    """
    이미지 필터 적용 태스크
    
    Args:
        image_data: 이미지 데이터
        filter_type: 필터 유형
        filter_params: 필터 파라미터
        user_id: 사용자 ID
        session_id: 세션 ID
    
    Returns:
        필터 적용 결과
    """
    task_id = self.request.id
    logger.info(f"Starting filter application: {task_id}, filter: {filter_type}")
    
    try:
        # 이미지 로드
        image = _load_and_validate_image(image_data)
        
        # 필터 적용
        filtered_image = _apply_image_filter(image, filter_type, filter_params or {})
        
        # 결과 저장
        save_result = _save_processed_image(
            filtered_image, user_id, session_id, task_id
        )
        
        result = {
            "filter_id": str(uuid.uuid4()),
            "task_id": task_id,
            "filter_type": filter_type,
            "filter_params": filter_params,
            "save_location": save_result["location"],
            "filtered_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Filter application completed: {task_id}")
        return result
        
    except Exception as e:
        logger.error(f"Filter application failed: {task_id}, {e}")
        raise


# 헬퍼 함수들
def _load_and_validate_image(image_data: Union[str, bytes]) -> Image.Image:
    """이미지 로드 및 검증"""
    try:
        # Base64 디코딩
        if isinstance(image_data, str):
            image_bytes = base64.b64decode(image_data)
        else:
            image_bytes = image_data
        
        # 파일 크기 검증
        if len(image_bytes) > IMAGE_CONFIG["max_file_size"]:
            raise ValueError(f"Image size exceeds maximum allowed size")
        
        # PIL 이미지로 변환
        image = Image.open(io.BytesIO(image_bytes))
        
        # 포맷 검증
        if image.format not in IMAGE_CONFIG["supported_formats"]:
            raise ValueError(f"Unsupported image format: {image.format}")
        
        return image
        
    except Exception as e:
        logger.error(f"Failed to load and validate image: {e}")
        raise


def _execute_image_operation(image: Image.Image, operation: Dict[str, Any]) -> Image.Image:
    """이미지 작업 실행"""
    operation_type = operation["type"]
    params = operation.get("params", {})
    
    if operation_type == "resize":
        return _resize_image(
            image, 
            params["size"], 
            params.get("method", "lanczos"),
            params.get("maintain_aspect_ratio", True)
        )
    
    elif operation_type == "crop":
        return _crop_image(image, params["box"])
    
    elif operation_type == "rotate":
        return _rotate_image(image, params["angle"], params.get("expand", True))
    
    elif operation_type == "flip":
        return _flip_image(image, params["direction"])
    
    elif operation_type == "filter":
        return _apply_image_filter(image, params["filter_type"], params.get("filter_params", {}))
    
    elif operation_type == "enhance":
        return _enhance_image(image, params["enhancement_type"], params["factor"])
    
    elif operation_type == "convert_mode":
        return _convert_image_mode(image, params["mode"])
    
    else:
        raise ValueError(f"Unsupported operation type: {operation_type}")


def _resize_image(
    image: Image.Image, 
    target_size: Tuple[int, int], 
    method: str = "lanczos",
    maintain_aspect_ratio: bool = True
) -> Image.Image:
    """이미지 리사이징"""
    try:
        # 리사이징 방법 매핑
        method_map = {
            "lanczos": Image.LANCZOS,
            "bilinear": Image.BILINEAR,
            "bicubic": Image.BICUBIC,
            "nearest": Image.NEAREST
        }
        
        resize_method = method_map.get(method, Image.LANCZOS)
        
        if maintain_aspect_ratio:
            # 종횡비 유지하면서 리사이징
            image.thumbnail(target_size, resize_method)
            return image
        else:
            # 정확한 크기로 리사이징
            return image.resize(target_size, resize_method)
            
    except Exception as e:
        logger.error(f"Failed to resize image: {e}")
        raise


def _crop_image(image: Image.Image, box: Tuple[int, int, int, int]) -> Image.Image:
    """이미지 크롭"""
    try:
        return image.crop(box)
    except Exception as e:
        logger.error(f"Failed to crop image: {e}")
        raise


def _rotate_image(image: Image.Image, angle: float, expand: bool = True) -> Image.Image:
    """이미지 회전"""
    try:
        return image.rotate(angle, expand=expand)
    except Exception as e:
        logger.error(f"Failed to rotate image: {e}")
        raise


def _flip_image(image: Image.Image, direction: str) -> Image.Image:
    """이미지 뒤집기"""
    try:
        if direction == "horizontal":
            return image.transpose(Image.FLIP_LEFT_RIGHT)
        elif direction == "vertical":
            return image.transpose(Image.FLIP_TOP_BOTTOM)
        else:
            raise ValueError(f"Invalid flip direction: {direction}")
    except Exception as e:
        logger.error(f"Failed to flip image: {e}")
        raise


def _apply_image_filter(
    image: Image.Image, 
    filter_type: str, 
    filter_params: Dict[str, Any]
) -> Image.Image:
    """이미지 필터 적용"""
    try:
        if filter_type == "blur":
            radius = filter_params.get("radius", 2)
            return image.filter(ImageFilter.GaussianBlur(radius=radius))
        
        elif filter_type == "sharpen":
            return image.filter(ImageFilter.SHARPEN)
        
        elif filter_type == "edge_enhance":
            return image.filter(ImageFilter.EDGE_ENHANCE)
        
        elif filter_type == "emboss":
            return image.filter(ImageFilter.EMBOSS)
        
        elif filter_type == "find_edges":
            return image.filter(ImageFilter.FIND_EDGES)
        
        elif filter_type == "smooth":
            return image.filter(ImageFilter.SMOOTH)
        
        elif filter_type == "detail":
            return image.filter(ImageFilter.DETAIL)
        
        else:
            raise ValueError(f"Unsupported filter type: {filter_type}")
            
    except Exception as e:
        logger.error(f"Failed to apply filter: {e}")
        raise


def _enhance_image(
    image: Image.Image, 
    enhancement_type: str, 
    factor: float
) -> Image.Image:
    """이미지 향상"""
    try:
        if enhancement_type == "brightness":
            enhancer = ImageEnhance.Brightness(image)
        elif enhancement_type == "contrast":
            enhancer = ImageEnhance.Contrast(image)
        elif enhancement_type == "color":
            enhancer = ImageEnhance.Color(image)
        elif enhancement_type == "sharpness":
            enhancer = ImageEnhance.Sharpness(image)
        else:
            raise ValueError(f"Unsupported enhancement type: {enhancement_type}")
        
        return enhancer.enhance(factor)
        
    except Exception as e:
        logger.error(f"Failed to enhance image: {e}")
        raise


def _convert_image_mode(image: Image.Image, mode: str) -> Image.Image:
    """이미지 모드 변환"""
    try:
        return image.convert(mode)
    except Exception as e:
        logger.error(f"Failed to convert image mode: {e}")
        raise


def _convert_output_format(
    image: Image.Image, 
    output_format: Optional[str] = None, 
    quality: Optional[int] = None
) -> Image.Image:
    """출력 포맷 변환"""
    try:
        if output_format and output_format.upper() != image.format:
            # RGB 모드로 변환 (JPEG 호환성)
            if output_format.upper() == "JPEG" and image.mode in ("RGBA", "P"):
                # 투명 배경을 흰색으로 변환
                background = Image.new("RGB", image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1] if image.mode == "RGBA" else None)
                image = background
            
            # 포맷 변환을 위해 메모리에서 처리
            output_buffer = io.BytesIO()
            save_kwargs = {"format": output_format.upper()}
            
            if quality and output_format.upper() in ["JPEG", "WEBP"]:
                save_kwargs["quality"] = quality
                save_kwargs["optimize"] = True
            
            image.save(output_buffer, **save_kwargs)
            output_buffer.seek(0)
            image = Image.open(output_buffer)
        
        return image
        
    except Exception as e:
        logger.error(f"Failed to convert output format: {e}")
        raise


def _compress_image(
    image: Image.Image, 
    quality: int = 85, 
    optimize: bool = True, 
    progressive: bool = True
) -> Image.Image:
    """이미지 압축"""
    try:
        # 메모리 버퍼에 압축된 이미지 저장
        output_buffer = io.BytesIO()
        
        save_kwargs = {
            "format": "JPEG",
            "quality": quality,
            "optimize": optimize
        }
        
        if progressive:
            save_kwargs["progressive"] = True
        
        # RGB 모드로 변환 (JPEG 호환성)
        if image.mode in ("RGBA", "P"):
            background = Image.new("RGB", image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1] if image.mode == "RGBA" else None)
            image = background
        
        image.save(output_buffer, **save_kwargs)
        output_buffer.seek(0)
        
        return Image.open(output_buffer)
        
    except Exception as e:
        logger.error(f"Failed to compress image: {e}")
        raise


def _generate_thumbnail(image: Image.Image, size: Tuple[int, int]) -> Image.Image:
    """썸네일 생성"""
    try:
        # 복사본 생성
        thumbnail = image.copy()
        
        # 썸네일 생성 (종횡비 유지)
        thumbnail.thumbnail(size, Image.LANCZOS)
        
        return thumbnail
        
    except Exception as e:
        logger.error(f"Failed to generate thumbnail: {e}")
        raise


def _calculate_image_size(image: Image.Image) -> int:
    """이미지 크기 계산 (바이트)"""
    try:
        output_buffer = io.BytesIO()
        image.save(output_buffer, format=image.format or "PNG")
        return len(output_buffer.getvalue())
    except Exception as e:
        logger.error(f"Failed to calculate image size: {e}")
        return 0


def _save_processed_image(
    image: Image.Image, 
    user_id: str, 
    session_id: str, 
    task_id: str
) -> Dict[str, Any]:
    """처리된 이미지 저장"""
    try:
        # 이미지를 base64로 인코딩
        output_buffer = io.BytesIO()
        image.save(output_buffer, format=image.format or "PNG")
        image_base64 = base64.b64encode(output_buffer.getvalue()).decode()
        
        # 스토리지 서비스에 저장
        response = requests.post(
            f"{STORAGE_SERVICE_URL}/images",
            json={
                "image_data": image_base64,
                "user_id": user_id,
                "session_id": session_id,
                "task_id": task_id,
                "metadata": {
                    "size": image.size,
                    "format": image.format,
                    "mode": image.mode
                }
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        logger.error(f"Failed to save processed image: {e}")
        raise


# 배치 이미지 처리 태스크
@image_task(name="batch_image_processing_task")
def batch_image_processing_task(
    self,
    image_requests: List[Dict[str, Any]],
    batch_id: str
) -> Dict[str, Any]:
    """
    배치 이미지 처리 태스크
    
    Args:
        image_requests: 이미지 처리 요청 목록
        batch_id: 배치 ID
    
    Returns:
        배치 처리 결과
    """
    task_id = self.request.id
    logger.info(f"Starting batch image processing: {task_id}, batch: {batch_id}")
    
    try:
        results = []
        failed_requests = []
        
        for i, request in enumerate(image_requests):
            try:
                # 개별 이미지 처리 태스크 실행
                result = process_image_task.delay(
                    image_data=request["image_data"],
                    operations=request["operations"],
                    user_id=request["user_id"],
                    session_id=request.get("session_id", batch_id),
                    output_format=request.get("output_format"),
                    quality=request.get("quality")
                )
                
                results.append({
                    "request_index": i,
                    "task_id": result.id,
                    "status": "submitted"
                })
                
            except Exception as e:
                failed_requests.append({
                    "request_index": i,
                    "error": str(e)
                })
        
        batch_result = {
            "batch_id": batch_id,
            "task_id": task_id,
            "total_requests": len(image_requests),
            "successful_submissions": len(results),
            "failed_submissions": len(failed_requests),
            "results": results,
            "failed_requests": failed_requests,
            "submitted_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Batch image processing completed: {task_id}")
        return batch_result
        
    except Exception as e:
        logger.error(f"Batch image processing failed: {task_id}, {e}")
        raise


# 이미지 최적화 태스크
@image_task(name="optimize_images_task")
def optimize_images_task(
    self,
    image_paths: List[str],
    optimization_level: str = "medium"
) -> Dict[str, Any]:
    """
    이미지 최적화 태스크
    
    Args:
        image_paths: 최적화할 이미지 경로 목록
        optimization_level: 최적화 수준 (low, medium, high)
    
    Returns:
        최적화 결과
    """
    task_id = self.request.id
    logger.info(f"Starting image optimization: {task_id}, level: {optimization_level}")
    
    try:
        optimization_results = []
        total_original_size = 0
        total_optimized_size = 0
        
        quality = IMAGE_CONFIG["quality_levels"].get(optimization_level, 80)
        
        for image_path in image_paths:
            try:
                # 이미지 로드
                with open(image_path, 'rb') as f:
                    image_data = f.read()
                
                original_size = len(image_data)
                total_original_size += original_size
                
                # 이미지 최적화
                image = Image.open(io.BytesIO(image_data))
                optimized_image = _compress_image(image, quality, True, True)
                
                # 최적화된 이미지 저장
                output_buffer = io.BytesIO()
                optimized_image.save(output_buffer, format="JPEG", quality=quality, optimize=True)
                optimized_data = output_buffer.getvalue()
                optimized_size = len(optimized_data)
                total_optimized_size += optimized_size
                
                # 원본 파일 덮어쓰기
                with open(image_path, 'wb') as f:
                    f.write(optimized_data)
                
                optimization_results.append({
                    "path": image_path,
                    "original_size": original_size,
                    "optimized_size": optimized_size,
                    "compression_ratio": round((1 - optimized_size / original_size) * 100, 2),
                    "status": "optimized"
                })
                
            except Exception as e:
                optimization_results.append({
                    "path": image_path,
                    "status": "failed",
                    "error": str(e)
                })
        
        result = {
            "optimization_id": str(uuid.uuid4()),
            "task_id": task_id,
            "optimization_level": optimization_level,
            "total_images": len(image_paths),
            "successful_optimizations": len([r for r in optimization_results if r["status"] == "optimized"]),
            "total_original_size": total_original_size,
            "total_optimized_size": total_optimized_size,
            "overall_compression_ratio": round((1 - total_optimized_size / total_original_size) * 100, 2) if total_original_size > 0 else 0,
            "results": optimization_results,
            "optimized_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Image optimization completed: {task_id}")
        return result
        
    except Exception as e:
        logger.error(f"Image optimization failed: {task_id}, {e}")
        raise