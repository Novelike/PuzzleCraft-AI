#!/bin/bash

# 백엔드 서비스 목록
BACKEND_SERVICES=(
    "puzzlecraft-api-gateway"
    "puzzlecraft-auth-service"
    "puzzlecraft-ocr-service"
    "puzzlecraft-puzzle-generator"
    "puzzlecraft-realtime-processor"
    "puzzlecraft-segmentation-service"
    "puzzlecraft-style-transfer"
    "puzzlecraft-game-manager"
)

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 서비스 상태 확인
show_status() {
    echo "=== PuzzleCraft AI 서비스 상태 ==="
    printf "%-35s %-15s %-10s\n" "서비스" "상태" "포트"
    printf "%-35s %-15s %-10s\n" "-----------------------------------" "---------------" "----------"

    for service in "${BACKEND_SERVICES[@]}"; do
        local status=$(systemctl is-active "$service" 2>/dev/null)
        local port=""

        case $service in
            "puzzlecraft-api-gateway") port="8000" ;;
            "puzzlecraft-auth-service") port="8001" ;;
            "puzzlecraft-ocr-service") port="8002" ;;
            "puzzlecraft-puzzle-generator") port="8003" ;;
            "puzzlecraft-realtime-processor") port="8004" ;;
            "puzzlecraft-segmentation-service") port="8005" ;;
            "puzzlecraft-style-transfer") port="8006" ;;
            "puzzlecraft-game-manager") port="8007" ;;
        esac

        case $status in
            "active")
                printf "%-35s ${GREEN}%-15s${NC} %-10s\n" "$service" "$status" "$port"
                ;;
            "inactive"|"failed")
                printf "%-35s ${RED}%-15s${NC} %-10s\n" "$service" "$status" "$port"
                ;;
            *)
                printf "%-35s ${YELLOW}%-15s${NC} %-10s\n" "$service" "$status" "$port"
                ;;
        esac
    done
}

# 서비스 시작
start_services() {
    echo "모든 백엔드 서비스를 시작합니다..."
    for service in "${BACKEND_SERVICES[@]}"; do
        echo "서비스 시작: $service"
        sudo systemctl start "$service"
        sleep 2
    done
}

# 서비스 중지
stop_services() {
    echo "모든 백엔드 서비스를 중지합니다..."
    for service in "${BACKEND_SERVICES[@]}"; do
        echo "서비스 중지: $service"
        sudo systemctl stop "$service"
    done
}

# 서비스 재시작
restart_services() {
    echo "모든 백엔드 서비스를 재시작합니다..."
    for service in "${BACKEND_SERVICES[@]}"; do
        echo "서비스 재시작: $service"
        sudo systemctl restart "$service"
        sleep 3
    done
}

# 메인 실행
case "${1:-status}" in
    "status"|"st")
        show_status
        ;;
    "start")
        start_services
        ;;
    "stop")
        stop_services
        ;;
    "restart"|"rs")
        restart_services
        ;;
    "help"|"-h"|"--help")
        echo "사용법: $0 [명령]"
        echo "명령:"
        echo "  status    - 서비스 상태 확인 (기본값)"
        echo "  start     - 모든 서비스 시작"
        echo "  stop      - 모든 서비스 중지"
        echo "  restart   - 모든 서비스 재시작"
        echo "  help      - 도움말 표시"
        ;;
    *)
        echo "알 수 없는 명령: $1"
        echo "도움말을 보려면 '$0 help'를 실행하세요."
        exit 1
        ;;
esac