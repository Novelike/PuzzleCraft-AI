#!/bin/bash

# =============================================================================
# PuzzleCraft AI 배포 스크립트 (외부 PostgreSQL + 로컬 Redis 환경)
# =============================================================================

# 설정 변수
PROJECT_NAME="PuzzleCraft_AI"
LOG_DIR="./logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DEPLOY_LOG="$LOG_DIR/deploy_$TIMESTAMP.log"
ERROR_LOG="$LOG_DIR/deploy_error_$TIMESTAMP.log"

# 외부 데이터베이스 설정
POSTGRES_HOST="10.0.0.207"
POSTGRES_PORT="5432"
POSTGRES_DB="puzzlecraft_db"
POSTGRES_USER="puzzlecraft"
POSTGRES_PASSWORD="puzzlecraft123"

# 로컬 Redis 설정
REDIS_HOST="localhost"
REDIS_PORT="6379"

# 백엔드 서비스 목록 (실제 존재하는 서비스만)
BACKEND_SERVICES=(
    "api-gateway:8000"
    "auth-service:8001"
    "game-manager:8002"
    "ocr-service:8003"
    "puzzle-generator:8004"
    "realtime-processor:8005"
    "segmentation-service:8006"
    "style-transfer:8007"
)

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 로그 디렉토리 생성
create_log_dir() {
    if [ ! -d "$LOG_DIR" ]; then
        mkdir -p "$LOG_DIR"
        echo "로그 디렉토리 생성: $LOG_DIR"
    fi
}

# 로그 함수
log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    echo "[$timestamp] [$level] $message" >> "$DEPLOY_LOG"

    case $level in
        "INFO")
            echo -e "${GREEN}[INFO]${NC} $message" | tee -a "$DEPLOY_LOG"
            ;;
        "WARN")
            echo -e "${YELLOW}[WARN]${NC} $message" | tee -a "$DEPLOY_LOG"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} $message" | tee -a "$DEPLOY_LOG" | tee -a "$ERROR_LOG"
            ;;
    esac
}

# 진행률 표시
show_progress() {
    local current=$1
    local total=$2
    local service=$3
    local percent=$((current * 100 / total))

    printf "\r${BLUE}진행률: [%-50s] %d%% (%d/%d) - %s${NC}" \
           "$(printf '#%.0s' $(seq 1 $((percent / 2))))" \
           "$percent" "$current" "$total" "$service"

    if [ $current -eq $total ]; then
        echo ""
    fi
}

# 환경 설정
setup_environment() {
    log "INFO" "환경 설정을 확인합니다..."

    create_log_dir

    # npm 충돌 해결
    log "INFO" "npm 충돌 문제를 해결합니다..."
    sudo apt remove -y npm
    sudo apt autoremove -y

    # Node.js 최신 버전 설치
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt install -y nodejs

    # 필수 패키지 설치
    log "INFO" "필수 패키지를 설치합니다..."
    sudo apt update 2>&1 | tee -a "$DEPLOY_LOG"
    sudo apt install -y python3 python3-pip python3-venv nginx postgresql-client redis-tools 2>&1 | tee -a "$DEPLOY_LOG"

    # Python 버전 확인
    local python_version=$(python3 --version 2>/dev/null || echo "없음")
    log "INFO" "Python 버전: $python_version"

    # Node.js 버전 확인
    local node_version=$(node --version 2>/dev/null || echo "없음")
    log "INFO" "Node.js 버전: $node_version"
}

# PostgreSQL 연결 테스트
test_postgres_connection() {
    log "INFO" "PostgreSQL 연결 테스트: $POSTGRES_HOST:$POSTGRES_PORT"

    if PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1;" &>/dev/null; then
        log "INFO" "PostgreSQL 연결 성공"
        return 0
    else
        log "ERROR" "PostgreSQL 연결 실패"
        return 1
    fi
}

# Redis 연결 테스트
test_redis_connection() {
    log "INFO" "Redis 연결 테스트: $REDIS_HOST:$REDIS_PORT"

    if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping | grep -q "PONG"; then
        log "INFO" "Redis 연결 성공"
        return 0
    else
        log "ERROR" "Redis 연결 실패"
        return 1
    fi
}

# 전역 환경 변수 파일 생성
create_global_env() {
    log "INFO" "전역 환경 변수 파일을 생성합니다..."

    cat > .env.global << EOF
# Database Configuration (외부 PostgreSQL)
DATABASE_URL=postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_HOST:$POSTGRES_PORT/$POSTGRES_DB
POSTGRES_HOST=$POSTGRES_HOST
POSTGRES_PORT=$POSTGRES_PORT
POSTGRES_DB=$POSTGRES_DB
POSTGRES_USER=$POSTGRES_USER
POSTGRES_PASSWORD=$POSTGRES_PASSWORD

# Redis Configuration (로컬)
REDIS_URL=redis://$REDIS_HOST:$REDIS_PORT
REDIS_HOST=$REDIS_HOST
REDIS_PORT=$REDIS_PORT

# API Configuration
API_GATEWAY_URL=http://localhost:8000
JWT_SECRET=your-jwt-secret-key-here

# AI Service Configuration
OPENAI_API_KEY=your-openai-api-key
HUGGINGFACE_API_KEY=your-huggingface-api-key

# Frontend Configuration
VITE_API_URL=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8004/ws
VITE_PUZZLE_GENERATOR_URL=http://localhost:8003
EOF

    log "INFO" "전역 환경 변수 파일 생성 완료: .env.global"
}

