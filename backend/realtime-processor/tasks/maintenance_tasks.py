"""
시스템 유지보수 관련 Celery 태스크
정리 작업, 헬스 체크, 통계 업데이트, 백업 등의 유지보수 작업을 처리
"""

import asyncio
import json
import logging
import time
import uuid
import os
import shutil
import psutil
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import requests
import redis.asyncio as redis

from ..celery_app import celery_app
from ..progress_tracker import ProgressTracker
from ..notification_service import NotificationService
from ..websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)

# 유지보수 설정
MAINTENANCE_CONFIG = {
    "cleanup_retention_days": int(os.getenv("CLEANUP_RETENTION_DAYS", "30")),
    "backup_retention_days": int(os.getenv("BACKUP_RETENTION_DAYS", "90")),
    "health_check_interval": int(os.getenv("HEALTH_CHECK_INTERVAL", "300")),  # 5분
    "statistics_update_interval": int(os.getenv("STATS_UPDATE_INTERVAL", "60")),  # 1분
    "log_cleanup_size_mb": int(os.getenv("LOG_CLEANUP_SIZE_MB", "1000")),  # 1GB
}

# 서비스 URL 설정
API_GATEWAY_URL = "http://api-gateway:8000"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


@celery_app.task(name="cleanup_expired_tasks")
def cleanup_expired_tasks(
    retention_days: int = None
) -> Dict[str, Any]:
    """
    만료된 태스크 정리
    
    Args:
        retention_days: 보관 일수 (기본값: 설정값 사용)
    
    Returns:
        정리 결과
    """
    task_id = cleanup_expired_tasks.request.id
    logger.info(f"Starting expired tasks cleanup: {task_id}")
    
    try:
        if retention_days is None:
            retention_days = MAINTENANCE_CONFIG["cleanup_retention_days"]
        
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        # Redis에서 만료된 태스크 결과 정리
        redis_cleanup_result = _cleanup_redis_tasks(cutoff_date)
        
        # 데이터베이스에서 만료된 태스크 기록 정리
        db_cleanup_result = _cleanup_database_tasks(cutoff_date)
        
        # 파일 시스템에서 임시 파일 정리
        file_cleanup_result = _cleanup_temporary_files(cutoff_date)
        
        result = {
            "cleanup_id": str(uuid.uuid4()),
            "task_id": task_id,
            "retention_days": retention_days,
            "cutoff_date": cutoff_date.isoformat(),
            "redis_cleanup": redis_cleanup_result,
            "database_cleanup": db_cleanup_result,
            "file_cleanup": file_cleanup_result,
            "cleaned_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Expired tasks cleanup completed: {task_id}")
        return result
        
    except Exception as e:
        logger.error(f"Expired tasks cleanup failed: {task_id}, {e}")
        raise


@celery_app.task(name="health_check")
def health_check() -> Dict[str, Any]:
    """
    시스템 헬스 체크
    
    Returns:
        헬스 체크 결과
    """
    task_id = health_check.request.id
    logger.info(f"Starting health check: {task_id}")
    
    try:
        # 시스템 리소스 체크
        system_health = _check_system_resources()
        
        # 서비스 상태 체크
        services_health = _check_services_health()
        
        # Redis 연결 체크
        redis_health = _check_redis_health()
        
        # 데이터베이스 연결 체크
        database_health = _check_database_health()
        
        # Celery 워커 상태 체크
        celery_health = _check_celery_workers()
        
        # 전체 상태 평가
        overall_status = _evaluate_overall_health([
            system_health, services_health, redis_health, 
            database_health, celery_health
        ])
        
        result = {
            "health_check_id": str(uuid.uuid4()),
            "task_id": task_id,
            "overall_status": overall_status,
            "system": system_health,
            "services": services_health,
            "redis": redis_health,
            "database": database_health,
            "celery": celery_health,
            "checked_at": datetime.utcnow().isoformat()
        }
        
        # 심각한 문제가 있으면 알림 발송
        if overall_status == "critical":
            _send_health_alert(result)
        
        logger.info(f"Health check completed: {task_id}, status: {overall_status}")
        return result
        
    except Exception as e:
        logger.error(f"Health check failed: {task_id}, {e}")
        raise


