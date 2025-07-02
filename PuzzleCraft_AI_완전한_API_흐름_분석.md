# 🌐 PuzzleCraft AI - 완전한 API 흐름 분석 및 Nginx 최적 구성

## 📋 **개요**

이 문서는 PuzzleCraft AI의 모든 백엔드 및 프론트엔드 API 흐름을 완전히 분석하고, Bastion 서버와 Main 서버의 최적 Nginx 구성을 제안합니다.

## 🏗️ **전체 시스템 아키텍처**

```
Internet → Bastion Server (puzzle.novelike.dev:443) → Main Server (10.0.3.153:80) → Backend Services
                                                    ↓
                                                    Frontend (Static Files)
```

## 🔍 **백엔드 서비스 완전 분석**

### **1. API Gateway (포트 8000) - 중앙 라우팅 허브**

**역할**: 모든 API 요청의 중앙 진입점
**엔드포인트**:
```
GET  /                     - 루트 정보
GET  /health              - 헬스 체크
GET  /api/services/status - 모든 서비스 상태 확인

# 라우터별 엔드포인트
/api/v1/auth/*     → Auth Service (8001)
/api/v1/puzzles/*  → Puzzle Generator (8004) 
/api/v1/games/*    → Game Manager (8002)
/api/v1/users/*    → 내부 처리 (TODO 상태)
```

**프록시 대상**:
- Auth Service (8001)
- Puzzle Generator (8004)
- Game Manager (8002)

### **2. Auth Service (포트 8001) - 인증 서비스**

**역할**: 사용자 인증 및 권한 관리
**엔드포인트**:
```
POST /register    - 회원가입
POST /login       - 로그인
GET  /me          - 현재 사용자 정보
POST /logout      - 로그아웃
GET  /health      - 헬스 체크
```

### **3. Game Manager (포트 8002) - 게임 세션 관리**

**역할**: 게임 세션, 점수, 리더보드 관리
**엔드포인트**:
```
POST /sessions                    - 게임 세션 생성
GET  /sessions/{session_id}       - 세션 정보 조회
POST /sessions/{session_id}/moves - 게임 움직임 기록
POST /sessions/{session_id}/complete - 게임 완료
GET  /leaderboard                 - 리더보드 조회
GET  /sessions                    - 세션 목록
WS   /ws/{session_id}            - 실시간 게임 WebSocket
GET  /health                      - 헬스 체크
```

### **4. OCR Service (포트 8003) - 텍스트 추출**

**역할**: 이미지에서 텍스트 추출 및 텍스트 퍼즐 생성
**엔드포인트**:
```
POST /extract-text/pytesseract    - PyTesseract OCR
POST /extract-text/easyocr        - EasyOCR
POST /extract-text/combined       - 통합 OCR
POST /create-text-puzzle          - 텍스트 퍼즐 생성
POST /preprocess-image            - 이미지 전처리
GET  /supported-languages         - 지원 언어 목록
GET  /health                      - 헬스 체크
```

### **5. Puzzle Generator (포트 8004) - AI 퍼즐 생성**

**역할**: AI 기반 지능형 퍼즐 생성 및 분석
**엔드포인트**:
```
POST /api/v1/analyze/complexity           - 이미지 복잡도 분석
POST /api/v1/analyze/difficulty-profile   - 난이도 프로필 생성
POST /api/v1/puzzles/generate-intelligent - 지능형 퍼즐 생성
GET  /api/v1/puzzles/status/{task_id}     - 생성 상태 확인
GET  /api/v1/puzzles/result/{task_id}     - 생성 결과 조회
POST /api/v1/puzzles/preview              - 퍼즐 미리보기
POST /api/v1/puzzles/optimize-for-user    - 사용자 맞춤 최적화
GET  /api/v1/ai-services/status           - AI 서비스 상태
GET  /api/v1/info/capabilities            - 서비스 기능 정보
GET  /api/v1/stats/difficulty             - 난이도 통계
GET  /health                              - 헬스 체크
```

### **6. Realtime Processor (포트 8005) - 실시간 처리**

