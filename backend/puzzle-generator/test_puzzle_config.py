"""
PuzzleConfig 생성 테스트 스크립트
예기치 않은 인수 경고 해결 확인
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from puzzle_engine import PuzzleConfig, PuzzleType, DifficultyLevel
from piece_generator import PieceShape

def test_puzzle_config_creation():
    """PuzzleConfig 생성 테스트"""
    print("PuzzleConfig 생성 테스트 시작...")
    
    try:
        # 첫 번째 케이스: main.py의 첫 번째 PuzzleConfig 생성 패턴
        print("\n1. 지능형 퍼즐 생성용 PuzzleConfig 테스트")
        config1 = PuzzleConfig(
            puzzle_type=PuzzleType.CLASSIC,
            difficulty=DifficultyLevel.MEDIUM,
            piece_count=50,
            use_ai_enhancement=True,
            style_type="watercolor"
        )
        print(f"✓ 성공: {config1}")
        
        # 두 번째 케이스: main.py의 두 번째 PuzzleConfig 생성 패턴
        print("\n2. 미리보기용 PuzzleConfig 테스트")
        config2 = PuzzleConfig(
            puzzle_type=PuzzleType.CLASSIC,
            difficulty=DifficultyLevel.MEDIUM,
            piece_count=20,
            use_ai_enhancement=False
        )
        print(f"✓ 성공: {config2}")
        
        # 기본값 테스트
        print("\n3. 기본값 PuzzleConfig 테스트")
        config3 = PuzzleConfig()
        print(f"✓ 성공: {config3}")
        
        print("\n모든 테스트 통과! PuzzleConfig 생성 문제가 해결되었습니다.")
        return True
        
    except Exception as e:
        print(f"✗ 실패: {str(e)}")
        return False

if __name__ == "__main__":
    test_puzzle_config_creation()