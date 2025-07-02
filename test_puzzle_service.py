import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'puzzle-generator'))

async def test_puzzle_service():
    """Test if puzzle-generator service can start properly"""
    try:
        # Import the required modules
        from puzzle_engine import IntelligentPuzzleEngine
        from ai_integration import AIServiceIntegrator
        from piece_generator import AdvancedPieceGenerator
        from difficulty_analyzer import IntelligentDifficultyAnalyzer
        
        print("✓ All modules imported successfully")
        
        # Try to initialize the services
        puzzle_engine = IntelligentPuzzleEngine()
        ai_integrator = AIServiceIntegrator()
        piece_generator = AdvancedPieceGenerator()
        difficulty_analyzer = IntelligentDifficultyAnalyzer()
        
        print("✓ All services initialized successfully")
        
        # Test if we can start the FastAPI app
        import uvicorn
        print("✓ uvicorn available")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_puzzle_service())
    if result:
        print("\n🎉 Puzzle service is ready to run!")
    else:
        print("\n❌ Puzzle service has issues that need to be resolved.")