"""
알림 관련 Celery 태스크
이메일, 푸시 알림, 브로드캐스트 메시지 등의 알림 작업을 처리
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os

from ..celery_app import notification_task, celery_app
from ..progress_tracker import ProgressTracker
from ..websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)

# 알림 서비스 설정
EMAIL_CONFIG = {
    "smtp_server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
    "smtp_port": int(os.getenv("SMTP_PORT", "587")),
    "smtp_username": os.getenv("SMTP_USERNAME", ""),
    "smtp_password": os.getenv("SMTP_PASSWORD", ""),
    "from_email": os.getenv("FROM_EMAIL", "noreply@puzzlecraft.ai")
}

PUSH_NOTIFICATION_CONFIG = {
    "fcm_server_key": os.getenv("FCM_SERVER_KEY", ""),
    "apns_key_id": os.getenv("APNS_KEY_ID", ""),
    "apns_team_id": os.getenv("APNS_TEAM_ID", ""),
    "apns_bundle_id": os.getenv("APNS_BUNDLE_ID", "com.puzzlecraft.app")
}

# 서비스 URL 설정
API_GATEWAY_URL = "http://api-gateway:8000"
USER_SERVICE_URL = "http://user-service:8000"


@notification_task(name="send_notification_task")
def send_notification_task(
    self,
    user_id: str,
    notification_type: str,
    message: str,
    data: Optional[Dict[str, Any]] = None,
    channels: Optional[List[str]] = None,
    priority: str = "normal",
    schedule_time: Optional[str] = None
) -> Dict[str, Any]:
    """
    통합 알림 발송 태스크
    
    Args:
        user_id: 사용자 ID
        notification_type: 알림 유형
        message: 알림 메시지
        data: 추가 데이터
        channels: 발송 채널 (websocket, email, push, sms)
        priority: 우선순위 (low, normal, high, urgent)
        schedule_time: 예약 발송 시간
    
    Returns:
        알림 발송 결과
    """
    task_id = self.request.id
    logger.info(f"Starting notification send: {task_id}, user: {user_id}, type: {notification_type}")
    
    try:
        # 기본 채널 설정
        if channels is None:
            channels = ["websocket", "email"]
        
        # 사용자 정보 조회
        user_info = _get_user_info(user_id)
        if not user_info:
            raise ValueError(f"User not found: {user_id}")
        
        # 사용자 알림 설정 확인
        notification_settings = _get_user_notification_settings(user_id)
        enabled_channels = _filter_enabled_channels(channels, notification_settings)
        
        if not enabled_channels:
            logger.info(f"No enabled channels for user {user_id}")
            return {
                "notification_id": str(uuid.uuid4()),
                "task_id": task_id,
                "status": "skipped",
                "reason": "No enabled channels",
                "sent_at": datetime.utcnow().isoformat()
            }
        
        # 예약 발송 처리
        if schedule_time:
            return _schedule_notification(
                task_id, user_id, notification_type, message, 
                data, enabled_channels, priority, schedule_time
            )
        
        # 즉시 발송
        results = {}
        notification_id = str(uuid.uuid4())
        
        # 채널별 발송
        for channel in enabled_channels:
            try:
                if channel == "websocket":
                    result = _send_websocket_notification(
                        user_id, notification_type, message, data
                    )
                elif channel == "email":
                    result = _send_email_notification(
                        user_info, notification_type, message, data
                    )
                elif channel == "push":
                    result = _send_push_notification(
                        user_info, notification_type, message, data
                    )
                elif channel == "sms":
                    result = _send_sms_notification(
                        user_info, notification_type, message, data
                    )
                else:
                    result = {"status": "unsupported", "channel": channel}
                
                results[channel] = result
                
            except Exception as e:
                logger.error(f"Failed to send {channel} notification: {e}")
                results[channel] = {"status": "failed", "error": str(e)}
        
        # 알림 기록 저장
        _save_notification_record(
            notification_id, user_id, notification_type, 
            message, data, results, priority
        )
        
        final_result = {
            "notification_id": notification_id,
            "task_id": task_id,
            "user_id": user_id,
            "notification_type": notification_type,
            "channels_attempted": enabled_channels,
            "results": results,
            "priority": priority,
            "sent_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Notification send completed: {task_id}")
        return final_result
        
    except Exception as e:
        logger.error(f"Notification send failed: {task_id}, {e}")
        raise


@notification_task(name="send_email_task")
def send_email_task(
    self,
    recipient_email: str,
    subject: str,
    body: str,
    body_type: str = "html",
    attachments: Optional[List[Dict[str, Any]]] = None,
    sender_email: Optional[str] = None,
    template_name: Optional[str] = None,
    template_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    이메일 발송 태스크
    
    Args:
        recipient_email: 수신자 이메일
        subject: 제목
        body: 본문
        body_type: 본문 유형 (text, html)
        attachments: 첨부파일 목록
        sender_email: 발신자 이메일
        template_name: 템플릿 이름
        template_data: 템플릿 데이터
    
    Returns:
        이메일 발송 결과
    """
    task_id = self.request.id
    logger.info(f"Starting email send: {task_id}, to: {recipient_email}")
    
    try:
        # 템플릿 처리
        if template_name:
            processed_content = _process_email_template(
                template_name, template_data or {}, subject, body
            )
            subject = processed_content["subject"]
            body = processed_content["body"]
            body_type = processed_content.get("body_type", body_type)
        
        # 이메일 메시지 생성
        msg = MIMEMultipart()
        msg['From'] = sender_email or EMAIL_CONFIG["from_email"]
        msg['To'] = recipient_email
        msg['Subject'] = subject
        
        # 본문 추가
        if body_type == "html":
            msg.attach(MIMEText(body, 'html'))
        else:
            msg.attach(MIMEText(body, 'plain'))
        
        # 첨부파일 처리
        if attachments:
            for attachment in attachments:
                _add_email_attachment(msg, attachment)
        
        # SMTP 서버를 통한 발송
        with smtplib.SMTP(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"]) as server:
            server.starttls()
            server.login(EMAIL_CONFIG["smtp_username"], EMAIL_CONFIG["smtp_password"])
            server.send_message(msg)
        
        result = {
            "email_id": str(uuid.uuid4()),
            "task_id": task_id,
            "recipient": recipient_email,
            "subject": subject,
            "status": "sent",
            "sent_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Email send completed: {task_id}")
        return result
        
    except Exception as e:
        logger.error(f"Email send failed: {task_id}, {e}")
        raise


@notification_task(name="send_push_notification_task")
def send_push_notification_task(
    self,
    device_tokens: Union[str, List[str]],
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None,
    platform: str = "both",  # ios, android, both
    badge_count: Optional[int] = None,
    sound: Optional[str] = None,
    click_action: Optional[str] = None
) -> Dict[str, Any]:
    """
    푸시 알림 발송 태스크
    
    Args:
        device_tokens: 디바이스 토큰(들)
        title: 알림 제목
        body: 알림 본문
        data: 추가 데이터
        platform: 플랫폼 (ios, android, both)
        badge_count: 배지 카운트 (iOS)
        sound: 알림 소리
        click_action: 클릭 액션
    
    Returns:
        푸시 알림 발송 결과
    """
    task_id = self.request.id
    logger.info(f"Starting push notification send: {task_id}")
    
    try:
        if isinstance(device_tokens, str):
            device_tokens = [device_tokens]
        
        results = []
        
        for token in device_tokens:
            try:
                # FCM을 통한 Android 푸시 알림
                if platform in ["android", "both"]:
                    fcm_result = _send_fcm_notification(
                        token, title, body, data, click_action
                    )
                    results.append({
                        "token": token,
                        "platform": "android",
                        "result": fcm_result
                    })
                
                # APNs를 통한 iOS 푸시 알림
                if platform in ["ios", "both"]:
                    apns_result = _send_apns_notification(
                        token, title, body, data, badge_count, sound
                    )
                    results.append({
                        "token": token,
                        "platform": "ios",
                        "result": apns_result
                    })
                    
            except Exception as e:
                logger.error(f"Failed to send push notification to {token}: {e}")
                results.append({
                    "token": token,
                    "platform": platform,
                    "result": {"status": "failed", "error": str(e)}
                })
        
        final_result = {
            "push_id": str(uuid.uuid4()),
            "task_id": task_id,
            "title": title,
            "body": body,
            "total_tokens": len(device_tokens),
            "results": results,
            "sent_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Push notification send completed: {task_id}")
        return final_result
        
    except Exception as e:
        logger.error(f"Push notification send failed: {task_id}, {e}")
        raise


@notification_task(name="broadcast_message_task")
def broadcast_message_task(
    self,
    message: str,
    target_type: str,  # all, users, groups, channels
    targets: Optional[List[str]] = None,
    message_type: str = "info",  # info, warning, error, success
    channels: Optional[List[str]] = None,
    data: Optional[Dict[str, Any]] = None,
    expiry_time: Optional[str] = None
) -> Dict[str, Any]:
    """
    브로드캐스트 메시지 발송 태스크
    
    Args:
        message: 브로드캐스트 메시지
        target_type: 대상 유형 (all, users, groups, channels)
        targets: 대상 목록
        message_type: 메시지 유형
        channels: 발송 채널
        data: 추가 데이터
        expiry_time: 만료 시간
    
    Returns:
        브로드캐스트 결과
    """
    task_id = self.request.id
    logger.info(f"Starting broadcast message: {task_id}, type: {target_type}")
    
    try:
        # 대상 사용자 목록 조회
        target_users = _get_broadcast_targets(target_type, targets)
        
        if not target_users:
            return {
                "broadcast_id": str(uuid.uuid4()),
                "task_id": task_id,
                "status": "no_targets",
                "sent_at": datetime.utcnow().isoformat()
            }
        
        # 기본 채널 설정
        if channels is None:
            channels = ["websocket"]
        
        broadcast_id = str(uuid.uuid4())
        results = []
        
        # 배치 처리로 알림 발송
        batch_size = 100
        for i in range(0, len(target_users), batch_size):
            batch_users = target_users[i:i + batch_size]
            
            batch_tasks = []
            for user_id in batch_users:
                # 개별 알림 태스크 생성
                task = send_notification_task.delay(
                    user_id=user_id,
                    notification_type="broadcast",
                    message=message,
                    data={
                        "broadcast_id": broadcast_id,
                        "message_type": message_type,
                        "expiry_time": expiry_time,
                        **(data or {})
                    },
                    channels=channels,
                    priority="normal"
                )
                batch_tasks.append({
                    "user_id": user_id,
                    "task_id": task.id
                })
            
            results.extend(batch_tasks)
        
        # 브로드캐스트 기록 저장
        _save_broadcast_record(
            broadcast_id, message, target_type, targets, 
            message_type, len(target_users), channels
        )
        
        final_result = {
            "broadcast_id": broadcast_id,
            "task_id": task_id,
            "message": message,
            "target_type": target_type,
            "total_targets": len(target_users),
            "total_tasks": len(results),
            "channels": channels,
            "message_type": message_type,
            "tasks": results,
            "sent_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Broadcast message completed: {task_id}")
        return final_result
        
    except Exception as e:
        logger.error(f"Broadcast message failed: {task_id}, {e}")
        raise


# 헬퍼 함수들
def _get_user_info(user_id: str) -> Optional[Dict[str, Any]]:
    """사용자 정보 조회"""
    try:
        response = requests.get(
            f"{USER_SERVICE_URL}/users/{user_id}",
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to get user info: {e}")
        return None


def _get_user_notification_settings(user_id: str) -> Dict[str, Any]:
    """사용자 알림 설정 조회"""
    try:
        response = requests.get(
            f"{USER_SERVICE_URL}/users/{user_id}/notification-settings",
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to get notification settings: {e}")
        return {
            "websocket": True,
            "email": True,
            "push": True,
            "sms": False
        }


def _filter_enabled_channels(
    channels: List[str], 
    settings: Dict[str, Any]
) -> List[str]:
    """활성화된 채널 필터링"""
    return [
        channel for channel in channels 
        if settings.get(channel, False)
    ]


def _schedule_notification(
    task_id: str,
    user_id: str,
    notification_type: str,
    message: str,
    data: Optional[Dict[str, Any]],
    channels: List[str],
    priority: str,
    schedule_time: str
) -> Dict[str, Any]:
    """알림 예약 발송"""
    try:
        # 예약 시간 파싱
        scheduled_datetime = datetime.fromisoformat(schedule_time.replace('Z', '+00:00'))
        
        # 예약 태스크 생성
        scheduled_task = send_notification_task.apply_async(
            args=[user_id, notification_type, message, data, channels, priority],
            eta=scheduled_datetime
        )
        
        return {
            "notification_id": str(uuid.uuid4()),
            "task_id": task_id,
            "scheduled_task_id": scheduled_task.id,
            "status": "scheduled",
            "scheduled_time": schedule_time,
            "created_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to schedule notification: {e}")
        raise


def _send_websocket_notification(
    user_id: str,
    notification_type: str,
    message: str,
    data: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """WebSocket 알림 발송"""
    try:
        websocket_manager = WebSocketManager()
        
        notification_data = {
            "type": "notification",
            "notification_type": notification_type,
            "message": message,
            "data": data or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 비동기 함수를 동기적으로 실행
        asyncio.run(websocket_manager.send_to_user(user_id, notification_data))
        
        return {"status": "sent", "channel": "websocket"}
    except Exception as e:
        logger.error(f"Failed to send websocket notification: {e}")
        return {"status": "failed", "error": str(e)}


def _send_email_notification(
    user_info: Dict[str, Any],
    notification_type: str,
    message: str,
    data: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """이메일 알림 발송"""
    try:
        email = user_info.get("email")
        if not email:
            return {"status": "failed", "error": "No email address"}
        
        # 이메일 템플릿 선택
        template_name = f"notification_{notification_type}"
        
        # 이메일 발송 태스크 실행
        result = send_email_task.delay(
            recipient_email=email,
            subject=f"PuzzleCraft AI - {notification_type.title()}",
            body=message,
            template_name=template_name,
            template_data={
                "user_name": user_info.get("name", "User"),
                "message": message,
                "data": data or {}
            }
        )
        
        return {"status": "sent", "channel": "email", "task_id": result.id}
    except Exception as e:
        logger.error(f"Failed to send email notification: {e}")
        return {"status": "failed", "error": str(e)}


def _send_push_notification(
    user_info: Dict[str, Any],
    notification_type: str,
    message: str,
    data: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """푸시 알림 발송"""
    try:
        device_tokens = user_info.get("device_tokens", [])
        if not device_tokens:
            return {"status": "failed", "error": "No device tokens"}
        
        # 푸시 알림 발송 태스크 실행
        result = send_push_notification_task.delay(
            device_tokens=device_tokens,
            title="PuzzleCraft AI",
            body=message,
            data={
                "notification_type": notification_type,
                **(data or {})
            }
        )
        
        return {"status": "sent", "channel": "push", "task_id": result.id}
    except Exception as e:
        logger.error(f"Failed to send push notification: {e}")
        return {"status": "failed", "error": str(e)}


def _send_sms_notification(
    user_info: Dict[str, Any],
    notification_type: str,
    message: str,
    data: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """SMS 알림 발송"""
    try:
        phone_number = user_info.get("phone_number")
        if not phone_number:
            return {"status": "failed", "error": "No phone number"}
        
        # SMS 서비스 API 호출 (예: Twilio, AWS SNS 등)
        # 실제 구현에서는 SMS 서비스 제공업체의 API를 사용
        
        return {"status": "sent", "channel": "sms"}
    except Exception as e:
        logger.error(f"Failed to send SMS notification: {e}")
        return {"status": "failed", "error": str(e)}


def _save_notification_record(
    notification_id: str,
    user_id: str,
    notification_type: str,
    message: str,
    data: Optional[Dict[str, Any]],
    results: Dict[str, Any],
    priority: str
) -> None:
    """알림 기록 저장"""
    try:
        record = {
            "notification_id": notification_id,
            "user_id": user_id,
            "notification_type": notification_type,
            "message": message,
            "data": data,
            "results": results,
            "priority": priority,
            "created_at": datetime.utcnow().isoformat()
        }
        
        requests.post(
            f"{API_GATEWAY_URL}/notifications/records",
            json=record,
            timeout=10
        )
    except Exception as e:
        logger.error(f"Failed to save notification record: {e}")


def _process_email_template(
    template_name: str,
    template_data: Dict[str, Any],
    default_subject: str,
    default_body: str
) -> Dict[str, Any]:
    """이메일 템플릿 처리"""
    try:
        response = requests.post(
            f"{API_GATEWAY_URL}/templates/email/{template_name}",
            json=template_data,
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to process email template: {e}")
        return {
            "subject": default_subject,
            "body": default_body,
            "body_type": "html"
        }


def _add_email_attachment(msg: MIMEMultipart, attachment: Dict[str, Any]) -> None:
    """이메일 첨부파일 추가"""
    try:
        filename = attachment["filename"]
        content = attachment["content"]  # base64 encoded
        content_type = attachment.get("content_type", "application/octet-stream")
        
        # Base64 디코딩
        import base64
        file_data = base64.b64decode(content)
        
        # 첨부파일 생성
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(file_data)
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename= {filename}'
        )
        
        msg.attach(part)
    except Exception as e:
        logger.error(f"Failed to add email attachment: {e}")


def _send_fcm_notification(
    device_token: str,
    title: str,
    body: str,
    data: Optional[Dict[str, Any]],
    click_action: Optional[str]
) -> Dict[str, Any]:
    """FCM 푸시 알림 발송"""
    try:
        fcm_url = "https://fcm.googleapis.com/fcm/send"
        headers = {
            "Authorization": f"key={PUSH_NOTIFICATION_CONFIG['fcm_server_key']}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "to": device_token,
            "notification": {
                "title": title,
                "body": body,
                "click_action": click_action
            },
            "data": data or {}
        }
        
        response = requests.post(fcm_url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        
        return {"status": "sent", "response": response.json()}
    except Exception as e:
        logger.error(f"Failed to send FCM notification: {e}")
        return {"status": "failed", "error": str(e)}


def _send_apns_notification(
    device_token: str,
    title: str,
    body: str,
    data: Optional[Dict[str, Any]],
    badge_count: Optional[int],
    sound: Optional[str]
) -> Dict[str, Any]:
    """APNs 푸시 알림 발송"""
    try:
        # APNs 구현 (실제로는 PyAPNs2 라이브러리 등을 사용)
        # 여기서는 간단한 예시만 제공
        
        payload = {
            "aps": {
                "alert": {
                    "title": title,
                    "body": body
                },
                "badge": badge_count,
                "sound": sound or "default"
            },
            "data": data or {}
        }
        
        # 실제 APNs 발송 로직
        # ...
        
        return {"status": "sent", "payload": payload}
    except Exception as e:
        logger.error(f"Failed to send APNs notification: {e}")
        return {"status": "failed", "error": str(e)}


def _get_broadcast_targets(
    target_type: str, 
    targets: Optional[List[str]]
) -> List[str]:
    """브로드캐스트 대상 조회"""
    try:
        if target_type == "all":
            # 모든 활성 사용자 조회
            response = requests.get(
                f"{USER_SERVICE_URL}/users/active",
                timeout=30
            )
        elif target_type == "users":
            # 특정 사용자들
            return targets or []
        elif target_type == "groups":
            # 그룹 멤버들 조회
            response = requests.post(
                f"{USER_SERVICE_URL}/groups/members",
                json={"group_ids": targets or []},
                timeout=30
            )
        elif target_type == "channels":
            # 채널 구독자들 조회
            response = requests.post(
                f"{USER_SERVICE_URL}/channels/subscribers",
                json={"channel_ids": targets or []},
                timeout=30
            )
        else:
            return []
        
        response.raise_for_status()
        result = response.json()
        return result.get("user_ids", [])
        
    except Exception as e:
        logger.error(f"Failed to get broadcast targets: {e}")
        return []


def _save_broadcast_record(
    broadcast_id: str,
    message: str,
    target_type: str,
    targets: Optional[List[str]],
    message_type: str,
    target_count: int,
    channels: List[str]
) -> None:
    """브로드캐스트 기록 저장"""
    try:
        record = {
            "broadcast_id": broadcast_id,
            "message": message,
            "target_type": target_type,
            "targets": targets,
            "message_type": message_type,
            "target_count": target_count,
            "channels": channels,
            "created_at": datetime.utcnow().isoformat()
        }
        
        requests.post(
            f"{API_GATEWAY_URL}/broadcasts/records",
            json=record,
            timeout=10
        )
    except Exception as e:
        logger.error(f"Failed to save broadcast record: {e}")


# 배치 알림 태스크
@notification_task(name="batch_notification_task")
def batch_notification_task(
    self,
    notifications: List[Dict[str, Any]],
    batch_id: str
) -> Dict[str, Any]:
    """
    배치 알림 발송 태스크
    
    Args:
        notifications: 알림 목록
        batch_id: 배치 ID
    
    Returns:
        배치 처리 결과
    """
    task_id = self.request.id
    logger.info(f"Starting batch notification: {task_id}, batch: {batch_id}")
    
    try:
        results = []
        failed_notifications = []
        
        for i, notification in enumerate(notifications):
            try:
                # 개별 알림 발송 태스크 실행
                result = send_notification_task.delay(
                    user_id=notification["user_id"],
                    notification_type=notification["notification_type"],
                    message=notification["message"],
                    data=notification.get("data"),
                    channels=notification.get("channels"),
                    priority=notification.get("priority", "normal")
                )
                
                results.append({
                    "notification_index": i,
                    "task_id": result.id,
                    "status": "submitted"
                })
                
            except Exception as e:
                failed_notifications.append({
                    "notification_index": i,
                    "error": str(e)
                })
        
        batch_result = {
            "batch_id": batch_id,
            "task_id": task_id,
            "total_notifications": len(notifications),
            "successful_submissions": len(results),
            "failed_submissions": len(failed_notifications),
            "results": results,
            "failed_notifications": failed_notifications,
            "submitted_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Batch notification completed: {task_id}")
        return batch_result
        
    except Exception as e:
        logger.error(f"Batch notification failed: {task_id}, {e}")
        raise


# 알림 정리 태스크
@notification_task(name="cleanup_old_notifications_task")
def cleanup_old_notifications_task(
    self,
    days_to_keep: int = 30
) -> Dict[str, Any]:
    """
    오래된 알림 정리 태스크
    
    Args:
        days_to_keep: 보관할 일수
    
    Returns:
        정리 결과
    """
    task_id = self.request.id
    logger.info(f"Starting notification cleanup: {task_id}")
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        response = requests.delete(
            f"{API_GATEWAY_URL}/notifications/cleanup",
            json={"cutoff_date": cutoff_date.isoformat()},
            timeout=60
        )
        response.raise_for_status()
        
        result = response.json()
        result["task_id"] = task_id
        result["cleanup_date"] = datetime.utcnow().isoformat()
        
        logger.info(f"Notification cleanup completed: {task_id}")
        return result
        
    except Exception as e:
        logger.error(f"Notification cleanup failed: {task_id}, {e}")
        raise