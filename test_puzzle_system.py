#!/usr/bin/env python3
"""
PuzzleCraft AI 시스템 통합 테스트 스크립트
원본 이미지 선택 문제 해결 및 전체 퍼즐 시스템 검증
"""

import asyncio
import aiohttp
import json
import os
import time
from pathlib import Path
import tempfile
import requests
from PIL import Image
import io
import logging
import traceback
from datetime import datetime

class PuzzleSystemTester:
    def __init__(self):
        self.base_url = "http://localhost:8000"  # API Gateway
        self.segmentation_url = "http://localhost:8006"  # Segmentation Service
        self.style_url = "http://localhost:8007"  # Style Transfer Service
        self.puzzle_url = "http://localhost:8002"  # Puzzle Generator

        self.test_results = {
            "original_image_selection": False,
            "style_transfer": False,
            "segmentation": False,
            "intelligent_puzzle_generation": False,
            "subject_background_separation": False,
            "api_integration": False,
            "frontend_compatibility": False
        }

        self.test_image_path = None

        # 로깅 설정
        self.setup_logging()

    def setup_logging(self):
        """로깅 설정"""
        # 로그 파일 설정
        log_filename = f"puzzle_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

        # 로거 설정
        self.logger = logging.getLogger('PuzzleSystemTester')
        self.logger.setLevel(logging.DEBUG)

        # 파일 핸들러
        file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)

        # 콘솔 핸들러
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # 포맷터
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # 핸들러 추가
        if not self.logger.handlers:
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

        print(f"📝 로그 파일: {log_filename}")

    def log_request_details(self, method, url, files=None, data=None, headers=None):
        """요청 상세 정보 로깅"""
        self.logger.info(f"🔄 API 요청: {method} {url}")

        if data:
            # 민감한 정보 제외하고 로깅
            safe_data = {k: v for k, v in data.items() if 'password' not in k.lower()}
            self.logger.debug(f"📤 요청 데이터: {safe_data}")

        if files:
            file_info = {}
            for key, file_obj in files.items():
                if hasattr(file_obj, 'name'):
                    file_info[key] = f"파일: {file_obj.name}"
                else:
                    file_info[key] = "파일 객체"
            self.logger.debug(f"📎 첨부 파일: {file_info}")

        if headers:
            # Authorization 헤더 등 민감한 정보 마스킹
            safe_headers = {}
            for k, v in headers.items():
                if 'auth' in k.lower() or 'token' in k.lower():
                    safe_headers[k] = "***MASKED***"
                else:
                    safe_headers[k] = v
            self.logger.debug(f"📋 요청 헤더: {safe_headers}")

    def log_response_details(self, response, test_name=""):
        """응답 상세 정보 로깅"""
        self.logger.info(f"📥 응답 상태: {response.status_code} ({test_name})")

        # 응답 헤더 로깅
        if hasattr(response, 'headers'):
            self.logger.debug(f"📋 응답 헤더: {dict(response.headers)}")

        # 응답 본문 로깅
        try:
            if response.headers.get('content-type', '').startswith('application/json'):
                response_data = response.json()
                self.logger.debug(f"📄 응답 본문 (JSON): {json.dumps(response_data, indent=2, ensure_ascii=False)}")
            else:
                # 텍스트 응답의 경우 일부만 로깅
                text_content = response.text[:1000]
                if len(response.text) > 1000:
                    text_content += "... (truncated)"
                self.logger.debug(f"📄 응답 본문 (Text): {text_content}")
        except Exception as e:
            self.logger.warning(f"⚠️ 응답 본문 파싱 실패: {str(e)}")

    def log_error_details(self, error, test_name="", context=None):
        """에러 상세 정보 로깅"""
        self.logger.error(f"❌ {test_name} 에러 발생: {str(error)}")

        if context:
            self.logger.error(f"🔍 에러 컨텍스트: {context}")

        # 스택 트레이스 로깅
        self.logger.error(f"📚 스택 트레이스:\n{traceback.format_exc()}")

    def log_network_diagnostics(self, url):
        """네트워크 진단 정보 로깅"""
        import urllib.parse
        parsed_url = urllib.parse.urlparse(url)

        self.logger.info(f"🌐 네트워크 진단 - 호스트: {parsed_url.hostname}:{parsed_url.port}")

        # 간단한 연결 테스트
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((parsed_url.hostname, parsed_url.port or 80))
            sock.close()

            if result == 0:
                self.logger.info(f"✅ 네트워크 연결 가능: {parsed_url.hostname}:{parsed_url.port}")
            else:
                self.logger.error(f"❌ 네트워크 연결 실패: {parsed_url.hostname}:{parsed_url.port} (에러 코드: {result})")
        except Exception as e:
            self.logger.error(f"❌ 네트워크 진단 실패: {str(e)}")

    def create_test_image(self):
        """테스트용 이미지 생성"""
        # 간단한 테스트 이미지 생성 (고양이와 배경)
        img = Image.new('RGB', (800, 600), color='lightblue')

        # 중앙에 원형 피사체 (고양이 대신 원)
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)

        # 배경 패턴
        for i in range(0, 800, 50):
            for j in range(0, 600, 50):
                draw.rectangle([i, j, i+25, j+25], fill='lightgreen')

        # 중앙 피사체
        center_x, center_y = 400, 300
        radius = 150
        draw.ellipse([center_x-radius, center_y-radius, 
                     center_x+radius, center_y+radius], 
                    fill='orange', outline='brown', width=5)

        # 임시 파일로 저장
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        img.save(temp_file.name, 'JPEG')
        self.test_image_path = temp_file.name

        print(f"✓ 테스트 이미지 생성: {self.test_image_path}")
        return temp_file.name

    async def test_service_health(self):
        """모든 서비스 헬스 체크"""
        print("\n=== 서비스 헬스 체크 ===")
        self.logger.info("🧪 서비스 헬스 체크 시작")

        services = [
            ("API Gateway", f"{self.base_url}/health"),
            ("Segmentation Service", f"{self.segmentation_url}/health"),
            ("Segmentation Advanced", f"{self.segmentation_url}/health-advanced"),
            ("Style Transfer", f"{self.style_url}/health"),
            ("Puzzle Generator", f"{self.puzzle_url}/health")
        ]

        async with aiohttp.ClientSession() as session:
            for service_name, url in services:
                try:
                    self.log_network_diagnostics(url)
                    self.logger.info(f"🔄 헬스 체크 요청: {service_name} -> {url}")

                    async with session.get(url, timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            print(f"✓ {service_name}: {data.get('status', 'OK')}")
                            self.logger.info(f"✅ {service_name} 헬스 체크 성공: {data}")
                        else:
                            print(f"✗ {service_name}: HTTP {response.status}")
                            self.logger.error(f"❌ {service_name} 헬스 체크 실패 - 상태 코드: {response.status}")

                            # 에러 응답 상세 분석
                            try:
                                error_text = await response.text()
                                self.logger.error(f"🔍 서버 에러 응답: {error_text[:500]}")
                            except:
                                self.logger.error(f"🔍 응답 본문 읽기 실패")

                except Exception as e:
                    print(f"✗ {service_name}: {str(e)}")
                    self.log_error_details(e, f"{service_name} 헬스 체크", {"url": url})

    async def test_original_image_selection(self):
        """원본 이미지 선택 기능 테스트"""
        print("\n=== 원본 이미지 선택 테스트 ===")
        self.logger.info("🧪 원본 이미지 선택 테스트 시작")

        try:
            # 1. 이미지 업로드 및 분석
            complexity_url = f"{self.segmentation_url}/analyze-image-complexity"
            self.log_network_diagnostics(complexity_url)

            with open(self.test_image_path, 'rb') as f:
                files = {'file': f}

                self.log_request_details("POST", complexity_url, files=files)

                # 복잡도 분석
                response = requests.post(
                    complexity_url,
                    files=files,
                    timeout=30
                )

                self.log_response_details(response, "복잡도 분석")

                if response.status_code == 200:
                    complexity_data = response.json()
                    print(f"✓ 이미지 복잡도 분석 완료: {complexity_data.get('complexity_level')}")
                    self.logger.info(f"✅ 복잡도 분석 성공: {complexity_data}")
                else:
                    print(f"✗ 복잡도 분석 실패: {response.status_code}")
                    self.logger.error(f"❌ 복잡도 분석 실패 - 상태 코드: {response.status_code}")

                    # 에러 응답 상세 분석
                    try:
                        error_data = response.json()
                        self.logger.error(f"🔍 서버 에러 응답: {error_data}")
                    except:
                        self.logger.error(f"🔍 서버 에러 응답 (텍스트): {response.text[:500]}")

                    return False

            # 2. 원본 이미지로 퍼즐 생성 (스타일 변환 없이)
            puzzle_url = f"{self.puzzle_url}/api/v1/puzzles/generate-intelligent"
            self.log_network_diagnostics(puzzle_url)

            with open(self.test_image_path, 'rb') as f:
                files = {'file': f}
                data = {
                    'piece_count': 20,
                    'style_type': 'original'  # 원본 이미지 사용
                }
                request_data = {'request': json.dumps(data)}

                self.log_request_details("POST", puzzle_url, files=files, data=request_data)

                response = requests.post(
                    puzzle_url,
                    files=files,
                    data=request_data,
                    timeout=60
                )

                self.log_response_details(response, "퍼즐 생성")

                if response.status_code == 200:
                    result = response.json()
                    print(f"✓ 원본 이미지로 퍼즐 생성 성공: {result.get('task_id')}")
                    self.logger.info(f"✅ 퍼즐 생성 성공: {result}")
                    self.test_results["original_image_selection"] = True
                    return True
                else:
                    print(f"✗ 원본 이미지 퍼즐 생성 실패: {response.status_code}")
                    self.logger.error(f"❌ 퍼즐 생성 실패 - 상태 코드: {response.status_code}")

                    # 에러 응답 상세 분석
                    try:
                        error_data = response.json()
                        self.logger.error(f"🔍 서버 에러 응답: {error_data}")
                    except:
                        self.logger.error(f"🔍 서버 에러 응답 (텍스트): {response.text[:500]}")

                    return False

        except Exception as e:
            print(f"✗ 원본 이미지 선택 테스트 실패: {str(e)}")
            self.log_error_details(e, "원본 이미지 선택 테스트", {
                "test_image_path": self.test_image_path,
                "segmentation_url": self.segmentation_url,
                "puzzle_url": self.puzzle_url
            })
            return False

    async def test_subject_background_separation(self):
        """피사체/배경 분리 테스트"""
        print("\n=== 피사체/배경 분리 테스트 ===")
        self.logger.info("🧪 피사체/배경 분리 테스트 시작")

        try:
            separation_url = f"{self.segmentation_url}/segment-subject-background"
            self.log_network_diagnostics(separation_url)

            with open(self.test_image_path, 'rb') as f:
                files = {'file': f}
                data = {'confidence_threshold': 0.7}

                self.log_request_details("POST", separation_url, files=files, data=data)

                response = requests.post(
                    separation_url,
                    files=files,
                    data=data,
                    timeout=30
                )

                self.log_response_details(response, "피사체/배경 분리")

                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        quality = result.get('separation_quality', {})
                        print(f"✓ 피사체/배경 분리 성공")
                        print(f"  - 품질 점수: {quality.get('quality_score', 0):.2f}")
                        print(f"  - 품질 등급: {quality.get('quality_grade', 'unknown')}")
                        print(f"  - 피사체 비율: {quality.get('subject_ratio', 0):.2f}")

                        self.logger.info(f"✅ 피사체/배경 분리 성공: {result}")
                        self.test_results["subject_background_separation"] = True
                        return True
                    else:
                        print(f"✗ 피사체/배경 분리 실패: {result.get('error')}")
                        self.logger.error(f"❌ 피사체/배경 분리 실패 - 서버 응답: {result}")
                        return False
                else:
                    print(f"✗ 피사체/배경 분리 API 실패: {response.status_code}")
                    self.logger.error(f"❌ 피사체/배경 분리 API 실패 - 상태 코드: {response.status_code}")

                    # 에러 응답 상세 분석
                    try:
                        error_data = response.json()
                        self.logger.error(f"🔍 서버 에러 응답: {error_data}")
                    except:
                        self.logger.error(f"🔍 서버 에러 응답 (텍스트): {response.text[:500]}")

                    return False

        except Exception as e:
            print(f"✗ 피사체/배경 분리 테스트 실패: {str(e)}")
            self.log_error_details(e, "피사체/배경 분리 테스트", {
                "test_image_path": self.test_image_path,
                "segmentation_url": self.segmentation_url,
                "confidence_threshold": 0.7
            })
            return False

    async def test_intelligent_puzzle_generation(self):
        """지능형 퍼즐 생성 테스트"""
        print("\n=== 지능형 퍼즐 생성 테스트 ===")
        self.logger.info("🧪 지능형 퍼즐 생성 테스트 시작")

        try:
            puzzle_gen_url = f"{self.segmentation_url}/generate-intelligent-puzzle"
            self.log_network_diagnostics(puzzle_gen_url)

            with open(self.test_image_path, 'rb') as f:
                files = {'file': f}
                data = {
                    'piece_count': 50,
                    'subject_background_ratio': 0.6
                }

                self.log_request_details("POST", puzzle_gen_url, files=files, data=data)

                response = requests.post(
                    puzzle_gen_url,
                    files=files,
                    data=data,
                    timeout=60
                )

                self.log_response_details(response, "지능형 퍼즐 생성")

                if response.status_code == 200:
                    result = response.json()
                    if result.get('puzzle_type') == 'intelligent_subject_background':
                        pieces = result.get('pieces', [])
                        distribution = result.get('piece_distribution', {})

                        print(f"✓ 지능형 퍼즐 생성 성공")
                        print(f"  - 총 피스 수: {len(pieces)}")
                        print(f"  - 피사체 피스: {distribution.get('subject_pieces', 0)}")
                        print(f"  - 배경 피스: {distribution.get('background_pieces', 0)}")

                        self.logger.info(f"✅ 지능형 퍼즐 생성 성공: {result}")
                        self.test_results["intelligent_puzzle_generation"] = True
                        return True
                    else:
                        print(f"✗ 지능형 퍼즐 생성 실패: {result.get('error')}")
                        self.logger.error(f"❌ 지능형 퍼즐 생성 실패 - 서버 응답: {result}")
                        return False
                else:
                    print(f"✗ 지능형 퍼즐 생성 API 실패: {response.status_code}")
                    self.logger.error(f"❌ 지능형 퍼즐 생성 API 실패 - 상태 코드: {response.status_code}")

                    # 에러 응답 상세 분석
                    try:
                        error_data = response.json()
                        self.logger.error(f"🔍 서버 에러 응답: {error_data}")
                    except:
                        self.logger.error(f"🔍 서버 에러 응답 (텍스트): {response.text[:500]}")

                    return False

        except Exception as e:
            print(f"✗ 지능형 퍼즐 생성 테스트 실패: {str(e)}")
            self.log_error_details(e, "지능형 퍼즐 생성 테스트", {
                "test_image_path": self.test_image_path,
                "segmentation_url": self.segmentation_url,
                "piece_count": 50,
                "subject_background_ratio": 0.6
            })
            return False

    async def test_style_transfer(self):
        """스타일 변환 테스트"""
        print("\n=== 스타일 변환 테스트 ===")

        try:
            # 1. 스타일 미리보기 테스트
            with open(self.test_image_path, 'rb') as f:
                files = {'file': f}
                data = {'style_type': 'watercolor'}

                response = requests.post(
                    f"{self.base_url}/api/v1/style/preview",
                    files=files,
                    data=data,
                    timeout=30
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        print(f"✓ 스타일 미리보기 성공: {result.get('preview_url')}")
                        self.test_results["style_transfer"] = True
                        return True
                    else:
                        print(f"✗ 스타일 미리보기 실패")
                        return False
                else:
                    print(f"✗ 스타일 미리보기 API 실패: {response.status_code}")
                    return False

        except Exception as e:
            print(f"✗ 스타일 변환 테스트 실패: {str(e)}")
            return False

    async def test_api_integration(self):
        """API 통합 테스트"""
        print("\n=== API 통합 테스트 ===")
        self.logger.info("🧪 API 통합 테스트 시작")

        try:
            # 전체 워크플로우 테스트
            with open(self.test_image_path, 'rb') as f:
                files = {'file': f}

                # 1. 이미지 분석
                analysis_url = f"{self.segmentation_url}/analyze-subject-background"
                self.log_network_diagnostics(analysis_url)
                self.log_request_details("POST", analysis_url, files=files)

                analysis_response = requests.post(
                    analysis_url,
                    files=files,
                    timeout=30
                )

                self.log_response_details(analysis_response, "이미지 분석")

                if analysis_response.status_code != 200:
                    print(f"✗ 이미지 분석 실패: {analysis_response.status_code}")
                    self.logger.error(f"❌ 이미지 분석 실패 - 상태 코드: {analysis_response.status_code}")

                    # 에러 응답 상세 분석
                    try:
                        error_data = analysis_response.json()
                        self.logger.error(f"🔍 서버 에러 응답: {error_data}")
                    except:
                        self.logger.error(f"🔍 서버 에러 응답 (텍스트): {analysis_response.text[:500]}")

                    return False

                analysis_data = analysis_response.json()
                print(f"✓ 이미지 분석 완료")
                self.logger.info(f"✅ 이미지 분석 성공: {analysis_data}")

                # 2. 퍼즐 생성 요청
                f.seek(0)  # 파일 포인터 리셋
                puzzle_data = {
                    'puzzle_type': 'intelligent_subject_background',
                    'piece_count': analysis_data.get('puzzle_recommendations', {}).get('recommended_piece_count', 30),
                    'difficulty': analysis_data.get('puzzle_recommendations', {}).get('difficulty', 'medium'),
                    'enable_ai_optimization': True
                }

                puzzle_url = f"{self.puzzle_url}/api/v1/puzzles/generate-intelligent"
                self.log_network_diagnostics(puzzle_url)

                puzzle_files = {'file': (f.name, f, 'image/jpeg')}
                puzzle_request_data = {'request': json.dumps(puzzle_data)}

                self.log_request_details("POST", puzzle_url, files=puzzle_files, data=puzzle_request_data)

                puzzle_response = requests.post(
                    puzzle_url,
                    files=puzzle_files,
                    data=puzzle_request_data,
                    timeout=120
                )

                self.log_response_details(puzzle_response, "통합 퍼즐 생성")

                if puzzle_response.status_code == 200:
                    puzzle_result = puzzle_response.json()
                    print(f"✓ 통합 퍼즐 생성 성공: {puzzle_result.get('task_id')}")
                    self.logger.info(f"✅ 통합 퍼즐 생성 성공: {puzzle_result}")
                    self.test_results["api_integration"] = True
                    return True
                else:
                    print(f"✗ 통합 퍼즐 생성 실패: {puzzle_response.status_code}")
                    self.logger.error(f"❌ 통합 퍼즐 생성 실패 - 상태 코드: {puzzle_response.status_code}")

                    # 에러 응답 상세 분석
                    try:
                        error_data = puzzle_response.json()
                        self.logger.error(f"🔍 서버 에러 응답: {error_data}")
                    except:
                        self.logger.error(f"🔍 서버 에러 응답 (텍스트): {puzzle_response.text[:500]}")

                    return False

        except Exception as e:
            print(f"✗ API 통합 테스트 실패: {str(e)}")
            self.log_error_details(e, "API 통합 테스트", {
                "test_image_path": self.test_image_path,
                "segmentation_url": self.segmentation_url,
                "puzzle_url": self.puzzle_url
            })
            return False

    def test_frontend_compatibility(self):
        """프론트엔드 호환성 테스트"""
        print("\n=== 프론트엔드 호환성 테스트 ===")

        try:
            # 프론트엔드 컴포넌트 파일 존재 확인
            frontend_files = [
                "frontend/web/src/pages/PuzzleCreate.tsx",
                "frontend/web/src/pages/PuzzlePlay.tsx",
                "frontend/web/src/components/PuzzleCreator/StyleSelector.tsx",
                "frontend/web/src/components/PuzzleGame/PuzzleGameBoard.tsx",
                "frontend/web/src/hooks/usePuzzleGame.ts",
                "frontend/web/src/hooks/useStyleTransfer.ts"
            ]

            missing_files = []
            for file_path in frontend_files:
                full_path = Path(file_path)
                if not full_path.exists():
                    missing_files.append(file_path)
                else:
                    print(f"✓ {file_path}")

            if missing_files:
                print(f"✗ 누락된 파일들: {missing_files}")
                return False
            else:
                print("✓ 모든 프론트엔드 컴포넌트 파일 존재")
                self.test_results["frontend_compatibility"] = True
                return True

        except Exception as e:
            print(f"✗ 프론트엔드 호환성 테스트 실패: {str(e)}")
            return False

    def generate_test_report(self):
        """테스트 결과 리포트 생성"""
        print("\n" + "="*60)
        print("🧩 PUZZLECRAFT AI 시스템 테스트 결과")
        print("="*60)

        total_tests = len(self.test_results)
        passed_tests = sum(self.test_results.values())

        print(f"\n📊 전체 테스트: {total_tests}")
        print(f"✅ 통과: {passed_tests}")
        print(f"❌ 실패: {total_tests - passed_tests}")
        print(f"📈 성공률: {(passed_tests/total_tests)*100:.1f}%")

        print(f"\n📋 상세 결과:")
        test_names = {
            "original_image_selection": "원본 이미지 선택 기능",
            "style_transfer": "스타일 변환 기능",
            "segmentation": "이미지 분할 기능",
            "intelligent_puzzle_generation": "지능형 퍼즐 생성",
            "subject_background_separation": "피사체/배경 분리",
            "api_integration": "API 통합",
            "frontend_compatibility": "프론트엔드 호환성"
        }

        for key, name in test_names.items():
            status = "✅ PASS" if self.test_results[key] else "❌ FAIL"
            print(f"  {name}: {status}")

        # 권장사항
        print(f"\n💡 권장사항:")
        if not self.test_results["original_image_selection"]:
            print("  - 원본 이미지 선택 로직을 다시 확인하세요")
            print("  - PuzzleCreate.tsx와 StyleSelector.tsx 수정사항을 적용하세요")

        if not self.test_results["subject_background_separation"]:
            print("  - segmentation 서비스의 고급 기능을 확인하세요")
            print("  - 테스트 이미지의 피사체가 명확한지 확인하세요")

        if not self.test_results["api_integration"]:
            print("  - 모든 마이크로서비스가 실행 중인지 확인하세요")
            print("  - 네트워크 연결 및 포트 설정을 확인하세요")

        if passed_tests == total_tests:
            print(f"\n🎉 축하합니다! 모든 테스트가 통과했습니다!")
            print(f"   PuzzleCraft AI 시스템이 완전히 구현되었습니다.")
        else:
            print(f"\n⚠️  일부 테스트가 실패했습니다. 위의 권장사항을 확인하세요.")

    async def run_all_tests(self):
        """모든 테스트 실행"""
        print("🧩 PuzzleCraft AI 시스템 통합 테스트 시작")
        print("="*60)

        # 테스트 이미지 생성
        self.create_test_image()

        # 서비스 헬스 체크
        await self.test_service_health()

        # 개별 기능 테스트
        await self.test_original_image_selection()
        await self.test_subject_background_separation()
        await self.test_intelligent_puzzle_generation()
        await self.test_style_transfer()
        await self.test_api_integration()
        self.test_frontend_compatibility()

        # 결과 리포트
        self.generate_test_report()

        # 정리
        if self.test_image_path and os.path.exists(self.test_image_path):
            os.unlink(self.test_image_path)
            print(f"\n🧹 테스트 이미지 정리 완료")

async def main():
    """메인 함수"""
    tester = PuzzleSystemTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    print("PuzzleCraft AI 시스템 테스트 스크립트")
    print("사용법: python test_puzzle_system.py")
    print("주의: 모든 마이크로서비스가 실행 중이어야 합니다.\n")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n테스트가 중단되었습니다.")
    except Exception as e:
        print(f"\n테스트 실행 중 오류 발생: {str(e)}")
