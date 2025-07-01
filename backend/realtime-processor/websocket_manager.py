"""
PuzzleCraft AI - WebSocket 연결 관리자
실시간 AI 처리를 위한 WebSocket 연결 관리 시스템
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Set, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
from datetime import datetime
import weakref

from fastapi import WebSocket, WebSocketDisconnect
import redis.asyncio as redis

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConnectionStatus(Enum):
    """연결 상태"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class MessageType(Enum):
    """메시지 타입"""
    # 연결 관리
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    PING = "ping"
    PONG = "pong"
    
    # AI 처리 관련
    TASK_START = "task_start"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETE = "task_complete"
    TASK_ERROR = "task_error"
    TASK_CANCEL = "task_cancel"
    
    # 협업 퍼즐 관련
    ROOM_JOIN = "room_join"
    ROOM_LEAVE = "room_leave"
    ROOM_UPDATE = "room_update"
    
    # 알림
    NOTIFICATION = "notification"
    BROADCAST = "broadcast"


@dataclass
class WebSocketMessage:
    """WebSocket 메시지 구조"""
    type: str
    data: Dict[str, Any]
    timestamp: float
    message_id: str
    sender_id: Optional[str] = None
    room_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())


@dataclass
class ConnectionInfo:
    """연결 정보"""
    connection_id: str
    websocket: WebSocket
    user_id: Optional[str]
    session_id: Optional[str]
    rooms: Set[str]
    status: ConnectionStatus
    connected_at: datetime
    last_ping: Optional[datetime]
    metadata: Dict[str, Any]