@celery_app.task(name="update_statistics")
def update_statistics() -> Dict[str, Any]:
    """
    시스템 통계 업데이트
    
    Returns:
        통계 업데이트 결과
    """
    task_id = update_statistics.request.id
    logger.info(f"Starting statistics update: {task_id}")
    
    try:
        # 태스크 통계 수집
        task_stats = _collect_task_statistics()
        
        # 사용자 활동 통계 수집
        user_stats = _collect_user_statistics()
        
        # 시스템 성능 통계 수집
        performance_stats = _collect_performance_statistics()
        
        # 에러 통계 수집
        error_stats = _collect_error_statistics()
        
        # 통계 데이터 저장
        save_result = _save_statistics({
            "task_stats": task_stats,
            "user_stats": user_stats,
            "performance_stats": performance_stats,
            "error_stats": error_stats,
            "collected_at": datetime.utcnow().isoformat()
        })
        
        result = {
            "statistics_id": str(uuid.uuid4()),
            "task_id": task_id,
            "task_statistics": task_stats,
            "user_statistics": user_stats,
            "performance_statistics": performance_stats,
            "error_statistics": error_stats,
            "save_result": save_result,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Statistics update completed: {task_id}")
        return result
        
    except Exception as e:
        logger.error(f"Statistics update failed: {task_id}, {e}")
        raise


@celery_app.task(name="backup_data_task")
def backup_data_task(
    backup_type: str = "incremental",
    include_files: bool = True,
    compression: bool = True
) -> Dict[str, Any]:
    """
    데이터 백업 태스크
    
    Args:
        backup_type: 백업 유형 (full, incremental)
        include_files: 파일 포함 여부
        compression: 압축 여부
    
    Returns:
        백업 결과
    """
    task_id = backup_data_task.request.id
    logger.info(f"Starting data backup: {task_id}, type: {backup_type}")
    
    try:
        # 진행률 추적 시작
        progress_tracker = ProgressTracker()
        asyncio.run(progress_tracker.start_task(
            task_id,
            "data_backup",
            {
                "backup_type": backup_type,
                "include_files": include_files,
                "compression": compression
            }
        ))
        
        # 1단계: 백업 준비
        asyncio.run(progress_tracker.update_step(
            task_id, "backup_preparation", 10, "Preparing backup"
        ))
        
        backup_info = _prepare_backup(backup_type)
        
        # 2단계: 데이터베이스 백업
        asyncio.run(progress_tracker.update_step(
            task_id, "database_backup", 30, "Backing up database"
        ))
        
        db_backup_result = _backup_database(backup_info, backup_type)
        
        # 3단계: Redis 백업
        asyncio.run(progress_tracker.update_step(
            task_id, "redis_backup", 50, "Backing up Redis"
        ))
        
        redis_backup_result = _backup_redis(backup_info)
        
        # 4단계: 파일 백업 (선택사항)
        file_backup_result = None
        if include_files:
            asyncio.run(progress_tracker.update_step(
                task_id, "file_backup", 70, "Backing up files"
            ))
            
            file_backup_result = _backup_files(backup_info)
        
        # 5단계: 백업 압축 (선택사항)
        if compression:
            asyncio.run(progress_tracker.update_step(
                task_id, "backup_compression", 85, "Compressing backup"
            ))
            
            _compress_backup(backup_info)
        
        # 6단계: 백업 검증
        asyncio.run(progress_tracker.update_step(
            task_id, "backup_verification", 95, "Verifying backup"
        ))
        
        verification_result = _verify_backup(backup_info)
        
        # 최종 결과 준비
        result = {
            "backup_id": backup_info["backup_id"],
            "task_id": task_id,
            "backup_type": backup_type,
            "backup_path": backup_info["backup_path"],
            "database_backup": db_backup_result,
            "redis_backup": redis_backup_result,
            "file_backup": file_backup_result,
            "compression_enabled": compression,
            "verification": verification_result,
            "backup_size": _calculate_backup_size(backup_info["backup_path"]),
            "created_at": datetime.utcnow().isoformat()
        }
        
        # 완료
        asyncio.run(progress_tracker.complete_step(
            task_id, "data_backup", {"backup_id": result["backup_id"]}
        ))
        
        logger.info(f"Data backup completed: {task_id}")
        return result
        
    except Exception as e:
        logger.error(f"Data backup failed: {task_id}, {e}")
        
        # 실패 처리
        if 'progress_tracker' in locals():
            asyncio.run(progress_tracker.fail_step(
                task_id, "data_backup", str(e)
            ))
        
        raise


@celery_app.task(name="cleanup_logs_task")
def cleanup_logs_task(
    max_size_mb: int = None,
    retention_days: int = None
) -> Dict[str, Any]:
    """
    로그 파일 정리 태스크
    
    Args:
        max_size_mb: 최대 로그 크기 (MB)
        retention_days: 보관 일수
    
    Returns:
        로그 정리 결과
    """
    task_id = cleanup_logs_task.request.id
    logger.info(f"Starting log cleanup: {task_id}")
    
    try:
        if max_size_mb is None:
            max_size_mb = MAINTENANCE_CONFIG["log_cleanup_size_mb"]
        
        if retention_days is None:
            retention_days = MAINTENANCE_CONFIG["cleanup_retention_days"]
        
        # 로그 디렉토리 스캔
        log_directories = _find_log_directories()
        
        cleanup_results = []
        total_freed_space = 0
        
        for log_dir in log_directories:
            dir_result = _cleanup_log_directory(
                log_dir, max_size_mb, retention_days
            )
            cleanup_results.append(dir_result)
            total_freed_space += dir_result.get("freed_space_mb", 0)
        
        result = {
            "cleanup_id": str(uuid.uuid4()),
            "task_id": task_id,
            "max_size_mb": max_size_mb,
            "retention_days": retention_days,
            "directories_processed": len(log_directories),
            "total_freed_space_mb": total_freed_space,
            "cleanup_results": cleanup_results,
            "cleaned_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Log cleanup completed: {task_id}")
        return result
        
    except Exception as e:
        logger.error(f"Log cleanup failed: {task_id}, {e}")
        raise


# 헬퍼 함수들
def _cleanup_redis_tasks(cutoff_date: datetime) -> Dict[str, Any]:
    """Redis에서 만료된 태스크 정리"""
    try:
        # Redis 연결
        redis_client = redis.from_url(REDIS_URL)
        
        # 만료된 키 패턴 검색
        patterns = [
            "celery-task-meta-*",
            "progress:*",
            "session:*"
        ]
        
        deleted_keys = 0
        for pattern in patterns:
            keys = asyncio.run(redis_client.keys(pattern))
            for key in keys:
                # 키의 생성 시간 확인 (가능한 경우)
                try:
                    ttl = asyncio.run(redis_client.ttl(key))
                    if ttl == -1:  # TTL이 설정되지 않은 키
                        asyncio.run(redis_client.delete(key))
                        deleted_keys += 1
                except:
                    pass
        
        return {
            "status": "success",
            "deleted_keys": deleted_keys
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup Redis tasks: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }


def _cleanup_database_tasks(cutoff_date: datetime) -> Dict[str, Any]:
    """데이터베이스에서 만료된 태스크 정리"""
    try:
        response = requests.delete(
            f"{API_GATEWAY_URL}/maintenance/cleanup-tasks",
            json={"cutoff_date": cutoff_date.isoformat()},
            timeout=60
        )
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        logger.error(f"Failed to cleanup database tasks: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }


def _cleanup_temporary_files(cutoff_date: datetime) -> Dict[str, Any]:
    """임시 파일 정리"""
    try:
        temp_directories = ["/tmp", "/var/tmp", "./temp"]
        deleted_files = 0
        freed_space = 0
        
        for temp_dir in temp_directories:
            if os.path.exists(temp_dir):
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                            if file_mtime < cutoff_date:
                                file_size = os.path.getsize(file_path)
                                os.remove(file_path)
                                deleted_files += 1
                                freed_space += file_size
                        except:
                            pass
        
        return {
            "status": "success",
            "deleted_files": deleted_files,
            "freed_space_bytes": freed_space
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup temporary files: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }


def _check_system_resources() -> Dict[str, Any]:
    """시스템 리소스 체크"""
    try:
        # CPU 사용률
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # 메모리 사용률
        memory = psutil.virtual_memory()
        
        # 디스크 사용률
        disk = psutil.disk_usage('/')
        
        # 네트워크 통계
        network = psutil.net_io_counters()
        
        status = "healthy"
        if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
            status = "warning"
        if cpu_percent > 95 or memory.percent > 95 or disk.percent > 95:
            status = "critical"
        
        return {
            "status": status,
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_gb": round(memory.available / (1024**3), 2),
            "disk_percent": disk.percent,
            "disk_free_gb": round(disk.free / (1024**3), 2),
            "network_bytes_sent": network.bytes_sent,
            "network_bytes_recv": network.bytes_recv
        }
        
    except Exception as e:
        logger.error(f"Failed to check system resources: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


def _check_services_health() -> Dict[str, Any]:
    """서비스 상태 체크"""
    services = [
        {"name": "api-gateway", "url": f"{API_GATEWAY_URL}/health"},
        {"name": "ai-service", "url": "http://ai-service:8000/health"},
        {"name": "ocr-service", "url": "http://ocr-service:8000/health"},
        {"name": "puzzle-engine", "url": "http://puzzle-engine:8000/health"}
    ]
    
    service_results = []
    healthy_count = 0
    
    for service in services:
        try:
            response = requests.get(service["url"], timeout=5)
            if response.status_code == 200:
                status = "healthy"
                healthy_count += 1
            else:
                status = "unhealthy"
            
            service_results.append({
                "name": service["name"],
                "status": status,
                "response_time_ms": response.elapsed.total_seconds() * 1000
            })
            
        except Exception as e:
            service_results.append({
                "name": service["name"],
                "status": "error",
                "error": str(e)
            })
    
    overall_status = "healthy"
    if healthy_count < len(services):
        overall_status = "warning"
    if healthy_count < len(services) / 2:
        overall_status = "critical"
    
    return {
        "status": overall_status,
        "healthy_services": healthy_count,
        "total_services": len(services),
        "services": service_results
    }


def _check_redis_health() -> Dict[str, Any]:
    """Redis 연결 체크"""
    try:
        redis_client = redis.from_url(REDIS_URL)
        
        # 연결 테스트
        start_time = time.time()
        result = asyncio.run(redis_client.ping())
        response_time = (time.time() - start_time) * 1000
        
        # Redis 정보 조회
        info = asyncio.run(redis_client.info())
        
        return {
            "status": "healthy" if result else "unhealthy",
            "response_time_ms": response_time,
            "connected_clients": info.get("connected_clients", 0),
            "used_memory_mb": round(info.get("used_memory", 0) / (1024**2), 2),
            "keyspace_hits": info.get("keyspace_hits", 0),
            "keyspace_misses": info.get("keyspace_misses", 0)
        }
        
    except Exception as e:
        logger.error(f"Failed to check Redis health: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


def _check_database_health() -> Dict[str, Any]:
    """데이터베이스 연결 체크"""
    try:
        response = requests.get(
            f"{API_GATEWAY_URL}/health/database",
            timeout=10
        )
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        logger.error(f"Failed to check database health: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


def _check_celery_workers() -> Dict[str, Any]:
    """Celery 워커 상태 체크"""
    try:
        from ..celery_app import celery_app
        
        inspect = celery_app.control.inspect()
        
        # 활성 워커 조회
        active_workers = inspect.active()
        worker_count = len(active_workers) if active_workers else 0
        
        # 워커 통계 조회
        stats = inspect.stats()
        
        status = "healthy"
        if worker_count == 0:
            status = "critical"
        elif worker_count < 2:
            status = "warning"
        
        return {
            "status": status,
            "active_workers": worker_count,
            "worker_stats": stats
        }
        
    except Exception as e:
        logger.error(f"Failed to check Celery workers: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


def _evaluate_overall_health(health_checks: List[Dict[str, Any]]) -> str:
    """전체 헬스 상태 평가"""
    critical_count = sum(1 for check in health_checks if check.get("status") == "critical")
    warning_count = sum(1 for check in health_checks if check.get("status") == "warning")
    error_count = sum(1 for check in health_checks if check.get("status") == "error")
    
    if critical_count > 0 or error_count > 0:
        return "critical"
    elif warning_count > 0:
        return "warning"
    else:
        return "healthy"


def _send_health_alert(health_result: Dict[str, Any]) -> None:
    """헬스 체크 알림 발송"""
    try:
        notification_service = NotificationService()
        
        # 관리자에게 알림 발송
        asyncio.run(notification_service.send_notification(
            "admin",
            "system_health_alert",
            {
                "overall_status": health_result["overall_status"],
                "health_check_id": health_result["health_check_id"],
                "checked_at": health_result["checked_at"]
            }
        ))
        
    except Exception as e:
        logger.error(f"Failed to send health alert: {e}")


def _collect_task_statistics() -> Dict[str, Any]:
    """태스크 통계 수집"""
    try:
        from ..celery_app import celery_app
        
        inspect = celery_app.control.inspect()
        
        # 활성 태스크
        active_tasks = inspect.active()
        active_count = sum(len(tasks) for tasks in active_tasks.values()) if active_tasks else 0
        
        # 예약된 태스크
        scheduled_tasks = inspect.scheduled()
        scheduled_count = sum(len(tasks) for tasks in scheduled_tasks.values()) if scheduled_tasks else 0
        
        # 예약된 태스크 (reserved)
        reserved_tasks = inspect.reserved()
        reserved_count = sum(len(tasks) for tasks in reserved_tasks.values()) if reserved_tasks else 0
        
        return {
            "active_tasks": active_count,
            "scheduled_tasks": scheduled_count,
            "reserved_tasks": reserved_count,
            "total_pending": active_count + scheduled_count + reserved_count
        }
        
    except Exception as e:
        logger.error(f"Failed to collect task statistics: {e}")
        return {}


def _collect_user_statistics() -> Dict[str, Any]:
    """사용자 활동 통계 수집"""
    try:
        response = requests.get(
            f"{API_GATEWAY_URL}/statistics/users",
            timeout=10
        )
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        logger.error(f"Failed to collect user statistics: {e}")
        return {}


def _collect_performance_statistics() -> Dict[str, Any]:
    """시스템 성능 통계 수집"""
    try:
        # CPU 및 메모리 사용률
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        # 디스크 I/O
        disk_io = psutil.disk_io_counters()
        
        # 네트워크 I/O
        network_io = psutil.net_io_counters()
        
        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "disk_read_mb": round(disk_io.read_bytes / (1024**2), 2),
            "disk_write_mb": round(disk_io.write_bytes / (1024**2), 2),
            "network_sent_mb": round(network_io.bytes_sent / (1024**2), 2),
            "network_recv_mb": round(network_io.bytes_recv / (1024**2), 2)
        }
        
    except Exception as e:
        logger.error(f"Failed to collect performance statistics: {e}")
        return {}


def _collect_error_statistics() -> Dict[str, Any]:
    """에러 통계 수집"""
    try:
        response = requests.get(
            f"{API_GATEWAY_URL}/statistics/errors",
            timeout=10
        )
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        logger.error(f"Failed to collect error statistics: {e}")
        return {}


def _save_statistics(stats_data: Dict[str, Any]) -> Dict[str, Any]:
    """통계 데이터 저장"""
    try:
        response = requests.post(
            f"{API_GATEWAY_URL}/statistics",
            json=stats_data,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        logger.error(f"Failed to save statistics: {e}")
        return {"status": "failed", "error": str(e)}


def _prepare_backup(backup_type: str) -> Dict[str, Any]:
    """백업 준비"""
    backup_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_path = f"./backups/{backup_type}_{timestamp}_{backup_id}"
    
    os.makedirs(backup_path, exist_ok=True)
    
    return {
        "backup_id": backup_id,
        "backup_type": backup_type,
        "backup_path": backup_path,
        "timestamp": timestamp
    }


def _backup_database(backup_info: Dict[str, Any], backup_type: str) -> Dict[str, Any]:
    """데이터베이스 백업"""
    try:
        response = requests.post(
            f"{API_GATEWAY_URL}/maintenance/backup-database",
            json={
                "backup_path": backup_info["backup_path"],
                "backup_type": backup_type
            },
            timeout=300
        )
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        logger.error(f"Failed to backup database: {e}")
        return {"status": "failed", "error": str(e)}


def _backup_redis(backup_info: Dict[str, Any]) -> Dict[str, Any]:
    """Redis 백업"""
    try:
        redis_client = redis.from_url(REDIS_URL)
        
        # Redis 데이터 덤프
        backup_file = os.path.join(backup_info["backup_path"], "redis_dump.rdb")
        
        # BGSAVE 명령 실행
        asyncio.run(redis_client.bgsave())
        
        # 백업 파일 복사 (실제 구현에서는 Redis 설정에 따라 다름)
        # 여기서는 간단한 예시만 제공
        
        return {
            "status": "success",
            "backup_file": backup_file
        }
        
    except Exception as e:
        logger.error(f"Failed to backup Redis: {e}")
        return {"status": "failed", "error": str(e)}


def _backup_files(backup_info: Dict[str, Any]) -> Dict[str, Any]:
    """파일 백업"""
    try:
        # 백업할 디렉토리 목록
        backup_directories = [
            "./uploads",
            "./logs",
            "./config"
        ]
        
        backed_up_files = 0
        total_size = 0
        
        for directory in backup_directories:
            if os.path.exists(directory):
                dest_dir = os.path.join(backup_info["backup_path"], os.path.basename(directory))
                shutil.copytree(directory, dest_dir)
                
                # 파일 수 및 크기 계산
                for root, dirs, files in os.walk(dest_dir):
                    backed_up_files += len(files)
                    for file in files:
                        total_size += os.path.getsize(os.path.join(root, file))
        
        return {
            "status": "success",
            "backed_up_files": backed_up_files,
            "total_size_bytes": total_size
        }
        
    except Exception as e:
        logger.error(f"Failed to backup files: {e}")
        return {"status": "failed", "error": str(e)}


def _compress_backup(backup_info: Dict[str, Any]) -> None:
    """백업 압축"""
    try:
        import tarfile
        
        backup_path = backup_info["backup_path"]
        compressed_path = f"{backup_path}.tar.gz"
        
        with tarfile.open(compressed_path, "w:gz") as tar:
            tar.add(backup_path, arcname=os.path.basename(backup_path))
        
        # 원본 디렉토리 삭제
        shutil.rmtree(backup_path)
        
        # 압축된 파일 경로 업데이트
        backup_info["backup_path"] = compressed_path
        backup_info["compressed"] = True
        
    except Exception as e:
        logger.error(f"Failed to compress backup: {e}")
        raise


def _verify_backup(backup_info: Dict[str, Any]) -> Dict[str, Any]:
    """백업 검증"""
    try:
        backup_path = backup_info["backup_path"]
        
        if not os.path.exists(backup_path):
            return {"status": "failed", "error": "Backup file not found"}
        
        file_size = os.path.getsize(backup_path)
        
        if file_size == 0:
            return {"status": "failed", "error": "Backup file is empty"}
        
        # 압축 파일인 경우 무결성 검사
        if backup_path.endswith(".tar.gz"):
            import tarfile
            try:
                with tarfile.open(backup_path, "r:gz") as tar:
                    tar.getnames()  # 파일 목록 읽기 시도
            except:
                return {"status": "failed", "error": "Backup file is corrupted"}
        
        return {
            "status": "success",
            "file_size_bytes": file_size,
            "verified_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to verify backup: {e}")
        return {"status": "failed", "error": str(e)}


def _calculate_backup_size(backup_path: str) -> int:
    """백업 크기 계산"""
    try:
        if os.path.isfile(backup_path):
            return os.path.getsize(backup_path)
        elif os.path.isdir(backup_path):
            total_size = 0
            for root, dirs, files in os.walk(backup_path):
                for file in files:
                    total_size += os.path.getsize(os.path.join(root, file))
            return total_size
        else:
            return 0
    except:
        return 0


def _find_log_directories() -> List[str]:
    """로그 디렉토리 찾기"""
    log_directories = []
    
    # 일반적인 로그 디렉토리
    common_log_dirs = [
        "./logs",
        "/var/log",
        "/tmp",
        "./temp"
    ]
    
    for log_dir in common_log_dirs:
        if os.path.exists(log_dir):
            log_directories.append(log_dir)
    
    return log_directories


def _cleanup_log_directory(
    log_dir: str, 
    max_size_mb: int, 
    retention_days: int
) -> Dict[str, Any]:
    """로그 디렉토리 정리"""
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        deleted_files = 0
        freed_space = 0
        
        for root, dirs, files in os.walk(log_dir):
            for file in files:
                if file.endswith(('.log', '.out', '.err')):
                    file_path = os.path.join(root, file)
                    try:
                        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                        file_size = os.path.getsize(file_path)
                        
                        # 오래된 파일이거나 크기가 큰 파일 삭제
                        if file_mtime < cutoff_date or file_size > max_size_mb * 1024 * 1024:
                            os.remove(file_path)
                            deleted_files += 1
                            freed_space += file_size
                    except:
                        pass
        
        return {
            "directory": log_dir,
            "status": "success",
            "deleted_files": deleted_files,
            "freed_space_mb": round(freed_space / (1024**2), 2)
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup log directory {log_dir}: {e}")
        return {
            "directory": log_dir,
            "status": "failed",
            "error": str(e)
        }


# 스케줄된 유지보수 태스크
@celery_app.task(name="scheduled_maintenance")
def scheduled_maintenance() -> Dict[str, Any]:
    """
    스케줄된 유지보수 작업
    
    Returns:
        유지보수 결과
    """
    task_id = scheduled_maintenance.request.id
    logger.info(f"Starting scheduled maintenance: {task_id}")
    
    try:
        maintenance_results = {}
        
        # 1. 만료된 태스크 정리
        cleanup_result = cleanup_expired_tasks.delay()
        maintenance_results["cleanup_tasks"] = cleanup_result.id
        
        # 2. 로그 정리
        log_cleanup_result = cleanup_logs_task.delay()
        maintenance_results["cleanup_logs"] = log_cleanup_result.id
        
        # 3. 헬스 체크
        health_result = health_check.delay()
        maintenance_results["health_check"] = health_result.id
        
        # 4. 통계 업데이트
        stats_result = update_statistics.delay()
        maintenance_results["update_statistics"] = stats_result.id
        
        result = {
            "maintenance_id": str(uuid.uuid4()),
            "task_id": task_id,
            "maintenance_tasks": maintenance_results,
            "scheduled_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Scheduled maintenance completed: {task_id}")
        return result
        
    except Exception as e:
        logger.error(f"Scheduled maintenance failed: {task_id}, {e}")
        raise