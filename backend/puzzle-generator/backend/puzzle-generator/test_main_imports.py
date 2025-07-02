"""
main.py 임포트 및 PuzzleConfig 사용 테스트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_main_imports():
    """main.py의 임포트와 PuzzleConfig 사용 테스트"""
    print("main.py 임포트 테스트 시작...")
    
    try:
        # main.py에서 사용하는 임포트들 테스트
        from puzzle_engine import IntelligentPuzzleEngine, PuzzleConfig, PuzzleType, DifficultyLevel
        from piece_generator import PieceShape
        print("✓ 모든 임포트 성공")
        
        # main.py에서 사용하는 PuzzleConfig 생성 패턴 테스트
        print("\nmain.py 스타일 PuzzleConfig 생성 테스트...")
        
        # 첫 번째 패턴 (지능형 퍼즐 생성)
        puzzle_config = PuzzleConfig(
            puzzle_type=PuzzleType("CLASSIC"),
            difficulty=DifficultyLevel("MEDIUM"),
            piece_count=50,
            use_ai_enhancement=True,
            style_type="watercolor"
        )
        print(f"✓ 지능형 퍼즐 설정 생성 성공: {puzzle_config.puzzle_type}, {puzzle_config.difficulty}")
        
        # 두 번째 패턴 (미리보기)
        config = PuzzleConfig(
            puzzle_type=PuzzleType.CLASSIC,
            difficulty=DifficultyLevel.MEDIUM,
            piece_count=20,
            use_ai_enhancement=False
        )
        print(f"✓ 미리보기 설정 생성 성공: {config.puzzle_type}, {config.difficulty}")
        
        print("\n모든 테스트 통과! main.py의 PuzzleConfig 사용이 정상적으로 작동합니다.")
        return True
        
    except Exception as e:
        print(f"✗ 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_main_imports()