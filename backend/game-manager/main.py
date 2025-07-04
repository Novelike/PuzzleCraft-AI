import httpx
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Float, Text, ForeignKey
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.dialects.postgresql import UUID
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from jose import JWTError, jwt
import os
from dotenv import load_dotenv
import uvicorn
import uuid
import json
import asyncio
from enum import Enum

load_dotenv()

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://puzzlecraft:puzzlecraft123@10.0.0.207:5432/puzzlecraft_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Security configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
ALGORITHM = "HS256"

security = HTTPBearer()

app = FastAPI(title="PuzzleCraft Game Manager", version="1.0.0")

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

# Enums
class GameMode(str, Enum):
	SINGLE = "single"
	CHALLENGE = "challenge"
	MULTIPLAYER = "multiplayer"

class GameStatus(str, Enum):
	WAITING = "waiting"
	ACTIVE = "active"
	PAUSED = "paused"
	COMPLETED = "completed"
	ABANDONED = "abandoned"

# Database Models
class GameSession(Base):
	__tablename__ = "game_sessions"

	id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
	puzzle_id = Column(String, nullable=False)
	user_id = Column(String, nullable=False)
	game_mode = Column(String, nullable=False)
	status = Column(String, default=GameStatus.WAITING)
	start_time = Column(DateTime, default=datetime.utcnow)
	end_time = Column(DateTime, nullable=True)
	completion_time = Column(Integer, nullable=True)  # in seconds
	score = Column(Integer, default=0)
	moves_count = Column(Integer, default=0)
	hints_used = Column(Integer, default=0)
	created_at = Column(DateTime, default=datetime.utcnow)
	updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class GameMove(Base):
	__tablename__ = "game_moves"

	id = Column(Integer, primary_key=True, index=True)
	session_id = Column(String, ForeignKey("game_sessions.id"), nullable=False)
	piece_id = Column(String, nullable=False)
	x = Column(Float, nullable=False)
	y = Column(Float, nullable=False)
	rotation = Column(Float, default=0)
	is_correct = Column(Boolean, default=False)
	timestamp = Column(DateTime, default=datetime.utcnow)

	session = relationship("GameSession", backref="moves")

class Leaderboard(Base):
	__tablename__ = "leaderboard"

	id = Column(Integer, primary_key=True, index=True)
	user_id = Column(String, nullable=False)
	username = Column(String, nullable=False)
	puzzle_id = Column(String, nullable=False)
	score = Column(Integer, nullable=False)
	completion_time = Column(Integer, nullable=False)
	game_mode = Column(String, nullable=False)
	created_at = Column(DateTime, default=datetime.utcnow)

# Pydantic Models
class GameSessionCreate(BaseModel):
	puzzle_id: str
	game_mode: GameMode

class GameSessionResponse(BaseModel):
	id: str
	puzzle_id: str
	game_mode: str
	status: str
	start_time: Optional[datetime]
	end_time: Optional[datetime]
	completion_time: Optional[int]
	score: Optional[int]
	moves_count: int
	hints_used: int

	class Config:
		from_attributes = True

class GameMoveCreate(BaseModel):
	piece_id: str
	x: float
	y: float
	rotation: Optional[float] = 0

class GameMoveResponse(BaseModel):
	id: int
	piece_id: str
	x: float
	y: float
	rotation: float
	is_correct: bool
	timestamp: datetime

	class Config:
		from_attributes = True

class LeaderboardEntry(BaseModel):
	username: str
	score: int
	completion_time: int
	game_mode: str
	created_at: datetime

	class Config:
		from_attributes = True

class UserStats(BaseModel):
	total_puzzles_completed: int
	total_play_time: int
	average_completion_time: float
	best_score: int
	current_streak: int

class GameCompletion(BaseModel):
	completion_time: int
	final_score: int

