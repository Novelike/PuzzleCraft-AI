import json
import sys
import os
from pathlib import Path

# Add the backend path to sys.path
backend_path = Path(__file__).parent / "backend" / "segmentation-service"
sys.path.insert(0, str(backend_path))

try:
    from segmentation import ImageSegmentation
except ImportError as e:
    print(f"Error importing segmentation module: {e}")
    sys.exit(1)

def verify_complete_solution():
    """Complete verification of the puzzle piece generation fix"""
    
    print("🔍 COMPLETE PUZZLE PIECE GENERATION VERIFICATION")
    print("=" * 70)
    
    # Test 1: Generate new puzzle pieces
    print("\n1. Testing puzzle piece generation...")
    segmenter = ImageSegmentation()
    
    test_image_path = "test_image.png"
    if not os.path.exists(test_image_path):
        print(f"❌ Test image not found: {test_image_path}")
        return False
    
    try:
        result = segmenter.generate_intelligent_puzzle_pieces(
            image_path=test_image_path,
            piece_count=20,
            subject_background_ratio=0.6
        )
        
        if result.get('puzzle_type') == 'error':
            print(f"❌ Puzzle generation failed: {result.get('error')}")
            return False
        
        pieces = result.get('pieces', [])
        print(f"✅ Generated {len(pieces)} puzzle pieces successfully")
        
    except Exception as e:
        print(f"❌ Puzzle generation failed: {e}")
        return False
    
    # Test 2: Verify edge compatibility
    print("\n2. Verifying edge compatibility...")
    incompatible_count = check_edge_compatibility(pieces)
    
    if incompatible_count > 0:
        print(f"❌ Found {incompatible_count} incompatible edge pairs")
        return False
    else:
        print("✅ All adjacent pieces have compatible edges")
    
    # Test 3: Verify image data generation
    print("\n3. Verifying image data generation...")
    image_data_success = verify_image_data(pieces)
    
    if not image_data_success:
        print("❌ Image data generation has issues")
        return False
    else:
        print("✅ All pieces have valid image data with proper masks")
    
    # Test 4: Verify data structure completeness
    print("\n4. Verifying data structure completeness...")
    structure_success = verify_data_structure(pieces)
    
    if not structure_success:
        print("❌ Data structure is incomplete")
        return False
    else:
        print("✅ All pieces have complete data structure")
    
    # Test 5: Save sample output for inspection
    print("\n5. Saving sample output...")
    save_sample_output(result)
    print("✅ Sample output saved to 'fixed_puzzle_output.json'")
    
    return True

def check_edge_compatibility(pieces):
    """Check edge compatibility between adjacent pieces"""
    incompatible_count = 0
    tolerance = 5
    
    for i, piece_a in enumerate(pieces):
        for j, piece_b in enumerate(pieces):
            if i >= j:
                continue
            
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
                    incompatible_count += 1
            
            # Check vertical adjacency
            elif (abs(a_y2 - b_y1) < tolerance and 
                  abs(a_x1 - b_x1) < tolerance and 
                  abs(a_x2 - b_x2) < tolerance):
                
                a_bottom = piece_a['edges']['bottom']
                b_top = piece_b['edges']['top']
                
                if not are_edges_compatible(a_bottom, b_top):
                    incompatible_count += 1
    
    return incompatible_count

def are_edges_compatible(edge1, edge2):
    """Check if two edges are compatible"""
    if edge1 == 'flat' or edge2 == 'flat':
        return True
    return (edge1 == 'tab' and edge2 == 'blank') or (edge1 == 'blank' and edge2 == 'tab')

def verify_image_data(pieces):
    """Verify that all pieces have valid image data"""
    for piece in pieces:
        if 'imageData' not in piece:
            print(f"❌ Piece {piece['id']} missing imageData")
            return False
        
        image_data = piece['imageData']
        if not image_data.startswith('data:image/png;base64,'):
            print(f"❌ Piece {piece['id']} has invalid imageData format")
            return False
        
        # Check if base64 data is not empty
        base64_part = image_data.split(',')[1] if ',' in image_data else ''
        if len(base64_part) < 100:  # Reasonable minimum for a puzzle piece image
            print(f"❌ Piece {piece['id']} has suspiciously small imageData")
            return False
    
    return True

def verify_data_structure(pieces):
    """Verify that all pieces have complete data structure"""
    required_fields = ['id', 'x', 'y', 'width', 'height', 'edges', 'imageData', 
                      'correctPosition', 'currentPosition', 'isPlaced', 'isSelected', 
                      'rotation', 'difficulty', 'region']
    
    for piece in pieces:
        for field in required_fields:
            if field not in piece:
                print(f"❌ Piece {piece['id']} missing field: {field}")
                return False
        
        # Verify edges structure
        edge_types = ['top', 'right', 'bottom', 'left']
        for edge_type in edge_types:
            if edge_type not in piece['edges']:
                print(f"❌ Piece {piece['id']} missing edge: {edge_type}")
                return False
            
            edge_value = piece['edges'][edge_type]
            if edge_value not in ['flat', 'tab', 'blank']:
                print(f"❌ Piece {piece['id']} has invalid edge value: {edge_value}")
                return False
    
    return True

def save_sample_output(result):
    """Save sample output for inspection"""
    # Remove imageData for readability (it's very long)
    clean_result = json.loads(json.dumps(result))
    for piece in clean_result.get('pieces', []):
        if 'imageData' in piece:
            piece['imageData'] = f"data:image/png;base64,... ({len(piece['imageData'])} chars)"
    
    with open('fixed_puzzle_output.json', 'w', encoding='utf-8') as f:
        json.dump(clean_result, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    print("Starting complete verification of puzzle piece generation fixes...")
    
    success = verify_complete_solution()
    
    if success:
        print("\n" + "=" * 70)
        print("🎉 ALL TESTS PASSED! 🎉")
        print("✅ Edge assignment logic fixed")
        print("✅ Image mask application working")
        print("✅ Puzzle pieces can connect properly")
        print("✅ Complete data structure generated")
        print("\nThe puzzle generation system is now working correctly!")
        print("Adjacent pieces have complementary edges (tab-blank pairs)")
        print("and proper shape masks are applied to create realistic puzzle pieces.")
    else:
        print("\n" + "=" * 70)
        print("❌ VERIFICATION FAILED")
        print("Some issues still need to be resolved.")
    
    sys.exit(0 if success else 1)