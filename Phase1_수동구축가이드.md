# PuzzleCraft AI - Phase 1 수동 구축 가이드

## 개요
이 문서는 PuzzleCraft AI 프로젝트의 Phase 1 기반 인프라 구축을 완료하기 위해 수동으로 설정해야 하는 부분들을 안내합니다.

## 🎯 현재 완료된 작업
- ✅ 프로젝트 디렉토리 구조 생성
- ✅ FastAPI 기본 API Gateway 설정
- ✅ React + TypeScript + Vite 웹 프론트엔드 기본 구조
- ✅ 기본 페이지 컴포넌트들 (Home, Login, Register, Dashboard, PuzzleCreate, PuzzleGame)
- ✅ Tailwind CSS 스타일링 설정

## 🔧 수동 구축이 필요한 작업들

### 1. 데이터베이스 설정 (PostgreSQL)

#### 1.1 PostgreSQL 설치 및 설정
```bash
# Windows (PostgreSQL 공식 사이트에서 다운로드)
# https://www.postgresql.org/download/windows/

# 또는 Docker를 사용하는 경우
docker run --name puzzlecraft-postgres \
  -e POSTGRES_DB=puzzlecraft \
  -e POSTGRES_USER=puzzlecraft_user \
  -e POSTGRES_PASSWORD=your_password \
  -p 5432:5432 \
  -d postgres:15
```

#### 1.2 데이터베이스 스키마 생성
```sql
-- backend/database/schema.sql 파일 생성 후 실행
CREATE DATABASE puzzlecraft;

\c puzzlecraft;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 사용자 테이블
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    profile_image_url TEXT,
    level INTEGER DEFAULT 1,
    total_points INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 퍼즐 테이블
CREATE TABLE puzzles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    original_image_url TEXT NOT NULL,
    processed_image_url TEXT,
    style_type VARCHAR(50),
    piece_count INTEGER NOT NULL,
    difficulty_level INTEGER NOT NULL,
    ocr_text TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 게임 세션 테이블
CREATE TABLE game_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    puzzle_id UUID REFERENCES puzzles(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    game_mode VARCHAR(20) NOT NULL, -- 'single', 'challenge', 'multiplayer'
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    completion_time INTEGER, -- 초 단위
    score INTEGER,
    status VARCHAR(20) DEFAULT 'active', -- 'active', 'completed', 'abandoned'
    created_at TIMESTAMP DEFAULT NOW()
);

-- 리더보드 테이블
CREATE TABLE leaderboards (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    puzzle_id UUID REFERENCES puzzles(id) ON DELETE CASCADE,
    score INTEGER NOT NULL,
    completion_time INTEGER NOT NULL,
    rank INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 인덱스 생성
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_puzzles_user_id ON puzzles(user_id);
CREATE INDEX idx_game_sessions_user_id ON game_sessions(user_id);
CREATE INDEX idx_game_sessions_puzzle_id ON game_sessions(puzzle_id);
CREATE INDEX idx_leaderboards_score ON leaderboards(score DESC);
```

#### 1.3 데이터베이스 연결 설정
```python
# backend/database/connection.py 파일 생성
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://puzzlecraft_user:your_password@localhost:5432/puzzlecraft"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 2. 환경 변수 설정

#### 2.1 백엔드 환경 변수
```bash
# backend/api-gateway/.env 파일 생성
DATABASE_URL=postgresql://puzzlecraft_user:your_password@localhost:5432/puzzlecraft
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-super-secret-jwt-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AWS S3 설정 (이미지 저장용)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_BUCKET_NAME=puzzlecraft-images
AWS_REGION=ap-northeast-2

# 개발 환경 설정
DEBUG=True
CORS_ORIGINS=["http://localhost:3000"]
```

#### 2.2 프론트엔드 환경 변수
```bash
# frontend/web/.env 파일 생성
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_APP_NAME=PuzzleCraft AI
```

### 3. Redis 설치 및 설정

#### 3.1 Redis 설치
```bash
# Windows (Redis 공식 사이트에서 다운로드)
# https://redis.io/download

# 또는 Docker를 사용하는 경우
docker run --name puzzlecraft-redis \
  -p 6379:6379 \
  -d redis:7-alpine
```

### 4. React Native 모바일 앱 설정

#### 4.1 React Native CLI 설치
```bash
npm install -g @react-native-community/cli
```

#### 4.2 React Native 프로젝트 초기화
```bash
cd frontend/mobile
npx react-native init PuzzleCraftMobile --template react-native-template-typescript
```

#### 4.3 필요한 패키지 설치
```bash
cd PuzzleCraftMobile
npm install @react-navigation/native @react-navigation/stack
npm install react-native-screens react-native-safe-area-context
npm install react-native-gesture-handler react-native-reanimated
npm install react-native-vector-icons
npm install @react-native-async-storage/async-storage
npm install react-native-image-picker
```

#### 4.4 Android 설정
```bash
# Android Studio 설치 필요
# https://developer.android.com/studio

