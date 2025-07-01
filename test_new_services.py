#!/usr/bin/env python3
"""
PuzzleCraft AI - 새로운 서비스 테스트 스크립트
Auth Service와 Game Manager 서비스의 기본 기능을 테스트합니다.
"""

import asyncio
import httpx
import json
from datetime import datetime

# 서비스 URL 설정
AUTH_SERVICE_URL = "http://localhost:8001"
GAME_MANAGER_URL = "http://localhost:8002"
API_GATEWAY_URL = "http://localhost:8000"

class ServiceTester:
    def __init__(self):
        self.access_token = None
        self.test_user = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpassword123"
        }
    
    async def test_auth_service_direct(self):
        """Auth Service 직접 테스트"""
        print("=== Auth Service 직접 테스트 ===")
        
        async with httpx.AsyncClient() as client:
            try:
                # 1. 회원가입 테스트
                print("1. 회원가입 테스트...")
                response = await client.post(
                    f"{AUTH_SERVICE_URL}/register",
                    json=self.test_user,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    self.access_token = result["access_token"]
                    print(f"✅ 회원가입 성공: {result['token_type']} 토큰 발급")
                else:
                    print(f"❌ 회원가입 실패: {response.status_code} - {response.text}")
                    return False
                
                # 2. 로그인 테스트
                print("2. 로그인 테스트...")
                login_data = {
                    "username": self.test_user["username"],
                    "password": self.test_user["password"]
                }
                response = await client.post(
                    f"{AUTH_SERVICE_URL}/login",
                    json=login_data,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    self.access_token = result["access_token"]
                    print(f"✅ 로그인 성공: 새 토큰 발급")
                else:
                    print(f"❌ 로그인 실패: {response.status_code} - {response.text}")
                    return False
                
                # 3. 사용자 정보 조회 테스트
                print("3. 사용자 정보 조회 테스트...")
                response = await client.get(
                    f"{AUTH_SERVICE_URL}/me",
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    user_info = response.json()
                    print(f"✅ 사용자 정보 조회 성공: {user_info['username']} ({user_info['email']})")
                else:
                    print(f"❌ 사용자 정보 조회 실패: {response.status_code} - {response.text}")
                    return False
                
                return True
                
            except Exception as e:
                print(f"❌ Auth Service 테스트 중 오류: {e}")
                return False
    
    async def test_game_manager_direct(self):
        """Game Manager 직접 테스트"""
        print("\n=== Game Manager 직접 테스트 ===")
        
        if not self.access_token:
            print("❌ 인증 토큰이 없습니다. Auth Service 테스트를 먼저 실행하세요.")
            return False
        
        async with httpx.AsyncClient() as client:
            try:
                headers = {"Authorization": f"Bearer {self.access_token}"}
                
                # 1. 게임 세션 생성 테스트
                print("1. 게임 세션 생성 테스트...")
                session_data = {
                    "puzzle_id": "test_puzzle_001",
                    "game_mode": "single"
                }
                response = await client.post(
                    f"{GAME_MANAGER_URL}/sessions",
                    json=session_data,
                    headers=headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    session = response.json()
                    session_id = session["id"]
                    print(f"✅ 게임 세션 생성 성공: {session_id}")
                else:
                    print(f"❌ 게임 세션 생성 실패: {response.status_code} - {response.text}")
                    return False
                
                # 2. 게임 세션 조회 테스트
                print("2. 게임 세션 조회 테스트...")
                response = await client.get(
                    f"{GAME_MANAGER_URL}/sessions/{session_id}",
                    headers=headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    session = response.json()
                    print(f"✅ 게임 세션 조회 성공: {session['status']} 상태")
                else:
                    print(f"❌ 게임 세션 조회 실패: {response.status_code} - {response.text}")
                    return False
                
                # 3. 퍼즐 조각 이동 테스트
                print("3. 퍼즐 조각 이동 테스트...")
                move_data = {
                    "piece_id": "piece_1",
                    "x": 100.0,
                    "y": 100.0,
                    "rotation": 0.0
                }
                response = await client.post(
                    f"{GAME_MANAGER_URL}/sessions/{session_id}/moves",
                    json=move_data,
                    headers=headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    move = response.json()
                    print(f"✅ 퍼즐 조각 이동 성공: {'정확' if move['is_correct'] else '부정확'}")
                else:
                    print(f"❌ 퍼즐 조각 이동 실패: {response.status_code} - {response.text}")
                    return False
                
                # 4. 리더보드 조회 테스트
                print("4. 리더보드 조회 테스트...")
                response = await client.get(
                    f"{GAME_MANAGER_URL}/leaderboard",
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    leaderboard = response.json()
                    print(f"✅ 리더보드 조회 성공: {len(leaderboard)}개 항목")
                else:
                    print(f"❌ 리더보드 조회 실패: {response.status_code} - {response.text}")
                    return False
                
                return True
                
            except Exception as e:
                print(f"❌ Game Manager 테스트 중 오류: {e}")
                return False
    
    async def test_api_gateway_integration(self):
        """API Gateway 통합 테스트"""
        print("\n=== API Gateway 통합 테스트 ===")
        
        async with httpx.AsyncClient() as client:
            try:
                # 1. API Gateway를 통한 로그인 테스트
                print("1. API Gateway를 통한 로그인 테스트...")
                login_data = {
                    "username": self.test_user["username"],
                    "password": self.test_user["password"]
                }
                response = await client.post(
                    f"{API_GATEWAY_URL}/api/v1/auth/login",
                    json=login_data,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    gateway_token = result["access_token"]
                    print(f"✅ API Gateway 로그인 성공")
                else:
                    print(f"❌ API Gateway 로그인 실패: {response.status_code} - {response.text}")
                    return False
                
                # 2. API Gateway를 통한 게임 세션 생성 테스트
                print("2. API Gateway를 통한 게임 세션 생성 테스트...")
                session_data = {
                    "puzzle_id": "gateway_test_puzzle",
                    "game_mode": "challenge"
                }
                response = await client.post(
                    f"{API_GATEWAY_URL}/api/v1/games/sessions",
                    json=session_data,
                    headers={"Authorization": f"Bearer {gateway_token}"},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    session = response.json()
                    print(f"✅ API Gateway 게임 세션 생성 성공: {session['id']}")
                else:
                    print(f"❌ API Gateway 게임 세션 생성 실패: {response.status_code} - {response.text}")
                    return False
                
                return True
                
            except Exception as e:
                print(f"❌ API Gateway 통합 테스트 중 오류: {e}")
                return False
    
    async def test_service_health(self):
        """서비스 헬스체크"""
        print("\n=== 서비스 헬스체크 ===")
        
        services = [
            ("Auth Service", f"{AUTH_SERVICE_URL}/health"),
            ("Game Manager", f"{GAME_MANAGER_URL}/health"),
            ("API Gateway", f"{API_GATEWAY_URL}/health")
        ]
        
        async with httpx.AsyncClient() as client:
            for service_name, health_url in services:
                try:
                    response = await client.get(health_url, timeout=5.0)
                    if response.status_code == 200:
                        health_data = response.json()
                        print(f"✅ {service_name}: {health_data.get('status', 'OK')}")
                    else:
                        print(f"❌ {service_name}: HTTP {response.status_code}")
                except Exception as e:
                    print(f"❌ {service_name}: 연결 실패 - {e}")
    
    async def run_all_tests(self):
        """모든 테스트 실행"""
        print("PuzzleCraft AI - 새로운 서비스 테스트 시작")
        print("=" * 50)
        
        # 헬스체크 먼저 실행
        await self.test_service_health()
        
        # Auth Service 테스트
        auth_success = await self.test_auth_service_direct()
        
        if auth_success:
            # Game Manager 테스트
            game_success = await self.test_game_manager_direct()
            
            # API Gateway 통합 테스트
            gateway_success = await self.test_api_gateway_integration()
            
            print("\n" + "=" * 50)
            print("테스트 결과 요약:")
            print(f"Auth Service: {'✅ 성공' if auth_success else '❌ 실패'}")
            print(f"Game Manager: {'✅ 성공' if game_success else '❌ 실패'}")
            print(f"API Gateway 통합: {'✅ 성공' if gateway_success else '❌ 실패'}")
            
            if auth_success and game_success and gateway_success:
                print("\n🎉 모든 테스트가 성공적으로 완료되었습니다!")
                print("Auth Service와 Game Manager가 정상적으로 구현되어 배포 준비가 완료되었습니다.")
            else:
                print("\n⚠️  일부 테스트가 실패했습니다. 서비스 상태를 확인해주세요.")
        else:
            print("\n❌ Auth Service 테스트 실패로 인해 다른 테스트를 건너뜁니다.")

async def main():
    """메인 함수"""
    tester = ServiceTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    print("사용법:")
    print("1. 먼저 서비스들을 시작하세요:")
    print("   docker-compose up -d")
    print("   또는")
    print("   ./scripts/manage-services.sh start")
    print("")
    print("2. 그 다음 이 테스트 스크립트를 실행하세요:")
    print("   python test_new_services.py")
    print("")
    
    # 사용자 확인
    try:
        input("서비스가 실행 중이면 Enter를 눌러 테스트를 시작하세요...")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n테스트가 중단되었습니다.")