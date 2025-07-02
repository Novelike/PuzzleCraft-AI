#!/usr/bin/env python3
"""
PuzzleCraft AI 서비스 시작 스크립트
모든 마이크로서비스를 백그라운드에서 실행합니다.
"""

import subprocess
import time
import os
import sys
from pathlib import Path

def start_service(service_name, port, directory):
    """개별 서비스 시작"""
    print(f"🚀 {service_name} 시작 중... (포트 {port})")
    
    service_path = Path("backend") / directory
    if not service_path.exists():
        print(f"❌ {service_name} 디렉토리를 찾을 수 없습니다: {service_path}")
        return None
    
    try:
        # Windows에서 백그라운드 실행
        if sys.platform == "win32":
            process = subprocess.Popen(
                [sys.executable, "main.py"],
                cwd=service_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:
            process = subprocess.Popen(
                [sys.executable, "main.py"],
                cwd=service_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        
        print(f"✅ {service_name} 시작됨 (PID: {process.pid})")
        return process
    
    except Exception as e:
        print(f"❌ {service_name} 시작 실패: {str(e)}")
        return None

def check_service_health(service_name, port):
    """서비스 헬스 체크"""
    import requests
    try:
        response = requests.get(f"http://localhost:{port}/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ {service_name} 정상 작동 중")
            return True
        else:
            print(f"⚠️ {service_name} 응답 오류: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ {service_name} 연결 실패: {str(e)}")
        return False

def main():
    """메인 함수"""
    print("🧩 PuzzleCraft AI 서비스 시작")
    print("=" * 50)
    
    # 시작할 서비스들 정의
    services = [
        ("Segmentation Service", 8006, "segmentation-service"),
        ("API Gateway", 8000, "api-gateway"),
        ("Style Transfer", 8007, "style-transfer"),
        ("Puzzle Generator", 8002, "puzzle-generator"),
    ]
    
    processes = []
    
    # 각 서비스 시작
    for service_name, port, directory in services:
        process = start_service(service_name, port, directory)
        if process:
            processes.append((service_name, port, process))
        time.sleep(2)  # 서비스 간 시작 간격
    
    # 서비스 시작 대기
    print("\n⏳ 서비스 초기화 대기 중...")
    time.sleep(10)
    
    # 헬스 체크
    print("\n🔍 서비스 상태 확인")
    print("-" * 30)
    
    healthy_services = 0
    for service_name, port, process in processes:
        if check_service_health(service_name, port):
            healthy_services += 1
    
    print(f"\n📊 실행 중인 서비스: {healthy_services}/{len(processes)}")
    
    if healthy_services == len(processes):
        print("🎉 모든 서비스가 정상적으로 실행되었습니다!")
        print("\n테스트를 실행하려면:")
        print("python test_puzzle_system.py")
    else:
        print("⚠️ 일부 서비스가 실행되지 않았습니다.")
        print("각 서비스의 로그를 확인하세요.")
    
    print("\n서비스를 중지하려면 Ctrl+C를 누르세요.")
    
    try:
        # 프로세스들이 실행 상태를 유지하도록 대기
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 서비스 중지 중...")
        for service_name, port, process in processes:
            try:
                process.terminate()
                print(f"✅ {service_name} 중지됨")
            except:
                pass

if __name__ == "__main__":
    main()