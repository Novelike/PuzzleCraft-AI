"""
PuzzleCraft AI - AI 작업 큐 시스템
비동기 AI 작업 처리를 위한 큐 관리 시스템
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import heapq
from concurrent.futures import ThreadPoolExecutor
import aiohttp

import redis.asyncio as redis
from celery import Celery

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """작업 상태"""
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskPriority(Enum):
    """작업 우선순위"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5


class AIServiceType(Enum):
    """AI 서비스 타입"""
    OCR = "ocr"
    SEGMENTATION = "segmentation"
    STYLE_TRANSFER = "style_transfer"
    PUZZLE_GENERATION = "puzzle_generation"
    COMPLEXITY_ANALYSIS = "complexity_analysis"


@dataclass
class AITask:
    """AI 작업 정의"""
    task_id: str
    task_type: AIServiceType
    priority: TaskPriority
    payload: Dict[str, Any]
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    connection_id: Optional[str] = None
    
    # 상태 관리
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    current_step: str = ""
    
    # 시간 정보
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_duration: Optional[int] = None  # seconds
    
    # 재시도 정보
    retry_count: int = 0
    max_retries: int = 3
    retry_delay: int = 5  # seconds
    
    # 결과 및 오류
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    # 의존성
    dependencies: List[str] = None  # 의존하는 다른 작업들의 task_id
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.dependencies is None:
            self.dependencies = []
    
    def __lt__(self, other):
        """우선순위 큐를 위한 비교 연산자"""
        if self.priority.value != other.priority.value:
            return self.priority.value > other.priority.value  # 높은 우선순위가 먼저
        return self.created_at < other.created_at  # 같은 우선순위면 먼저 생성된 것이 먼저
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        data = asdict(self)
        data['task_type'] = self.task_type.value
        data['priority'] = self.priority.value
        data['status'] = self.status.value
        data['created_at'] = self.created_at.isoformat()
        if self.started_at:
            data['started_at'] = self.started_at.isoformat()
        if self.completed_at:
            data['completed_at'] = self.completed_at.isoformat()
        return data


@dataclass
class WorkerInfo:
    """워커 정보"""
    worker_id: str
    worker_type: str
    supported_tasks: List[AIServiceType]
    max_concurrent_tasks: int
    current_tasks: int
    status: str  # active, busy, inactive, error
    last_heartbeat: datetime
    performance_metrics: Dict[str, Any]


