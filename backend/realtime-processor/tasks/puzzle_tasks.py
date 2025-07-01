"""
퍼즐 관련 Celery 태스크
퍼즐 생성, 검증, 최적화, 저장 등의 작업을 처리
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import requests
import aiohttp
import aiofiles

from ..celery_app import puzzle_task, celery_app
from ..progress_tracker import ProgressTracker
from ..notification_service import NotificationService

logger = logging.getLogger(__name__)

# 서비스 URL 설정
PUZZLE_ENGINE_URL = "http://puzzle-engine:8000"
AI_SERVICE_URL = "http://ai-service:8000"
API_GATEWAY_URL = "http://api-gateway:8000"


@puzzle_task(name="generate_puzzle_task")
def generate_puzzle_task(
    self,
    puzzle_type: str,
    difficulty: str,
    parameters: Dict[str, Any],
    user_id: str,
    session_id: str
) -> Dict[str, Any]:
    """
    퍼즐 생성 태스크
    
    Args:
        puzzle_type: 퍼즐 유형 (crossword, sudoku, word_search, etc.)
        difficulty: 난이도 (easy, medium, hard)
        parameters: 퍼즐 생성 파라미터
        user_id: 사용자 ID
        session_id: 세션 ID
    
    Returns:
        생성된 퍼즐 데이터
    """
    task_id = self.request.id
    logger.info(f"Starting puzzle generation task: {task_id}")
    
    try:
        # 진행률 추적 시작
        progress_tracker = ProgressTracker()
        asyncio.run(progress_tracker.start_task(
            task_id,
            "puzzle_generation",
            {
                "puzzle_type": puzzle_type,
                "difficulty": difficulty,
                "user_id": user_id,
                "session_id": session_id
            }
        ))
        
        # 1단계: 퍼즐 파라미터 검증
        asyncio.run(progress_tracker.update_step(
            task_id, "parameter_validation", 10, "Validating parameters"
        ))
        
        validated_params = _validate_puzzle_parameters(puzzle_type, difficulty, parameters)
        if not validated_params["valid"]:
            raise ValueError(f"Invalid parameters: {validated_params['errors']}")
        
        # 2단계: AI 서비스를 통한 컨텐츠 생성
        asyncio.run(progress_tracker.update_step(
            task_id, "content_generation", 30, "Generating puzzle content"
        ))
        
        content_data = _generate_puzzle_content(puzzle_type, difficulty, parameters)
        
        # 3단계: 퍼즐 엔진을 통한 퍼즐 구조 생성
        asyncio.run(progress_tracker.update_step(
            task_id, "structure_generation", 60, "Creating puzzle structure"
        ))
        
        puzzle_structure = _create_puzzle_structure(puzzle_type, content_data, parameters)
        
        # 4단계: 퍼즐 검증
        asyncio.run(progress_tracker.update_step(
            task_id, "puzzle_validation", 80, "Validating puzzle"
        ))
        
        validation_result = _validate_puzzle(puzzle_structure)
        if not validation_result["valid"]:
            raise ValueError(f"Puzzle validation failed: {validation_result['errors']}")
        
        # 5단계: 퍼즐 최적화
        asyncio.run(progress_tracker.update_step(
            task_id, "puzzle_optimization", 90, "Optimizing puzzle"
        ))
        
        optimized_puzzle = _optimize_puzzle(puzzle_structure, parameters)
        
        # 6단계: 결과 준비
        asyncio.run(progress_tracker.update_step(
            task_id, "result_preparation", 95, "Preparing result"
        ))
        
        result = {
            "puzzle_id": str(uuid.uuid4()),
            "task_id": task_id,
            "puzzle_type": puzzle_type,
            "difficulty": difficulty,
            "puzzle_data": optimized_puzzle,
            "metadata": {
                "user_id": user_id,
                "session_id": session_id,
                "created_at": datetime.utcnow().isoformat(),
                "generation_time": time.time() - self.request.called_directly,
                "parameters": parameters
            }
        }
        
        # 완료
        asyncio.run(progress_tracker.complete_step(
            task_id, "puzzle_generation", {"puzzle_id": result["puzzle_id"]}
        ))
        
        # 알림 발송
        notification_service = NotificationService()
        asyncio.run(notification_service.send_notification(
            user_id,
            "puzzle_generated",
            {
                "puzzle_id": result["puzzle_id"],
                "puzzle_type": puzzle_type,
                "difficulty": difficulty
            }
        ))
        
        logger.info(f"Puzzle generation completed: {task_id}")
        return result
        
    except Exception as e:
        logger.error(f"Puzzle generation failed: {task_id}, {e}")
        
        # 실패 처리
        if 'progress_tracker' in locals():
            asyncio.run(progress_tracker.fail_step(
                task_id, "puzzle_generation", str(e)
            ))
        
        raise


@puzzle_task(name="validate_puzzle_task")
def validate_puzzle_task(
    self,
    puzzle_data: Dict[str, Any],
    validation_rules: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    퍼즐 검증 태스크
    
    Args:
        puzzle_data: 검증할 퍼즐 데이터
        validation_rules: 검증 규칙
    
    Returns:
        검증 결과
    """
    task_id = self.request.id
    logger.info(f"Starting puzzle validation task: {task_id}")
    
    try:
        validation_result = _validate_puzzle(puzzle_data, validation_rules)
        
        result = {
            "task_id": task_id,
            "valid": validation_result["valid"],
            "errors": validation_result.get("errors", []),
            "warnings": validation_result.get("warnings", []),
            "score": validation_result.get("score", 0),
            "validated_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Puzzle validation completed: {task_id}")
        return result
        
    except Exception as e:
        logger.error(f"Puzzle validation failed: {task_id}, {e}")
        raise