# Android SDK 경로 설정
export ANDROID_HOME=$HOME/Android/Sdk
export PATH=$PATH:$ANDROID_HOME/emulator
export PATH=$PATH:$ANDROID_HOME/tools
export PATH=$PATH:$ANDROID_HOME/tools/bin
export PATH=$PATH:$ANDROID_HOME/platform-tools
```

#### 4.5 iOS 설정 (macOS만 해당)
```bash
# Xcode 설치 필요
# App Store에서 Xcode 다운로드

# CocoaPods 설치
sudo gem install cocoapods

# iOS 의존성 설치
cd ios
pod install
```

### 5. Docker 설정

#### 5.1 백엔드 Dockerfile
```dockerfile
# backend/api-gateway/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 포트 노출
EXPOSE 8000

# 애플리케이션 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

#### 5.2 Docker Compose 설정
```yaml
# docker-compose.yml 파일 생성
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: puzzlecraft
      POSTGRES_USER: puzzlecraft_user
      POSTGRES_PASSWORD: your_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  api-gateway:
    build: ./backend/api-gateway
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://puzzlecraft_user:your_password@postgres:5432/puzzlecraft
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis
    volumes:
      - ./backend/api-gateway:/app

volumes:
  postgres_data:
```

### 6. 개발 스크립트 설정

#### 6.1 루트 package.json
```json
{
  "name": "puzzlecraft-ai",
  "private": true,
  "scripts": {
    "dev": "concurrently \"npm run dev:backend\" \"npm run dev:frontend\"",
    "dev:backend": "cd backend/api-gateway && uvicorn main:app --reload --host 0.0.0.0 --port 8000",
    "dev:frontend": "cd frontend/web && npm run dev",
    "dev:mobile": "cd frontend/mobile/PuzzleCraftMobile && npx react-native start",
    "build": "npm run build:frontend",
    "build:frontend": "cd frontend/web && npm run build",
    "docker:up": "docker-compose up -d",
    "docker:down": "docker-compose down",
    "db:migrate": "cd backend && python -m alembic upgrade head",
    "db:seed": "cd backend && python scripts/seed_data.py"
  },
  "devDependencies": {
    "concurrently": "^8.2.2"
  }
}
```

### 7. npm 패키지 이슈 해결

#### 7.1 보안 취약점 해결
```bash
# 프론트엔드 디렉토리에서 실행
cd frontend/web

# 보안 취약점 확인
npm audit

# 보안 취약점 자동 수정 (breaking change 포함)
npm audit fix --force

# 패키지 업데이트
npm update

# ESLint 최신 버전 업데이트 (deprecated 경고 해결)
npm install eslint@latest @typescript-eslint/eslint-plugin@latest @typescript-eslint/parser@latest --save-dev
```

#### 7.2 일반적인 npm 경고 해결
```bash
# deprecated 패키지 경고가 나타나는 경우:
# - inflight, rimraf, glob 등은 의존성 패키지에서 사용하는 것으로 직접 수정 불가
# - @humanwhocodes 관련 패키지는 ESLint 업데이트로 해결
# - peer dependency 경고는 일반적으로 무시해도 됨

# 개발 서버 정상 작동 확인
npm run dev
```

### 8. 실행 순서

#### 8.1 초기 설정
```bash
# 1. 루트 디렉토리에서 의존성 설치
npm install

# 2. 백엔드 의존성 설치
cd backend/api-gateway
pip install -r requirements.txt

# 3. 프론트엔드 의존성 설치
cd ../../frontend/web
npm install

# 4. 환경 변수 파일 생성 (.env 파일들)
# 위의 환경 변수 설정 섹션 참조

# 5. 데이터베이스 설정
# PostgreSQL 설치 및 스키마 생성

# 6. Redis 설치 및 실행
```

#### 7.2 개발 서버 실행
```bash
# 루트 디렉토리에서
npm run dev

# 또는 개별 실행
npm run dev:backend  # 백엔드만
npm run dev:frontend # 프론트엔드만
npm run dev:mobile   # 모바일만
```

#### 7.3 Docker를 사용하는 경우
```bash
# Docker Compose로 전체 환경 실행
npm run docker:up

# 종료
npm run docker:down
```

## 🚀 다음 단계 (Phase 2)
Phase 1 완료 후 다음 작업들을 진행합니다:
- AI 서비스 개발 (OCR, 이미지 세그멘테이션, 스타일 변환)
- 퍼즐 생성 엔진 개발
- 실시간 멀티플레이어 기능
- 모바일 앱 UI/UX 구현

## 📞 문제 해결
설정 중 문제가 발생하면 다음을 확인하세요:
1. 모든 환경 변수가 올바르게 설정되었는지
2. 데이터베이스 연결이 정상적인지
3. 포트 충돌이 없는지 (3000, 8000, 5432, 6379)
4. 방화벽 설정이 올바른지

## 📝 참고 자료
- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [React 공식 문서](https://react.dev/)
- [React Native 공식 문서](https://reactnative.dev/)
- [PostgreSQL 공식 문서](https://www.postgresql.org/docs/)
- [Redis 공식 문서](https://redis.io/documentation)
