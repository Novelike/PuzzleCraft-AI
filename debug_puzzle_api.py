import requests
import json

def test_puzzle_api():
    """퍼즐 API 응답 구조 디버깅"""
    
    # 이슈에서 제공된 퍼즐 ID
    puzzle_id = "6b1e248c-dafa-4e79-931b-efc3914edafe"
    
    # API 게이트웨이 URL (로컬 환경 기준)
    api_url = f"http://localhost:8000/api/v1/puzzles/{puzzle_id}"
    
    print(f"🔍 퍼즐 API 테스트 시작: {puzzle_id}")
    print(f"📡 요청 URL: {api_url}")
    
    try:
        response = requests.get(api_url, timeout=30)
        print(f"📊 응답 상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 응답 성공!")
            print(f"🔍 응답 데이터 타입: {type(data)}")
            print(f"🔍 최상위 키들: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            
            # pieces 배열 확인
            if "pieces" in data:
                pieces = data["pieces"]
                print(f"🧩 pieces 배열 길이: {len(pieces)}")
                print(f"🧩 pieces 타입: {type(pieces)}")
                
                if len(pieces) > 0:
                    first_piece = pieces[0]
                    print(f"🔍 첫 번째 피스 키들: {list(first_piece.keys()) if isinstance(first_piece, dict) else 'Not a dict'}")
                    
                    # 이미지 데이터 확인
                    if "imageData" in first_piece:
                        image_data = first_piece["imageData"]
                        print(f"🖼️ 이미지 데이터 존재: {bool(image_data)}")
                        if image_data:
                            print(f"🖼️ 이미지 데이터 샘플: {image_data[:100]}...")
                    else:
                        print("❌ 첫 번째 피스에 imageData가 없습니다")
                else:
                    print("❌ pieces 배열이 비어있습니다")
            else:
                print("❌ 응답에 pieces 키가 없습니다")
                
            # 기타 중요 필드들 확인
            print(f"🔍 imageUrl: {data.get('imageUrl', 'None')}")
            print(f"🔍 difficulty: {data.get('difficulty', 'None')}")
            print(f"🔍 estimatedSolveTime: {data.get('estimatedSolveTime', 'None')}")
            
            # 전체 응답을 파일로 저장
            with open("puzzle_api_response.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print("💾 전체 응답을 puzzle_api_response.json에 저장했습니다")
            
        else:
            print(f"❌ 응답 실패: {response.status_code}")
            print(f"❌ 응답 내용: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 요청 실패: {e}")
    except Exception as e:
        print(f"❌ 예외 발생: {e}")

if __name__ == "__main__":
    test_puzzle_api()