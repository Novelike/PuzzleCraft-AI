# 🌐 PuzzleCraft AI Nginx 설정 가이드

## 📋 **개요**
이 문서는 PuzzleCraft AI의 실제 운영 중인 nginx 설정을 기반으로 작성되었습니다. Bastion 서버와 Main 서버의 실제 구성을 반영하여 업데이트된 엔드포인트에 맞는 추가 설정을 제공합니다.

## 🏗️ **아키텍처**
```
Internet → Bastion Server (puzzle.novelike.dev:443) → Main Server (10.0.3.153:80) → Backend Services
                                                    ↓
                                                    Frontend (Static Files)
```

## 📁 **현재 운영 중인 설정**

### 1. **Bastion 서버 설정** (`/etc/nginx/sites-available/novelike.conf`)

```nginx
server {
    listen 443 ssl http2;
    server_name puzzle.novelike.dev;

    include /etc/nginx/ssl/novelike.dev_ssl.conf;

    # ✅ 프론트엔드 - Main 서버로 프록시
    location / {
        proxy_pass http://10.0.3.153:80;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # ✅ API 요청 - API Gateway로 직접 연결
    location /api/ {
        proxy_pass http://10.0.3.153:8000/api/;  # 직접 API Gateway로
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 타임아웃 설정
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    # ✅ WebSocket - 올바른 포트로 직접 연결
    location /ws/ {
        proxy_pass http://10.0.3.153:8005/ws/;  # 직접 Realtime Processor로
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    client_max_body_size 100M;
}
```

### 2. **Main 서버 설정** (`/etc/nginx/sites-available/puzzlecraft`)

```nginx
server {
    listen 80;
    server_name localhost;

    # ✅ 프론트엔드 정적 파일
    location / {
        root /opt/PuzzleCraft-AI/frontend/web/dist;
        try_files $uri $uri/ /index.html;

        # 정적 파일 캐싱
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # ✅ API Gateway (수정됨)
    location /api/ {
        proxy_pass http://localhost:8000/api/;  # ✅ API Gateway의 /api 경로로 전달
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # API 최적화 설정
        proxy_buffering on;
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        proxy_busy_buffers_size 256k;
    }

    location = /api {
        return 301 /api/;
    }

    # ✅ WebSocket (수정됨)
    location /ws/ {
        proxy_pass http://localhost:8005/ws/;  # ✅ 올바른 포트
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 🔧 개별 서비스 직접 접근 (개발/디버깅용)
    location /auth/ {
        proxy_pass http://localhost:8001/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /ocr/ {
        proxy_pass http://localhost:8003/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /puzzle/ {
        proxy_pass http://localhost:8004/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # 파일 업로드 크기 제한
    client_max_body_size 100M;

    # 로그 설정
    access_log /var/log/nginx/puzzlecraft_access.log;
    error_log /var/log/nginx/puzzlecraft_error.log;
}
```

## 🔧 **업데이트된 엔드포인트에 대한 추가 설정**

### 3. **새로운 API 엔드포인트 지원**

현재 구현된 API Gateway 라우팅에 맞춰 다음 엔드포인트들이 추가로 지원됩니다:

```nginx
# Main 서버에 추가할 설정 (필요시)
location /api/v1/puzzles/analyze/complexity {
    proxy_pass http://localhost:8000/api/v1/puzzles/analyze/complexity;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # 파일 업로드를 위한 특별 설정
    client_max_body_size 100M;
    proxy_request_buffering off;
}

location /api/v1/puzzles/generate-intelligent {
    proxy_pass http://localhost:8000/api/v1/puzzles/generate-intelligent;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # 긴 처리 시간을 위한 타임아웃 설정
    proxy_read_timeout 300s;
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
}
```

### 4. **레이트 리미팅 설정** (`/etc/nginx/conf.d/rate-limiting.conf`)

```nginx
# 레이트 리미팅 존 설정
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=upload:10m rate=2r/s;
limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/s;
limit_req_zone $binary_remote_addr zone=puzzle_gen:10m rate=1r/s;

# API 엔드포인트별 레이트 리미팅 적용
location /api/v1/puzzles/analyze/ {
    limit_req zone=upload burst=3 nodelay;
    # 기존 프록시 설정...
}

location /api/v1/puzzles/generate-intelligent {
    limit_req zone=puzzle_gen burst=2 nodelay;
    # 기존 프록시 설정...
}

location /api/v1/auth/ {
    limit_req zone=auth burst=10 nodelay;
    # 기존 프록시 설정...
}

location /api/ {
    limit_req zone=api burst=20 nodelay;
    # 기존 프록시 설정...
}
```

### 5. **캐싱 설정** (`/etc/nginx/conf.d/caching.conf`)

```nginx
# 프록시 캐시 경로 설정
proxy_cache_path /var/cache/nginx/puzzlecraft levels=1:2 keys_zone=puzzlecraft:10m max_size=1g inactive=60m use_temp_path=off;

# API 응답 캐싱
location /api/v1/puzzles/status/ {
    proxy_cache puzzlecraft;
    proxy_cache_valid 200 5m;
    proxy_cache_key "$scheme$request_method$host$request_uri";
    add_header X-Cache-Status $upstream_cache_status;
    # 기존 프록시 설정...
}

# 정적 파일 캐싱 (이미 Main 서버에 설정됨)
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
    add_header Vary Accept-Encoding;
}
```

## 🚀 **배포 단계**

### 1. **Bastion 서버 설정**

```bash
# Bastion 서버에서 SSL 설정 확인
sudo nginx -t
sudo systemctl reload nginx

# SSL 인증서가 이미 설정되어 있는지 확인
ls -la /etc/nginx/ssl/novelike.dev_ssl.conf
```

