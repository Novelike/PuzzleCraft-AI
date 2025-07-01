"""
실시간 알림 서비스
AI 작업 진행 상황, 완료, 오류 등에 대한 다양한 알림을 처리합니다.
"""

import asyncio
import json
import logging
import smtplib
import ssl
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
import aiohttp
import redis.asyncio as redis
from jinja2 import Template

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """알림 타입"""
    PROGRESS_UPDATE = "progress_update"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    SYSTEM_ALERT = "system_alert"
    USER_MESSAGE = "user_message"


class NotificationChannel(Enum):
    """알림 채널"""
    WEBSOCKET = "websocket"
    EMAIL = "email"
    PUSH = "push"
    SMS = "sms"
    WEBHOOK = "webhook"


class NotificationPriority(Enum):
    """알림 우선순위"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class NotificationTemplate:
    """알림 템플릿"""
    id: str
    name: str
    subject_template: str
    body_template: str
    notification_type: NotificationType
    channels: List[NotificationChannel]
    priority: NotificationPriority = NotificationPriority.NORMAL
    variables: Dict[str, Any] = None

    def __post_init__(self):
        if self.variables is None:
            self.variables = {}


@dataclass
class NotificationRecipient:
    """알림 수신자"""
    user_id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    push_token: Optional[str] = None
    websocket_id: Optional[str] = None
    preferences: Dict[NotificationChannel, bool] = None

    def __post_init__(self):
        if self.preferences is None:
            self.preferences = {
                NotificationChannel.WEBSOCKET: True,
                NotificationChannel.EMAIL: True,
                NotificationChannel.PUSH: False,
                NotificationChannel.SMS: False,
                NotificationChannel.WEBHOOK: False
            }


@dataclass
class Notification:
    """알림 객체"""
    id: str
    notification_type: NotificationType
    title: str
    message: str
    recipient: NotificationRecipient
    channels: List[NotificationChannel]
    priority: NotificationPriority
    data: Dict[str, Any] = None
    created_at: datetime = None
    scheduled_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    status: str = "pending"
    retry_count: int = 0
    max_retries: int = 3

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.data is None:
            self.data = {}

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "id": self.id,
            "type": self.notification_type.value,
            "title": self.title,
            "message": self.message,
            "recipient_id": self.recipient.user_id,
            "channels": [ch.value for ch in self.channels],
            "priority": self.priority.value,
            "data": self.data,
            "created_at": self.created_at.isoformat(),
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "status": self.status,
            "retry_count": self.retry_count
        }


class EmailService:
    """이메일 서비스"""
    
    def __init__(self, smtp_server: str, smtp_port: int, username: str, password: str):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password

    async def send_email(self, recipient: str, subject: str, body: str, is_html: bool = False) -> bool:
        """이메일 발송"""
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.username
            message["To"] = recipient

            if is_html:
                part = MIMEText(body, "html")
            else:
                part = MIMEText(body, "plain")
            
            message.attach(part)

            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.username, self.password)
                server.sendmail(self.username, recipient, message.as_string())
            
            logger.info(f"이메일 발송 성공: {recipient}")
            return True
            
        except Exception as e:
            logger.error(f"이메일 발송 실패: {recipient}, 오류: {str(e)}")
            return False


class PushNotificationService:
    """푸시 알림 서비스"""
    
    def __init__(self, fcm_server_key: str):
        self.fcm_server_key = fcm_server_key
        self.fcm_url = "https://fcm.googleapis.com/fcm/send"

    async def send_push_notification(self, token: str, title: str, body: str, data: Dict[str, Any] = None) -> bool:
        """푸시 알림 발송"""
        try:
            headers = {
                "Authorization": f"key={self.fcm_server_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "to": token,
                "notification": {
                    "title": title,
                    "body": body
                }
            }
            
            if data:
                payload["data"] = data

            async with aiohttp.ClientSession() as session:
                async with session.post(self.fcm_url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        logger.info(f"푸시 알림 발송 성공: {token}")
                        return True
                    else:
                        logger.error(f"푸시 알림 발송 실패: {token}, 상태코드: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"푸시 알림 발송 실패: {token}, 오류: {str(e)}")
            return False


class WebhookService:
    """웹훅 서비스"""
    
    async def send_webhook(self, url: str, data: Dict[str, Any], headers: Dict[str, str] = None) -> bool:
        """웹훅 발송"""
        try:
            if headers is None:
                headers = {"Content-Type": "application/json"}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    if 200 <= response.status < 300:
                        logger.info(f"웹훅 발송 성공: {url}")
                        return True
                    else:
                        logger.error(f"웹훅 발송 실패: {url}, 상태코드: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"웹훅 발송 실패: {url}, 오류: {str(e)}")
            return False


class NotificationService:
    """통합 알림 서비스"""
    
    def __init__(self, 
                 redis_url: str = "redis://localhost:6379",
                 websocket_manager=None,
                 email_config: Dict[str, Any] = None,
                 push_config: Dict[str, Any] = None):
        self.redis_url = redis_url
        self.redis_client = None
        self.websocket_manager = websocket_manager
        
        # 서비스 초기화
        self.email_service = None
        if email_config:
            self.email_service = EmailService(**email_config)
            
        self.push_service = None
        if push_config:
            self.push_service = PushNotificationService(**push_config)
            
        self.webhook_service = WebhookService()
        
        # 템플릿 저장소
        self.templates: Dict[str, NotificationTemplate] = {}
        self.recipients: Dict[str, NotificationRecipient] = {}
        
        # 처리 큐
        self.notification_queue = asyncio.Queue()
        self.retry_queue = asyncio.Queue()
        
        # 통계
        self.stats = {
            "sent": 0,
            "failed": 0,
            "retries": 0,
            "by_channel": {channel.value: 0 for channel in NotificationChannel},
            "by_type": {ntype.value: 0 for ntype in NotificationType}
        }
        
        # 작업자 태스크
        self.workers = []
        self.retry_worker = None
        self.running = False

    async def initialize(self):
        """서비스 초기화"""
        try:
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            
            # 기본 템플릿 로드
            await self._load_default_templates()
            
            # 저장된 수신자 정보 로드
            await self._load_recipients()
            
            # 작업자 시작
            await self._start_workers()
            
            self.running = True
            logger.info("알림 서비스 초기화 완료")
            
        except Exception as e:
            logger.error(f"알림 서비스 초기화 실패: {str(e)}")
            raise

    async def shutdown(self):
        """서비스 종료"""
        self.running = False
        
        # 작업자 종료
        for worker in self.workers:
            worker.cancel()
        
        if self.retry_worker:
            self.retry_worker.cancel()
        
        # Redis 연결 종료
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("알림 서비스 종료 완료")

    async def register_template(self, template: NotificationTemplate):
        """알림 템플릿 등록"""
        self.templates[template.id] = template
        await self.redis_client.hset(
            "notification_templates",
            template.id,
            json.dumps(asdict(template), default=str)
        )
        logger.info(f"알림 템플릿 등록: {template.id}")

    async def register_recipient(self, recipient: NotificationRecipient):
        """수신자 등록"""
        self.recipients[recipient.user_id] = recipient
        await self.redis_client.hset(
            "notification_recipients",
            recipient.user_id,
            json.dumps(asdict(recipient), default=str)
        )
        logger.info(f"수신자 등록: {recipient.user_id}")

    async def send_notification(self, 
                              notification_type: NotificationType,
                              recipient_id: str,
                              title: str,
                              message: str,
                              data: Dict[str, Any] = None,
                              channels: List[NotificationChannel] = None,
                              priority: NotificationPriority = NotificationPriority.NORMAL,
                              scheduled_at: Optional[datetime] = None) -> str:
        """알림 발송"""
        try:
            # 수신자 확인
            if recipient_id not in self.recipients:
                raise ValueError(f"등록되지 않은 수신자: {recipient_id}")
            
            recipient = self.recipients[recipient_id]
            
            # 채널 결정
            if channels is None:
                channels = [ch for ch, enabled in recipient.preferences.items() if enabled]
            
            # 알림 객체 생성
            notification = Notification(
                id=f"notif_{int(datetime.now().timestamp() * 1000)}",
                notification_type=notification_type,
                title=title,
                message=message,
                recipient=recipient,
                channels=channels,
                priority=priority,
                data=data or {},
                scheduled_at=scheduled_at
            )
            
            # 큐에 추가
            await self.notification_queue.put(notification)
            
            # Redis에 저장
            await self.redis_client.hset(
                "notifications",
                notification.id,
                json.dumps(notification.to_dict())
            )
            
            logger.info(f"알림 큐에 추가: {notification.id}")
            return notification.id
            
        except Exception as e:
            logger.error(f"알림 발송 실패: {str(e)}")
            raise

    async def send_template_notification(self,
                                       template_id: str,
                                       recipient_id: str,
                                       variables: Dict[str, Any] = None,
                                       scheduled_at: Optional[datetime] = None) -> str:
        """템플릿 기반 알림 발송"""
        if template_id not in self.templates:
            raise ValueError(f"등록되지 않은 템플릿: {template_id}")
        
        template = self.templates[template_id]
        template_vars = {**template.variables, **(variables or {})}
        
        # 템플릿 렌더링
        title = Template(template.subject_template).render(**template_vars)
        message = Template(template.body_template).render(**template_vars)
        
        return await self.send_notification(
            notification_type=template.notification_type,
            recipient_id=recipient_id,
            title=title,
            message=message,
            data=template_vars,
            channels=template.channels,
            priority=template.priority,
            scheduled_at=scheduled_at
        )

    async def _start_workers(self):
        """작업자 시작"""
        # 알림 처리 작업자
        for i in range(3):  # 3개의 작업자
            worker = asyncio.create_task(self._notification_worker(f"worker-{i}"))
            self.workers.append(worker)
        
        # 재시도 작업자
        self.retry_worker = asyncio.create_task(self._retry_worker())

    async def _notification_worker(self, worker_name: str):
        """알림 처리 작업자"""
        logger.info(f"알림 작업자 시작: {worker_name}")
        
        while self.running:
            try:
                # 큐에서 알림 가져오기
                notification = await asyncio.wait_for(
                    self.notification_queue.get(), 
                    timeout=1.0
                )
                
                # 예약된 알림인지 확인
                if notification.scheduled_at and notification.scheduled_at > datetime.now():
                    # 다시 큐에 넣기 (나중에 처리)
                    await asyncio.sleep(1)
                    await self.notification_queue.put(notification)
                    continue
                
                # 알림 발송
                success = await self._send_notification(notification)
                
                if success:
                    notification.status = "sent"
                    notification.sent_at = datetime.now()
                    self.stats["sent"] += 1
                else:
                    notification.status = "failed"
                    self.stats["failed"] += 1
                    
                    # 재시도 큐에 추가
                    if notification.retry_count < notification.max_retries:
                        await self.retry_queue.put(notification)
                
                # 상태 업데이트
                await self.redis_client.hset(
                    "notifications",
                    notification.id,
                    json.dumps(notification.to_dict())
                )
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"알림 작업자 오류 ({worker_name}): {str(e)}")

    async def _retry_worker(self):
        """재시도 작업자"""
        logger.info("재시도 작업자 시작")
        
        while self.running:
            try:
                # 재시도 큐에서 알림 가져오기
                notification = await asyncio.wait_for(
                    self.retry_queue.get(),
                    timeout=5.0
                )
                
                # 재시도 대기
                wait_time = min(2 ** notification.retry_count, 60)  # 지수 백오프
                await asyncio.sleep(wait_time)
                
                notification.retry_count += 1
                self.stats["retries"] += 1
                
                # 다시 메인 큐에 추가
                await self.notification_queue.put(notification)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"재시도 작업자 오류: {str(e)}")

    async def _send_notification(self, notification: Notification) -> bool:
        """실제 알림 발송"""
        success_count = 0
        total_channels = len(notification.channels)
        
        for channel in notification.channels:
            try:
                channel_success = False
                
                if channel == NotificationChannel.WEBSOCKET:
                    channel_success = await self._send_websocket_notification(notification)
                elif channel == NotificationChannel.EMAIL:
                    channel_success = await self._send_email_notification(notification)
                elif channel == NotificationChannel.PUSH:
                    channel_success = await self._send_push_notification(notification)
                elif channel == NotificationChannel.WEBHOOK:
                    channel_success = await self._send_webhook_notification(notification)
                
                if channel_success:
                    success_count += 1
                    self.stats["by_channel"][channel.value] += 1
                
            except Exception as e:
                logger.error(f"채널 {channel.value} 발송 실패: {str(e)}")
        
        # 통계 업데이트
        self.stats["by_type"][notification.notification_type.value] += 1
        
        # 최소 하나의 채널에서 성공하면 성공으로 간주
        return success_count > 0

    async def _send_websocket_notification(self, notification: Notification) -> bool:
        """WebSocket 알림 발송"""
        if not self.websocket_manager:
            return False
        
        try:
            message = {
                "type": "notification",
                "data": notification.to_dict()
            }
            
            if notification.recipient.websocket_id:
                await self.websocket_manager.send_to_connection(
                    notification.recipient.websocket_id,
                    message
                )
            else:
                # 사용자 ID로 발송
                await self.websocket_manager.send_to_user(
                    notification.recipient.user_id,
                    message
                )
            
            return True
            
        except Exception as e:
            logger.error(f"WebSocket 알림 발송 실패: {str(e)}")
            return False

    async def _send_email_notification(self, notification: Notification) -> bool:
        """이메일 알림 발송"""
        if not self.email_service or not notification.recipient.email:
            return False
        
        return await self.email_service.send_email(
            notification.recipient.email,
            notification.title,
            notification.message
        )

    async def _send_push_notification(self, notification: Notification) -> bool:
        """푸시 알림 발송"""
        if not self.push_service or not notification.recipient.push_token:
            return False
        
        return await self.push_service.send_push_notification(
            notification.recipient.push_token,
            notification.title,
            notification.message,
            notification.data
        )

    async def _send_webhook_notification(self, notification: Notification) -> bool:
        """웹훅 알림 발송"""
        # 웹훅 URL은 data에서 가져오기
        webhook_url = notification.data.get("webhook_url")
        if not webhook_url:
            return False
        
        return await self.webhook_service.send_webhook(
            webhook_url,
            notification.to_dict()
        )

    async def _load_default_templates(self):
        """기본 템플릿 로드"""
        default_templates = [
            NotificationTemplate(
                id="task_started",
                name="작업 시작",
                subject_template="작업이 시작되었습니다: {{ task_name }}",
                body_template="{{ task_name }} 작업이 시작되었습니다. 예상 소요 시간: {{ estimated_time }}분",
                notification_type=NotificationType.TASK_STARTED,
                channels=[NotificationChannel.WEBSOCKET, NotificationChannel.EMAIL]
            ),
            NotificationTemplate(
                id="task_completed",
                name="작업 완료",
                subject_template="작업이 완료되었습니다: {{ task_name }}",
                body_template="{{ task_name }} 작업이 성공적으로 완료되었습니다. 소요 시간: {{ duration }}분",
                notification_type=NotificationType.TASK_COMPLETED,
                channels=[NotificationChannel.WEBSOCKET, NotificationChannel.EMAIL, NotificationChannel.PUSH]
            ),
            NotificationTemplate(
                id="task_failed",
                name="작업 실패",
                subject_template="작업이 실패했습니다: {{ task_name }}",
                body_template="{{ task_name }} 작업이 실패했습니다. 오류: {{ error_message }}",
                notification_type=NotificationType.TASK_FAILED,
                channels=[NotificationChannel.WEBSOCKET, NotificationChannel.EMAIL, NotificationChannel.PUSH],
                priority=NotificationPriority.HIGH
            ),
            NotificationTemplate(
                id="progress_update",
                name="진행률 업데이트",
                subject_template="작업 진행률: {{ progress }}%",
                body_template="{{ task_name }} 작업이 {{ progress }}% 완료되었습니다. 현재 단계: {{ current_step }}",
                notification_type=NotificationType.PROGRESS_UPDATE,
                channels=[NotificationChannel.WEBSOCKET]
            )
        ]
        
        for template in default_templates:
            await self.register_template(template)

    async def _load_recipients(self):
        """저장된 수신자 정보 로드"""
        try:
            recipients_data = await self.redis_client.hgetall("notification_recipients")
            for user_id, data in recipients_data.items():
                recipient_dict = json.loads(data)
                # Enum 변환
                if "preferences" in recipient_dict:
                    preferences = {}
                    for channel_str, enabled in recipient_dict["preferences"].items():
                        try:
                            channel = NotificationChannel(channel_str)
                            preferences[channel] = enabled
                        except ValueError:
                            continue
                    recipient_dict["preferences"] = preferences
                
                recipient = NotificationRecipient(**recipient_dict)
                self.recipients[user_id.decode()] = recipient
                
            logger.info(f"수신자 {len(self.recipients)}명 로드 완료")
            
        except Exception as e:
            logger.error(f"수신자 로드 실패: {str(e)}")

    async def get_notification_status(self, notification_id: str) -> Optional[Dict[str, Any]]:
        """알림 상태 조회"""
        try:
            data = await self.redis_client.hget("notifications", notification_id)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"알림 상태 조회 실패: {str(e)}")
            return None

    async def get_statistics(self) -> Dict[str, Any]:
        """통계 정보 조회"""
        return {
            **self.stats,
            "queue_size": self.notification_queue.qsize(),
            "retry_queue_size": self.retry_queue.qsize(),
            "templates_count": len(self.templates),
            "recipients_count": len(self.recipients)
        }

    async def cancel_notification(self, notification_id: str) -> bool:
        """알림 취소"""
        try:
            # Redis에서 상태 업데이트
            notification_data = await self.redis_client.hget("notifications", notification_id)
            if notification_data:
                notification_dict = json.loads(notification_data)
                notification_dict["status"] = "cancelled"
                await self.redis_client.hset(
                    "notifications",
                    notification_id,
                    json.dumps(notification_dict)
                )
                return True
            return False
        except Exception as e:
            logger.error(f"알림 취소 실패: {str(e)}")
            return False


# 진행률 추적기와의 통합을 위한 콜백 함수들
async def create_progress_callbacks(notification_service: NotificationService):
    """진행률 추적기용 콜백 함수 생성"""
    
    async def on_task_started(task_id: str, step: Any):
        """작업 시작 콜백"""
        # 작업과 연관된 사용자 찾기 (실제 구현에서는 task_id로 사용자 조회)
        user_id = "default_user"  # 실제로는 task_id에서 추출
        
        await notification_service.send_template_notification(
            template_id="task_started",
            recipient_id=user_id,
            variables={
                "task_name": f"Task {task_id}",
                "estimated_time": 10  # 예상 시간
            }
        )
    
    async def on_task_completed(task_id: str, step: Any):
        """작업 완료 콜백"""
        user_id = "default_user"
        
        await notification_service.send_template_notification(
            template_id="task_completed",
            recipient_id=user_id,
            variables={
                "task_name": f"Task {task_id}",
                "duration": 5  # 실제 소요 시간
            }
        )
    
    async def on_task_failed(task_id: str, step: Any):
        """작업 실패 콜백"""
        user_id = "default_user"
        
        await notification_service.send_template_notification(
            template_id="task_failed",
            recipient_id=user_id,
            variables={
                "task_name": f"Task {task_id}",
                "error_message": getattr(step, 'error_message', 'Unknown error')
            }
        )
    
    async def on_progress_update(task_id: str, step: Any):
        """진행률 업데이트 콜백"""
        user_id = "default_user"
        
        await notification_service.send_template_notification(
            template_id="progress_update",
            recipient_id=user_id,
            variables={
                "task_name": f"Task {task_id}",
                "progress": getattr(step, 'progress', 0),
                "current_step": getattr(step, 'name', 'Unknown step')
            }
        )
    
    return {
        "task_started": on_task_started,
        "task_completed": on_task_completed,
        "task_failed": on_task_failed,
        "progress_update": on_progress_update
    }