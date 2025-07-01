#!/bin/bash

# =============================================================================
# PuzzleCraft AI 서비스 상태 확인 스크립트 (외부 PostgreSQL + 로컬 Redis)
# =============================================================================

LOG_DIR="./logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
CHECK_LOG="$LOG_DIR/health_check_$TIMESTAMP.log"

# 외부 PostgreSQL 설정
POSTGRES_HOST="10.0.0.207"
POSTGRES_PORT="5432"
POSTGRES_DB="puzzlecraft"
POSTGRES_USER="puzzlecraft"
POSTGRES_PASSWORD="puzzlecraft"

# 로컬 Redis 설정
REDIS_HOST="localhost"
REDIS_PORT="6379"

# 서비스 및 포트 매핑
declare -A SERVICE_PORTS=(
    ["puzzlecraft-api-gateway"]="8000"
    ["puzzlecraft-auth-service"]="8001"
    ["puzzlecraft-ocr-service"]="8002"
    ["puzzlecraft-puzzle-generator"]="8003"
    ["puzzlecraft-realtime-processor"]="8004"
    ["puzzlecraft-segmentation-service"]="8005"
    ["puzzlecraft-style-transfer"]="8006"
    ["puzzlecraft-game-manager"]="8007"
    ["nginx"]="80"
)

# 헬스체크 엔드포인트
declare -A HEALTH_ENDPOINTS=(
    ["puzzlecraft-api-gateway"]="/health"
    ["puzzlecraft-auth-service"]="/health"
    ["puzzlecraft-ocr-service"]="/health"
    ["puzzlecraft-puzzle-generator"]="/health"
    ["puzzlecraft-realtime-processor"]="/health"
    ["puzzlecraft-segmentation-service"]="/health"
    ["puzzlecraft-style-transfer"]="/health"
    ["puzzlecraft-game-manager"]="/health"
)

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo "[$timestamp] [$level] $message" >> "$CHECK_LOG"
}

