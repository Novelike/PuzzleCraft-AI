"""
실시간 처리 FastAPI WebSocket 서버
AI 작업 큐, 진행률 추적, 알림 서비스를 통합한 실시간 처리 시스템
"""

import asyncio
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Optional, Any

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# 로컬 모듈 임포트
from websocket_manager import WebSocketManager
from ai_task_queue import AITaskQueue, TaskPriority, AIServiceType
from progress_tracker import ProgressTracker
from notification_service import (
	NotificationService,
	NotificationRecipient,
	NotificationType,
	NotificationChannel,
	NotificationPriority,
	create_progress_callbacks
)

# 로깅 설정
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 라이프사이클 이벤트 핸들러
@asynccontextmanager
async def lifespan(app: FastAPI):
	"""애플리케이션 라이프사이클 관리"""
	# 시작 시
	await initialize_services()
	yield
	# 종료 시
	await shutdown_services()

# FastAPI 앱 생성
app = FastAPI(
	title="PuzzleCraft AI - 실시간 처리 서버",
	description="AI 기반 퍼즐 생성을 위한 실시간 처리 및 WebSocket 서버",
	version="1.0.0",
	lifespan=lifespan
)

# CORS 설정
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

# 전역 서비스 인스턴스
websocket_manager: Optional[WebSocketManager] = None
ai_task_queue: Optional[AITaskQueue] = None
progress_tracker: Optional[ProgressTracker] = None
notification_service: Optional[NotificationService] = None


# Pydantic 모델들
class TaskRequest(BaseModel):
	"""작업 요청 모델"""
	task_type: str = Field(..., description="작업 타입")
	user_id: str = Field(..., description="사용자 ID")
	parameters: Dict[str, Any] = Field(default_factory=dict, description="작업 매개변수")
	priority: str = Field(default="normal", description="작업 우선순위")
	callback_url: Optional[str] = Field(None, description="콜백 URL")


class UserRegistration(BaseModel):
	"""사용자 등록 모델"""
	user_id: str = Field(..., description="사용자 ID")
	name: str = Field(..., description="사용자 이름")
	email: Optional[str] = Field(None, description="이메일")
	phone: Optional[str] = Field(None, description="전화번호")
	push_token: Optional[str] = Field(None, description="푸시 토큰")
	notification_preferences: Dict[str, bool] = Field(
		default_factory=lambda: {
			"websocket": True,
			"email": True,
			"push": False,
			"sms": False,
			"webhook": False
		},
		description="알림 설정"
	)


class TaskResponse(BaseModel):
	"""작업 응답 모델"""
	task_id: str
	status: str
	message: str
	estimated_completion: Optional[str] = None


class ProgressResponse(BaseModel):
	"""진행률 응답 모델"""
	task_id: str
	overall_progress: float
	current_step: str
	steps: List[Dict[str, Any]]
	estimated_completion: Optional[str] = None
	performance_metrics: Dict[str, Any]


