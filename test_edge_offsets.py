import sys
import os
sys.path.append('backend/segmentation-service')

from segmentation import ImageSegmentation
import json

def test_edge_offsets():
    """Test that all puzzle pieces have edgeOffsets property"""
    print("Testing edgeOffsets property in puzzle pieces...")
    
    # Create segmentation instance
    segmentation = ImageSegmentation()
    
    # Test with a sample image (we'll use a placeholder path)
    test_image_path = "test_image.jpg"
    
    # Create a simple test image if it doesn't exist
    import cv2
    import numpy as np
    
    if not os.path.exists(test_image_path):
        # Create a simple test image
        test_img = np.ones((400, 600, 3), dtype=np.uint8) * 255
        cv2.rectangle(test_img, (100, 100), (500, 300), (0, 0, 255), -1)
        cv2.imwrite(test_image_path, test_img)
        print(f"Created test image: {test_image_path}")
    
    # Test 1: create_puzzle_pieces function
    print("\n1. Testing create_puzzle_pieces function...")
    try:
        result1 = segmentation.create_puzzle_pieces(test_image_path, piece_count=6)
        pieces1 = result1.get('pieces', [])
        
        missing_offsets = []
        for piece in pieces1:
            if 'edgeOffsets' not in piece:
                missing_offsets.append(piece.get('id', 'unknown'))
            else:
                print(f"  Piece {piece.get('id')}: edgeOffsets = {piece['edgeOffsets']}")
        
        if missing_offsets:
            print(f"  ❌ Missing edgeOffsets in pieces: {missing_offsets}")
        else:
            print(f"  ✅ All {len(pieces1)} pieces have edgeOffsets property")
            
    except Exception as e:
        print(f"  ❌ Error testing create_puzzle_pieces: {e}")
    
    # Test 2: generate_intelligent_puzzle_pieces function
    print("\n2. Testing generate_intelligent_puzzle_pieces function...")
    try:
        result2 = segmentation.generate_intelligent_puzzle_pieces(test_image_path, piece_count=8)
        pieces2 = result2.get('pieces', [])
        
        missing_offsets = []
        for piece in pieces2:
            if 'edgeOffsets' not in piece:
                missing_offsets.append(piece.get('id', 'unknown'))
            else:
                print(f"  Piece {piece.get('id')}: edgeOffsets = {piece['edgeOffsets']}")
        
        if missing_offsets:
            print(f"  ❌ Missing edgeOffsets in pieces: {missing_offsets}")
        else:
            print(f"  ✅ All {len(pieces2)} pieces have edgeOffsets property")
            
    except Exception as e:
        print(f"  ❌ Error testing generate_intelligent_puzzle_pieces: {e}")
    
    # Test 3: _create_grid_based_pieces function (fallback)
    print("\n3. Testing _create_grid_based_pieces function...")
    try:
        result3 = segmentation._create_grid_based_pieces(test_image_path, piece_count=4)
        pieces3 = result3.get('pieces', [])
        
        missing_offsets = []
        for piece in pieces3:
            if 'edgeOffsets' not in piece:
                missing_offsets.append(piece.get('id', 'unknown'))
            else:
                print(f"  Piece {piece.get('id')}: edgeOffsets = {piece['edgeOffsets']}")
        
        if missing_offsets:
            print(f"  ❌ Missing edgeOffsets in pieces: {missing_offsets}")
        else:
            print(f"  ✅ All {len(pieces3)} pieces have edgeOffsets property")
            
    except Exception as e:
        print(f"  ❌ Error testing _create_grid_based_pieces: {e}")
    
    print("\n" + "="*50)
    print("Test completed!")
    
    # Clean up test image
    if os.path.exists(test_image_path):
        os.remove(test_image_path)
        print("Cleaned up test image")

if __name__ == "__main__":
    test_edge_offsets()