### 2. **Main 서버 설정**

```bash
# Main 서버에서 nginx 설정 업데이트
sudo nano /etc/nginx/sites-available/puzzlecraft

# 설정 테스트 및 재로드
sudo nginx -t
sudo systemctl reload nginx

# 프론트엔드 빌드 및 배포
cd /opt/PuzzleCraft-AI/frontend/web
npm run build

# 빌드된 파일이 올바른 위치에 있는지 확인
ls -la /opt/PuzzleCraft-AI/frontend/web/dist/
```

### 3. **백엔드 서비스 시작**

```bash
# API Gateway 시작 (포트 8000)
cd /opt/PuzzleCraft-AI/backend/api-gateway
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 퍼즐 생성기 시작 (포트 8004)
cd /opt/PuzzleCraft-AI/backend/puzzle-generator
python -m uvicorn main:app --host 0.0.0.0 --port 8004 --reload

# 또는 시작 스크립트 사용
cd /opt/PuzzleCraft-AI
python start_services.py
```

### 4. **서비스 상태 확인**

```bash
# 서비스 포트 확인
netstat -tlnp | grep :8000  # API Gateway
netstat -tlnp | grep :8004  # Puzzle Generator
netstat -tlnp | grep :8005  # WebSocket (필요시)

# API 엔드포인트 테스트
curl http://localhost:8000/health
curl http://localhost:8004/health

# 외부에서 접근 테스트
curl https://puzzle.novelike.dev/api/health
```

## 📊 **모니터링 및 로깅**

### 1. **Nginx 접근 로그**

```nginx
# 사용자 정의 로그 형식 (Main 서버에 이미 설정됨)
access_log /var/log/nginx/puzzlecraft_access.log;
error_log /var/log/nginx/puzzlecraft_error.log;

# 더 자세한 로그 형식이 필요한 경우
log_format detailed '$remote_addr - $remote_user [$time_local] '
                   '"$request" $status $body_bytes_sent '
                   '"$http_referer" "$http_user_agent" '
                   '$request_time $upstream_response_time '
                   '$upstream_addr $upstream_status';
```

### 2. **헬스 체크 스크립트**

```bash
#!/bin/bash
# /usr/local/bin/puzzlecraft-health-check.sh

# API Gateway 상태 확인
if ! curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "API Gateway가 다운되었습니다"
    # 서비스 재시작 또는 알림 발송
fi

# Puzzle Generator 상태 확인
if ! curl -f http://localhost:8004/health > /dev/null 2>&1; then
    echo "Puzzle Generator가 다운되었습니다"
    # 서비스 재시작 또는 알림 발송
fi

# 외부 접근 확인
if ! curl -f https://puzzle.novelike.dev/api/health > /dev/null 2>&1; then
    echo "외부 접근이 불가능합니다"
    # 네트워크 또는 nginx 문제 확인
fi
```

## 🔧 **성능 튜닝**

### 1. **Nginx Worker 설정**

```nginx
# /etc/nginx/nginx.conf
worker_processes auto;
worker_connections 1024;
keepalive_timeout 65;
keepalive_requests 100;

# 파일 업로드 최적화
client_body_buffer_size 128k;
client_max_body_size 100M;
```

### 2. **백엔드 서비스 확장**

```bash
# 다중 인스턴스 실행
# API Gateway 인스턴스들
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
uvicorn main:app --host 0.0.0.0 --port 8001 --workers 4

# Puzzle Generator 인스턴스들
uvicorn main:app --host 0.0.0.0 --port 8004 --workers 2
uvicorn main:app --host 0.0.0.0 --port 8005 --workers 2
```

## 🛡️ **보안 고려사항**

1. **방화벽 설정**: 필요한 포트만 허용 (80, 443, 22, 8000, 8004, 8005)
2. **레이트 리미팅**: API 엔드포인트에 대한 적극적인 요청 제한
3. **SSL/TLS**: 강력한 암호화 및 프로토콜 사용 (이미 설정됨)
4. **보안 헤더**: 공격 방지를 위한 보안 헤더 추가
5. **접근 제어**: 민감한 엔드포인트에 대한 접근 제한
6. **모니터링**: 로그 모니터링 및 알림 설정

## 📝 **환경 변수 설정**

### **프로덕션 환경**
```bash
# 백엔드 서비스 환경 변수
export ENVIRONMENT=production
export ALLOWED_HOSTS=puzzle.novelike.dev
export ALLOWED_ORIGINS=https://puzzle.novelike.dev
export REDIS_URL=redis://localhost:6379
export DATABASE_URL=postgresql://user:pass@localhost/puzzlecraft

# 프론트엔드 환경 변수 (.env.production)
VITE_API_URL=https://puzzle.novelike.dev/api
VITE_PUZZLE_GENERATOR_URL=https://puzzle.novelike.dev/api/v1/puzzles
VITE_WS_URL=wss://puzzle.novelike.dev/ws
```

### **로컬 개발 환경**
```bash
# 프론트엔드 환경 변수 (.env.local)
VITE_API_URL=http://localhost:8000/api
VITE_PUZZLE_GENERATOR_URL=http://localhost:8000/api/v1/puzzles
VITE_WS_URL=ws://localhost:8005/ws
```

## 🎯 **요약**

이 설정은 실제 운영 중인 PuzzleCraft AI의 nginx 구성을 기반으로 하며, 업데이트된 엔드포인트와 새로운 API 라우팅을 지원합니다. Bastion 서버와 Main 서버의 이중 구조를 통해 안정적이고 확장 가능한 배포를 제공합니다.
