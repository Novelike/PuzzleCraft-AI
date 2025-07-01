#!/usr/bin/env python3
"""
PuzzleCraft AI - Phase 2 Services Test Script
테스트 스크립트: AI 서비스들의 기본 동작을 확인합니다.
"""

import requests
import time
import sys
from pathlib import Path

# 서비스 URL 설정
SERVICES = {
    'OCR': 'http://localhost:8001',
    'Segmentation': 'http://localhost:8002', 
    'Style Transfer': 'http://localhost:8003'
}

def test_service_health(service_name, base_url):
    """서비스 상태 확인"""
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {service_name} 서비스: 정상 동작")
            print(f"   - 상태: {data.get('status', 'unknown')}")
            print(f"   - 버전: {data.get('version', 'unknown')}")
            if 'model_loaded' in data:
                print(f"   - 모델 로드: {'성공' if data['model_loaded'] else '실패'}")
            return True
        else:
            print(f"❌ {service_name} 서비스: HTTP {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ {service_name} 서비스: 연결 실패 (서비스가 실행되지 않음)")
        return False
    except requests.exceptions.Timeout:
        print(f"❌ {service_name} 서비스: 응답 시간 초과")
        return False
    except Exception as e:
        print(f"❌ {service_name} 서비스: 오류 - {str(e)}")
        return False

def test_ocr_endpoints():
    """OCR 서비스 엔드포인트 테스트"""
    base_url = SERVICES['OCR']
    print("\n🔍 OCR 서비스 엔드포인트 테스트:")
    
    endpoints = [
        '/supported-languages',
        '/health'
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code == 200:
                print(f"   ✅ {endpoint}: 정상")
            else:
                print(f"   ❌ {endpoint}: HTTP {response.status_code}")
        except Exception as e:
            print(f"   ❌ {endpoint}: 오류 - {str(e)}")

def test_segmentation_endpoints():
    """세그멘테이션 서비스 엔드포인트 테스트"""
    base_url = SERVICES['Segmentation']
    print("\n🎯 세그멘테이션 서비스 엔드포인트 테스트:")
    
    endpoints = [
        '/supported-classes',
        '/model-info',
        '/health'
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            if response.status_code == 200:
                print(f"   ✅ {endpoint}: 정상")
                if endpoint == '/supported-classes':
                    data = response.json()
                    print(f"      - 지원 클래스 수: {data.get('total_classes', 'unknown')}")
            else:
                print(f"   ❌ {endpoint}: HTTP {response.status_code}")
        except Exception as e:
            print(f"   ❌ {endpoint}: 오류 - {str(e)}")

def test_style_transfer_endpoints():
    """스타일 변환 서비스 엔드포인트 테스트"""
    base_url = SERVICES['Style Transfer']
    print("\n🎨 스타일 변환 서비스 엔드포인트 테스트:")
    
    endpoints = [
        '/available-styles',
        '/model-info',
        '/list-outputs',
        '/health'
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            if response.status_code == 200:
                print(f"   ✅ {endpoint}: 정상")
                if endpoint == '/available-styles':
                    data = response.json()
                    print(f"      - 사용 가능한 스타일 수: {data.get('total_styles', 'unknown')}")
                    styles = data.get('style_names', [])
                    if styles:
                        print(f"      - 스타일 목록: {', '.join(styles[:3])}{'...' if len(styles) > 3 else ''}")
            else:
                print(f"   ❌ {endpoint}: HTTP {response.status_code}")
        except Exception as e:
            print(f"   ❌ {endpoint}: 오류 - {str(e)}")

def print_service_info():
    """서비스 정보 출력"""
    print("=" * 60)
    print("🚀 PuzzleCraft AI - Phase 2 서비스 테스트")
    print("=" * 60)
    print("\n📋 구현된 AI 서비스들:")
    print("1. OCR 서비스 (포트 8001)")
    print("   - Pytesseract & EasyOCR 기반 텍스트 추출")
    print("   - 이미지 전처리 및 텍스트 퍼즐 생성")
    print("   - 한국어/영어 지원")
    
    print("\n2. 이미지 세그멘테이션 서비스 (포트 8002)")
    print("   - Mask R-CNN 기반 객체 분할")
    print("   - 세그멘테이션 기반 퍼즐 조각 생성")
    print("   - 이미지 복잡도 분석")
    
    print("\n3. 스타일 변환 서비스 (포트 8003)")
    print("   - 6가지 예술적 스타일 변환")
    print("   - 배치 스타일 적용")
    print("   - 미리보기 기능")
    
    print("\n" + "=" * 60)

def print_startup_instructions():
    """서비스 시작 방법 안내"""
    print("\n📝 서비스 시작 방법:")
    print("\n1. OCR 서비스 시작:")
    print("   cd backend\\ocr-service")
    print("   pip install -r requirements.txt")
    print("   python main.py")
    
    print("\n2. 세그멘테이션 서비스 시작:")
    print("   cd backend\\segmentation-service")
    print("   pip install -r requirements.txt")
    print("   python main.py")
    
    print("\n3. 스타일 변환 서비스 시작:")
    print("   cd backend\\style-transfer")
    print("   pip install -r requirements.txt")
    print("   python main.py")
    
    print("\n💡 팁: 각 서비스를 별도의 터미널에서 실행하세요.")

def main():
    """메인 테스트 함수"""
    print_service_info()
    
    print("\n🔍 서비스 상태 확인 중...")
    print("-" * 40)
    
    # 각 서비스 상태 확인
    results = {}
    for service_name, base_url in SERVICES.items():
        results[service_name] = test_service_health(service_name, base_url)
        time.sleep(1)  # 서비스 간 요청 간격
    
    # 실행 중인 서비스에 대해 상세 테스트
    if results.get('OCR'):
        test_ocr_endpoints()
    
    if results.get('Segmentation'):
        test_segmentation_endpoints()
    
    if results.get('Style Transfer'):
        test_style_transfer_endpoints()
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("📊 테스트 결과 요약:")
    print("-" * 40)
    
    running_services = sum(results.values())
    total_services = len(results)
    
    print(f"실행 중인 서비스: {running_services}/{total_services}")
    
    for service_name, is_running in results.items():
        status = "🟢 실행 중" if is_running else "🔴 중지됨"
        print(f"  {service_name}: {status}")
    
    if running_services == 0:
        print("\n⚠️  실행 중인 서비스가 없습니다.")
        print_startup_instructions()
    elif running_services < total_services:
        print(f"\n⚠️  {total_services - running_services}개 서비스가 실행되지 않았습니다.")
        print("실행되지 않은 서비스를 시작해주세요.")
    else:
        print("\n🎉 모든 AI 서비스가 정상적으로 실행 중입니다!")
        print("\n📖 자세한 사용법은 'Phase2_AI서비스구현가이드.md' 파일을 참조하세요.")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n테스트가 중단되었습니다.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {str(e)}")
        sys.exit(1)