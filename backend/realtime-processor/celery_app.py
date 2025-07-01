"""
Celery 애플리케이션 설정
비동기 작업 처리를 위한 Celery 설정 및 태스크 정의
"""

import os
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from celery import Celery, Task
from celery.signals import task_prerun, task_postrun, task_failure, task_success
from celery.exceptions import Retry, WorkerLostError
from kombu import Queue, Exchange

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis URL 설정
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", f"{REDIS_URL}/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", f"{REDIS_URL}/1")

# Celery 애플리케이션 생성
celery_app = Celery(
    "puzzlecraft_realtime",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=[
        "celery_app.tasks.puzzle_tasks",
        "celery_app.tasks.ai_tasks",
        "celery_app.tasks.notification_tasks",
        "celery_app.tasks.image_tasks"
    ]
)

# Celery 설정
celery_app.conf.update(
    # 작업 직렬화
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # 작업 라우팅
    task_routes={
        "celery_app.tasks.puzzle_tasks.*": {"queue": "puzzle_queue"},
        "celery_app.tasks.ai_tasks.*": {"queue": "ai_queue"},
        "celery_app.tasks.notification_tasks.*": {"queue": "notification_queue"},
        "celery_app.tasks.image_tasks.*": {"queue": "image_queue"},
    },
    
    # 큐 설정
    task_default_queue="default",
    task_queues=(
        Queue("default", Exchange("default"), routing_key="default"),
        Queue("puzzle_queue", Exchange("puzzle"), routing_key="puzzle"),
        Queue("ai_queue", Exchange("ai"), routing_key="ai"),
        Queue("notification_queue", Exchange("notification"), routing_key="notification"),
        Queue("image_queue", Exchange("image"), routing_key="image"),
        Queue("priority_queue", Exchange("priority"), routing_key="priority"),
    ),
    
    # 작업 실행 설정
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    
    # 재시도 설정
    task_default_retry_delay=60,  # 60초
    task_max_retries=3,
    
    # 결과 만료 시간
    result_expires=3600,  # 1시간
    
    # 작업 시간 제한
    task_soft_time_limit=300,  # 5분
    task_time_limit=600,  # 10분
    
    # 워커 설정
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=False,
    
    # 모니터링
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # 보안
    worker_hijack_root_logger=False,
    worker_log_color=False,
    
    # 배치 설정
    task_compression="gzip",
    result_compression="gzip",
    
    # 비트 설정
    beat_schedule={
        "cleanup-expired-tasks": {
            "task": "celery_app.tasks.maintenance_tasks.cleanup_expired_tasks",
            "schedule": timedelta(hours=1),
        },
        "health-check": {
            "task": "celery_app.tasks.maintenance_tasks.health_check",
            "schedule": timedelta(minutes=5),
        },
        "update-statistics": {
            "task": "celery_app.tasks.maintenance_tasks.update_statistics",
            "schedule": timedelta(minutes=1),
        },
    },
)


class CallbackTask(Task):
    """콜백 기능이 있는 커스텀 태스크 클래스"""
    
    def __call__(self, *args, **kwargs):
        """태스크 실행"""
        try:
            return super().__call__(*args, **kwargs)
        except Exception as exc:
            logger.error(f"Task {self.name} failed: {exc}")
            raise
    
    def on_success(self, retval, task_id, args, kwargs):
        """태스크 성공 시 콜백"""
        logger.info(f"Task {self.name} succeeded: {task_id}")
        
        # 진행률 추적기 업데이트
        if hasattr(self, 'progress_tracker') and self.progress_tracker:
            asyncio.create_task(
                self.progress_tracker.complete_step(
                    task_id, 
                    "task_execution", 
                    {"result": retval}
                )
            )
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """태스크 실패 시 콜백"""
        logger.error(f"Task {self.name} failed: {task_id}, {exc}")
        
        # 진행률 추적기 업데이트
        if hasattr(self, 'progress_tracker') and self.progress_tracker:
            asyncio.create_task(
                self.progress_tracker.fail_step(
                    task_id,
                    "task_execution",
                    str(exc)
                )
            )
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """태스크 재시도 시 콜백"""
        logger.warning(f"Task {self.name} retrying: {task_id}, {exc}")


# 기본 태스크 클래스 설정
celery_app.Task = CallbackTask


# 시그널 핸들러
@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """태스크 실행 전 핸들러"""
    logger.info(f"Task {task.name} starting: {task_id}")


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    """태스크 실행 후 핸들러"""
    logger.info(f"Task {task.name} finished: {task_id}, state: {state}")


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds):
    """태스크 실패 핸들러"""
    logger.error(f"Task failed: {task_id}, exception: {exception}")


@task_success.connect
def task_success_handler(sender=None, task_id=None, result=None, **kwds):
    """태스크 성공 핸들러"""
    logger.info(f"Task succeeded: {task_id}")


# 헬퍼 함수들
def get_task_info(task_id: str) -> Optional[Dict[str, Any]]:
    """태스크 정보 조회"""
    try:
        result = celery_app.AsyncResult(task_id)
        return {
            "task_id": task_id,
            "state": result.state,
            "result": result.result,
            "traceback": result.traceback,
            "date_done": result.date_done,
            "successful": result.successful(),
            "failed": result.failed(),
        }
    except Exception as e:
        logger.error(f"Failed to get task info: {e}")
        return None


def cancel_task(task_id: str) -> bool:
    """태스크 취소"""
    try:
        celery_app.control.revoke(task_id, terminate=True)
        return True
    except Exception as e:
        logger.error(f"Failed to cancel task: {e}")
        return False