**역할**: WebSocket 연결 및 실시간 알림 처리
**엔드포인트**:
```
WS   /ws/{user_id}              - 사용자별 WebSocket 연결
POST /users/register            - 실시간 사용자 등록
POST /tasks/submit              - 작업 제출
GET  /tasks/{task_id}/status    - 작업 상태 확인
DELETE /tasks/{task_id}         - 작업 삭제
GET  /tasks/{task_id}/history   - 작업 히스토리
GET  /statistics                - 통계 정보
POST /notifications/send        - 알림 전송
GET  /debug/connections         - 연결 디버그 정보
GET  /health                    - 헬스 체크
```

### **7. Segmentation Service (포트 8006) - 이미지 분할**

**역할**: AI 기반 이미지 객체 분할 및 퍼즐 조각 생성
**엔드포인트**:
```
POST /segment-objects           - 객체 분할
POST /create-puzzle-pieces      - 퍼즐 조각 생성
POST /segment-and-create-puzzle - 분할 및 퍼즐 생성
GET  /supported-classes         - 지원 클래스 목록
GET  /model-info               - 모델 정보
POST /analyze-image-complexity  - 이미지 복잡도 분석
GET  /health                   - 헬스 체크
```

### **8. Style Transfer (포트 8007) - 스타일 변환**

**역할**: AI 기반 이미지 스타일 변환
**엔드포인트**:
```
POST /apply-style              - 스타일 적용
POST /batch-apply-styles       - 배치 스타일 적용
GET  /available-styles         - 사용 가능한 스타일 목록
GET  /style-info/{style_name}  - 스타일 정보
GET  /download/{filename}      - 파일 다운로드
DELETE /cleanup/{filename}     - 파일 정리
POST /preview-style           - 스타일 미리보기
GET  /model-info              - 모델 정보
GET  /list-outputs            - 출력 파일 목록
GET  /health                  - 헬스 체크
```

## 🌐 **프론트엔드 API 연결 분석**

### **환경별 설정**

**로컬 개발 환경**:
```env
VITE_API_URL=http://localhost:8000/api
VITE_PUZZLE_GENERATOR_URL=http://localhost:8000/api/v1/puzzles
VITE_WS_URL=ws://localhost:8005/ws
```

**프로덕션 환경**:
```env
VITE_API_URL=https://puzzle.novelike.dev/api
VITE_PUZZLE_GENERATOR_URL=https://puzzle.novelike.dev/api/v1/puzzles
VITE_WS_URL=wss://puzzle.novelike.dev/ws
```

### **주요 API 클라이언트 흐름**

1. **인증 흐름**: Frontend → API Gateway → Auth Service
2. **퍼즐 생성**: Frontend → API Gateway → Puzzle Generator
3. **게임 플레이**: Frontend → API Gateway → Game Manager
4. **실시간 기능**: Frontend → Realtime Processor (직접 연결)

## 📊 **완전한 API 흐름 매핑**

### **1. 사용자 인증 흐름**
```
Frontend → https://puzzle.novelike.dev/api/v1/auth/login
       ↓
Bastion Server (443) → Main Server (80) → API Gateway (8000)
       ↓
API Gateway → Auth Service (8001) → Database
```

### **2. 퍼즐 생성 흐름**
```
Frontend → https://puzzle.novelike.dev/api/v1/puzzles/analyze/complexity
       ↓
Bastion Server → Main Server → API Gateway (8000)
       ↓
API Gateway → Puzzle Generator (8004)
       ↓
Puzzle Generator → OCR Service (8003) [필요시]
                → Segmentation Service (8006) [필요시]
                → Style Transfer (8007) [필요시]
```

### **3. 게임 플레이 흐름**
```
Frontend → https://puzzle.novelike.dev/api/v1/games/sessions
       ↓
Bastion Server → Main Server → API Gateway (8000)
       ↓
API Gateway → Game Manager (8002) → Database
```

### **4. 실시간 기능 흐름**
```
Frontend → wss://puzzle.novelike.dev/ws/{user_id}
       ↓
Bastion Server → Main Server → Realtime Processor (8005)
```

## 🔧 **Bastion vs Main 서버 Nginx 필요성 분석**

### **현재 구성의 장점**

1. **보안 계층화**: Bastion 서버가 SSL 종료 및 보안 필터링
2. **로드 분산**: 트래픽을 Main 서버로 분산
3. **장애 격리**: Bastion 서버 장애 시 Main 서버 독립 운영 가능
4. **SSL 관리**: 중앙화된 SSL 인증서 관리

### **최적화 권장사항**

