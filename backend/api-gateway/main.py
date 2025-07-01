from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import uvicorn
import os
import redis.asyncio as redis
from contextlib import asynccontextmanager
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis 기반 레이트 리미터 설정
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
limiter = Limiter(key_func=get_remote_address, storage_uri=redis_url)

# 라이프사이클 이벤트 핸들러
@asynccontextmanager
async def lifespan(app: FastAPI):
	"""애플리케이션 라이프사이클 관리"""
	# 시작 시
	logger.info("API Gateway 초기화 시작")

	# Redis 연결 테스트
	try:
		redis_client = redis.from_url(redis_url)
		await redis_client.ping()
		logger.info("Redis 연결 성공")
		await redis_client.close()
	except Exception as e:
		logger.warning(f"Redis 연결 실패: {e}, 메모리 기반 레이트 리미팅 사용")

	logger.info("API Gateway 초기화 완료")
	yield

	# 종료 시
	logger.info("API Gateway 종료")

app = FastAPI(
	title="PuzzleCraft AI API Gateway",
	description="AI 기반 퍼즐 게임을 위한 통합 API 게이트웨이",
	version="1.0.0",
	lifespan=lifespan
)

# 레이트 리미팅 미들웨어 추가
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# 신뢰할 수 있는 호스트 미들웨어 (프로덕션 환경)
if os.getenv("ENVIRONMENT") == "production":
	allowed_hosts = os.getenv("ALLOWED_HOSTS", "puzzle.novelike.dev,localhost").split(",")
	app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

# CORS 미들웨어 (보안 강화)
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
if os.getenv("ENVIRONMENT") == "production":
	# 프로덕션에서는 특정 도메인만 허용
	allowed_origins = ["https://puzzle.novelike.dev", "https://www.puzzle.novelike.dev"]

app.add_middleware(
	CORSMiddleware,
	allow_origins=allowed_origins,
	allow_credentials=True,
	allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
	allow_headers=["*"],
	expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)

# 보안 헤더 미들웨어
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
	"""보안 헤더 추가"""
	response = await call_next(request)

	# 보안 헤더 설정
	response.headers["X-Content-Type-Options"] = "nosniff"
	response.headers["X-Frame-Options"] = "DENY"
	response.headers["X-XSS-Protection"] = "1; mode=block"
	response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
	response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
	response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"

	return response

# 라우터 등록 (라우터가 존재하는 경우에만)
try:
	from routers import auth, puzzles, games, users
	app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
	app.include_router(puzzles.router, prefix="/api/v1/puzzles", tags=["puzzles"])
	app.include_router(games.router, prefix="/api/v1/games", tags=["games"])
	app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
	logger.info("모든 라우터 등록 완료")
except ImportError as e:
	logger.warning(f"라우터 임포트 실패: {e}, 기본 엔드포인트만 사용")

# 기본 엔드포인트 (레이트 리미팅 적용)
@app.get("/")
@app.get("/api/")
@limiter.limit("100/minute")
async def root(request: Request):
	"""API Gateway 루트 엔드포인트"""
	return {
		"message": "PuzzleCraft AI API Gateway",
		"version": "1.0.0",
		"status": "operational",
		"endpoints": {
			"health": "/health",
			"docs": "/docs",
			"auth": "/api/v1/auth",
			"puzzles": "/api/v1/puzzles",
			"games": "/api/v1/games",
			"users": "/api/v1/users"
		}
	}

@app.get("/health")
@app.get("/api/health")
@limiter.limit("200/minute")
async def health_check(request: Request):
	"""헬스체크 엔드포인트"""
	return {
		"status": "healthy",
		"service": "api-gateway",
		"version": "1.0.0",
		"timestamp": "2024-01-01T00:00:00Z"
	}

# 서비스 프록시 엔드포인트들 (레이트 리미팅 적용)
@app.get("/api/services/status")
@limiter.limit("50/minute")
async def services_status(request: Request):
	"""모든 서비스 상태 확인"""
	import httpx

	services = {
		"auth-service": "http://localhost:8001/health",
		"game-manager": "http://localhost:8002/health",
		"ocr-service": "http://localhost:8003/health",
		"puzzle-generator": "http://localhost:8004/health",
		"realtime-processor": "http://localhost:8005/health",
		"segmentation-service": "http://localhost:8006/health",
		"style-transfer": "http://localhost:8007/health"
	}

	status_results = {}

	async with httpx.AsyncClient(timeout=5.0) as client:
		for service_name, url in services.items():
			try:
				response = await client.get(url)
				status_results[service_name] = {
					"status": "healthy" if response.status_code == 200 else "unhealthy",
					"response_time": response.elapsed.total_seconds(),
					"status_code": response.status_code
				}
			except Exception as e:
				status_results[service_name] = {
					"status": "error",
					"error": str(e)
				}

	return {
		"gateway_status": "healthy",
		"services": status_results,
		"timestamp": "2024-01-01T00:00:00Z"
	}

if __name__ == "__main__":
	uvicorn.run(
		"main:app",
		host="0.0.0.0",
		port=8000,
		reload=True,
		log_level="info"
	)
