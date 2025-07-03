import sys
import os
import json
from pathlib import Path

# Add the backend path to sys.path
backend_path = Path(__file__).parent / "backend" / "segmentation-service"
sys.path.insert(0, str(backend_path))

try:
    from segmentation import ImageSegmentation
except ImportError as e:
    print(f"Error importing segmentation module: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)

def test_edge_assignment():
    """Test the edge assignment logic with a sample image"""
    
    # Initialize the segmentation engine
    segmenter = ImageSegmentation()
    
    # Use the test image
    test_image_path = "test_image.png"
    
    if not os.path.exists(test_image_path):
        print(f"Test image not found: {test_image_path}")
        print("Please make sure test_image.png exists in the project root")
        return False
    
    print("Testing edge assignment logic...")
    print("=" * 60)
    
    try:
        # Generate puzzle pieces
        result = segmenter.generate_intelligent_puzzle_pieces(
            image_path=test_image_path,
            piece_count=20,
            subject_background_ratio=0.6
        )
        
        if result.get('puzzle_type') == 'error':
            print(f"❌ Puzzle generation failed: {result.get('error')}")
            return False
        
        pieces = result.get('pieces', [])
        print(f"✅ Generated {len(pieces)} puzzle pieces")
        
        # Check edge compatibility
        incompatible_pairs = []
        tolerance = 5
        
        for i, piece_a in enumerate(pieces):
            for j, piece_b in enumerate(pieces):
                if i >= j:
                    continue
                
                # Get bbox coordinates
                if 'bbox' not in piece_a or 'bbox' not in piece_b:
                    continue
                    
                a_x1, a_y1, a_x2, a_y2 = piece_a['bbox']
                b_x1, b_y1, b_x2, b_y2 = piece_b['bbox']
                
                # Check horizontal adjacency
                if (abs(a_x2 - b_x1) < tolerance and 
                    abs(a_y1 - b_y1) < tolerance and 
                    abs(a_y2 - b_y2) < tolerance):
                    
                    a_right = piece_a['edges']['right']
                    b_left = piece_b['edges']['left']
                    
                    if not are_edges_compatible(a_right, b_left):
                        incompatible_pairs.append({
                            'piece_a': piece_a['id'],
                            'piece_b': piece_b['id'],
                            'position': 'horizontal',
                            'a_edge': f"right={a_right}",
                            'b_edge': f"left={b_left}"
                        })
                
                # Check vertical adjacency
                elif (abs(a_y2 - b_y1) < tolerance and 
                      abs(a_x1 - b_x1) < tolerance and 
                      abs(a_x2 - b_x2) < tolerance):
                    
                    a_bottom = piece_a['edges']['bottom']
                    b_top = piece_b['edges']['top']
                    
                    if not are_edges_compatible(a_bottom, b_top):
                        incompatible_pairs.append({
                            'piece_a': piece_a['id'],
                            'piece_b': piece_b['id'],
                            'position': 'vertical',
                            'a_edge': f"bottom={a_bottom}",
                            'b_edge': f"top={b_top}"
                        })
        
        # Report results
        if incompatible_pairs:
            print(f"❌ Found {len(incompatible_pairs)} incompatible edge pairs:")
            for pair in incompatible_pairs:
                print(f"   {pair['piece_a']} ↔ {pair['piece_b']} ({pair['position']})")
                print(f"   {pair['a_edge']} | {pair['b_edge']}")
            return False
        else:
            print("✅ All adjacent pieces have compatible edges!")
            
            # Show some examples
            print("\nEdge assignment examples:")
            for i, piece in enumerate(pieces[:5]):  # Show first 5 pieces
                print(f"  {piece['id']}: {piece['edges']}")
            
            return True
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def are_edges_compatible(edge1, edge2):
    """Check if two edges are compatible"""
    if edge1 == 'flat' or edge2 == 'flat':
        return True
    return (edge1 == 'tab' and edge2 == 'blank') or (edge1 == 'blank' and edge2 == 'tab')

if __name__ == "__main__":
    success = test_edge_assignment()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ EDGE ASSIGNMENT FIX SUCCESSFUL!")
        print("The puzzle pieces now have compatible edges.")
    else:
        print("\n" + "=" * 60)
        print("❌ EDGE ASSIGNMENT FIX FAILED!")
        print("There are still compatibility issues.")
    
    sys.exit(0 if success else 1)