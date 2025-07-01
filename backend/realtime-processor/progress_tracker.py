"""
PuzzleCraft AI - 진행률 추적 시스템
실시간 AI 작업 진행률 추적 및 예측 시스템
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import statistics
from collections import deque, defaultdict

import redis.asyncio as redis

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProgressStage(Enum):
    """진행 단계"""
    INITIALIZATION = "initialization"
    PREPROCESSING = "preprocessing"
    AI_PROCESSING = "ai_processing"
    POSTPROCESSING = "postprocessing"
    FINALIZATION = "finalization"
    COMPLETED = "completed"
    ERROR = "error"


class ProgressMetric(Enum):
    """진행률 측정 지표"""
    PERCENTAGE = "percentage"
    ITEMS_PROCESSED = "items_processed"
    BYTES_PROCESSED = "bytes_processed"
    TIME_ELAPSED = "time_elapsed"
    ESTIMATED_REMAINING = "estimated_remaining"


@dataclass
class ProgressStep:
    """진행 단계 정보"""
    step_id: str
    name: str
    description: str
    stage: ProgressStage
    weight: float  # 전체 진행률에서 차지하는 비중 (0.0 - 1.0)
    progress: float = 0.0  # 이 단계의 진행률 (0.0 - 1.0)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_duration: Optional[int] = None  # seconds
    actual_duration: Optional[int] = None  # seconds
    status: str = "pending"  # pending, active, completed, failed, skipped
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ProgressSnapshot:
    """진행률 스냅샷"""
    task_id: str
    timestamp: datetime
    overall_progress: float
    current_stage: ProgressStage
    current_step: str
    steps: List[ProgressStep]
    estimated_completion: Optional[datetime]
    performance_metrics: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "timestamp": self.timestamp.isoformat(),
            "overall_progress": self.overall_progress,
            "current_stage": self.current_stage.value,
            "current_step": self.current_step,
            "steps": [asdict(step) for step in self.steps],
            "estimated_completion": self.estimated_completion.isoformat() if self.estimated_completion else None,
            "performance_metrics": self.performance_metrics
        }


@dataclass
class PerformanceMetrics:
    """성능 지표"""
    throughput: float  # items/second
    processing_rate: float  # bytes/second
    cpu_usage: float  # percentage
    memory_usage: float  # bytes
    network_io: float  # bytes/second
    disk_io: float  # bytes/second
    error_rate: float  # percentage
    latency: float  # milliseconds


class ProgressTracker:
    """진행률 추적기"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        """초기화"""
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        
        # 진행률 데이터
        self.task_progress: Dict[str, List[ProgressStep]] = {}
        self.progress_history: Dict[str, deque] = {}  # task_id -> deque of snapshots
        self.performance_history: Dict[str, deque] = {}  # task_id -> deque of metrics
        
        # 예측 모델 데이터
        self.historical_durations: Dict[str, List[float]] = defaultdict(list)  # step_type -> durations
        self.completion_patterns: Dict[str, List[Tuple[float, float]]] = defaultdict(list)  # task_type -> (progress, time)
        
        # 콜백 함수들
        self.progress_callbacks: Dict[str, List[Callable]] = {
            "on_step_start": [],
            "on_step_progress": [],
            "on_step_complete": [],
            "on_stage_change": [],
            "on_milestone": [],
        }
        
        # 설정
        self.max_history_size = 1000
        self.snapshot_interval = 5  # seconds
        self.prediction_window = 100  # number of historical data points to use
        
        # 백그라운드 작업
        self._snapshot_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
        logger.info("진행률 추적기 초기화 완료")

    async def initialize(self):
        """비동기 초기화"""
        try:
            # Redis 연결
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("Redis 연결 성공")
            
            # 기존 데이터 복원
            await self._restore_progress_data()
            
        except Exception as e:
            logger.warning(f"Redis 연결 실패: {str(e)}, 메모리 모드로 동작")
            self.redis_client = None
        
        # 백그라운드 작업 시작
        self._snapshot_task = asyncio.create_task(self._periodic_snapshot())
        self._cleanup_task = asyncio.create_task(self._cleanup_old_data())

    async def shutdown(self):
        """종료 처리"""
        logger.info("진행률 추적기 종료 중...")
        
        # 백그라운드 작업 중단
        for task in [self._snapshot_task, self._cleanup_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Redis에 데이터 저장
        if self.redis_client:
            await self._save_progress_data()
            await self.redis_client.close()
        
        logger.info("진행률 추적기 종료 완료")

    async def start_tracking(
        self,
        task_id: str,
        steps: List[Dict[str, Any]],
        task_type: str = "default"
    ) -> bool:
        """작업 추적 시작"""
        try:
            # 진행 단계 생성
            progress_steps = []
            total_weight = 0.0
            
            for step_data in steps:
                step = ProgressStep(
                    step_id=step_data.get("step_id", str(uuid.uuid4())),
                    name=step_data["name"],
                    description=step_data.get("description", ""),
                    stage=ProgressStage(step_data.get("stage", "ai_processing")),
                    weight=step_data.get("weight", 1.0 / len(steps)),
                    estimated_duration=step_data.get("estimated_duration")
                )
                progress_steps.append(step)
                total_weight += step.weight
            
            # 가중치 정규화
            if total_weight > 0:
                for step in progress_steps:
                    step.weight = step.weight / total_weight
            
            # 과거 데이터를 기반으로 예상 시간 조정
            await self._adjust_estimates_from_history(progress_steps, task_type)
            
            # 추적 시작
            self.task_progress[task_id] = progress_steps
            self.progress_history[task_id] = deque(maxlen=self.max_history_size)
            self.performance_history[task_id] = deque(maxlen=self.max_history_size)
            
            # 첫 번째 스냅샷 생성
            await self._create_snapshot(task_id)
            
            logger.info(f"작업 추적 시작: {task_id} ({len(progress_steps)}개 단계)")
            return True
            
        except Exception as e:
            logger.error(f"작업 추적 시작 실패: {str(e)}")
            return False

    async def update_step_progress(
        self,
        task_id: str,
        step_id: str,
        progress: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """단계 진행률 업데이트"""
        if task_id not in self.task_progress:
            logger.warning(f"추적되지 않는 작업: {task_id}")
            return False
        
        try:
            # 해당 단계 찾기
            step = None
            for s in self.task_progress[task_id]:
                if s.step_id == step_id:
                    step = s
                    break
            
            if not step:
                logger.warning(f"단계를 찾을 수 없음: {step_id}")
                return False
            
            # 진행률 업데이트
            old_progress = step.progress
            step.progress = max(0.0, min(1.0, progress))
            
            # 메타데이터 업데이트
            if metadata:
                step.metadata.update(metadata)
            
            # 단계 시작 처리
            if old_progress == 0.0 and step.progress > 0.0:
                step.started_at = datetime.now()
                step.status = "active"
                await self._execute_callbacks("on_step_start", task_id, step)
            
            # 단계 완료 처리
            if step.progress >= 1.0 and step.status != "completed":
                step.completed_at = datetime.now()
                step.status = "completed"
                if step.started_at:
                    step.actual_duration = int((step.completed_at - step.started_at).total_seconds())
                    # 과거 데이터에 추가
                    step_type = f"{step.stage.value}_{step.name}"
                    self.historical_durations[step_type].append(step.actual_duration)
                
                await self._execute_callbacks("on_step_complete", task_id, step)
            
            # 진행률 변화 콜백
            if old_progress != step.progress:
                await self._execute_callbacks("on_step_progress", task_id, step)
            
            # 스냅샷 업데이트
            await self._create_snapshot(task_id)
            
            return True
            
        except Exception as e:
            logger.error(f"단계 진행률 업데이트 실패: {str(e)}")
            return False

    async def complete_step(
        self,
        task_id: str,
        step_id: str,
        result: Optional[Dict[str, Any]] = None
    ) -> bool:
        """단계 완료"""
        return await self.update_step_progress(task_id, step_id, 1.0, result)

    async def fail_step(
        self,
        task_id: str,
        step_id: str,
        error_message: str
    ) -> bool:
        """단계 실패"""
        if task_id not in self.task_progress:
            return False
        
        try:
            # 해당 단계 찾기
            step = None
            for s in self.task_progress[task_id]:
                if s.step_id == step_id:
                    step = s
                    break
            
            if not step:
                return False
            
            step.status = "failed"
            step.error_message = error_message
            step.completed_at = datetime.now()
            
            if step.started_at:
                step.actual_duration = int((step.completed_at - step.started_at).total_seconds())
            
            # 스냅샷 업데이트
            await self._create_snapshot(task_id)
            
            logger.warning(f"단계 실패: {step_id} - {error_message}")
            return True
            
        except Exception as e:
            logger.error(f"단계 실패 처리 실패: {str(e)}")
            return False

    async def skip_step(self, task_id: str, step_id: str, reason: str = "") -> bool:
        """단계 건너뛰기"""
        if task_id not in self.task_progress:
            return False
        
        try:
            # 해당 단계 찾기
            step = None
            for s in self.task_progress[task_id]:
                if s.step_id == step_id:
                    step = s
                    break
            
            if not step:
                return False
            
            step.status = "skipped"
            step.progress = 1.0  # 건너뛴 단계는 완료로 처리
            step.completed_at = datetime.now()
            step.metadata["skip_reason"] = reason
            
            # 스냅샷 업데이트
            await self._create_snapshot(task_id)
            
            logger.info(f"단계 건너뛰기: {step_id} - {reason}")
            return True
            
        except Exception as e:
            logger.error(f"단계 건너뛰기 실패: {str(e)}")
            return False

    async def get_progress_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """진행률 상태 조회"""
        if task_id not in self.task_progress:
            return None
        
        try:
            steps = self.task_progress[task_id]
            
            # 전체 진행률 계산
            overall_progress = sum(step.progress * step.weight for step in steps)
            
            # 현재 단계 찾기
            current_step = None
            current_stage = ProgressStage.INITIALIZATION
            
            for step in steps:
                if step.status == "active":
                    current_step = step.name
                    current_stage = step.stage
                    break
                elif step.status in ["pending"] and current_step is None:
                    current_step = step.name
                    current_stage = step.stage
                    break
            
            if current_step is None:
                # 모든 단계가 완료되었거나 실패
                if all(step.status in ["completed", "skipped"] for step in steps):
                    current_step = "완료"
                    current_stage = ProgressStage.COMPLETED
                else:
                    current_step = "오류"
                    current_stage = ProgressStage.ERROR
            
            # 예상 완료 시간 계산
            estimated_completion = await self._estimate_completion_time(task_id)
            
            # 성능 지표 계산
            performance_metrics = await self._calculate_performance_metrics(task_id)
            
            return {
                "task_id": task_id,
                "overall_progress": overall_progress,
                "current_stage": current_stage.value,
                "current_step": current_step,
                "estimated_completion": estimated_completion.isoformat() if estimated_completion else None,
                "steps": [
                    {
                        "step_id": step.step_id,
                        "name": step.name,
                        "description": step.description,
                        "stage": step.stage.value,
                        "progress": step.progress,
                        "status": step.status,
                        "weight": step.weight,
                        "started_at": step.started_at.isoformat() if step.started_at else None,
                        "completed_at": step.completed_at.isoformat() if step.completed_at else None,
                        "estimated_duration": step.estimated_duration,
                        "actual_duration": step.actual_duration,
                        "error_message": step.error_message,
                        "metadata": step.metadata
                    }
                    for step in steps
                ],
                "performance_metrics": performance_metrics,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"진행률 상태 조회 실패: {str(e)}")
            return None

    async def get_progress_history(
        self,
        task_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """진행률 히스토리 조회"""
        if task_id not in self.progress_history:
            return []
        
        history = list(self.progress_history[task_id])
        if limit > 0:
            history = history[-limit:]
        
        return [snapshot.to_dict() for snapshot in history]

    async def stop_tracking(self, task_id: str) -> bool:
        """작업 추적 중단"""
        try:
            if task_id in self.task_progress:
                # 최종 스냅샷 생성
                await self._create_snapshot(task_id)
                
                # Redis에 저장
                if self.redis_client:
                    await self._save_task_progress(task_id)
                
                # 메모리에서 제거 (히스토리는 유지)
                del self.task_progress[task_id]
                
                logger.info(f"작업 추적 중단: {task_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"작업 추적 중단 실패: {str(e)}")
            return False

    def register_callback(self, event: str, callback: Callable):
        """콜백 함수 등록"""
        if event in self.progress_callbacks:
            self.progress_callbacks[event].append(callback)

    async def _create_snapshot(self, task_id: str):
        """진행률 스냅샷 생성"""
        if task_id not in self.task_progress:
            return
        
        try:
            steps = self.task_progress[task_id]
            overall_progress = sum(step.progress * step.weight for step in steps)
            
            # 현재 단계 및 스테이지 결정
            current_step = "초기화"
            current_stage = ProgressStage.INITIALIZATION
            
            for step in steps:
                if step.status == "active":
                    current_step = step.name
                    current_stage = step.stage
                    break
                elif step.status == "pending":
                    current_step = step.name
                    current_stage = step.stage
                    break
            
            # 예상 완료 시간
            estimated_completion = await self._estimate_completion_time(task_id)
            
            # 성능 지표
            performance_metrics = await self._calculate_performance_metrics(task_id)
            
            # 스냅샷 생성
            snapshot = ProgressSnapshot(
                task_id=task_id,
                timestamp=datetime.now(),
                overall_progress=overall_progress,
                current_stage=current_stage,
                current_step=current_step,
                steps=steps.copy(),
                estimated_completion=estimated_completion,
                performance_metrics=performance_metrics
            )
            
            # 히스토리에 추가
            self.progress_history[task_id].append(snapshot)
            
        except Exception as e:
            logger.error(f"스냅샷 생성 실패: {str(e)}")

    async def _estimate_completion_time(self, task_id: str) -> Optional[datetime]:
        """완료 시간 예측"""
        if task_id not in self.task_progress:
            return None
        
        try:
            steps = self.task_progress[task_id]
            current_time = datetime.now()
            
            # 남은 작업량 계산
            remaining_work = 0.0
            estimated_remaining_time = 0.0
            
            for step in steps:
                if step.status in ["pending", "active"]:
                    remaining_progress = 1.0 - step.progress
                    remaining_work += remaining_progress * step.weight
                    
                    # 예상 시간 계산
                    if step.estimated_duration:
                        if step.status == "active" and step.started_at:
                            # 현재 진행 중인 단계
                            elapsed = (current_time - step.started_at).total_seconds()
                            if step.progress > 0:
                                estimated_total = elapsed / step.progress
                                estimated_remaining_time += max(0, estimated_total - elapsed)
                            else:
                                estimated_remaining_time += step.estimated_duration
                        else:
                            # 대기 중인 단계
                            estimated_remaining_time += step.estimated_duration * remaining_progress
            
            if estimated_remaining_time > 0:
                return current_time + timedelta(seconds=estimated_remaining_time)
            
            return None
            
        except Exception as e:
            logger.error(f"완료 시간 예측 실패: {str(e)}")
            return None

    async def _calculate_performance_metrics(self, task_id: str) -> Dict[str, Any]:
        """성능 지표 계산"""
        try:
            if task_id not in self.progress_history or not self.progress_history[task_id]:
                return {}
            
            history = list(self.progress_history[task_id])
            
            if len(history) < 2:
                return {}
            
            # 최근 데이터 분석
            recent_snapshots = history[-10:]  # 최근 10개 스냅샷
            
            # 처리 속도 계산
            time_diffs = []
            progress_diffs = []
            
            for i in range(1, len(recent_snapshots)):
                prev = recent_snapshots[i-1]
                curr = recent_snapshots[i]
                
                time_diff = (curr.timestamp - prev.timestamp).total_seconds()
                progress_diff = curr.overall_progress - prev.overall_progress
                
                if time_diff > 0:
                    time_diffs.append(time_diff)
                    progress_diffs.append(progress_diff)
            
            # 평균 처리 속도
            avg_speed = 0.0
            if time_diffs and progress_diffs:
                total_progress = sum(progress_diffs)
                total_time = sum(time_diffs)
                if total_time > 0:
                    avg_speed = total_progress / total_time
            
            # 예상 남은 시간
            current_progress = recent_snapshots[-1].overall_progress
            remaining_progress = 1.0 - current_progress
            estimated_remaining = 0.0
            
            if avg_speed > 0:
                estimated_remaining = remaining_progress / avg_speed
            
            return {
                "processing_speed": avg_speed,  # progress per second
                "estimated_remaining_seconds": estimated_remaining,
                "total_snapshots": len(history),
                "current_progress": current_progress,
                "remaining_progress": remaining_progress
            }
            
        except Exception as e:
            logger.error(f"성능 지표 계산 실패: {str(e)}")
            return {}

    async def _adjust_estimates_from_history(
        self,
        steps: List[ProgressStep],
        task_type: str
    ):
        """과거 데이터를 기반으로 예상 시간 조정"""
        try:
            for step in steps:
                step_type = f"{step.stage.value}_{step.name}"
                
                if step_type in self.historical_durations:
                    durations = self.historical_durations[step_type]
                    if durations:
                        # 최근 데이터에 더 높은 가중치
                        recent_durations = durations[-self.prediction_window:]
                        if len(recent_durations) >= 3:
                            # 중앙값 사용 (이상치 제거)
                            estimated = statistics.median(recent_durations)
                            step.estimated_duration = int(estimated)
                        elif step.estimated_duration is None:
                            # 평균값 사용
                            step.estimated_duration = int(statistics.mean(recent_durations))
                            
        except Exception as e:
            logger.error(f"예상 시간 조정 실패: {str(e)}")

    async def _execute_callbacks(self, event: str, task_id: str, step: ProgressStep):
        """콜백 함수 실행"""
        if event in self.progress_callbacks:
            for callback in self.progress_callbacks[event]:
                try:
                    await callback(task_id, step)
                except Exception as e:
                    logger.error(f"콜백 실행 중 오류: {str(e)}")

    async def _periodic_snapshot(self):
        """주기적 스냅샷 생성"""
        while True:
            try:
                await asyncio.sleep(self.snapshot_interval)
                
                # 모든 활성 작업에 대해 스냅샷 생성
                for task_id in list(self.task_progress.keys()):
                    await self._create_snapshot(task_id)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"주기적 스냅샷 생성 중 오류: {str(e)}")

    async def _cleanup_old_data(self):
        """오래된 데이터 정리"""
        while True:
            try:
                await asyncio.sleep(3600)  # 1시간마다 실행
                
                cutoff_time = datetime.now() - timedelta(days=7)
                
                # 오래된 히스토리 정리
                for task_id in list(self.progress_history.keys()):
                    history = self.progress_history[task_id]
                    
                    # 오래된 스냅샷 제거
                    while history and history[0].timestamp < cutoff_time:
                        history.popleft()
                    
                    # 빈 히스토리 제거
                    if not history:
                        del self.progress_history[task_id]
                
                # 과거 성능 데이터 정리
                for task_id in list(self.performance_history.keys()):
                    perf_history = self.performance_history[task_id]
                    
                    # 오래된 데이터 제거 (구체적인 로직은 데이터 구조에 따라)
                    if not perf_history:
                        del self.performance_history[task_id]
                
                # 과거 지속 시간 데이터 제한
                for step_type in self.historical_durations:
                    durations = self.historical_durations[step_type]
                    if len(durations) > self.prediction_window * 2:
                        # 최근 데이터만 유지
                        self.historical_durations[step_type] = durations[-self.prediction_window:]
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"데이터 정리 중 오류: {str(e)}")

    async def _save_progress_data(self):
        """Redis에 진행률 데이터 저장"""
        if not self.redis_client:
            return
        
        try:
            # 활성 작업 진행률 저장
            for task_id in self.task_progress:
                await self._save_task_progress(task_id)
            
            # 과거 지속 시간 데이터 저장
            if self.historical_durations:
                await self.redis_client.hset(
                    "progress:historical_durations",
                    mapping={
                        step_type: json.dumps(durations)
                        for step_type, durations in self.historical_durations.items()
                    }
                )
                
        except Exception as e:
            logger.error(f"진행률 데이터 저장 실패: {str(e)}")

    async def _save_task_progress(self, task_id: str):
        """특정 작업의 진행률 저장"""
        if not self.redis_client or task_id not in self.task_progress:
            return
        
        try:
            steps_data = []
            for step in self.task_progress[task_id]:
                step_dict = asdict(step)
                # datetime 객체를 문자열로 변환
                if step_dict.get('started_at'):
                    step_dict['started_at'] = step.started_at.isoformat()
                if step_dict.get('completed_at'):
                    step_dict['completed_at'] = step.completed_at.isoformat()
                step_dict['stage'] = step.stage.value
                steps_data.append(step_dict)
            
            key = f"progress:task:{task_id}"
            await self.redis_client.set(key, json.dumps(steps_data))
            await self.redis_client.expire(key, 86400 * 7)  # 7일 TTL
            
        except Exception as e:
            logger.error(f"작업 진행률 저장 실패: {str(e)}")

    async def _restore_progress_data(self):
        """Redis에서 진행률 데이터 복원"""
        if not self.redis_client:
            return
        
        try:
            # 과거 지속 시간 데이터 복원
            durations_data = await self.redis_client.hgetall("progress:historical_durations")
            if durations_data:
                for step_type, durations_json in durations_data.items():
                    try:
                        durations = json.loads(durations_json)
                        self.historical_durations[step_type] = durations
                    except json.JSONDecodeError:
                        continue
            
            # 활성 작업 진행률 복원
            keys = await self.redis_client.keys("progress:task:*")
            for key in keys:
                try:
                    task_id = key.split(":")[-1]
                    steps_json = await self.redis_client.get(key)
                    if steps_json:
                        steps_data = json.loads(steps_json)
                        steps = []
                        
                        for step_dict in steps_data:
                            # 문자열을 datetime 객체로 변환
                            if step_dict.get('started_at'):
                                step_dict['started_at'] = datetime.fromisoformat(step_dict['started_at'])
                            if step_dict.get('completed_at'):
                                step_dict['completed_at'] = datetime.fromisoformat(step_dict['completed_at'])
                            step_dict['stage'] = ProgressStage(step_dict['stage'])
                            
                            step = ProgressStep(**step_dict)
                            steps.append(step)
                        
                        self.task_progress[task_id] = steps
                        self.progress_history[task_id] = deque(maxlen=self.max_history_size)
                        
                except Exception as e:
                    logger.error(f"작업 진행률 복원 실패 {key}: {str(e)}")
                    continue
            
            logger.info(f"진행률 데이터 복원 완료: {len(self.task_progress)}개 작업")
            
        except Exception as e:
            logger.error(f"진행률 데이터 복원 실패: {str(e)}")

    def get_global_statistics(self) -> Dict[str, Any]:
        """전역 통계 조회"""
        try:
            active_tasks = len(self.task_progress)
            total_steps = sum(len(steps) for steps in self.task_progress.values())
            
            # 단계별 평균 지속 시간
            avg_durations = {}
            for step_type, durations in self.historical_durations.items():
                if durations:
                    avg_durations[step_type] = statistics.mean(durations)
            
            # 전체 진행률 분포
            progress_distribution = []
            for steps in self.task_progress.values():
                overall_progress = sum(step.progress * step.weight for step in steps)
                progress_distribution.append(overall_progress)
            
            return {
                "active_tasks": active_tasks,
                "total_steps": total_steps,
                "average_step_durations": avg_durations,
                "progress_distribution": {
                    "min": min(progress_distribution) if progress_distribution else 0,
                    "max": max(progress_distribution) if progress_distribution else 0,
                    "avg": statistics.mean(progress_distribution) if progress_distribution else 0
                },
                "historical_data_points": sum(len(durations) for durations in self.historical_durations.values()),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"전역 통계 조회 실패: {str(e)}")
            return {}


# 전역 진행률 추적기 인스턴스
progress_tracker = ProgressTracker()