class AITaskQueue:
    """AI 작업 큐 관리자"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379", celery_broker: str = None):
        """초기화"""
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        
        # 메모리 기반 큐 (Redis 백업)
        self.pending_queue: List[AITask] = []
        self.processing_tasks: Dict[str, AITask] = {}
        self.completed_tasks: Dict[str, AITask] = {}
        self.failed_tasks: Dict[str, AITask] = {}
        
        # 워커 관리
        self.workers: Dict[str, WorkerInfo] = {}
        self.worker_assignments: Dict[str, str] = {}  # task_id -> worker_id
        
        # Celery 설정 (선택적)
        self.celery_app: Optional[Celery] = None
        if celery_broker:
            self.celery_app = Celery('ai_tasks', broker=celery_broker)
            self._setup_celery_tasks()
        
        # 통계
        self.stats = {
            "total_tasks": 0,
            "pending_tasks": 0,
            "processing_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "average_processing_time": 0.0,
            "throughput_per_minute": 0.0,
        }
        
        # 콜백 함수들
        self.task_callbacks: Dict[str, List[Callable]] = {
            "on_task_start": [],
            "on_task_progress": [],
            "on_task_complete": [],
            "on_task_error": [],
        }
        
        # 백그라운드 작업
        self._queue_processor_task: Optional[asyncio.Task] = None
        self._stats_updater_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
        logger.info("AI 작업 큐 관리자 초기화 완료")

    async def initialize(self):
        """비동기 초기화"""
        try:
            # Redis 연결
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("Redis 연결 성공")
            
            # Redis에서 기존 작업 복원
            await self._restore_tasks_from_redis()
            
        except Exception as e:
            logger.warning(f"Redis 연결 실패: {str(e)}, 메모리 모드로 동작")
            self.redis_client = None
        
        # 백그라운드 작업 시작
        self._queue_processor_task = asyncio.create_task(self._process_queue())
        self._stats_updater_task = asyncio.create_task(self._update_stats())
        self._cleanup_task = asyncio.create_task(self._cleanup_old_tasks())

    async def shutdown(self):
        """종료 처리"""
        logger.info("AI 작업 큐 관리자 종료 중...")
        
        # 백그라운드 작업 중단
        for task in [self._queue_processor_task, self._stats_updater_task, self._cleanup_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # 진행 중인 작업들 취소
        for task_id in list(self.processing_tasks.keys()):
            await self.cancel_task(task_id)
        
        # Redis에 상태 저장
        if self.redis_client:
            await self._save_tasks_to_redis()
            await self.redis_client.close()
        
        logger.info("AI 작업 큐 관리자 종료 완료")

    async def submit_task(
        self,
        task_type: AIServiceType,
        payload: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        connection_id: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
        estimated_duration: Optional[int] = None
    ) -> str:
        """작업 제출"""
        task_id = str(uuid.uuid4())
        
        task = AITask(
            task_id=task_id,
            task_type=task_type,
            priority=priority,
            payload=payload,
            user_id=user_id,
            session_id=session_id,
            connection_id=connection_id,
            dependencies=dependencies or [],
            estimated_duration=estimated_duration
        )
        
        # 의존성 검사
        if not await self._check_dependencies(task):
            task.status = TaskStatus.PENDING
            # 의존성이 해결될 때까지 대기
            await self._store_pending_task(task)
        else:
            # 큐에 추가
            await self._add_to_queue(task)
        
        # 통계 업데이트
        self.stats["total_tasks"] += 1
        self.stats["pending_tasks"] = len(self.pending_queue)
        
        # Redis에 저장
        if self.redis_client:
            await self._save_task_to_redis(task)
        
        logger.info(f"새 작업 제출: {task_id} ({task_type.value}, 우선순위: {priority.value})")
        return task_id

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """작업 상태 조회"""
        task = await self._find_task(task_id)
        if not task:
            return None
        
        return {
            "task_id": task_id,
            "status": task.status.value,
            "progress": task.progress,
            "current_step": task.current_step,
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "estimated_duration": task.estimated_duration,
            "retry_count": task.retry_count,
            "error": task.error,
            "result": task.result
        }

    async def update_task_progress(
        self,
        task_id: str,
        progress: float,
        current_step: str = "",
        partial_result: Optional[Dict[str, Any]] = None
    ):
        """작업 진행률 업데이트"""
        task = self.processing_tasks.get(task_id)
        if not task:
            logger.warning(f"진행률 업데이트 실패: 작업을 찾을 수 없음 {task_id}")
            return
        
        task.progress = max(0.0, min(1.0, progress))
        task.current_step = current_step
        
        if partial_result:
            if not task.result:
                task.result = {}
            task.result.update(partial_result)
        
        # Redis 업데이트
        if self.redis_client:
            await self._save_task_to_redis(task)
        
        # 콜백 실행
        await self._execute_callbacks("on_task_progress", task)

    async def complete_task(self, task_id: str, result: Dict[str, Any]):
        """작업 완료 처리"""
        task = self.processing_tasks.get(task_id)
        if not task:
            logger.warning(f"작업 완료 실패: 작업을 찾을 수 없음 {task_id}")
            return
        
        task.status = TaskStatus.COMPLETED
        task.progress = 1.0
        task.completed_at = datetime.now()
        task.result = result
        
        # 처리 중에서 완료로 이동
        del self.processing_tasks[task_id]
        self.completed_tasks[task_id] = task
        
        # 워커 할당 해제
        if task_id in self.worker_assignments:
            worker_id = self.worker_assignments[task_id]
            if worker_id in self.workers:
                self.workers[worker_id].current_tasks -= 1
            del self.worker_assignments[task_id]
        
        # 의존성 해결 - 이 작업을 기다리던 작업들 활성화
        await self._resolve_dependencies(task_id)
        
        # Redis 업데이트
        if self.redis_client:
            await self._save_task_to_redis(task)
        
        # 콜백 실행
        await self._execute_callbacks("on_task_complete", task)
        
        logger.info(f"작업 완료: {task_id}")

    async def fail_task(self, task_id: str, error: str, retry: bool = True):
        """작업 실패 처리"""
        task = self.processing_tasks.get(task_id)
        if not task:
            logger.warning(f"작업 실패 처리 실패: 작업을 찾을 수 없음 {task_id}")
            return
        
        task.error = error
        
        # 재시도 로직
        if retry and task.retry_count < task.max_retries:
            task.retry_count += 1
            task.status = TaskStatus.RETRYING
            task.progress = 0.0
            task.current_step = f"재시도 {task.retry_count}/{task.max_retries}"
            
            # 재시도 지연 후 큐에 다시 추가
            asyncio.create_task(self._retry_task_after_delay(task))
            
            logger.info(f"작업 재시도 예약: {task_id} ({task.retry_count}/{task.max_retries})")
        else:
            # 최종 실패
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            
            # 처리 중에서 실패로 이동
            del self.processing_tasks[task_id]
            self.failed_tasks[task_id] = task
            
            logger.error(f"작업 최종 실패: {task_id} - {error}")
        
        # 워커 할당 해제
        if task_id in self.worker_assignments:
            worker_id = self.worker_assignments[task_id]
            if worker_id in self.workers:
                self.workers[worker_id].current_tasks -= 1
            del self.worker_assignments[task_id]
        
        # Redis 업데이트
        if self.redis_client:
            await self._save_task_to_redis(task)
        
        # 콜백 실행
        await self._execute_callbacks("on_task_error", task)

    async def cancel_task(self, task_id: str) -> bool:
        """작업 취소"""
        task = await self._find_task(task_id)
        if not task:
            return False
        
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            return False
        
        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.now()
        
        # 큐에서 제거
        if task in self.pending_queue:
            self.pending_queue.remove(task)
            heapq.heapify(self.pending_queue)
        
        # 처리 중이면 워커에서 제거
        if task_id in self.processing_tasks:
            del self.processing_tasks[task_id]
            
            # 워커 할당 해제
            if task_id in self.worker_assignments:
                worker_id = self.worker_assignments[task_id]
                if worker_id in self.workers:
                    self.workers[worker_id].current_tasks -= 1
                del self.worker_assignments[task_id]
        
        # Redis 업데이트
        if self.redis_client:
            await self._save_task_to_redis(task)
        
        logger.info(f"작업 취소: {task_id}")
        return True

    async def register_worker(
        self,
        worker_id: str,
        worker_type: str,
        supported_tasks: List[AIServiceType],
        max_concurrent_tasks: int = 1
    ):
        """워커 등록"""
        worker_info = WorkerInfo(
            worker_id=worker_id,
            worker_type=worker_type,
            supported_tasks=supported_tasks,
            max_concurrent_tasks=max_concurrent_tasks,
            current_tasks=0,
            status="active",
            last_heartbeat=datetime.now(),
            performance_metrics={}
        )
        
        self.workers[worker_id] = worker_info
        logger.info(f"워커 등록: {worker_id} ({worker_type})")

    async def unregister_worker(self, worker_id: str):
        """워커 등록 해제"""
        if worker_id in self.workers:
            # 해당 워커의 작업들을 다시 큐에 추가
            tasks_to_requeue = [
                task_id for task_id, assigned_worker in self.worker_assignments.items()
                if assigned_worker == worker_id
            ]
            
            for task_id in tasks_to_requeue:
                task = self.processing_tasks.get(task_id)
                if task:
                    task.status = TaskStatus.QUEUED
                    task.progress = 0.0
                    task.current_step = "워커 재할당 대기"
                    await self._add_to_queue(task)
                    del self.processing_tasks[task_id]
                del self.worker_assignments[task_id]
            
            del self.workers[worker_id]
            logger.info(f"워커 등록 해제: {worker_id}")

    async def worker_heartbeat(self, worker_id: str, metrics: Optional[Dict[str, Any]] = None):
        """워커 하트비트"""
        if worker_id in self.workers:
            self.workers[worker_id].last_heartbeat = datetime.now()
            if metrics:
                self.workers[worker_id].performance_metrics.update(metrics)

    def register_callback(self, event: str, callback: Callable):
        """콜백 함수 등록"""
        if event in self.task_callbacks:
            self.task_callbacks[event].append(callback)

    async def _add_to_queue(self, task: AITask):
        """큐에 작업 추가"""
        task.status = TaskStatus.QUEUED
        heapq.heappush(self.pending_queue, task)

    async def _find_task(self, task_id: str) -> Optional[AITask]:
        """작업 찾기"""
        # 처리 중인 작업에서 찾기
        if task_id in self.processing_tasks:
            return self.processing_tasks[task_id]
        
        # 완료된 작업에서 찾기
        if task_id in self.completed_tasks:
            return self.completed_tasks[task_id]
        
        # 실패한 작업에서 찾기
        if task_id in self.failed_tasks:
            return self.failed_tasks[task_id]
        
        # 대기 중인 작업에서 찾기
        for task in self.pending_queue:
            if task.task_id == task_id:
                return task
        
        return None

    async def _check_dependencies(self, task: AITask) -> bool:
        """의존성 검사"""
        for dep_task_id in task.dependencies:
            dep_task = await self._find_task(dep_task_id)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                return False
        return True

    async def _resolve_dependencies(self, completed_task_id: str):
        """의존성 해결"""
        # 대기 중인 작업들 중에서 이 작업을 기다리던 것들 찾기
        tasks_to_activate = []
        
        for task in list(self.pending_queue):
            if completed_task_id in task.dependencies:
                if await self._check_dependencies(task):
                    tasks_to_activate.append(task)
        
        # 활성화할 작업들을 큐에서 제거하고 다시 추가
        for task in tasks_to_activate:
            self.pending_queue.remove(task)
            await self._add_to_queue(task)
        
        if tasks_to_activate:
            heapq.heapify(self.pending_queue)

    async def _process_queue(self):
        """큐 처리 루프"""
        while True:
            try:
                await asyncio.sleep(1)  # 1초마다 확인
                
                if not self.pending_queue:
                    continue
                
                # 사용 가능한 워커 찾기
                available_worker = await self._find_available_worker()
                if not available_worker:
                    continue
                
                # 우선순위가 가장 높은 작업 가져오기
                task = heapq.heappop(self.pending_queue)
                
                # 워커가 이 작업을 처리할 수 있는지 확인
                if task.task_type not in available_worker.supported_tasks:
                    # 다시 큐에 추가
                    heapq.heappush(self.pending_queue, task)
                    continue
                
                # 작업 할당
                await self._assign_task_to_worker(task, available_worker)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"큐 처리 중 오류: {str(e)}")

    async def _find_available_worker(self) -> Optional[WorkerInfo]:
        """사용 가능한 워커 찾기"""
        for worker in self.workers.values():
            if (worker.status == "active" and 
                worker.current_tasks < worker.max_concurrent_tasks):
                return worker
        return None

    async def _assign_task_to_worker(self, task: AITask, worker: WorkerInfo):
        """워커에 작업 할당"""
        task.status = TaskStatus.PROCESSING
        task.started_at = datetime.now()
        task.current_step = "처리 시작"
        
        # 작업 이동
        self.processing_tasks[task.task_id] = task
        self.worker_assignments[task.task_id] = worker.worker_id
        worker.current_tasks += 1
        
        # 실제 작업 실행
        if self.celery_app:
            # Celery로 비동기 실행
            self.celery_app.send_task(
                f'process_{task.task_type.value}',
                args=[task.task_id, task.payload],
                task_id=task.task_id
            )
        else:
            # 직접 실행
            asyncio.create_task(self._execute_task(task))
        
        # 콜백 실행
        await self._execute_callbacks("on_task_start", task)
        
        logger.info(f"작업 할당: {task.task_id} -> {worker.worker_id}")

    async def _execute_task(self, task: AITask):
        """작업 직접 실행 (Celery 없이)"""
        try:
            # AI 서비스 호출
            result = await self._call_ai_service(task)
            await self.complete_task(task.task_id, result)
            
        except Exception as e:
            await self.fail_task(task.task_id, str(e))

    async def _call_ai_service(self, task: AITask) -> Dict[str, Any]:
        """AI 서비스 호출"""
        service_urls = {
            AIServiceType.OCR: "http://localhost:8001",
            AIServiceType.SEGMENTATION: "http://localhost:8002",
            AIServiceType.STYLE_TRANSFER: "http://localhost:8003",
            AIServiceType.PUZZLE_GENERATION: "http://localhost:8004",
            AIServiceType.COMPLEXITY_ANALYSIS: "http://localhost:8004"
        }
        
        base_url = service_urls.get(task.task_type)
        if not base_url:
            raise ValueError(f"지원하지 않는 작업 타입: {task.task_type}")
        
        # 진행률 업데이트
        await self.update_task_progress(task.task_id, 0.1, "AI 서비스 연결 중")
        
        async with aiohttp.ClientSession() as session:
            # 서비스별 엔드포인트 결정
            endpoint = self._get_service_endpoint(task.task_type)
            url = f"{base_url}{endpoint}"
            
            await self.update_task_progress(task.task_id, 0.3, "요청 전송 중")
            
            # 요청 전송
            async with session.post(url, json=task.payload) as response:
                if response.status == 200:
                    result = await response.json()
                    await self.update_task_progress(task.task_id, 0.9, "결과 처리 중")
                    return result
                else:
                    error_text = await response.text()
                    raise Exception(f"AI 서비스 오류 ({response.status}): {error_text}")

    def _get_service_endpoint(self, task_type: AIServiceType) -> str:
        """서비스 타입별 엔드포인트 반환"""
        endpoints = {
            AIServiceType.OCR: "/api/v1/ocr/extract",
            AIServiceType.SEGMENTATION: "/api/v1/segment/image",
            AIServiceType.STYLE_TRANSFER: "/api/v1/style/transfer",
            AIServiceType.PUZZLE_GENERATION: "/api/v1/puzzles/generate",
            AIServiceType.COMPLEXITY_ANALYSIS: "/api/v1/analyze/complexity"
        }
        return endpoints.get(task_type, "/")

    async def _retry_task_after_delay(self, task: AITask):
        """지연 후 작업 재시도"""
        await asyncio.sleep(task.retry_delay)
        
        # 처리 중에서 제거하고 큐에 다시 추가
        if task.task_id in self.processing_tasks:
            del self.processing_tasks[task.task_id]
        
        await self._add_to_queue(task)

    async def _execute_callbacks(self, event: str, task: AITask):
        """콜백 함수 실행"""
        if event in self.task_callbacks:
            for callback in self.task_callbacks[event]:
                try:
                    await callback(task)
                except Exception as e:
                    logger.error(f"콜백 실행 중 오류: {str(e)}")

    async def _update_stats(self):
        """통계 업데이트 루프"""
        while True:
            try:
                await asyncio.sleep(60)  # 1분마다 업데이트
                
                self.stats.update({
                    "pending_tasks": len(self.pending_queue),
                    "processing_tasks": len(self.processing_tasks),
                    "completed_tasks": len(self.completed_tasks),
                    "failed_tasks": len(self.failed_tasks),
                })
                
                # 평균 처리 시간 계산
                if self.completed_tasks:
                    total_time = 0
                    count = 0
                    for task in self.completed_tasks.values():
                        if task.started_at and task.completed_at:
                            duration = (task.completed_at - task.started_at).total_seconds()
                            total_time += duration
                            count += 1
                    
                    if count > 0:
                        self.stats["average_processing_time"] = total_time / count
                
                # Redis에 통계 저장
                if self.redis_client:
                    await self.redis_client.hset("ai_queue:stats", mapping=self.stats)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"통계 업데이트 중 오류: {str(e)}")

    async def _cleanup_old_tasks(self):
        """오래된 작업 정리"""
        while True:
            try:
                await asyncio.sleep(3600)  # 1시간마다 실행
                
                cutoff_time = datetime.now() - timedelta(days=7)  # 7일 이전
                
                # 완료된 작업 정리
                old_completed = [
                    task_id for task_id, task in self.completed_tasks.items()
                    if task.completed_at and task.completed_at < cutoff_time
                ]
                
                for task_id in old_completed:
                    del self.completed_tasks[task_id]
                
                # 실패한 작업 정리
                old_failed = [
                    task_id for task_id, task in self.failed_tasks.items()
                    if task.completed_at and task.completed_at < cutoff_time
                ]
                
                for task_id in old_failed:
                    del self.failed_tasks[task_id]
                
                if old_completed or old_failed:
                    logger.info(f"오래된 작업 정리: 완료 {len(old_completed)}개, 실패 {len(old_failed)}개")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"작업 정리 중 오류: {str(e)}")

    async def _save_task_to_redis(self, task: AITask):
        """Redis에 작업 저장"""
        if not self.redis_client:
            return
        
        try:
            key = f"ai_task:{task.task_id}"
            await self.redis_client.hset(key, mapping=task.to_dict())
            await self.redis_client.expire(key, 86400 * 7)  # 7일 TTL
        except Exception as e:
            logger.error(f"Redis 작업 저장 실패: {str(e)}")

    async def _save_tasks_to_redis(self):
        """모든 작업을 Redis에 저장"""
        if not self.redis_client:
            return
        
        try:
            # 진행 중인 작업들만 저장 (복원 시 필요)
            for task in self.processing_tasks.values():
                await self._save_task_to_redis(task)
            
            for task in self.pending_queue:
                await self._save_task_to_redis(task)
                
        except Exception as e:
            logger.error(f"Redis 작업 일괄 저장 실패: {str(e)}")

    async def _restore_tasks_from_redis(self):
        """Redis에서 작업 복원"""
        if not self.redis_client:
            return
        
        try:
            # 작업 키 패턴으로 검색
            keys = await self.redis_client.keys("ai_task:*")
            
            for key in keys:
                task_data = await self.redis_client.hgetall(key)
                if task_data:
                    # 작업 객체 복원
                    task = self._restore_task_from_dict(task_data)
                    if task:
                        # 상태에 따라 적절한 컬렉션에 추가
                        if task.status == TaskStatus.PROCESSING:
                            # 처리 중이던 작업은 다시 큐에 추가
                            task.status = TaskStatus.QUEUED
                            await self._add_to_queue(task)
                        elif task.status == TaskStatus.QUEUED:
                            await self._add_to_queue(task)
                        elif task.status == TaskStatus.COMPLETED:
                            self.completed_tasks[task.task_id] = task
                        elif task.status == TaskStatus.FAILED:
                            self.failed_tasks[task.task_id] = task
            
            logger.info(f"Redis에서 {len(keys)}개 작업 복원 완료")
            
        except Exception as e:
            logger.error(f"Redis 작업 복원 실패: {str(e)}")

    def _restore_task_from_dict(self, task_data: Dict[str, Any]) -> Optional[AITask]:
        """딕셔너리에서 작업 객체 복원"""
        try:
            # 문자열을 적절한 타입으로 변환
            task_data['task_type'] = AIServiceType(task_data['task_type'])
            task_data['priority'] = TaskPriority(task_data['priority'])
            task_data['status'] = TaskStatus(task_data['status'])
            task_data['created_at'] = datetime.fromisoformat(task_data['created_at'])
            
            if task_data.get('started_at'):
                task_data['started_at'] = datetime.fromisoformat(task_data['started_at'])
            if task_data.get('completed_at'):
                task_data['completed_at'] = datetime.fromisoformat(task_data['completed_at'])
            
            # JSON 문자열을 딕셔너리로 변환
            if isinstance(task_data.get('payload'), str):
                task_data['payload'] = json.loads(task_data['payload'])
            if isinstance(task_data.get('result'), str):
                task_data['result'] = json.loads(task_data['result'])
            if isinstance(task_data.get('dependencies'), str):
                task_data['dependencies'] = json.loads(task_data['dependencies'])
            
            return AITask(**task_data)
            
        except Exception as e:
            logger.error(f"작업 복원 실패: {str(e)}")
            return None

    def _setup_celery_tasks(self):
        """Celery 작업 설정"""
        if not self.celery_app:
            return
        
        @self.celery_app.task(bind=True)
        def process_ocr(self, task_id: str, payload: Dict[str, Any]):
            # OCR 처리 로직
            pass
        
        @self.celery_app.task(bind=True)
        def process_segmentation(self, task_id: str, payload: Dict[str, Any]):
            # 세그멘테이션 처리 로직
            pass
        
        @self.celery_app.task(bind=True)
        def process_style_transfer(self, task_id: str, payload: Dict[str, Any]):
            # 스타일 변환 처리 로직
            pass

    def get_queue_stats(self) -> Dict[str, Any]:
        """큐 통계 조회"""
        return {
            **self.stats,
            "workers": {
                worker_id: {
                    "type": worker.worker_type,
                    "status": worker.status,
                    "current_tasks": worker.current_tasks,
                    "max_tasks": worker.max_concurrent_tasks,
                    "last_heartbeat": worker.last_heartbeat.isoformat()
                }
                for worker_id, worker in self.workers.items()
            }
        }


# 전역 AI 작업 큐 인스턴스
ai_task_queue = AITaskQueue()