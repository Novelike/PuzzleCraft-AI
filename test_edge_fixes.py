import sys
import os
sys.path.append('backend/segmentation-service')

from segmentation import ImageSegmentation
import json

def test_edge_fixes():
    """Test the edge compatibility fixes"""
    print("🧪 Testing edge compatibility fixes...")
    print("=" * 60)

    # Create segmentation instance
    segmentation = ImageSegmentation()

    # Test with a simple test image
    test_image_path = "test_image.png"

    if not os.path.exists(test_image_path):
        print(f"❌ Test image not found: {test_image_path}")
        print("Creating a simple test image...")

        import cv2
        import numpy as np

        # Create a simple 640x480 test image
        test_img = np.zeros((480, 640, 3), dtype=np.uint8)
        test_img[:, :] = (100, 150, 200)  # Light blue background

        # Add some simple shapes for testing
        cv2.rectangle(test_img, (100, 100), (300, 200), (255, 0, 0), -1)  # Blue rectangle
        cv2.circle(test_img, (450, 300), 80, (0, 255, 0), -1)  # Green circle

        cv2.imwrite(test_image_path, test_img)
        print(f"✅ Created test image: {test_image_path}")

    try:
        # Generate puzzle pieces with the fixed logic
        print(f"🔧 Generating puzzle pieces with fixed edge logic...")
        result = segmentation.generate_intelligent_puzzle_pieces(
            test_image_path, 
            piece_count=16  # 4x4 grid for testing
        )

        if 'error' in result:
            print(f"❌ Puzzle generation failed: {result.get('error', 'Unknown error')}")
            return False

        pieces = result['pieces']
        print(f"✅ Generated {len(pieces)} puzzle pieces")

        # Analyze edge compatibility
        print("\n🔍 Analyzing edge compatibility...")
        incompatible_pairs = []
        tolerance = 1  # Same tolerance as in the fix

        for i, piece_a in enumerate(pieces):
            for j, piece_b in enumerate(pieces):
                if i >= j:  # Avoid duplicate checks
                    continue

                # Get positions and dimensions from bbox
                a_x1, a_y1, a_x2, a_y2 = piece_a['bbox']
                b_x1, b_y1, b_x2, b_y2 = piece_b['bbox']

                # Check if pieces are horizontally adjacent (A is left of B)
                if (abs(a_x2 - b_x1) <= tolerance and abs(a_y1 - b_y1) <= tolerance):
                    a_right = piece_a['edges']['right']
                    b_left = piece_b['edges']['left']

                    if not are_edges_compatible(a_right, b_left):
                        incompatible_pairs.append({
                            'piece_a': piece_a['id'],
                            'piece_b': piece_b['id'],
                            'position': 'horizontal',
                            'a_edge': f"right={a_right}",
                            'b_edge': f"left={b_left}",
                            'issue': f"Both edges are '{a_right}'" if a_right == b_left else f"Incompatible: {a_right} vs {b_left}"
                        })

                # Check if pieces are vertically adjacent (A is above B)
                elif (abs(a_y2 - b_y1) <= tolerance and abs(a_x1 - b_x1) <= tolerance):
                    a_bottom = piece_a['edges']['bottom']
                    b_top = piece_b['edges']['top']

                    if not are_edges_compatible(a_bottom, b_top):
                        incompatible_pairs.append({
                            'piece_a': piece_a['id'],
                            'piece_b': piece_b['id'],
                            'position': 'vertical',
                            'a_edge': f"bottom={a_bottom}",
                            'b_edge': f"top={b_top}",
                            'issue': f"Both edges are '{a_bottom}'" if a_bottom == b_top else f"Incompatible: {a_bottom} vs {b_top}"
                        })

        # Report results
        if incompatible_pairs:
            print(f"❌ Found {len(incompatible_pairs)} incompatible edge pairs:")
            for pair in incompatible_pairs:
                print(f"   🔴 {pair['piece_a']} ↔ {pair['piece_b']} ({pair['position']})")
                print(f"      {pair['a_edge']} | {pair['b_edge']}")
                print(f"      Issue: {pair['issue']}")
            return False
        else:
            print("✅ All adjacent pieces have compatible edges!")

        # Save the fixed puzzle data for inspection
        output_file = "fixed_puzzle_test_output.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved fixed puzzle data to: {output_file}")

        # Show some piece information
        print(f"\n📊 Piece Information Summary:")
        for i, piece in enumerate(pieces[:5]):  # Show first 5 pieces
            print(f"   Piece {piece['id']}: edges={piece['edges']}, size=({piece['width']}×{piece['height']})")

        return True

    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

def are_edges_compatible(edge1, edge2):
    """Check if two edges are compatible (one tab, one blank)"""
    if edge1 == 'flat' or edge2 == 'flat':
        return True  # Flat edges are always compatible

    # For tab/blank edges, they must be complementary
    return (edge1 == 'tab' and edge2 == 'blank') or (edge1 == 'blank' and edge2 == 'tab')

if __name__ == "__main__":
    success = test_edge_fixes()

    if success:
        print("\n" + "=" * 60)
        print("🎉 EDGE COMPATIBILITY FIXES SUCCESSFUL!")
        print("All adjacent pieces now have compatible edges.")
        print("The puzzle generation system has been fixed.")
    else:
        print("\n" + "=" * 60)
        print("❌ EDGE COMPATIBILITY FIXES FAILED!")
        print("There are still issues with edge compatibility.")
        sys.exit(1)
