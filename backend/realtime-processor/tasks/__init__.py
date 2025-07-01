"""
Celery 태스크 패키지
다양한 유형의 비동기 작업을 처리하는 태스크들을 포함
"""

from .puzzle_tasks import *
from .ai_tasks import *
from .notification_tasks import *
from .image_tasks import *
from .maintenance_tasks import *

__all__ = [
    # Puzzle tasks
    "generate_puzzle_task",
    "validate_puzzle_task",
    "optimize_puzzle_task",
    "save_puzzle_task",
    
    # AI tasks
    "process_ai_request_task",
    "generate_ai_content_task",
    "analyze_image_task",
    "train_model_task",
    
    # Notification tasks
    "send_notification_task",
    "send_email_task",
    "send_push_notification_task",
    "broadcast_message_task",
    
    # Image tasks
    "process_image_task",
    "resize_image_task",
    "compress_image_task",
    "generate_thumbnail_task",
    
    # Maintenance tasks
    "cleanup_expired_tasks",
    "health_check",
    "update_statistics",
    "backup_data_task",
]