def get_active_tasks() -> List[Dict[str, Any]]:
    """활성 태스크 목록 조회"""
    try:
        inspect = celery_app.control.inspect()
        active_tasks = inspect.active()
        
        if not active_tasks:
            return []
        
        tasks = []
        for worker, task_list in active_tasks.items():
            for task in task_list:
                tasks.append({
                    "worker": worker,
                    "task_id": task["id"],
                    "name": task["name"],
                    "args": task["args"],
                    "kwargs": task["kwargs"],
                    "time_start": task["time_start"],
                })
        
        return tasks
    except Exception as e:
        logger.error(f"Failed to get active tasks: {e}")
        return []


def get_worker_stats() -> Dict[str, Any]:
    """워커 통계 조회"""
    try:
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        
        if not stats:
            return {}
        
        return {
            "workers": len(stats),
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Failed to get worker stats: {e}")
        return {}


def purge_queue(queue_name: str) -> int:
    """큐 비우기"""
    try:
        return celery_app.control.purge()
    except Exception as e:
        logger.error(f"Failed to purge queue: {e}")
        return 0


# 태스크 데코레이터
def puzzle_task(bind=True, **kwargs):
    """퍼즐 태스크 데코레이터"""
    return celery_app.task(
        bind=bind,
        queue="puzzle_queue",
        **kwargs
    )


def ai_task(bind=True, **kwargs):
    """AI 태스크 데코레이터"""
    return celery_app.task(
        bind=bind,
        queue="ai_queue",
        **kwargs
    )


def notification_task(bind=True, **kwargs):
    """알림 태스크 데코레이터"""
    return celery_app.task(
        bind=bind,
        queue="notification_queue",
        **kwargs
    )


def image_task(bind=True, **kwargs):
    """이미지 처리 태스크 데코레이터"""
    return celery_app.task(
        bind=bind,
        queue="image_queue",
        **kwargs
    )


def priority_task(bind=True, **kwargs):
    """우선순위 태스크 데코레이터"""
    return celery_app.task(
        bind=bind,
        queue="priority_queue",
        **kwargs
    )


# 태스크 체인 헬퍼
class TaskChain:
    """태스크 체인 관리 클래스"""
    
    def __init__(self):
        self.tasks = []
    
    def add_task(self, task, *args, **kwargs):
        """태스크 추가"""
        self.tasks.append((task, args, kwargs))
        return self
    
    def execute(self):
        """체인 실행"""
        if not self.tasks:
            return None
        
        # 첫 번째 태스크 실행
        first_task, args, kwargs = self.tasks[0]
        result = first_task.delay(*args, **kwargs)
        
        # 나머지 태스크들을 체인으로 연결
        for task, args, kwargs in self.tasks[1:]:
            result = task.apply_async(args=args, kwargs=kwargs, link=result)
        
        return result


# 태스크 그룹 헬퍼
class TaskGroup:
    """태스크 그룹 관리 클래스"""
    
    def __init__(self):
        self.tasks = []
    
    def add_task(self, task, *args, **kwargs):
        """태스크 추가"""
        self.tasks.append((task, args, kwargs))
        return self
    
    def execute(self):
        """그룹 실행"""
        from celery import group
        
        job = group([
            task.s(*args, **kwargs) 
            for task, args, kwargs in self.tasks
        ])
        
        return job.apply_async()


# 모니터링 클래스
class CeleryMonitor:
    """Celery 모니터링 클래스"""
    
    def __init__(self):
        self.app = celery_app
    
    def get_queue_length(self, queue_name: str) -> int:
        """큐 길이 조회"""
        try:
            with self.app.connection() as conn:
                queue = Queue(queue_name)
                return queue(conn.channel()).queue_declare(passive=True).message_count
        except Exception as e:
            logger.error(f"Failed to get queue length: {e}")
            return 0
    
    def get_worker_count(self) -> int:
        """워커 수 조회"""
        try:
            inspect = self.app.control.inspect()
            stats = inspect.stats()
            return len(stats) if stats else 0
        except Exception as e:
            logger.error(f"Failed to get worker count: {e}")
            return 0
    
    def get_task_count_by_state(self) -> Dict[str, int]:
        """상태별 태스크 수 조회"""
        try:
            inspect = self.app.control.inspect()
            
            # 활성 태스크
            active = inspect.active()
            active_count = sum(len(tasks) for tasks in active.values()) if active else 0
            
            # 예약된 태스크
            scheduled = inspect.scheduled()
            scheduled_count = sum(len(tasks) for tasks in scheduled.values()) if scheduled else 0
            
            # 예약된 태스크 (reserved)
            reserved = inspect.reserved()
            reserved_count = sum(len(tasks) for tasks in reserved.values()) if reserved else 0
            
            return {
                "active": active_count,
                "scheduled": scheduled_count,
                "reserved": reserved_count
            }
        except Exception as e:
            logger.error(f"Failed to get task count by state: {e}")
            return {"active": 0, "scheduled": 0, "reserved": 0}
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """종합 통계 조회"""
        return {
            "worker_count": self.get_worker_count(),
            "task_counts": self.get_task_count_by_state(),
            "queue_lengths": {
                "default": self.get_queue_length("default"),
                "puzzle_queue": self.get_queue_length("puzzle_queue"),
                "ai_queue": self.get_queue_length("ai_queue"),
                "notification_queue": self.get_queue_length("notification_queue"),
                "image_queue": self.get_queue_length("image_queue"),
                "priority_queue": self.get_queue_length("priority_queue"),
            },
            "timestamp": datetime.utcnow().isoformat()
        }


# 전역 모니터 인스턴스
monitor = CeleryMonitor()


if __name__ == "__main__":
    # Celery 워커 실행
    celery_app.start()