**✅ 두 서버 모두 Nginx 필요 - 현재 구성 유지 권장**

**이유**:
1. **Bastion 서버**: SSL 종료, 보안, 캐싱
2. **Main 서버**: 서비스 라우팅, 로드 밸런싱, 정적 파일 서빙

## 🚀 **최적 Nginx 구성**

### **1. Bastion 서버 최적 구성**

```nginx
# /etc/nginx/sites-available/puzzlecraft-bastion
upstream main_servers {
    server 10.0.3.153:80 weight=3;
    # 추가 Main 서버 시 확장 가능
    # server 10.0.3.154:80 weight=2;
    
    # 헬스 체크
    keepalive 32;
}

# HTTP → HTTPS 리다이렉트
server {
    listen 80;
    server_name puzzle.novelike.dev;
    return 301 https://$server_name$request_uri;
}

# 메인 HTTPS 서버
server {
    listen 443 ssl http2;
    server_name puzzle.novelike.dev;

    # SSL 설정
    include /etc/nginx/ssl/novelike.dev_ssl.conf;
    
    # 보안 헤더
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # 압축 설정
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/javascript
        application/xml+rss
        application/json
        image/svg+xml;

    # 프론트엔드 및 API 요청 - Main 서버로 프록시
    location / {
        proxy_pass http://main_servers;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # 타임아웃 설정
        proxy_connect_timeout 30s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # API 요청 특별 처리
    location /api/ {
        proxy_pass http://main_servers;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # API 특화 타임아웃
        proxy_connect_timeout 30s;
        proxy_send_timeout 120s;
        proxy_read_timeout 300s;
        
        # 파일 업로드 지원
        client_max_body_size 100M;
        proxy_request_buffering off;
    }

    # WebSocket 연결
    location /ws/ {
        proxy_pass http://main_servers;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 타임아웃
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    # 헬스 체크 (캐싱 없음)
    location /health {
        proxy_pass http://main_servers;
        access_log off;
        proxy_cache off;
    }

    # 파일 업로드 제한
    client_max_body_size 100M;
    client_body_timeout 60s;
    client_header_timeout 60s;

    # 로그 설정
    access_log /var/log/nginx/puzzlecraft_bastion_access.log;
    error_log /var/log/nginx/puzzlecraft_bastion_error.log;
}
```

### **2. Main 서버 최적 구성**

```nginx
# /etc/nginx/sites-available/puzzlecraft-main

# 백엔드 서비스 업스트림 정의
upstream api_gateway {
    server localhost:8000 weight=3;
    # 다중 인스턴스 시 확장
    # server localhost:8001 weight=2;
    keepalive 16;
}

upstream auth_service {
    server localhost:8001;
    keepalive 8;
}

upstream game_manager {
    server localhost:8002;
    keepalive 8;
}

upstream ocr_service {
    server localhost:8003;
    keepalive 8;
}

upstream puzzle_generator {
    server localhost:8004 weight=3;
    # server localhost:8014 weight=2;
    keepalive 16;
}

upstream realtime_processor {
    server localhost:8005;
    keepalive 8;
}

upstream segmentation_service {
    server localhost:8006;
    keepalive 8;
}

upstream style_transfer {
    server localhost:8007;
    keepalive 8;
}

# 메인 서버 설정
server {
    listen 80;
    server_name localhost;

    # 프론트엔드 정적 파일
    location / {
        root /opt/PuzzleCraft-AI/frontend/web/dist;
        try_files $uri $uri/ /index.html;
        
        # 정적 파일 캐싱
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
            add_header Vary Accept-Encoding;
        }
    }

    # API Gateway 라우팅 (메인 API 진입점)
    location /api/ {
        proxy_pass http://api_gateway;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # API 최적화 설정
        proxy_buffering on;
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        proxy_busy_buffers_size 256k;
        
        # 타임아웃 설정
        proxy_connect_timeout 30s;
        proxy_send_timeout 120s;
        proxy_read_timeout 300s;
    }

    # WebSocket 연결 (실시간 기능)
    location /ws/ {
        proxy_pass http://realtime_processor;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 타임아웃
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    # 직접 서비스 접근 (개발/디버깅용)
    location /direct/auth/ {
        proxy_pass http://auth_service/;
        include /etc/nginx/conf.d/proxy_params.conf;
    }

    location /direct/game/ {
        proxy_pass http://game_manager/;
        include /etc/nginx/conf.d/proxy_params.conf;
    }

    location /direct/ocr/ {
        proxy_pass http://ocr_service/;
        include /etc/nginx/conf.d/proxy_params.conf;
    }

    location /direct/puzzle/ {
        proxy_pass http://puzzle_generator/;
        include /etc/nginx/conf.d/proxy_params.conf;
    }

    location /direct/segment/ {
        proxy_pass http://segmentation_service/;
        include /etc/nginx/conf.d/proxy_params.conf;
    }

    location /direct/style/ {
        proxy_pass http://style_transfer/;
        include /etc/nginx/conf.d/proxy_params.conf;
    }

    # 헬스 체크 엔드포인트
    location /health {
        proxy_pass http://api_gateway/health;
        access_log off;
    }

    # 서비스별 헬스 체크
    location /health/services {
        proxy_pass http://api_gateway/api/services/status;
        access_log off;
    }

    # 파일 업로드 설정
    client_max_body_size 100M;
    client_body_buffer_size 128k;
    client_body_timeout 60s;
    client_header_timeout 60s;

    # 로그 설정
    access_log /var/log/nginx/puzzlecraft_main_access.log;
    error_log /var/log/nginx/puzzlecraft_main_error.log;
}
```