# 포트 연결 테스트
test_port() {
    local host=${1:-localhost}
    local port=$2
    local timeout=${3:-5}
    
    if timeout "$timeout" bash -c "</dev/tcp/$host/$port" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# HTTP 헬스체크
test_http_health() {
    local url=$1
    local timeout=${2:-10}
    
    local response=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$timeout" "$url" 2>/dev/null)
    
    if [ "$response" = "200" ]; then
        return 0
    else
        return 1
    fi
}

# PostgreSQL 연결 테스트
test_postgres_health() {
    if PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1;" &>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Redis 연결 테스트
test_redis_health() {
    if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping | grep -q "PONG" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# 개별 서비스 상태 확인
check_service_health() {
    local service=$1
    local port=${SERVICE_PORTS[$service]}
    local endpoint=${HEALTH_ENDPOINTS[$service]}
    
    # systemd 서비스 상태 확인
    local service_status=$(systemctl is-active "$service" 2>/dev/null)
    if [ "$service_status" != "active" ]; then
        echo "❌ STOPPED"
        log "ERROR" "$service: systemd 서비스가 실행되지 않음 (상태: $service_status)"
        return 1
    fi
    
    # 포트 연결 테스트
    if [ -n "$port" ] && [ "$port" != "-" ]; then
        if ! test_port "localhost" "$port" 3; then
            echo "❌ PORT_FAIL"
            log "ERROR" "$service: 포트 $port 연결 실패"
            return 1
        fi
    fi
    
    # HTTP 헬스체크 (백엔드 서비스만)
    if [ -n "$endpoint" ]; then
        local health_url="http://localhost:$port$endpoint"
        if test_http_health "$health_url" 5; then
            echo "✅ HEALTHY"
            log "INFO" "$service: 정상 (포트: $port)"
            return 0
        else
            echo "⚠️  HTTP_FAIL"
            log "WARN" "$service: HTTP 헬스체크 실패 ($health_url)"
            return 1
        fi
    else
        echo "✅ RUNNING"
        log "INFO" "$service: 실행 중 (포트: $port)"
        return 0
    fi
}

# 데이터베이스 상태 확인
check_database_health() {
    echo ""
    echo "=== 데이터베이스 상태 ==="
    
    # PostgreSQL 상태
    if test_postgres_health; then
        echo "✅ PostgreSQL ($POSTGRES_HOST:$POSTGRES_PORT): 연결 성공"
        log "INFO" "PostgreSQL 연결 성공"
        
        # 데이터베이스 정보 조회
        local db_info=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT version();" 2>/dev/null | head -1 | xargs)
        echo "   버전: $db_info"
        
        # 연결 수 확인
        local connections=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null | xargs)
        echo "   활성 연결 수: $connections"
    else
        echo "❌ PostgreSQL ($POSTGRES_HOST:$POSTGRES_PORT): 연결 실패"
        log "ERROR" "PostgreSQL 연결 실패"
    fi
    
    # Redis 상태
    if test_redis_health; then
        echo "✅ Redis ($REDIS_HOST:$REDIS_PORT): 연결 성공"
        log "INFO" "Redis 연결 성공"
        
        # Redis 정보 조회
        local redis_info=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" info server 2>/dev/null | grep "redis_version" | cut -d: -f2 | tr -d '\r')
        echo "   버전: $redis_info"
        
        # 메모리 사용량 확인
        local memory_usage=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" info memory 2>/dev/null | grep "used_memory_human" | cut -d: -f2 | tr -d '\r')
        echo "   메모리 사용량: $memory_usage"
    else
        echo "❌ Redis ($REDIS_HOST:$REDIS_PORT): 연결 실패"
        log "ERROR" "Redis 연결 실패"
    fi
}

# 시스템 리소스 확인
check_system_resources() {
    echo ""
    echo "=== 시스템 리소스 상태 ==="
    
    # CPU 사용률
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1 2>/dev/null || echo "N/A")
    echo "CPU 사용률: ${cpu_usage}%"
    
    # 메모리 사용률
    local mem_info=$(free | grep Mem)
    local mem_total=$(echo $mem_info | awk '{print $2}')
    local mem_used=$(echo $mem_info | awk '{print $3}')
    local mem_percent=$(awk "BEGIN {printf \"%.1f\", $mem_used/$mem_total*100}")
    echo "메모리 사용률: ${mem_percent}% ($(numfmt --to=iec $((mem_used*1024)))/$(numfmt --to=iec $((mem_total*1024))))"
    
    # 디스크 사용률
    local disk_usage=$(df -h / | awk 'NR==2{print $5}' | cut -d'%' -f1)
    local disk_available=$(df -h / | awk 'NR==2{print $4}')
    echo "디스크 사용률: ${disk_usage}% (사용 가능: $disk_available)"
    
    # 시스템 로드
    local load_avg=$(uptime | awk -F'load average:' '{print $2}' | xargs)
    echo "시스템 로드: $load_avg"
    
    # systemd 서비스 수
    local active_services=$(systemctl list-units --type=service --state=active | grep -c "puzzlecraft-" 2>/dev/null || echo "0")
    echo "실행 중인 PuzzleCraft 서비스: ${active_services}개"
    
    log "INFO" "시스템 리소스 - CPU: ${cpu_usage}%, 메모리: ${mem_percent}%, 디스크: ${disk_usage}%, 로드: $load_avg"
}

# 네트워크 연결 확인
check_network_connectivity() {
    echo ""
    echo "=== 네트워크 연결 상태 ==="
    
    # 외부 인터넷 연결
    if ping -c 1 8.8.8.8 &>/dev/null; then
        echo "✅ 외부 인터넷 연결: 정상"
        log "INFO" "외부 인터넷 연결 정상"
    else
        echo "❌ 외부 인터넷 연결: 실패"
        log "ERROR" "외부 인터넷 연결 실패"
    fi
    
    # PostgreSQL 서버 연결
    if ping -c 1 "$POSTGRES_HOST" &>/dev/null; then
        echo "✅ PostgreSQL 서버 ($POSTGRES_HOST): 네트워크 연결 정상"
        log "INFO" "PostgreSQL 서버 네트워크 연결 정상"
    else
        echo "❌ PostgreSQL 서버 ($POSTGRES_HOST): 네트워크 연결 실패"
        log "ERROR" "PostgreSQL 서버 네트워크 연결 실패"
    fi
    
    # 포트 사용 현황
    echo ""
    echo "주요 포트 사용 현황:"
    for service in "${!SERVICE_PORTS[@]}"; do
        local port=${SERVICE_PORTS[$service]}
        if netstat -tuln 2>/dev/null | grep -q ":$port "; then
            echo "  포트 $port: 사용 중 ($service)"
        else
            echo "  포트 $port: 사용 가능"
        fi
    done
}

# 메인 헬스체크 실행
main_health_check() {
    mkdir -p "$LOG_DIR"
    
    echo "=== PuzzleCraft AI 서비스 상태 확인 ==="
    echo "확인 시간: $(date)"
    echo "환경: 외부 PostgreSQL ($POSTGRES_HOST:$POSTGRES_PORT) + 로컬 Redis ($REDIS_HOST:$REDIS_PORT)"
    echo ""
    
    log "INFO" "헬스체크 시작"
    
    # 데이터베이스 상태 먼저 확인
    check_database_health
    
    echo ""
    echo "=== 서비스 상태 ==="
    printf "%-35s %-10s %-15s %s\n" "서비스" "포트" "상태" "비고"
    printf "%-35s %-10s %-15s %s\n" "-----------------------------------" "----------" "---------------" "----"
    
    local total_services=0
    local healthy_services=0
    
    for service in "${!SERVICE_PORTS[@]}"; do
        local port=${SERVICE_PORTS[$service]}
        local status=$(check_service_health "$service")
        
        printf "%-35s %-10s %s\n" "$service" "$port" "$status"
        
        total_services=$((total_services + 1))
        if [[ "$status" == *"✅"* ]]; then
            healthy_services=$((healthy_services + 1))
        fi
    done
    
    echo ""
    echo "서비스 상태 요약: $healthy_services/$total_services 정상"
    
    # 시스템 리소스 확인
    check_system_resources
    
    # 네트워크 연결 확인
    check_network_connectivity
    
    echo ""
    echo "=== 헬스체크 완료 ==="
    echo "상세 로그: $CHECK_LOG"
    
    log "INFO" "헬스체크 완료 - $healthy_services/$total_services 서비스 정상"
    
    # 결과에 따른 종료 코드
    if [ "$healthy_services" -eq "$total_services" ]; then
        return 0
    else
        return 1
    fi
}

# 스크립트 실행
case "${1:-check}" in
    "check"|"health")
        main_health_check
        ;;
    "quick"|"q")
        echo "=== 빠른 상태 확인 ==="
        echo "PostgreSQL: $(test_postgres_health && echo "✅ 연결됨" || echo "❌ 연결 실패")"
        echo "Redis: $(test_redis_health && echo "✅ 연결됨" || echo "❌ 연결 실패")"
        echo ""
        for service in "${!SERVICE_PORTS[@]}"; do
            local status=$(check_service_health "$service")
            printf "%-35s %s\n" "$service" "$status"
        done
        ;;
    "db"|"database")
        check_database_health
        ;;
    "help"|"-h"|"--help")
        echo "사용법: $0 [옵션]"
        echo "옵션:"
        echo "  check, health  - 전체 헬스체크 (기본값)"
        echo "  quick, q       - 빠른 상태 확인"
        echo "  db, database   - 데이터베이스 연결만 확인"
        echo "  help           - 도움말 표시"
        ;;
    *)
        echo "알 수 없는 옵션: $1"
        echo "도움말을 보려면 '$0 help'를 실행하세요."
        exit 1
        ;;
esac
