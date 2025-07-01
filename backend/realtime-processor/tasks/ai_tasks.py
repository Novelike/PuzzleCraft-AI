"""
AI 관련 Celery 태스크
AI 컨텐츠 생성, 이미지 분석, 모델 훈련 등의 작업을 처리
"""

import asyncio
import json
import logging
import time
import uuid
import base64
import io
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime
import requests
import aiohttp
import numpy as np
from PIL import Image

from ..celery_app import ai_task, celery_app
from ..progress_tracker import ProgressTracker
from ..notification_service import NotificationService

logger = logging.getLogger(__name__)

# 서비스 URL 설정
AI_SERVICE_URL = "http://ai-service:8000"
OCR_SERVICE_URL = "http://ocr-service:8000"
API_GATEWAY_URL = "http://api-gateway:8000"

# AI 모델 설정
AI_MODELS = {
    "text_generation": {
        "gpt": "gpt-3.5-turbo",
        "claude": "claude-3-sonnet",
        "local": "local-llm"
    },
    "image_analysis": {
        "vision": "gpt-4-vision",
        "local": "local-vision"
    },
    "ocr": {
        "tesseract": "tesseract",
        "paddle": "paddleocr",
        "easyocr": "easyocr"
    }
}


@ai_task(name="process_ai_request_task")
def process_ai_request_task(
    self,
    request_type: str,
    request_data: Dict[str, Any],
    user_id: str,
    session_id: str,
    model_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    AI 요청 처리 태스크
    
    Args:
        request_type: 요청 유형 (text_generation, image_analysis, etc.)
        request_data: 요청 데이터
        user_id: 사용자 ID
        session_id: 세션 ID
        model_config: 모델 설정
    
    Returns:
        AI 처리 결과
    """
    task_id = self.request.id
    logger.info(f"Starting AI request processing: {task_id}, type: {request_type}")
    
    try:
        # 진행률 추적 시작
        progress_tracker = ProgressTracker()
        asyncio.run(progress_tracker.start_task(
            task_id,
            "ai_request_processing",
            {
                "request_type": request_type,
                "user_id": user_id,
                "session_id": session_id
            }
        ))
        
        # 1단계: 요청 검증
        asyncio.run(progress_tracker.update_step(
            task_id, "request_validation", 10, "Validating AI request"
        ))
        
        validation_result = _validate_ai_request(request_type, request_data, model_config)
        if not validation_result["valid"]:
            raise ValueError(f"Invalid AI request: {validation_result['errors']}")
        
        # 2단계: 모델 선택 및 설정
        asyncio.run(progress_tracker.update_step(
            task_id, "model_selection", 20, "Selecting AI model"
        ))
        
        selected_model = _select_ai_model(request_type, model_config)
        
        # 3단계: AI 처리 실행
        asyncio.run(progress_tracker.update_step(
            task_id, "ai_processing", 50, f"Processing with {selected_model['name']}"
        ))
        
        ai_result = _execute_ai_processing(
            request_type, 
            request_data, 
            selected_model,
            task_id
        )
        
        # 4단계: 결과 후처리
        asyncio.run(progress_tracker.update_step(
            task_id, "result_postprocessing", 80, "Post-processing results"
        ))
        
        processed_result = _postprocess_ai_result(ai_result, request_type, request_data)
        
        # 5단계: 결과 저장
        asyncio.run(progress_tracker.update_step(
            task_id, "result_saving", 90, "Saving results"
        ))
        
        save_result = _save_ai_result(processed_result, user_id, session_id)
        
        # 최종 결과 준비
        final_result = {
            "request_id": str(uuid.uuid4()),
            "task_id": task_id,
            "request_type": request_type,
            "model_used": selected_model,
            "result": processed_result,
            "metadata": {
                "user_id": user_id,
                "session_id": session_id,
                "processed_at": datetime.utcnow().isoformat(),
                "processing_time": time.time() - self.request.called_directly,
                "save_location": save_result.get("location")
            }
        }
        
        # 완료
        asyncio.run(progress_tracker.complete_step(
            task_id, "ai_request_processing", {"request_id": final_result["request_id"]}
        ))
        
        # 알림 발송
        notification_service = NotificationService()
        asyncio.run(notification_service.send_notification(
            user_id,
            "ai_request_completed",
            {
                "request_id": final_result["request_id"],
                "request_type": request_type,
                "model_used": selected_model["name"]
            }
        ))
        
        logger.info(f"AI request processing completed: {task_id}")
        return final_result
        
    except Exception as e:
        logger.error(f"AI request processing failed: {task_id}, {e}")
        
        # 실패 처리
        if 'progress_tracker' in locals():
            asyncio.run(progress_tracker.fail_step(
                task_id, "ai_request_processing", str(e)
            ))
        
        raise


@ai_task(name="generate_ai_content_task")
def generate_ai_content_task(
    self,
    content_type: str,
    prompt: str,
    parameters: Dict[str, Any],
    user_id: str,
    session_id: str
) -> Dict[str, Any]:
    """
    AI 컨텐츠 생성 태스크
    
    Args:
        content_type: 컨텐츠 유형 (text, image, audio, etc.)
        prompt: 생성 프롬프트
        parameters: 생성 파라미터
        user_id: 사용자 ID
        session_id: 세션 ID
    
    Returns:
        생성된 컨텐츠
    """
    task_id = self.request.id
    logger.info(f"Starting AI content generation: {task_id}, type: {content_type}")
    
    try:
        # 컨텐츠 유형별 처리
        if content_type == "text":
            result = _generate_text_content(prompt, parameters, task_id)
        elif content_type == "image":
            result = _generate_image_content(prompt, parameters, task_id)
        elif content_type == "puzzle_clues":
            result = _generate_puzzle_clues(prompt, parameters, task_id)
        elif content_type == "story":
            result = _generate_story_content(prompt, parameters, task_id)
        else:
            raise ValueError(f"Unsupported content type: {content_type}")
        
        final_result = {
            "content_id": str(uuid.uuid4()),
            "task_id": task_id,
            "content_type": content_type,
            "prompt": prompt,
            "generated_content": result,
            "metadata": {
                "user_id": user_id,
                "session_id": session_id,
                "generated_at": datetime.utcnow().isoformat(),
                "parameters": parameters
            }
        }
        
        logger.info(f"AI content generation completed: {task_id}")
        return final_result
        
    except Exception as e:
        logger.error(f"AI content generation failed: {task_id}, {e}")
        raise


@ai_task(name="analyze_image_task")
def analyze_image_task(
    self,
    image_data: Union[str, bytes],
    analysis_type: str,
    parameters: Optional[Dict[str, Any]] = None,
    user_id: str,
    session_id: str
) -> Dict[str, Any]:
    """
    이미지 분석 태스크
    
    Args:
        image_data: 이미지 데이터 (base64 또는 bytes)
        analysis_type: 분석 유형 (ocr, object_detection, classification, etc.)
        parameters: 분석 파라미터
        user_id: 사용자 ID
        session_id: 세션 ID
    
    Returns:
        이미지 분석 결과
    """
    task_id = self.request.id
    logger.info(f"Starting image analysis: {task_id}, type: {analysis_type}")
    
    try:
        # 이미지 전처리
        processed_image = _preprocess_image(image_data)
        
        # 분석 유형별 처리
        if analysis_type == "ocr":
            result = _perform_ocr_analysis(processed_image, parameters or {})
        elif analysis_type == "object_detection":
            result = _perform_object_detection(processed_image, parameters or {})
        elif analysis_type == "classification":
            result = _perform_image_classification(processed_image, parameters or {})
        elif analysis_type == "puzzle_detection":
            result = _detect_puzzle_elements(processed_image, parameters or {})
        else:
            raise ValueError(f"Unsupported analysis type: {analysis_type}")
        
        final_result = {
            "analysis_id": str(uuid.uuid4()),
            "task_id": task_id,
            "analysis_type": analysis_type,
            "result": result,
            "metadata": {
                "user_id": user_id,
                "session_id": session_id,
                "analyzed_at": datetime.utcnow().isoformat(),
                "image_info": {
                    "size": processed_image.get("size"),
                    "format": processed_image.get("format"),
                    "mode": processed_image.get("mode")
                }
            }
        }
        
        logger.info(f"Image analysis completed: {task_id}")
        return final_result
        
    except Exception as e:
        logger.error(f"Image analysis failed: {task_id}, {e}")
        raise


@ai_task(name="train_model_task")
def train_model_task(
    self,
    model_type: str,
    training_data: Dict[str, Any],
    training_config: Dict[str, Any],
    user_id: str,
    session_id: str
) -> Dict[str, Any]:
    """
    모델 훈련 태스크
    
    Args:
        model_type: 모델 유형
        training_data: 훈련 데이터
        training_config: 훈련 설정
        user_id: 사용자 ID
        session_id: 세션 ID
    
    Returns:
        훈련 결과
    """
    task_id = self.request.id
    logger.info(f"Starting model training: {task_id}, type: {model_type}")
    
    try:
        # 진행률 추적 시작
        progress_tracker = ProgressTracker()
        asyncio.run(progress_tracker.start_task(
            task_id,
            "model_training",
            {
                "model_type": model_type,
                "user_id": user_id,
                "session_id": session_id
            }
        ))
        
        # 1단계: 데이터 검증
        asyncio.run(progress_tracker.update_step(
            task_id, "data_validation", 10, "Validating training data"
        ))
        
        data_validation = _validate_training_data(training_data, model_type)
        if not data_validation["valid"]:
            raise ValueError(f"Invalid training data: {data_validation['errors']}")
        
        # 2단계: 데이터 전처리
        asyncio.run(progress_tracker.update_step(
            task_id, "data_preprocessing", 20, "Preprocessing training data"
        ))
        
        preprocessed_data = _preprocess_training_data(training_data, training_config)
        
        # 3단계: 모델 초기화
        asyncio.run(progress_tracker.update_step(
            task_id, "model_initialization", 30, "Initializing model"
        ))
        
        model_info = _initialize_model(model_type, training_config)
        
        # 4단계: 모델 훈련
        asyncio.run(progress_tracker.update_step(
            task_id, "model_training_process", 40, "Training model"
        ))
        
        training_result = _train_model(
            model_info, 
            preprocessed_data, 
            training_config,
            task_id,
            progress_tracker
        )
        
        # 5단계: 모델 평가
        asyncio.run(progress_tracker.update_step(
            task_id, "model_evaluation", 80, "Evaluating model"
        ))
        
        evaluation_result = _evaluate_model(training_result, preprocessed_data)
        
        # 6단계: 모델 저장
        asyncio.run(progress_tracker.update_step(
            task_id, "model_saving", 90, "Saving model"
        ))
        
        save_result = _save_trained_model(training_result, model_type, user_id)
        
        final_result = {
            "training_id": str(uuid.uuid4()),
            "task_id": task_id,
            "model_type": model_type,
            "training_result": training_result,
            "evaluation_result": evaluation_result,
            "model_location": save_result["location"],
            "metadata": {
                "user_id": user_id,
                "session_id": session_id,
                "trained_at": datetime.utcnow().isoformat(),
                "training_config": training_config
            }
        }
        
        # 완료
        asyncio.run(progress_tracker.complete_step(
            task_id, "model_training", {"training_id": final_result["training_id"]}
        ))
        
        logger.info(f"Model training completed: {task_id}")
        return final_result
        
    except Exception as e:
        logger.error(f"Model training failed: {task_id}, {e}")
        
        # 실패 처리
        if 'progress_tracker' in locals():
            asyncio.run(progress_tracker.fail_step(
                task_id, "model_training", str(e)
            ))
        
        raise


# 헬퍼 함수들
def _validate_ai_request(
    request_type: str, 
    request_data: Dict[str, Any], 
    model_config: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """AI 요청 검증"""
    errors = []
    
    # 요청 유형 검증
    valid_types = ["text_generation", "image_analysis", "content_generation", "model_training"]
    if request_type not in valid_types:
        errors.append(f"Invalid request type: {request_type}")
    
    # 필수 데이터 검증
    if not request_data:
        errors.append("Request data is required")
    
    # 요청 유형별 검증
    if request_type == "text_generation":
        if "prompt" not in request_data:
            errors.append("Prompt is required for text generation")
    
    elif request_type == "image_analysis":
        if "image_data" not in request_data:
            errors.append("Image data is required for image analysis")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors
    }


def _select_ai_model(
    request_type: str, 
    model_config: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """AI 모델 선택"""
    if model_config and "model_name" in model_config:
        model_name = model_config["model_name"]
    else:
        # 기본 모델 선택
        if request_type == "text_generation":
            model_name = AI_MODELS["text_generation"]["gpt"]
        elif request_type == "image_analysis":
            model_name = AI_MODELS["image_analysis"]["vision"]
        else:
            model_name = "default"
    
    return {
        "name": model_name,
        "type": request_type,
        "config": model_config or {}
    }


def _execute_ai_processing(
    request_type: str,
    request_data: Dict[str, Any],
    selected_model: Dict[str, Any],
    task_id: str
) -> Dict[str, Any]:
    """AI 처리 실행"""
    try:
        response = requests.post(
            f"{AI_SERVICE_URL}/process",
            json={
                "request_type": request_type,
                "request_data": request_data,
                "model": selected_model,
                "task_id": task_id
            },
            timeout=120
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to execute AI processing: {e}")
        raise


def _postprocess_ai_result(
    ai_result: Dict[str, Any], 
    request_type: str, 
    request_data: Dict[str, Any]
) -> Dict[str, Any]:
    """AI 결과 후처리"""
    processed_result = ai_result.copy()
    
    # 요청 유형별 후처리
    if request_type == "text_generation":
        # 텍스트 정제
        if "generated_text" in processed_result:
            processed_result["generated_text"] = processed_result["generated_text"].strip()
    
    elif request_type == "image_analysis":
        # 신뢰도 점수 정규화
        if "confidence_scores" in processed_result:
            scores = processed_result["confidence_scores"]
            processed_result["confidence_scores"] = {
                k: round(v, 3) for k, v in scores.items()
            }
    
    return processed_result


def _save_ai_result(
    result: Dict[str, Any], 
    user_id: str, 
    session_id: str
) -> Dict[str, Any]:
    """AI 결과 저장"""
    try:
        response = requests.post(
            f"{API_GATEWAY_URL}/ai-results",
            json={
                "result": result,
                "user_id": user_id,
                "session_id": session_id
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to save AI result: {e}")
        raise


def _generate_text_content(
    prompt: str, 
    parameters: Dict[str, Any], 
    task_id: str
) -> Dict[str, Any]:
    """텍스트 컨텐츠 생성"""
    try:
        response = requests.post(
            f"{AI_SERVICE_URL}/generate-text",
            json={
                "prompt": prompt,
                "parameters": parameters,
                "task_id": task_id
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to generate text content: {e}")
        raise


def _generate_image_content(
    prompt: str, 
    parameters: Dict[str, Any], 
    task_id: str
) -> Dict[str, Any]:
    """이미지 컨텐츠 생성"""
    try:
        response = requests.post(
            f"{AI_SERVICE_URL}/generate-image",
            json={
                "prompt": prompt,
                "parameters": parameters,
                "task_id": task_id
            },
            timeout=120
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to generate image content: {e}")
        raise


def _generate_puzzle_clues(
    prompt: str, 
    parameters: Dict[str, Any], 
    task_id: str
) -> Dict[str, Any]:
    """퍼즐 단서 생성"""
    try:
        response = requests.post(
            f"{AI_SERVICE_URL}/generate-puzzle-clues",
            json={
                "prompt": prompt,
                "parameters": parameters,
                "task_id": task_id
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to generate puzzle clues: {e}")
        raise


def _generate_story_content(
    prompt: str, 
    parameters: Dict[str, Any], 
    task_id: str
) -> Dict[str, Any]:
    """스토리 컨텐츠 생성"""
    try:
        response = requests.post(
            f"{AI_SERVICE_URL}/generate-story",
            json={
                "prompt": prompt,
                "parameters": parameters,
                "task_id": task_id
            },
            timeout=90
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to generate story content: {e}")
        raise


def _preprocess_image(image_data: Union[str, bytes]) -> Dict[str, Any]:
    """이미지 전처리"""
    try:
        # Base64 디코딩
        if isinstance(image_data, str):
            image_bytes = base64.b64decode(image_data)
        else:
            image_bytes = image_data
        
        # PIL 이미지로 변환
        image = Image.open(io.BytesIO(image_bytes))
        
        return {
            "image": image,
            "size": image.size,
            "format": image.format,
            "mode": image.mode,
            "bytes": image_bytes
        }
    except Exception as e:
        logger.error(f"Failed to preprocess image: {e}")
        raise


def _perform_ocr_analysis(
    processed_image: Dict[str, Any], 
    parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """OCR 분석 수행"""
    try:
        # 이미지를 base64로 인코딩
        image_base64 = base64.b64encode(processed_image["bytes"]).decode()
        
        response = requests.post(
            f"{OCR_SERVICE_URL}/extract-text",
            json={
                "image_data": image_base64,
                "parameters": parameters
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to perform OCR analysis: {e}")
        raise


def _perform_object_detection(
    processed_image: Dict[str, Any], 
    parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """객체 탐지 수행"""
    try:
        image_base64 = base64.b64encode(processed_image["bytes"]).decode()
        
        response = requests.post(
            f"{AI_SERVICE_URL}/detect-objects",
            json={
                "image_data": image_base64,
                "parameters": parameters
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to perform object detection: {e}")
        raise


def _perform_image_classification(
    processed_image: Dict[str, Any], 
    parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """이미지 분류 수행"""
    try:
        image_base64 = base64.b64encode(processed_image["bytes"]).decode()
        
        response = requests.post(
            f"{AI_SERVICE_URL}/classify-image",
            json={
                "image_data": image_base64,
                "parameters": parameters
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to perform image classification: {e}")
        raise


def _detect_puzzle_elements(
    processed_image: Dict[str, Any], 
    parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """퍼즐 요소 탐지"""
    try:
        image_base64 = base64.b64encode(processed_image["bytes"]).decode()
        
        response = requests.post(
            f"{AI_SERVICE_URL}/detect-puzzle-elements",
            json={
                "image_data": image_base64,
                "parameters": parameters
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to detect puzzle elements: {e}")
        raise


def _validate_training_data(
    training_data: Dict[str, Any], 
    model_type: str
) -> Dict[str, Any]:
    """훈련 데이터 검증"""
    errors = []
    
    if not training_data:
        errors.append("Training data is required")
        return {"valid": False, "errors": errors}
    
    # 모델 유형별 검증
    if model_type == "text_classifier":
        if "texts" not in training_data or "labels" not in training_data:
            errors.append("Texts and labels are required for text classifier")
    
    elif model_type == "image_classifier":
        if "images" not in training_data or "labels" not in training_data:
            errors.append("Images and labels are required for image classifier")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors
    }


def _preprocess_training_data(
    training_data: Dict[str, Any], 
    training_config: Dict[str, Any]
) -> Dict[str, Any]:
    """훈련 데이터 전처리"""
    # 실제 구현에서는 데이터 정규화, 증강 등을 수행
    return training_data


def _initialize_model(
    model_type: str, 
    training_config: Dict[str, Any]
) -> Dict[str, Any]:
    """모델 초기화"""
    return {
        "model_type": model_type,
        "config": training_config,
        "initialized_at": datetime.utcnow().isoformat()
    }


def _train_model(
    model_info: Dict[str, Any],
    preprocessed_data: Dict[str, Any],
    training_config: Dict[str, Any],
    task_id: str,
    progress_tracker: ProgressTracker
) -> Dict[str, Any]:
    """모델 훈련"""
    try:
        response = requests.post(
            f"{AI_SERVICE_URL}/train-model",
            json={
                "model_info": model_info,
                "training_data": preprocessed_data,
                "training_config": training_config,
                "task_id": task_id
            },
            timeout=3600  # 1시간
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to train model: {e}")
        raise


def _evaluate_model(
    training_result: Dict[str, Any], 
    test_data: Dict[str, Any]
) -> Dict[str, Any]:
    """모델 평가"""
    try:
        response = requests.post(
            f"{AI_SERVICE_URL}/evaluate-model",
            json={
                "model_result": training_result,
                "test_data": test_data
            },
            timeout=300
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to evaluate model: {e}")
        raise


def _save_trained_model(
    training_result: Dict[str, Any], 
    model_type: str, 
    user_id: str
) -> Dict[str, Any]:
    """훈련된 모델 저장"""
    try:
        response = requests.post(
            f"{API_GATEWAY_URL}/models",
            json={
                "training_result": training_result,
                "model_type": model_type,
                "user_id": user_id
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to save trained model: {e}")
        raise


# 배치 처리 태스크
@ai_task(name="batch_ai_processing_task")
def batch_ai_processing_task(
    self,
    ai_requests: List[Dict[str, Any]],
    batch_id: str
) -> Dict[str, Any]:
    """
    배치 AI 처리 태스크
    
    Args:
        ai_requests: AI 요청 목록
        batch_id: 배치 ID
    
    Returns:
        배치 처리 결과
    """
    task_id = self.request.id
    logger.info(f"Starting batch AI processing: {task_id}, batch: {batch_id}")
    
    try:
        results = []
        failed_requests = []
        
        for i, request in enumerate(ai_requests):
            try:
                # 개별 AI 처리 태스크 실행
                result = process_ai_request_task.delay(
                    request["request_type"],
                    request["request_data"],
                    request["user_id"],
                    request.get("session_id", batch_id),
                    request.get("model_config")
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
            "total_requests": len(ai_requests),
            "successful_submissions": len(results),
            "failed_submissions": len(failed_requests),
            "results": results,
            "failed_requests": failed_requests,
            "submitted_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Batch AI processing completed: {task_id}")
        return batch_result
        
    except Exception as e:
        logger.error(f"Batch AI processing failed: {task_id}, {e}")
        raise