# 서비스 초기화
async def initialize_services():
	"""모든 서비스 초기화"""
	global websocket_manager, ai_task_queue, progress_tracker, notification_service

	try:
		# Redis URL 설정
		redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

		# WebSocket 관리자 초기화
		websocket_manager = WebSocketManager()
		await websocket_manager.initialize()

		# 진행률 추적기 초기화
		progress_tracker = ProgressTracker(redis_url=redis_url)
		await progress_tracker.initialize()

		# 알림 서비스 초기화
		email_config = None
		if all(os.getenv(key) for key in ["SMTP_SERVER", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD"]):
			email_config = {
				"smtp_server": os.getenv("SMTP_SERVER"),
				"smtp_port": int(os.getenv("SMTP_PORT", "587")),
				"username": os.getenv("SMTP_USERNAME"),
				"password": os.getenv("SMTP_PASSWORD")
			}

		push_config = None
		if os.getenv("FCM_SERVER_KEY"):
			push_config = {
				"fcm_server_key": os.getenv("FCM_SERVER_KEY")
			}

		notification_service = NotificationService(
			redis_url=redis_url,
			websocket_manager=websocket_manager,
			email_config=email_config,
			push_config=push_config
		)
		await notification_service.initialize()

		# AI 작업 큐 초기화
		ai_task_queue = AITaskQueue(
			redis_url=redis_url
		)
		await ai_task_queue.initialize()

		# 진행률 추적기에 알림 콜백 등록
		callbacks = await create_progress_callbacks(notification_service)
		for event, callback in callbacks.items():
			progress_tracker.register_callback(event, callback)

		logger.info("모든 서비스 초기화 완료")

	except Exception as e:
		logger.error(f"서비스 초기화 실패: {str(e)}")
		raise


# 서비스 종료
async def shutdown_services():
	"""모든 서비스 종료"""
	global websocket_manager, ai_task_queue, progress_tracker, notification_service

	try:
		if ai_task_queue:
			await ai_task_queue.shutdown()
		if progress_tracker:
			await progress_tracker.shutdown()
		if notification_service:
			await notification_service.shutdown()
		if websocket_manager:
			await websocket_manager.shutdown()

		logger.info("모든 서비스 종료 완료")

	except Exception as e:
		logger.error(f"서비스 종료 중 오류: {str(e)}")


# 의존성 함수들
async def get_websocket_manager() -> WebSocketManager:
	"""WebSocket 관리자 의존성"""
	if not websocket_manager:
		raise HTTPException(status_code=503, detail="WebSocket 관리자가 초기화되지 않았습니다")
	return websocket_manager


async def get_ai_task_queue() -> AITaskQueue:
	"""AI 작업 큐 의존성"""
	if not ai_task_queue:
		raise HTTPException(status_code=503, detail="AI 작업 큐가 초기화되지 않았습니다")
	return ai_task_queue


async def get_progress_tracker() -> ProgressTracker:
	"""진행률 추적기 의존성"""
	if not progress_tracker:
		raise HTTPException(status_code=503, detail="진행률 추적기가 초기화되지 않았습니다")
	return progress_tracker


async def get_notification_service() -> NotificationService:
	"""알림 서비스 의존성"""
	if not notification_service:
		raise HTTPException(status_code=503, detail="알림 서비스가 초기화되지 않았습니다")
	return notification_service




# WebSocket 엔드포인트
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(
		websocket: WebSocket,
		user_id: str,
		ws_manager: WebSocketManager = Depends(get_websocket_manager)
):
	"""WebSocket 연결 엔드포인트"""
	connection_id = str(uuid.uuid4())

	try:
		await ws_manager.connect(websocket, connection_id, user_id)
		logger.info(f"WebSocket 연결 성공: {user_id} ({connection_id})")

		# 연결 확인 메시지 전송
		await ws_manager.send_to_connection(connection_id, {
			"type": "connection_established",
			"connection_id": connection_id,
			"user_id": user_id,
			"timestamp": datetime.now().isoformat()
		})

		# 메시지 수신 루프
		while True:
			try:
				data = await websocket.receive_text()
				message = json.loads(data)

				# 메시지 타입에 따른 처리
				await handle_websocket_message(connection_id, user_id, message)

			except WebSocketDisconnect:
				break
			except json.JSONDecodeError:
				await ws_manager.send_to_connection(connection_id, {
					"type": "error",
					"message": "잘못된 JSON 형식입니다"
				})
			except Exception as e:
				logger.error(f"WebSocket 메시지 처리 오류: {str(e)}")
				await ws_manager.send_to_connection(connection_id, {
					"type": "error",
					"message": f"메시지 처리 중 오류가 발생했습니다: {str(e)}"
				})

	except Exception as e:
		logger.error(f"WebSocket 연결 오류: {str(e)}")
	finally:
		await ws_manager.disconnect(connection_id)
		logger.info(f"WebSocket 연결 종료: {user_id} ({connection_id})")


async def handle_websocket_message(connection_id: str, user_id: str, message: Dict[str, Any]):
	"""WebSocket 메시지 처리"""
	message_type = message.get("type")

	if message_type == "ping":
		# 핑 응답
		await websocket_manager.send_to_connection(connection_id, {
			"type": "pong",
			"timestamp": datetime.now().isoformat()
		})

	elif message_type == "subscribe_task":
		# 작업 구독
		task_id = message.get("task_id")
		if task_id:
			await websocket_manager.subscribe_to_task(connection_id, task_id)
			await websocket_manager.send_to_connection(connection_id, {
				"type": "subscribed",
				"task_id": task_id
			})

	elif message_type == "unsubscribe_task":
		# 작업 구독 해제
		task_id = message.get("task_id")
		if task_id:
			await websocket_manager.unsubscribe_from_task(connection_id, task_id)
			await websocket_manager.send_to_connection(connection_id, {
				"type": "unsubscribed",
				"task_id": task_id
			})

	elif message_type == "get_task_status":
		# 작업 상태 조회
		task_id = message.get("task_id")
		if task_id and progress_tracker:
			status = await progress_tracker.get_progress_status(task_id)
			await websocket_manager.send_to_connection(connection_id, {
				"type": "task_status",
				"task_id": task_id,
				"status": status
			})
	else:
		await websocket_manager.send_to_connection(connection_id, {
			"type": "error",
			"message": f"알 수 없는 메시지 타입: {message_type}"
		})


# REST API 엔드포인트들

@app.get("/")
async def root():
	"""루트 엔드포인트"""
	return {
		"message": "PuzzleCraft AI 실시간 처리 서버",
		"version": "1.0.0",
		"status": "running",
		"timestamp": datetime.now().isoformat()
	}


@app.get("/health")
async def health_check():
	"""헬스 체크"""
	try:
		# 각 서비스 상태 확인
		services_status = {
			"websocket_manager": websocket_manager is not None,
			"ai_task_queue": ai_task_queue is not None,
			"progress_tracker": progress_tracker is not None,
			"notification_service": notification_service is not None
		}

		all_healthy = all(services_status.values())

		return {
			"status": "healthy" if all_healthy else "degraded",
			"services": services_status,
			"timestamp": datetime.now().isoformat()
		}
	except Exception as e:
		return JSONResponse(
			status_code=503,
			content={
				"status": "unhealthy",
				"error": str(e),
				"timestamp": datetime.now().isoformat()
			}
		)


@app.post("/users/register", response_model=Dict[str, str])
async def register_user(
		user_data: UserRegistration,
		notification_svc: NotificationService = Depends(get_notification_service)
):
	"""사용자 등록"""
	try:
		# 알림 채널 매핑
		channel_mapping = {
			"websocket": NotificationChannel.WEBSOCKET,
			"email": NotificationChannel.EMAIL,
			"push": NotificationChannel.PUSH,
			"sms": NotificationChannel.SMS,
			"webhook": NotificationChannel.WEBHOOK
		}

		preferences = {}
		for channel_str, enabled in user_data.notification_preferences.items():
			if channel_str in channel_mapping:
				preferences[channel_mapping[channel_str]] = enabled

		# 수신자 객체 생성
		recipient = NotificationRecipient(
			user_id=user_data.user_id,
			name=user_data.name,
			email=user_data.email,
			phone=user_data.phone,
			push_token=user_data.push_token,
			preferences=preferences
		)

		# 수신자 등록
		await notification_svc.register_recipient(recipient)

		return {
			"message": "사용자가 성공적으로 등록되었습니다",
			"user_id": user_data.user_id
		}

	except Exception as e:
		logger.error(f"사용자 등록 실패: {str(e)}")
		raise HTTPException(status_code=500, detail=f"사용자 등록 실패: {str(e)}")


@app.post("/tasks/submit", response_model=TaskResponse)
async def submit_task(
		task_request: TaskRequest,
		background_tasks: BackgroundTasks,
		task_queue: AITaskQueue = Depends(get_ai_task_queue)
):
	"""작업 제출"""
	try:
		# 우선순위 매핑
		priority_mapping = {
			"low": TaskPriority.LOW,
			"normal": TaskPriority.NORMAL,
			"high": TaskPriority.HIGH,
			"critical": TaskPriority.CRITICAL
		}

		priority = priority_mapping.get(task_request.priority.lower(), TaskPriority.NORMAL)

		# 작업 타입 매핑
		task_type_mapping = {
			"puzzle_generation": AIServiceType.PUZZLE_GENERATOR,
			"image_processing": AIServiceType.STYLE_TRANSFER,
			"ocr_processing": AIServiceType.OCR,
			"ai_analysis": AIServiceType.SEGMENTATION
		}

		task_type = task_type_mapping.get(task_request.task_type.lower(), AIServiceType.PUZZLE_GENERATOR)

		# 작업 제출
		task_id = await task_queue.submit_task(
			task_type=task_type,
			user_id=task_request.user_id,
			parameters=task_request.parameters,
			priority=priority,
			callback_url=task_request.callback_url
		)

		# 예상 완료 시간 계산 (간단한 추정)
		estimated_minutes = 5  # 기본값
		if task_type == AIServiceType.PUZZLE_GENERATOR:
			estimated_minutes = 10
		elif task_type == AIServiceType.STYLE_TRANSFER:
			estimated_minutes = 3
		elif task_type == AIServiceType.OCR:
			estimated_minutes = 2

		estimated_completion = datetime.now().replace(
			minute=datetime.now().minute + estimated_minutes
		).isoformat()

		return TaskResponse(
			task_id=task_id,
			status="submitted",
			message="작업이 성공적으로 제출되었습니다",
			estimated_completion=estimated_completion
		)

	except Exception as e:
		logger.error(f"작업 제출 실패: {str(e)}")
		raise HTTPException(status_code=500, detail=f"작업 제출 실패: {str(e)}")


@app.get("/tasks/{task_id}/status", response_model=ProgressResponse)
async def get_task_status(
		task_id: str,
		tracker: ProgressTracker = Depends(get_progress_tracker)
):
	"""작업 상태 조회"""
	try:
		status = await tracker.get_progress_status(task_id)

		if not status:
			raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")

		return ProgressResponse(
			task_id=task_id,
			overall_progress=status.get("overall_progress", 0),
			current_step=status.get("current_step", ""),
			steps=status.get("steps", []),
			estimated_completion=status.get("estimated_completion"),
			performance_metrics=status.get("performance_metrics", {})
		)

	except HTTPException:
		raise
	except Exception as e:
		logger.error(f"작업 상태 조회 실패: {str(e)}")
		raise HTTPException(status_code=500, detail=f"작업 상태 조회 실패: {str(e)}")


@app.delete("/tasks/{task_id}")
async def cancel_task(
		task_id: str,
		task_queue: AITaskQueue = Depends(get_ai_task_queue)
):
	"""작업 취소"""
	try:
		success = await task_queue.cancel_task(task_id)

		if not success:
			raise HTTPException(status_code=404, detail="작업을 찾을 수 없거나 취소할 수 없습니다")

		return {"message": "작업이 성공적으로 취소되었습니다", "task_id": task_id}

	except HTTPException:
		raise
	except Exception as e:
		logger.error(f"작업 취소 실패: {str(e)}")
		raise HTTPException(status_code=500, detail=f"작업 취소 실패: {str(e)}")


@app.get("/tasks/{task_id}/history")
async def get_task_history(
		task_id: str,
		limit: int = 100,
		tracker: ProgressTracker = Depends(get_progress_tracker)
):
	"""작업 히스토리 조회"""
	try:
		history = await tracker.get_progress_history(task_id, limit)
		return {"task_id": task_id, "history": history}

	except Exception as e:
		logger.error(f"작업 히스토리 조회 실패: {str(e)}")
		raise HTTPException(status_code=500, detail=f"작업 히스토리 조회 실패: {str(e)}")


@app.get("/statistics")
async def get_statistics(
		task_queue: AITaskQueue = Depends(get_ai_task_queue),
		tracker: ProgressTracker = Depends(get_progress_tracker),
		notification_svc: NotificationService = Depends(get_notification_service),
		ws_manager: WebSocketManager = Depends(get_websocket_manager)
):
	"""시스템 통계 조회"""
	try:
		stats = {
			"task_queue": await task_queue.get_statistics(),
			"progress_tracker": await tracker.get_global_statistics(),
			"notification_service": await notification_svc.get_statistics(),
			"websocket_manager": await ws_manager.get_statistics(),
			"timestamp": datetime.now().isoformat()
		}

		return stats

	except Exception as e:
		logger.error(f"통계 조회 실패: {str(e)}")
		raise HTTPException(status_code=500, detail=f"통계 조회 실패: {str(e)}")


@app.post("/notifications/send")
async def send_notification(
		notification_type: str,
		recipient_id: str,
		title: str,
		message: str,
		data: Optional[Dict[str, Any]] = None,
		channels: Optional[List[str]] = None,
		priority: str = "normal",
		notification_svc: NotificationService = Depends(get_notification_service)
):
	"""직접 알림 발송"""
	try:
		# 타입 매핑
		type_mapping = {
			"progress_update": NotificationType.PROGRESS_UPDATE,
			"task_started": NotificationType.TASK_STARTED,
			"task_completed": NotificationType.TASK_COMPLETED,
			"task_failed": NotificationType.TASK_FAILED,
			"system_alert": NotificationType.SYSTEM_ALERT,
			"user_message": NotificationType.USER_MESSAGE
		}

		channel_mapping = {
			"websocket": NotificationChannel.WEBSOCKET,
			"email": NotificationChannel.EMAIL,
			"push": NotificationChannel.PUSH,
			"sms": NotificationChannel.SMS,
			"webhook": NotificationChannel.WEBHOOK
		}

		priority_mapping = {
			"low": NotificationPriority.LOW,
			"normal": NotificationPriority.NORMAL,
			"high": NotificationPriority.HIGH,
			"critical": NotificationPriority.CRITICAL
		}

		notif_type = type_mapping.get(notification_type.lower(), NotificationType.USER_MESSAGE)
		notif_priority = priority_mapping.get(priority.lower(), NotificationPriority.NORMAL)

		notif_channels = None
		if channels:
			notif_channels = [channel_mapping[ch] for ch in channels if ch in channel_mapping]

		notification_id = await notification_svc.send_notification(
			notification_type=notif_type,
			recipient_id=recipient_id,
			title=title,
			message=message,
			data=data,
			channels=notif_channels,
			priority=notif_priority
		)

		return {
			"message": "알림이 성공적으로 발송되었습니다",
			"notification_id": notification_id
		}

	except Exception as e:
		logger.error(f"알림 발송 실패: {str(e)}")
		raise HTTPException(status_code=500, detail=f"알림 발송 실패: {str(e)}")


# 개발용 엔드포인트
@app.get("/debug/connections")
async def debug_connections(ws_manager: WebSocketManager = Depends(get_websocket_manager)):
	"""디버그: 현재 연결 상태"""
	return await ws_manager.get_statistics()


if __name__ == "__main__":
	# 환경 변수 설정
	host = os.getenv("HOST", "0.0.0.0")
	port = int(os.getenv("PORT", "8000"))

	# 서버 실행
	uvicorn.run(
		"main:app",
		host=host,
		port=port,
		reload=True,  # 개발 모드
		log_level="info"
	)