### **3. 공통 설정 파일**

```nginx
# /etc/nginx/conf.d/proxy_params.conf
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_connect_timeout 30s;
proxy_send_timeout 60s;
proxy_read_timeout 60s;
```

### **4. 레이트 리미팅 설정**

```nginx
# /etc/nginx/conf.d/rate_limiting.conf

# 레이트 리미팅 존 정의
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/s;
limit_req_zone $binary_remote_addr zone=upload:10m rate=2r/s;
limit_req_zone $binary_remote_addr zone=puzzle_gen:10m rate=1r/s;
limit_req_zone $binary_remote_addr zone=websocket:10m rate=10r/s;

# API 엔드포인트별 적용
location /api/v1/auth/ {
    limit_req zone=auth burst=10 nodelay;
    # 기존 프록시 설정...
}

location /api/v1/puzzles/analyze/ {
    limit_req zone=upload burst=3 nodelay;
    # 기존 프록시 설정...
}

location /api/v1/puzzles/generate-intelligent {
    limit_req zone=puzzle_gen burst=2 nodelay;
    # 기존 프록시 설정...
}

location /ws/ {
    limit_req zone=websocket burst=5 nodelay;
    # 기존 프록시 설정...
}
```

### **5. 캐싱 설정**

```nginx
# /etc/nginx/conf.d/caching.conf

# 프록시 캐시 경로
proxy_cache_path /var/cache/nginx/puzzlecraft 
                 levels=1:2 
                 keys_zone=puzzlecraft:10m 
                 max_size=1g 
                 inactive=60m 
                 use_temp_path=off;

# API 응답 캐싱
location /api/v1/puzzles/status/ {
    proxy_cache puzzlecraft;
    proxy_cache_valid 200 5m;
    proxy_cache_key "$scheme$request_method$host$request_uri";
    add_header X-Cache-Status $upstream_cache_status;
    # 기존 프록시 설정...
}

location /api/v1/info/ {
    proxy_cache puzzlecraft;
    proxy_cache_valid 200 1h;
    proxy_cache_key "$scheme$request_method$host$request_uri";
    add_header X-Cache-Status $upstream_cache_status;
    # 기존 프록시 설정...
}

# 정적 파일 캐싱
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
    add_header Vary Accept-Encoding;
    
    # Gzip 압축
    gzip_static on;
}
```

## 📈 **성능 최적화 권장사항**

### **1. 서비스 확장성**

```bash
# API Gateway 다중 인스턴스
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
uvicorn main:app --host 0.0.0.0 --port 8001 --workers 4

# Puzzle Generator 다중 인스턴스 (GPU 고려)
uvicorn main:app --host 0.0.0.0 --port 8004 --workers 2
uvicorn main:app --host 0.0.0.0 --port 8014 --workers 2
```

### **2. 데이터베이스 연결 풀링**

```python
# 각 서비스에서 연결 풀 설정
DATABASE_POOL_SIZE = 20
DATABASE_MAX_OVERFLOW = 30
```

