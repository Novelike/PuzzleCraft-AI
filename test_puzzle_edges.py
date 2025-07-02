import requests
import json

def test_puzzle_creation():
    """Test puzzle creation with edges information"""

    # Test image path (you can change this to any image file)
    test_image_path = "test_image.jpg"

    # Create a simple test image if it doesn't exist
    try:
        from PIL import Image
        import numpy as np

        # Create a simple test image
        img_array = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
        img = Image.fromarray(img_array)
        img.save(test_image_path)
        print(f"✅ Created test image: {test_image_path}")
    except Exception as e:
        print(f"⚠️ Could not create test image: {e}")
        return

    # Test the puzzle creation API
    url = "http://localhost:8006/create-puzzle-pieces"

    try:
        with open(test_image_path, 'rb') as f:
            files = {'file': f}
            data = {'piece_count': 9}  # 3x3 grid for easy testing

            response = requests.post(url, files=files, data=data)

        if response.status_code == 200:
            result = response.json()
            print("✅ Puzzle creation successful!")
            print(f"📊 Total pieces: {result.get('total_pieces', 0)}")
            print(f"🧩 Puzzle type: {result.get('puzzle_type', 'unknown')}")

            # Check if pieces have edges information
            pieces = result.get('pieces', [])
            if pieces:
                first_piece = pieces[0]
                print(f"\n🔍 First piece analysis:")
                print(f"   ID: {first_piece.get('id', 'N/A')}")
                print(f"   Type: {first_piece.get('type', 'N/A')}")
                print(f"   Has edges: {'edges' in first_piece}")

                if 'edges' in first_piece:
                    edges = first_piece['edges']
                    print(f"   Edges: {edges}")
                    print(f"   ✅ Edges information is present!")
                else:
                    print(f"   ❌ No edges information found")

                # Check required fields for frontend
                required_fields = ['width', 'height', 'correctPosition', 'currentPosition']
                missing_fields = [field for field in required_fields if field not in first_piece]

                if missing_fields:
                    print(f"   ⚠️ Missing fields: {missing_fields}")
                else:
                    print(f"   ✅ All required fields present")

            # Save result for inspection
            with open('test_puzzle_result.json', 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\n💾 Full result saved to test_puzzle_result.json")

        else:
            print(f"❌ API call failed with status {response.status_code}")
            print(f"Response: {response.text}")

    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the API. Make sure the segmentation service is running on port 8006")
    except Exception as e:
        print(f"❌ Error during API call: {e}")

if __name__ == "__main__":
    print("🧪 Testing puzzle creation with edges information...")
    test_puzzle_creation()