# WebSocket Connection Manager
class ConnectionManager:
	def __init__(self):
		self.active_connections: Dict[str, List[WebSocket]] = {}

	async def connect(self, websocket: WebSocket, session_id: str):
		await websocket.accept()
		if session_id not in self.active_connections:
			self.active_connections[session_id] = []
		self.active_connections[session_id].append(websocket)

	def disconnect(self, websocket: WebSocket, session_id: str):
		if session_id in self.active_connections:
			self.active_connections[session_id].remove(websocket)
			if not self.active_connections[session_id]:
				del self.active_connections[session_id]

	async def send_personal_message(self, message: str, websocket: WebSocket):
		await websocket.send_text(message)

	async def broadcast_to_session(self, message: str, session_id: str):
		if session_id in self.active_connections:
			for connection in self.active_connections[session_id]:
				await connection.send_text(message)

manager = ConnectionManager()

# Database dependency
def get_db():
	db = SessionLocal()
	try:
		yield db
	finally:
		db.close()

# Security functions
async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)):
	credentials_exception = HTTPException(
		status_code=status.HTTP_401_UNAUTHORIZED,
		detail="Could not validate credentials",
		headers={"WWW-Authenticate": "Bearer"},
	)
	try:
		# 인증 서비스에서 실제 사용자 정보 가져오기
		async with httpx.AsyncClient() as client:
			response = await client.get(
				f"{AUTH_SERVICE_URL}/me",
				headers={"Authorization": f"Bearer {credentials.credentials}"},
				timeout=10.0
			)
			if response.status_code == 200:
				user_info = response.json()
				return user_info["id"]  # ✅ 실제 UUID 문자열 반환
			else:
				raise credentials_exception
	except Exception:
		raise credentials_exception