class WebSocketManager:
    """WebSocket 연결 관리자"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        """초기화"""
        self.connections: Dict[str, ConnectionInfo] = {}
        self.rooms: Dict[str, Set[str]] = {}  # room_id -> connection_ids
        self.user_connections: Dict[str, Set[str]] = {}  # user_id -> connection_ids
        
        # Redis 연결 (선택적)
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        
        # 메시지 핸들러
        self.message_handlers: Dict[str, List[Callable]] = {}
        
        # 통계
        self.stats = {
            "total_connections": 0,
            "active_connections": 0,
            "total_messages": 0,
            "rooms_count": 0,
        }
        
        # 정리 작업을 위한 태스크
        self._cleanup_task: Optional[asyncio.Task] = None
        
        logger.info("WebSocket 관리자 초기화 완료")

    async def initialize(self):
        """비동기 초기화"""
        try:
            # Redis 연결 시도
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("Redis 연결 성공")
        except Exception as e:
            logger.warning(f"Redis 연결 실패: {str(e)}, 메모리 모드로 동작")
            self.redis_client = None
        
        # 정리 작업 시작
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())

    async def shutdown(self):
        """종료 처리"""
        logger.info("WebSocket 관리자 종료 중...")
        
        # 정리 작업 중단
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # 모든 연결 종료
        for connection_id in list(self.connections.keys()):
            await self.disconnect(connection_id)
        
        # Redis 연결 종료
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("WebSocket 관리자 종료 완료")

    async def connect(
        self, 
        websocket: WebSocket, 
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """새 연결 등록"""
        connection_id = str(uuid.uuid4())
        
        try:
            await websocket.accept()
            
            connection_info = ConnectionInfo(
                connection_id=connection_id,
                websocket=websocket,
                user_id=user_id,
                session_id=session_id,
                rooms=set(),
                status=ConnectionStatus.CONNECTED,
                connected_at=datetime.now(),
                last_ping=datetime.now(),
                metadata=metadata or {}
            )
            
            self.connections[connection_id] = connection_info
            
            # 사용자별 연결 추적
            if user_id:
                if user_id not in self.user_connections:
                    self.user_connections[user_id] = set()
                self.user_connections[user_id].add(connection_id)
            
            # 통계 업데이트
            self.stats["total_connections"] += 1
            self.stats["active_connections"] = len(self.connections)
            
            # 연결 확인 메시지 전송
            await self.send_to_connection(connection_id, WebSocketMessage(
                type=MessageType.CONNECT.value,
                data={
                    "connection_id": connection_id,
                    "status": "connected",
                    "server_time": datetime.now().isoformat()
                },
                timestamp=time.time(),
                message_id=str(uuid.uuid4())
            ))
            
            logger.info(f"새 WebSocket 연결: {connection_id} (사용자: {user_id})")
            return connection_id
            
        except Exception as e:
            logger.error(f"WebSocket 연결 실패: {str(e)}")
            raise

    async def disconnect(self, connection_id: str):
        """연결 해제"""
        if connection_id not in self.connections:
            return
        
        connection_info = self.connections[connection_id]
        
        try:
            # 상태 업데이트
            connection_info.status = ConnectionStatus.DISCONNECTING
            
            # 모든 방에서 제거
            for room_id in list(connection_info.rooms):
                await self.leave_room(connection_id, room_id)
            
            # 사용자별 연결에서 제거
            if connection_info.user_id:
                user_connections = self.user_connections.get(connection_info.user_id)
                if user_connections:
                    user_connections.discard(connection_id)
                    if not user_connections:
                        del self.user_connections[connection_info.user_id]
            
            # WebSocket 연결 종료
            try:
                await connection_info.websocket.close()
            except:
                pass
            
            # 연결 정보 제거
            del self.connections[connection_id]
            
            # 통계 업데이트
            self.stats["active_connections"] = len(self.connections)
            
            logger.info(f"WebSocket 연결 해제: {connection_id}")
            
        except Exception as e:
            logger.error(f"연결 해제 중 오류: {str(e)}")

    async def send_to_connection(self, connection_id: str, message: WebSocketMessage) -> bool:
        """특정 연결에 메시지 전송"""
        if connection_id not in self.connections:
            logger.warning(f"존재하지 않는 연결: {connection_id}")
            return False
        
        connection_info = self.connections[connection_id]
        
        try:
            await connection_info.websocket.send_text(message.to_json())
            self.stats["total_messages"] += 1
            return True
            
        except WebSocketDisconnect:
            logger.info(f"연결이 끊어짐: {connection_id}")
            await self.disconnect(connection_id)
            return False
            
        except Exception as e:
            logger.error(f"메시지 전송 실패 [{connection_id}]: {str(e)}")
            await self.disconnect(connection_id)
            return False

    async def send_to_user(self, user_id: str, message: WebSocketMessage) -> int:
        """특정 사용자의 모든 연결에 메시지 전송"""
        if user_id not in self.user_connections:
            return 0
        
        connection_ids = list(self.user_connections[user_id])
        sent_count = 0
        
        for connection_id in connection_ids:
            if await self.send_to_connection(connection_id, message):
                sent_count += 1
        
        return sent_count

    async def send_to_room(self, room_id: str, message: WebSocketMessage, exclude_connection: Optional[str] = None) -> int:
        """방의 모든 연결에 메시지 전송"""
        if room_id not in self.rooms:
            return 0
        
        connection_ids = list(self.rooms[room_id])
        sent_count = 0
        
        for connection_id in connection_ids:
            if connection_id != exclude_connection:
                if await self.send_to_connection(connection_id, message):
                    sent_count += 1
        
        return sent_count

    async def broadcast(self, message: WebSocketMessage, exclude_connection: Optional[str] = None) -> int:
        """모든 연결에 메시지 브로드캐스트"""
        connection_ids = list(self.connections.keys())
        sent_count = 0
        
        for connection_id in connection_ids:
            if connection_id != exclude_connection:
                if await self.send_to_connection(connection_id, message):
                    sent_count += 1
        
        return sent_count

    async def join_room(self, connection_id: str, room_id: str) -> bool:
        """방 참가"""
        if connection_id not in self.connections:
            return False
        
        connection_info = self.connections[connection_id]
        
        # 방에 추가
        if room_id not in self.rooms:
            self.rooms[room_id] = set()
        
        self.rooms[room_id].add(connection_id)
        connection_info.rooms.add(room_id)
        
        # 통계 업데이트
        self.stats["rooms_count"] = len(self.rooms)
        
        # 방 참가 알림
        await self.send_to_connection(connection_id, WebSocketMessage(
            type=MessageType.ROOM_JOIN.value,
            data={
                "room_id": room_id,
                "status": "joined",
                "room_members": len(self.rooms[room_id])
            },
            timestamp=time.time(),
            message_id=str(uuid.uuid4()),
            room_id=room_id
        ))
        
        logger.info(f"연결 {connection_id}이 방 {room_id}에 참가")
        return True

    async def leave_room(self, connection_id: str, room_id: str) -> bool:
        """방 떠나기"""
        if connection_id not in self.connections or room_id not in self.rooms:
            return False
        
        connection_info = self.connections[connection_id]
        
        # 방에서 제거
        self.rooms[room_id].discard(connection_id)
        connection_info.rooms.discard(room_id)
        
        # 빈 방 제거
        if not self.rooms[room_id]:
            del self.rooms[room_id]
        
        # 통계 업데이트
        self.stats["rooms_count"] = len(self.rooms)
        
        # 방 떠나기 알림
        await self.send_to_connection(connection_id, WebSocketMessage(
            type=MessageType.ROOM_LEAVE.value,
            data={
                "room_id": room_id,
                "status": "left"
            },
            timestamp=time.time(),
            message_id=str(uuid.uuid4()),
            room_id=room_id
        ))
        
        logger.info(f"연결 {connection_id}이 방 {room_id}에서 떠남")
        return True

    async def handle_message(self, connection_id: str, message_data: str):
        """수신된 메시지 처리"""
        if connection_id not in self.connections:
            return
        
        try:
            data = json.loads(message_data)
            message_type = data.get("type")
            
            if message_type == MessageType.PING.value:
                await self._handle_ping(connection_id)
            elif message_type == MessageType.ROOM_JOIN.value:
                room_id = data.get("data", {}).get("room_id")
                if room_id:
                    await self.join_room(connection_id, room_id)
            elif message_type == MessageType.ROOM_LEAVE.value:
                room_id = data.get("data", {}).get("room_id")
                if room_id:
                    await self.leave_room(connection_id, room_id)
            else:
                # 등록된 핸들러 실행
                await self._execute_handlers(message_type, connection_id, data)
                
        except json.JSONDecodeError:
            logger.error(f"잘못된 JSON 메시지: {connection_id}")
        except Exception as e:
            logger.error(f"메시지 처리 중 오류: {str(e)}")

    def register_handler(self, message_type: str, handler: Callable):
        """메시지 핸들러 등록"""
        if message_type not in self.message_handlers:
            self.message_handlers[message_type] = []
        self.message_handlers[message_type].append(handler)

    async def _execute_handlers(self, message_type: str, connection_id: str, data: Dict[str, Any]):
        """등록된 핸들러 실행"""
        if message_type in self.message_handlers:
            for handler in self.message_handlers[message_type]:
                try:
                    await handler(connection_id, data)
                except Exception as e:
                    logger.error(f"핸들러 실행 중 오류: {str(e)}")

    async def _handle_ping(self, connection_id: str):
        """핑 메시지 처리"""
        if connection_id in self.connections:
            self.connections[connection_id].last_ping = datetime.now()
            
            await self.send_to_connection(connection_id, WebSocketMessage(
                type=MessageType.PONG.value,
                data={"timestamp": time.time()},
                timestamp=time.time(),
                message_id=str(uuid.uuid4())
            ))

    async def _periodic_cleanup(self):
        """주기적 정리 작업"""
        while True:
            try:
                await asyncio.sleep(30)  # 30초마다 실행
                
                current_time = datetime.now()
                stale_connections = []
                
                # 오래된 연결 찾기 (5분 이상 핑 없음)
                for connection_id, connection_info in self.connections.items():
                    if connection_info.last_ping:
                        time_diff = (current_time - connection_info.last_ping).total_seconds()
                        if time_diff > 300:  # 5분
                            stale_connections.append(connection_id)
                
                # 오래된 연결 제거
                for connection_id in stale_connections:
                    logger.info(f"비활성 연결 제거: {connection_id}")
                    await self.disconnect(connection_id)
                
                # Redis에 통계 저장 (선택적)
                if self.redis_client:
                    await self._save_stats_to_redis()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"정리 작업 중 오류: {str(e)}")

    async def _save_stats_to_redis(self):
        """Redis에 통계 저장"""
        try:
            stats_key = "websocket:stats"
            await self.redis_client.hset(stats_key, mapping=self.stats)
            await self.redis_client.expire(stats_key, 3600)  # 1시간 TTL
        except Exception as e:
            logger.error(f"Redis 통계 저장 실패: {str(e)}")

    def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """연결 정보 조회"""
        if connection_id not in self.connections:
            return None
        
        connection_info = self.connections[connection_id]
        return {
            "connection_id": connection_id,
            "user_id": connection_info.user_id,
            "session_id": connection_info.session_id,
            "status": connection_info.status.value,
            "connected_at": connection_info.connected_at.isoformat(),
            "last_ping": connection_info.last_ping.isoformat() if connection_info.last_ping else None,
            "rooms": list(connection_info.rooms),
            "metadata": connection_info.metadata
        }

    def get_stats(self) -> Dict[str, Any]:
        """통계 정보 조회"""
        return {
            **self.stats,
            "rooms": {
                room_id: len(connections) 
                for room_id, connections in self.rooms.items()
            },
            "users": {
                user_id: len(connections)
                for user_id, connections in self.user_connections.items()
            }
        }

    def get_room_info(self, room_id: str) -> Optional[Dict[str, Any]]:
        """방 정보 조회"""
        if room_id not in self.rooms:
            return None
        
        connections = self.rooms[room_id]
        members = []
        
        for connection_id in connections:
            if connection_id in self.connections:
                connection_info = self.connections[connection_id]
                members.append({
                    "connection_id": connection_id,
                    "user_id": connection_info.user_id,
                    "connected_at": connection_info.connected_at.isoformat()
                })
        
        return {
            "room_id": room_id,
            "member_count": len(connections),
            "members": members
        }


# 전역 WebSocket 관리자 인스턴스
websocket_manager = WebSocketManager()