import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'puzzle-generator'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'segmentation-service'))

import numpy as np
import cv2
from PIL import Image

# Import the classes we want to test
try:
    from puzzle_engine import IntelligentPuzzleEngine, DifficultyLevel
    from segmentation import ImageSegmentation
    print("✅ Successfully imported puzzle engine and segmentation classes")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Trying alternative import...")

    # Add the backend directories to path
    backend_path = os.path.join(os.path.dirname(__file__), 'backend')
    puzzle_gen_path = os.path.join(backend_path, 'puzzle-generator')
    seg_path = os.path.join(backend_path, 'segmentation-service')

    if puzzle_gen_path not in sys.path:
        sys.path.insert(0, puzzle_gen_path)
    if seg_path not in sys.path:
        sys.path.insert(0, seg_path)

    try:
        from puzzle_engine import IntelligentPuzzleEngine, DifficultyLevel
        from segmentation import ImageSegmentation
        print("✅ Successfully imported with alternative method")
    except ImportError as e2:
        print(f"❌ Still failed to import: {e2}")
        print("Available files in puzzle-generator:")
        if os.path.exists(puzzle_gen_path):
            print(os.listdir(puzzle_gen_path))
        print("Available files in segmentation-service:")
        if os.path.exists(seg_path):
            print(os.listdir(seg_path))
        exit(1)

def test_puzzle_engine_masks():
    """Test the puzzle engine mask generation"""
    print("\n🔍 Testing Puzzle Engine Mask Generation")
    print("=" * 50)

    try:
        engine = IntelligentPuzzleEngine()

        # Test different edge configurations
        test_cases = [
            {"top": "flat", "right": "tab", "bottom": "blank", "left": "flat"},
            {"top": "tab", "right": "blank", "bottom": "tab", "left": "blank"},
            {"top": "blank", "right": "flat", "bottom": "flat", "left": "tab"},
        ]

        width, height = 100, 100

        for i, edges in enumerate(test_cases):
            print(f"\n🧩 Test case {i+1}: {edges}")

            # Generate mask
            mask = engine._generate_piece_shape(width, height, DifficultyLevel.MEDIUM, edges)

            if mask is not None:
                print(f"  ✅ Mask generated: {mask.shape}")
                print(f"  📊 Mask stats: min={mask.min()}, max={mask.max()}, unique_values={np.unique(mask)}")

                # Save mask as image for visual inspection
                mask_image = (mask * 255).astype(np.uint8)
                cv2.imwrite(f'test_mask_engine_{i+1}.png', mask_image)
                print(f"  💾 Saved as test_mask_engine_{i+1}.png")

                # Check for tabs and blanks
                has_extensions = mask.shape[0] > height or mask.shape[1] > width
                print(f"  🔍 Has extensions (tabs): {has_extensions}")

            else:
                print(f"  ❌ No mask generated (might be EASY difficulty)")

    except Exception as e:
        print(f"❌ Error testing puzzle engine: {e}")
        import traceback
        traceback.print_exc()

def test_segmentation_masks():
    """Test the segmentation service mask generation"""
    print("\n🔍 Testing Segmentation Service Mask Generation")
    print("=" * 50)

    try:
        segmentation = ImageSegmentation()

        # Test different edge configurations
        test_cases = [
            {"top": "flat", "right": "tab", "bottom": "blank", "left": "flat"},
            {"top": "tab", "right": "blank", "bottom": "tab", "left": "blank"},
            {"top": "blank", "right": "flat", "bottom": "flat", "left": "tab"},
        ]

        width, height = 100, 100

        for i, edges in enumerate(test_cases):
            print(f"\n🧩 Test case {i+1}: {edges}")

            # Generate mask
            mask = segmentation._create_puzzle_shape_mask(width, height, edges)

            if mask is not None:
                print(f"  ✅ Mask generated: {mask.shape}")
                print(f"  📊 Mask stats: min={mask.min()}, max={mask.max()}, unique_values={np.unique(mask)}")

                # Save mask as image for visual inspection
                mask_image = (mask * 255).astype(np.uint8)
                cv2.imwrite(f'test_mask_segmentation_{i+1}.png', mask_image)
                print(f"  💾 Saved as test_mask_segmentation_{i+1}.png")

                # Check for tabs and blanks
                has_extensions = mask.shape[0] > height or mask.shape[1] > width
                print(f"  🔍 Has extensions (tabs): {has_extensions}")

            else:
                print(f"  ❌ No mask generated")

    except Exception as e:
        print(f"❌ Error testing segmentation service: {e}")
        import traceback
        traceback.print_exc()

def analyze_mask_shapes():
    """Analyze the generated masks to verify tab/blank shapes"""
    print("\n🔍 Analyzing Generated Masks")
    print("=" * 50)

    # Look for generated mask files
    mask_files = [f for f in os.listdir('.') if f.startswith('test_mask_') and f.endswith('.png')]

    for mask_file in mask_files:
        print(f"\n📊 Analyzing {mask_file}")

        # Load mask
        mask = cv2.imread(mask_file, cv2.IMREAD_GRAYSCALE)
        if mask is None:
            print(f"  ❌ Could not load {mask_file}")
            continue

        # Find contours to analyze shape
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest_contour)
            perimeter = cv2.arcLength(largest_contour, True)

            # Calculate shape complexity
            if perimeter > 0:
                compactness = 4 * np.pi * area / (perimeter * perimeter)
                print(f"  📐 Area: {area:.0f}, Perimeter: {perimeter:.1f}")
                print(f"  🔄 Compactness: {compactness:.3f} (1.0 = perfect circle, lower = more complex)")

                # Analyze bounding box vs actual shape
                x, y, w, h = cv2.boundingRect(largest_contour)
                bbox_area = w * h
                fill_ratio = area / bbox_area if bbox_area > 0 else 0
                print(f"  📦 Bounding box: {w}x{h}, Fill ratio: {fill_ratio:.3f}")

                if fill_ratio < 0.8:
                    print(f"  ✅ Shape has indentations (blanks)")
                if w > 100 or h > 100:  # Original size was 100x100
                    print(f"  ✅ Shape has extensions (tabs)")
            else:
                print(f"  ❌ Could not calculate shape metrics")
        else:
            print(f"  ❌ No contours found in mask")

if __name__ == "__main__":
    print("🧩 Testing Puzzle Piece Mask Generation")
    print("=" * 60)

    # Test both engines
    test_puzzle_engine_masks()
    test_segmentation_masks()

    # Analyze results
    analyze_mask_shapes()

    print("\n✅ Testing complete! Check the generated PNG files to visually verify the shapes.")