# Game Logic Functions
def calculate_score(completion_time: int, moves_count: int, hints_used: int, game_mode: str) -> int:
	"""Calculate game score based on performance metrics"""
	base_score = 1000

	# Time bonus (faster completion = higher score)
	time_bonus = max(0, 500 - (completion_time // 10))

	# Move penalty (fewer moves = higher score)
	move_penalty = min(300, moves_count * 2)

	# Hint penalty
	hint_penalty = hints_used * 50

	# Game mode multiplier
	mode_multiplier = {
		GameMode.SINGLE: 1.0,
		GameMode.CHALLENGE: 1.5,
		GameMode.MULTIPLAYER: 2.0
	}.get(game_mode, 1.0)

	final_score = int((base_score + time_bonus - move_penalty - hint_penalty) * mode_multiplier)
	return max(0, final_score)

def validate_piece_placement(piece_id: str, x: float, y: float, rotation: float) -> bool:
	"""Validate if a puzzle piece is placed correctly"""
	# This is a simplified validation - in a real implementation,
	# you would check against the actual puzzle solution
	# For now, we'll use a mock validation based on piece_id
	correct_positions = {
		"piece_1": {"x": 100, "y": 100, "rotation": 0},
		"piece_2": {"x": 200, "y": 100, "rotation": 90},
		"piece_3": {"x": 100, "y": 200, "rotation": 180},
		"piece_4": {"x": 200, "y": 200, "rotation": 270},
	}

	if piece_id not in correct_positions:
		return False

	correct = correct_positions[piece_id]
	tolerance = 10  # pixels
	rotation_tolerance = 15  # degrees

	return (abs(x - correct["x"]) <= tolerance and
	        abs(y - correct["y"]) <= tolerance and
	        abs(rotation - correct["rotation"]) <= rotation_tolerance)

# API Routes
@app.post("/sessions", response_model=GameSessionResponse)
async def create_game_session(
		session_data: GameSessionCreate,
		user_id: str = Depends(get_current_user_id),
		db: Session = Depends(get_db)
):
	"""Create a new game session"""
	db_session = GameSession(
		puzzle_id=session_data.puzzle_id,
		user_id=user_id,
		game_mode=session_data.game_mode,
		status=GameStatus.ACTIVE
	)
	db.add(db_session)
	db.commit()
	db.refresh(db_session)

	return db_session

@app.get("/sessions/{session_id}", response_model=GameSessionResponse)
async def get_game_session(
		session_id: str,
		user_id: str = Depends(get_current_user_id),
		db: Session = Depends(get_db)
):
	"""Get game session details"""
	try:
		session = db.query(GameSession).filter(
			GameSession.id == session_id,
			GameSession.user_id == user_id
		).first()

		if not session:
			raise HTTPException(status_code=404, detail="Game session not found")

		# moves_count 필드가 없는 경우를 대비하여 기본값 설정
		if not hasattr(session, 'moves_count') or session.moves_count is None:
			session.moves_count = 0

		return session
	except Exception as e:
		print(f"Database query error in get_game_session: {e}")
		raise HTTPException(status_code=500, detail="Failed to fetch game session")

@app.post("/sessions/{session_id}/moves", response_model=GameMoveResponse)
async def make_move(
		session_id: str,
		move: GameMoveCreate,
		user_id: str = Depends(get_current_user_id),
		db: Session = Depends(get_db)
):
	"""Record a puzzle piece move"""
	# Verify session exists and belongs to user
	session = db.query(GameSession).filter(
		GameSession.id == session_id,
		GameSession.user_id == user_id,
		GameSession.status == GameStatus.ACTIVE
	).first()

	if not session:
		raise HTTPException(status_code=404, detail="Active game session not found")

	# Validate piece placement
	is_correct = validate_piece_placement(move.piece_id, move.x, move.y, move.rotation)

	# Create move record
	db_move = GameMove(
		session_id=session_id,
		piece_id=move.piece_id,
		x=move.x,
		y=move.y,
		rotation=move.rotation,
		is_correct=is_correct
	)
	db.add(db_move)

	# Update session move count (moves_count 필드가 없는 경우를 대비)
	try:
		if hasattr(session, 'moves_count'):
			if session.moves_count is None:
				session.moves_count = 0
			session.moves_count += 1
		else:
			# moves_count 필드가 없는 경우 무시
			pass
	except Exception as e:
		print(f"Warning: Could not update moves_count: {e}")

	db.commit()
	db.refresh(db_move)

	# Broadcast move to other players in multiplayer mode
	if session.game_mode == GameMode.MULTIPLAYER:
		move_data = {
			"type": "move",
			"piece_id": move.piece_id,
			"x": move.x,
			"y": move.y,
			"rotation": move.rotation,
			"is_correct": is_correct,
			"user_id": user_id
		}
		await manager.broadcast_to_session(json.dumps(move_data), session_id)

	return db_move

@app.post("/sessions/{session_id}/complete")
async def complete_game(
		session_id: str,
		completion: GameCompletion,
		user_id: str = Depends(get_current_user_id),
		db: Session = Depends(get_db)
):
	"""Complete a game session"""
	session = db.query(GameSession).filter(
		GameSession.id == session_id,
		GameSession.user_id == user_id,
		GameSession.status == GameStatus.ACTIVE
	).first()

	if not session:
		raise HTTPException(status_code=404, detail="Active game session not found")

	# Update session
	session.status = GameStatus.COMPLETED
	session.end_time = datetime.utcnow()
	session.completion_time = completion.completion_time
	session.score = completion.final_score

	# Add to leaderboard
	# First, get username (in real implementation, fetch from auth service)
	username = f"user_{user_id}"

	leaderboard_entry = Leaderboard(
		user_id=user_id,
		username=username,
		puzzle_id=session.puzzle_id,
		score=completion.final_score,
		completion_time=completion.completion_time,
		game_mode=session.game_mode
	)
	db.add(leaderboard_entry)
	db.commit()

	return {
		"message": "Game completed successfully",
		"completion_time": completion.completion_time,
		"score": completion.final_score,
		"session_id": session_id
	}

@app.get("/leaderboard", response_model=List[LeaderboardEntry])
async def get_leaderboard(
		puzzle_id: Optional[str] = None,
		game_mode: Optional[str] = None,
		limit: int = 10,
		db: Session = Depends(get_db)
):
	"""Get leaderboard entries"""
	query = db.query(Leaderboard)

	if puzzle_id:
		query = query.filter(Leaderboard.puzzle_id == puzzle_id)
	if game_mode:
		query = query.filter(Leaderboard.game_mode == game_mode)

	entries = query.order_by(Leaderboard.score.desc()).limit(limit).all()
	return entries

@app.get("/sessions", response_model=List[GameSessionResponse])
async def list_game_sessions(
		skip: int = 0,
		limit: int = 10,
		user_id: str = Depends(get_current_user_id),
		db: Session = Depends(get_db)
):
	"""List user's game sessions"""
	try:
		sessions = db.query(GameSession).filter(
			GameSession.user_id == user_id
		).offset(skip).limit(limit).all()

		# moves_count 필드가 없는 경우를 대비하여 기본값 설정
		for session in sessions:
			if not hasattr(session, 'moves_count') or session.moves_count is None:
				session.moves_count = 0

		return sessions
	except Exception as e:
		# 데이터베이스 스키마 문제가 있는 경우 빈 리스트 반환
		print(f"Database query error in list_game_sessions: {e}")
		return []

@app.get("/stats", response_model=UserStats)
async def get_user_stats(
		user_id: str = Depends(get_current_user_id),  # ✅ JWT에서 user_id 추출
		db: Session = Depends(get_db)
):
	"""사용자 게임 통계 조회"""
	try:
		# 완료된 게임 세션들 조회 - moves_count 컬럼 문제를 피하기 위해 필요한 컬럼만 선택
		completed_sessions = db.query(
			GameSession.id,
			GameSession.completion_time,
			GameSession.score,
			GameSession.created_at
		).filter(
			GameSession.user_id == user_id,
			GameSession.status == GameStatus.COMPLETED
		).all()
	except Exception as e:
		# 데이터베이스 스키마 문제가 있는 경우 기본값 반환
		print(f"Database query error: {e}")
		return UserStats(
			total_puzzles_completed=0,
			total_play_time=0,
			average_completion_time=0.0,
			best_score=0,
			current_streak=0
		)

	if not completed_sessions:
		return UserStats(
			total_puzzles_completed=0,
			total_play_time=0,
			average_completion_time=0.0,
			best_score=0,
			current_streak=0
		)

	# 통계 계산 - 튜플 형태의 데이터 처리
	total_puzzles = len(completed_sessions)
	total_time = sum(session.completion_time or 0 for session in completed_sessions)
	avg_time = total_time / total_puzzles if total_puzzles > 0 else 0.0
	best_score = max(session.score or 0 for session in completed_sessions)
	current_streak = calculate_current_streak_from_tuples(completed_sessions)

	return UserStats(
		total_puzzles_completed=total_puzzles,
		total_play_time=total_time,
		average_completion_time=avg_time,
		best_score=best_score,
		current_streak=current_streak
	)

def calculate_current_streak(sessions: List[GameSession]) -> int:
	"""현재 연속 완료 일수 계산"""
	if not sessions:
		return 0

	# 날짜별로 그룹화하여 연속 일수 계산
	from collections import defaultdict
	dates = defaultdict(int)

	for session in sessions:
		if session.created_at:
			date_key = session.created_at.date()
			dates[date_key] += 1

	# 최근 날짜부터 연속 일수 계산
	sorted_dates = sorted(dates.keys(), reverse=True)
	streak = 0
	current_date = datetime.now().date()

	for date in sorted_dates:
		if (current_date - date).days == streak:
			streak += 1
		else:
			break

	return streak

def calculate_current_streak_from_tuples(sessions) -> int:
	"""튜플 형태의 세션 데이터에서 현재 연속 완료 일수 계산"""
	if not sessions:
		return 0

	# 날짜별로 그룹화하여 연속 일수 계산
	from collections import defaultdict
	dates = defaultdict(int)

	for session in sessions:
		# 튜플에서 created_at은 4번째 요소 (인덱스 3)
		if len(session) > 3 and session[3]:
			date_key = session[3].date()
			dates[date_key] += 1

	# 최근 날짜부터 연속 일수 계산
	sorted_dates = sorted(dates.keys(), reverse=True)
	streak = 0
	current_date = datetime.now().date()

	for date in sorted_dates:
		if (current_date - date).days == streak:
			streak += 1
		else:
			break

	return streak

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
	"""WebSocket endpoint for real-time multiplayer communication"""
	await manager.connect(websocket, session_id)
	try:
		while True:
			data = await websocket.receive_text()
			# Echo the message to all connected clients in the session
			await manager.broadcast_to_session(data, session_id)
	except WebSocketDisconnect:
		manager.disconnect(websocket, session_id)

@app.get("/")
async def root():
	return {"message": "PuzzleCraft Game Manager"}

@app.get("/health")
async def health_check():
	return {"status": "healthy", "service": "game-manager"}

# Create tables
Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
	uvicorn.run(app, host="0.0.0.0", port=8002)