@puzzle_task(name="optimize_puzzle_task")
def optimize_puzzle_task(
    self,
    puzzle_data: Dict[str, Any],
    optimization_params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    퍼즐 최적화 태스크
    
    Args:
        puzzle_data: 최적화할 퍼즐 데이터
        optimization_params: 최적화 파라미터
    
    Returns:
        최적화된 퍼즐 데이터
    """
    task_id = self.request.id
    logger.info(f"Starting puzzle optimization task: {task_id}")
    
    try:
        optimized_puzzle = _optimize_puzzle(puzzle_data, optimization_params)
        
        result = {
            "task_id": task_id,
            "original_puzzle": puzzle_data,
            "optimized_puzzle": optimized_puzzle,
            "optimization_stats": {
                "improvements": _calculate_improvements(puzzle_data, optimized_puzzle),
                "optimized_at": datetime.utcnow().isoformat()
            }
        }
        
        logger.info(f"Puzzle optimization completed: {task_id}")
        return result
        
    except Exception as e:
        logger.error(f"Puzzle optimization failed: {task_id}, {e}")
        raise


@puzzle_task(name="save_puzzle_task")
def save_puzzle_task(
    self,
    puzzle_data: Dict[str, Any],
    storage_options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    퍼즐 저장 태스크
    
    Args:
        puzzle_data: 저장할 퍼즐 데이터
        storage_options: 저장 옵션
    
    Returns:
        저장 결과
    """
    task_id = self.request.id
    logger.info(f"Starting puzzle save task: {task_id}")
    
    try:
        # 데이터베이스에 저장
        save_result = _save_puzzle_to_database(puzzle_data, storage_options)
        
        # 파일 시스템에 백업 저장
        if storage_options and storage_options.get("backup_to_file", False):
            file_path = _save_puzzle_to_file(puzzle_data, storage_options)
            save_result["backup_file"] = file_path
        
        result = {
            "task_id": task_id,
            "puzzle_id": puzzle_data.get("puzzle_id"),
            "saved": True,
            "save_result": save_result,
            "saved_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Puzzle save completed: {task_id}")
        return result
        
    except Exception as e:
        logger.error(f"Puzzle save failed: {task_id}, {e}")
        raise


# 헬퍼 함수들
def _validate_puzzle_parameters(
    puzzle_type: str, 
    difficulty: str, 
    parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """퍼즐 파라미터 검증"""
    errors = []
    
    # 퍼즐 타입 검증
    valid_types = ["crossword", "sudoku", "word_search", "jigsaw", "logic"]
    if puzzle_type not in valid_types:
        errors.append(f"Invalid puzzle type: {puzzle_type}")
    
    # 난이도 검증
    valid_difficulties = ["easy", "medium", "hard", "expert"]
    if difficulty not in valid_difficulties:
        errors.append(f"Invalid difficulty: {difficulty}")
    
    # 파라미터별 검증
    if puzzle_type == "crossword":
        if "grid_size" not in parameters:
            errors.append("Grid size is required for crossword puzzles")
        elif not isinstance(parameters["grid_size"], (int, tuple)):
            errors.append("Grid size must be an integer or tuple")
    
    elif puzzle_type == "sudoku":
        if "variant" in parameters and parameters["variant"] not in ["classic", "diagonal", "irregular"]:
            errors.append("Invalid sudoku variant")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors
    }


def _generate_puzzle_content(
    puzzle_type: str, 
    difficulty: str, 
    parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """AI 서비스를 통한 퍼즐 컨텐츠 생성"""
    try:
        response = requests.post(
            f"{AI_SERVICE_URL}/generate-content",
            json={
                "puzzle_type": puzzle_type,
                "difficulty": difficulty,
                "parameters": parameters
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to generate puzzle content: {e}")
        raise


def _create_puzzle_structure(
    puzzle_type: str, 
    content_data: Dict[str, Any], 
    parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """퍼즐 엔진을 통한 퍼즐 구조 생성"""
    try:
        response = requests.post(
            f"{PUZZLE_ENGINE_URL}/create-structure",
            json={
                "puzzle_type": puzzle_type,
                "content_data": content_data,
                "parameters": parameters
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to create puzzle structure: {e}")
        raise


def _validate_puzzle(
    puzzle_data: Dict[str, Any], 
    validation_rules: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """퍼즐 검증"""
    try:
        response = requests.post(
            f"{PUZZLE_ENGINE_URL}/validate",
            json={
                "puzzle_data": puzzle_data,
                "validation_rules": validation_rules or {}
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to validate puzzle: {e}")
        raise


def _optimize_puzzle(
    puzzle_data: Dict[str, Any], 
    optimization_params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """퍼즐 최적화"""
    try:
        response = requests.post(
            f"{PUZZLE_ENGINE_URL}/optimize",
            json={
                "puzzle_data": puzzle_data,
                "optimization_params": optimization_params or {}
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to optimize puzzle: {e}")
        raise


def _calculate_improvements(
    original_puzzle: Dict[str, Any], 
    optimized_puzzle: Dict[str, Any]
) -> Dict[str, Any]:
    """최적화 개선사항 계산"""
    improvements = {
        "size_reduction": 0,
        "complexity_improvement": 0,
        "solvability_improvement": 0
    }
    
    # 크기 개선
    original_size = len(json.dumps(original_puzzle))
    optimized_size = len(json.dumps(optimized_puzzle))
    improvements["size_reduction"] = (original_size - optimized_size) / original_size * 100
    
    # 복잡도 개선 (예시)
    original_complexity = original_puzzle.get("metadata", {}).get("complexity", 0)
    optimized_complexity = optimized_puzzle.get("metadata", {}).get("complexity", 0)
    if original_complexity > 0:
        improvements["complexity_improvement"] = (optimized_complexity - original_complexity) / original_complexity * 100
    
    return improvements


def _save_puzzle_to_database(
    puzzle_data: Dict[str, Any], 
    storage_options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """데이터베이스에 퍼즐 저장"""
    try:
        response = requests.post(
            f"{API_GATEWAY_URL}/puzzles",
            json={
                "puzzle_data": puzzle_data,
                "storage_options": storage_options or {}
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to save puzzle to database: {e}")
        raise


def _save_puzzle_to_file(
    puzzle_data: Dict[str, Any], 
    storage_options: Optional[Dict[str, Any]] = None
) -> str:
    """파일 시스템에 퍼즐 저장"""
    try:
        puzzle_id = puzzle_data.get("puzzle_id", str(uuid.uuid4()))
        file_path = f"/tmp/puzzles/{puzzle_id}.json"
        
        # 디렉토리 생성
        import os
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # 파일 저장
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(puzzle_data, f, ensure_ascii=False, indent=2)
        
        return file_path
    except Exception as e:
        logger.error(f"Failed to save puzzle to file: {e}")
        raise


# 배치 처리 태스크
@puzzle_task(name="batch_generate_puzzles_task")
def batch_generate_puzzles_task(
    self,
    puzzle_requests: List[Dict[str, Any]],
    batch_id: str
) -> Dict[str, Any]:
    """
    배치 퍼즐 생성 태스크
    
    Args:
        puzzle_requests: 퍼즐 생성 요청 목록
        batch_id: 배치 ID
    
    Returns:
        배치 처리 결과
    """
    task_id = self.request.id
    logger.info(f"Starting batch puzzle generation: {task_id}, batch: {batch_id}")
    
    try:
        results = []
        failed_requests = []
        
        for i, request in enumerate(puzzle_requests):
            try:
                # 개별 퍼즐 생성 태스크 실행
                result = generate_puzzle_task.delay(
                    request["puzzle_type"],
                    request["difficulty"],
                    request["parameters"],
                    request["user_id"],
                    request.get("session_id", batch_id)
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
            "total_requests": len(puzzle_requests),
            "successful_submissions": len(results),
            "failed_submissions": len(failed_requests),
            "results": results,
            "failed_requests": failed_requests,
            "submitted_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Batch puzzle generation completed: {task_id}")
        return batch_result
        
    except Exception as e:
        logger.error(f"Batch puzzle generation failed: {task_id}, {e}")
        raise