# 백엔드 서비스 배포
deploy_backend_services() {
    log "INFO" "백엔드 서비스들을 배포합니다..."

    local total=${#BACKEND_SERVICES[@]}
    local current=0

    for service_info in "${BACKEND_SERVICES[@]}"; do
        local service=$(echo "$service_info" | cut -d':' -f1)
        local port=$(echo "$service_info" | cut -d':' -f2)

        current=$((current + 1))
        show_progress $current $total "$service"

        log "INFO" "배포 중: $service (포트: $port)"

        # 서비스 디렉토리 확인
        if [ ! -d "backend/$service" ]; then
            log "ERROR" "서비스 디렉토리를 찾을 수 없습니다: backend/$service"
            continue
        fi

        cd "backend/$service"

        # Python 가상환경 생성
        if [ ! -d "venv" ]; then
            log "INFO" "$service: Python 가상환경 생성 중..."
            python3 -m venv venv 2>&1 | tee -a "../../$DEPLOY_LOG"
        fi

        # 가상환경 활성화 및 의존성 설치
        log "INFO" "$service: 의존성 설치 중..."
        source venv/bin/activate

        if [ -f "requirements.txt" ]; then
            # pip 업그레이드
            pip install --upgrade pip 2>&1 | tee -a "../../$DEPLOY_LOG"

            # 호환성 문제가 있는 패키지들을 수정하여 설치
            # cryptography 버전 문제 해결
            sed -i 's/cryptography==41.0.8/cryptography>=41.0.0,<46.0.0/' requirements.txt 2>/dev/null || true

            # strawberry-graphql 버전 문제 해결
            sed -i 's/strawberry-graphql==0.214.1/strawberry-graphql>=0.200.0,<0.280.0/' requirements.txt 2>/dev/null || true

            # 의존성 설치 (오류 무시하고 계속 진행)
            pip install -r requirements.txt 2>&1 | tee -a "../../$DEPLOY_LOG" || log "WARN" "$service: 일부 의존성 설치 실패, 계속 진행합니다."
        else
            log "WARN" "$service: requirements.txt 파일이 없습니다."
        fi

        # 서비스별 환경 변수 파일 생성
        cat > .env << EOL
DATABASE_URL=postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_HOST:$POSTGRES_PORT/$POSTGRES_DB
REDIS_URL=redis://$REDIS_HOST:$REDIS_PORT
PORT=$port
HOST=0.0.0.0
SERVICE_NAME=$service
LOG_LEVEL=INFO
EOL

        # systemd 서비스 파일 생성
        sudo tee /etc/systemd/system/puzzlecraft-$service.service > /dev/null << EOL
[Unit]
Description=PuzzleCraft $service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
EnvironmentFile=$(pwd)/.env
ExecStart=$(pwd)/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/puzzlecraft-$service.log
StandardError=append:/var/log/puzzlecraft-$service-error.log

[Install]
WantedBy=multi-user.target
EOL

        # 로그 파일 생성 및 권한 설정
        sudo touch /var/log/puzzlecraft-$service.log
        sudo touch /var/log/puzzlecraft-$service-error.log
        sudo chown $USER:$USER /var/log/puzzlecraft-$service*.log

        # 서비스 등록 및 시작
        sudo systemctl daemon-reload
        sudo systemctl enable puzzlecraft-$service
        sudo systemctl restart puzzlecraft-$service

        # 서비스 상태 확인
        sleep 5
        if systemctl is-active --quiet puzzlecraft-$service; then
            log "INFO" "$service 배포 완료 (포트: $port)"
        else
            log "ERROR" "$service 배포 실패"
            sudo systemctl status puzzlecraft-$service 2>&1 | tee -a "../../$ERROR_LOG"
        fi

        deactivate
        cd "../.."
    done

    log "INFO" "백엔드 서비스 배포가 완료되었습니다."
}

# 메인 실행 함수
main() {
    case "${1:-deploy}" in
        "deploy"|"start")
            setup_environment
            if test_postgres_connection && test_redis_connection; then
                create_global_env
                deploy_backend_services
            else
                log "ERROR" "데이터베이스 연결 실패로 배포를 중단합니다."
                exit 1
            fi
            ;;
        "backend")
            setup_environment
            create_global_env
            deploy_backend_services
            ;;
        "test-db")
            create_log_dir
            test_postgres_connection
            test_redis_connection
            ;;
        "help"|"-h"|"--help")
            echo "사용법: $0 [옵션]"
            echo "옵션:"
            echo "  deploy, start    - 전체 서비스 배포 (기본값)"
            echo "  backend         - 백엔드 서비스만 배포"
            echo "  test-db         - 데이터베이스 연결 테스트"
            echo "  help            - 도움말 표시"
            ;;
        *)
            log "ERROR" "알 수 없는 옵션: $1"
            echo "도움말을 보려면 '$0 help'를 실행하세요."
            exit 1
            ;;
    esac
}

# 스크립트 실행
main "$@"
