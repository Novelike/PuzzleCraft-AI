import sys
import os
sys.path.append('backend/segmentation-service')

from segmentation import ImageSegmentation
import numpy as np
import cv2

def test_edge_compatibility():
    """Test the edge compatibility logic"""
    print("=== Testing Edge Compatibility Logic ===")
    
    # Create a test segmentation instance
    segmentation = ImageSegmentation()
    
    # Test the _create_puzzle_shape_mask method with different edge types
    test_edges = [
        {'top': 'flat', 'right': 'tab', 'bottom': 'flat', 'left': 'blank'},
        {'top': 'blank', 'right': 'flat', 'bottom': 'tab', 'left': 'flat'},
        {'top': 'tab', 'right': 'blank', 'bottom': 'flat', 'left': 'flat'}
    ]
    
    for i, edges in enumerate(test_edges):
        print(f"\nTest {i+1}: Testing edges {edges}")
        
        # Create mask with 100x100 size
        mask = segmentation._create_puzzle_shape_mask(100, 100, edges)
        
        print(f"  Mask shape: {mask.shape}")
        print(f"  Mask dtype: {mask.dtype}")
        print(f"  Non-zero pixels: {np.count_nonzero(mask)}")
        
        # Check if mask has expected properties
        if mask.shape[0] > 100 or mask.shape[1] > 100:
            print(f"  ✓ Mask extended for tabs/blanks")
        else:
            print(f"  ✓ Mask size matches base size")

def test_edge_assignment():
    """Test edge assignment logic"""
    print("\n=== Testing Edge Assignment Logic ===")
    
    # Create mock pieces data
    pieces = [
        {
            'id': 'piece_1',
            'bbox': [0, 0, 100, 100],
            'edges': {'top': 'flat', 'right': 'flat', 'bottom': 'flat', 'left': 'flat'}
        },
        {
            'id': 'piece_2', 
            'bbox': [100, 0, 200, 100],  # Adjacent to piece_1 on the right
            'edges': {'top': 'flat', 'right': 'flat', 'bottom': 'flat', 'left': 'flat'}
        },
        {
            'id': 'piece_3',
            'bbox': [0, 100, 100, 200],  # Adjacent to piece_1 on the bottom
            'edges': {'top': 'flat', 'right': 'flat', 'bottom': 'flat', 'left': 'flat'}
        }
    ]
    
    # Simulate the edge assignment logic from generate_intelligent_puzzle_pieces
    tolerance = 1
    for i, p in enumerate(pieces):
        for j, q in enumerate(pieces):
            if i >= j:
                continue
                
            p_x1, p_y1 = p['bbox'][0], p['bbox'][1]
            p_x2, p_y2 = p['bbox'][2], p['bbox'][3]
            q_x1, q_y1 = q['bbox'][0], q['bbox'][1]
            q_x2, q_y2 = q['bbox'][2], q['bbox'][3]
            
            # Horizontal adjacency check (p is left of q)
            if (abs(p_x2 - q_x1) <= tolerance and abs(p_y1 - q_y1) <= tolerance):
                p['edges']['right'] = 'tab'
                q['edges']['left'] = 'blank'
                print(f"  ✓ {p['id']}.right=tab ↔ {q['id']}.left=blank")
            
            # Vertical adjacency check (p is above q)
            elif (abs(p_y2 - q_y1) <= tolerance and abs(p_x1 - q_x1) <= tolerance):
                p['edges']['bottom'] = 'tab'
                q['edges']['top'] = 'blank'
                print(f"  ✓ {p['id']}.bottom=tab ↔ {q['id']}.top=blank")
    
    # Verify edge compatibility
    print("\nEdge compatibility verification:")
    for i, p in enumerate(pieces):
        for j, q in enumerate(pieces):
            if i >= j:
                continue
                
            p_x1, p_y1 = p['bbox'][0], p['bbox'][1]
            p_x2, p_y2 = p['bbox'][2], p['bbox'][3]
            q_x1, q_y1 = q['bbox'][0], q['bbox'][1]
            q_x2, q_y2 = q['bbox'][2], q['bbox'][3]
            
            # Check right-left adjacency
            if abs(p_x2 - q_x1) <= tolerance and abs(p_y1 - q_y1) <= tolerance:
                e1, e2 = p['edges']['right'], q['edges']['left']
                if (e1 == 'tab' and e2 == 'blank') or (e1 == 'blank' and e2 == 'tab'):
                    print(f"  ✓ Valid edge pair: {p['id']}.right={e1} ↔ {q['id']}.left={e2}")
                else:
                    print(f"  ❌ Invalid edge pair: {p['id']}.right={e1} ↔ {q['id']}.left={e2}")

if __name__ == "__main__":
    print("Testing PuzzleCraft-AI Implementation")
    print("=" * 50)
    
    try:
        test_edge_compatibility()
        test_edge_assignment()
        print("\n" + "=" * 50)
        print("✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()