### **3. Redis 캐싱 활용**

```python
# OCR 결과 캐싱
REDIS_CACHE_TTL = 3600  # 1시간
REDIS_MAX_CONNECTIONS = 50
```

## 🛡️ **보안 강화 방안**

### **1. 방화벽 설정**

```bash
# Bastion 서버
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS

# Main 서버
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # Nginx
ufw allow 8000:8007/tcp  # Backend services (내부 네트워크만)
```

### **2. SSL/TLS 강화**

```nginx
# 강력한 SSL 설정
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384;
ssl_prefer_server_ciphers off;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
ssl_stapling on;
ssl_stapling_verify on;
```

### **3. 접근 제어**

```nginx
# 관리자 엔드포인트 접근 제한
location /admin/ {
    allow 10.0.0.0/8;
    deny all;
    # 기존 프록시 설정...
}

# 디버그 엔드포인트 접근 제한
location /debug/ {
    allow 127.0.0.1;
    allow 10.0.3.0/24;
    deny all;
    # 기존 프록시 설정...
}
```

## 📊 **모니터링 및 로깅**

### **1. 로그 분석 설정**

```nginx
# 상세 로그 형식
log_format detailed '$remote_addr - $remote_user [$time_local] '
                   '"$request" $status $body_bytes_sent '
                   '"$http_referer" "$http_user_agent" '
                   '$request_time $upstream_response_time '
                   '$upstream_addr $upstream_status '
                   '"$http_x_forwarded_for"';

access_log /var/log/nginx/puzzlecraft_detailed.log detailed;
```

### **2. 헬스 체크 스크립트**

```bash
#!/bin/bash
# /usr/local/bin/puzzlecraft-monitor.sh

SERVICES=(
    "API Gateway:8000"
    "Auth Service:8001"
    "Game Manager:8002"
    "OCR Service:8003"
    "Puzzle Generator:8004"
    "Realtime Processor:8005"
    "Segmentation Service:8006"
    "Style Transfer:8007"
)

for service in "${SERVICES[@]}"; do
    name=$(echo $service | cut -d: -f1)
    port=$(echo $service | cut -d: -f2)
    
    if ! curl -f http://localhost:$port/health > /dev/null 2>&1; then
        echo "❌ $name (포트 $port) 다운됨"
        # 알림 발송 또는 재시작 로직
    else
        echo "✅ $name (포트 $port) 정상"
    fi
done
```

## 🚀 **배포 및 운영 가이드**

### **1. 단계별 배포**

```bash
# 1. Bastion 서버 설정
sudo nginx -t && sudo systemctl reload nginx

# 2. Main 서버 설정
sudo nginx -t && sudo systemctl reload nginx

# 3. 백엔드 서비스 시작
cd /opt/PuzzleCraft-AI
python start_services.py

# 4. 프론트엔드 빌드 및 배포
cd frontend/web
npm run build
sudo cp -r dist/* /opt/PuzzleCraft-AI/frontend/web/dist/
```

### **2. 무중단 배포**

```bash
# 서비스별 순차 재시작
sudo systemctl reload puzzlecraft-api-gateway
sudo systemctl reload puzzlecraft-puzzle-generator
# ... 기타 서비스들
```

## 📝 **결론 및 권장사항**

### **✅ 최종 권장 구성**

1. **Bastion + Main 서버 구성 유지**: 보안과 확장성을 위해 현재 구조 유지
2. **API Gateway 중심 라우팅**: 모든 API 요청을 API Gateway를 통해 라우팅
3. **서비스별 직접 접근 제한**: 디버깅 목적으로만 직접 접근 허용
4. **WebSocket 직접 연결**: 실시간 기능을 위해 Realtime Processor 직접 연결
5. **단계적 확장**: 트래픽 증가에 따른 서비스 인스턴스 확장

### **🎯 핵심 이점**

- **보안**: 계층화된 보안 구조
- **확장성**: 서비스별 독립적 확장 가능
- **유지보수**: 중앙화된 라우팅 관리
- **성능**: 캐싱 및 로드 밸런싱 최적화
- **모니터링**: 통합된 로깅 및 헬스 체크

이 구성을 통해 PuzzleCraft AI는 안정적이고 확장 가능한 마이크로서비스 아키텍처를 구현할 수 있습니다.