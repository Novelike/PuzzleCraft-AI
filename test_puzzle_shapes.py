import requests
import json
import base64
import io
from PIL import Image
import numpy as np

def test_puzzle_shape_generation():
    """Test puzzle generation to verify tab/blank shape implementation"""
    
    print("🔍 Testing puzzle shape generation...")
    
    # Test image upload and puzzle creation
    api_base = "http://localhost:8000/api/v1"
    
    # Create a simple test image
    test_image = Image.new('RGB', (200, 200), color='red')
    test_image.save('test_image.png')
    
    try:
        # Upload image
        print("📤 Uploading test image...")
        with open('test_image.png', 'rb') as f:
            files = {'file': ('test_image.png', f, 'image/png')}
            upload_response = requests.post(f"{api_base}/upload", files=files)
        
        if upload_response.status_code != 200:
            print(f"❌ Upload failed: {upload_response.status_code}")
            return
            
        upload_data = upload_response.json()
        image_url = upload_data.get('url')
        print(f"✅ Image uploaded: {image_url}")
        
        # Create puzzle
        print("🧩 Creating puzzle...")
        puzzle_data = {
            "imageUrl": image_url,
            "difficulty": "medium",
            "pieceCount": 4  # 2x2 grid for simple testing
        }
        
        create_response = requests.post(f"{api_base}/puzzles", json=puzzle_data)
        
        if create_response.status_code != 200:
            print(f"❌ Puzzle creation failed: {create_response.status_code}")
            print(f"Response: {create_response.text}")
            return
            
        puzzle_result = create_response.json()
        puzzle_id = puzzle_result.get('id')
        print(f"✅ Puzzle created: {puzzle_id}")
        
        # Get puzzle details
        print("📊 Getting puzzle details...")
        details_response = requests.get(f"{api_base}/puzzles/{puzzle_id}")
        
        if details_response.status_code != 200:
            print(f"❌ Failed to get puzzle details: {details_response.status_code}")
            return
            
        puzzle_details = details_response.json()
        pieces = puzzle_details.get('pieces', [])
        
        print(f"🧩 Found {len(pieces)} pieces")
        
        # Analyze pieces for tab/blank shapes
        tab_pieces = []
        blank_pieces = []
        
        for i, piece in enumerate(pieces):
            edges = piece.get('edges', {})
            image_data = piece.get('imageData', '')
            
            print(f"\n🔍 Piece {i} ({piece.get('id', 'unknown')}):")
            print(f"  Edges: {edges}")
            print(f"  Has imageData: {bool(image_data)}")
            
            if image_data:
                print(f"  ImageData sample: {image_data[:50]}...")
                
                # Check for tab and blank edges
                for edge_pos, edge_type in edges.items():
                    if edge_type == 'tab':
                        tab_pieces.append((i, edge_pos, piece))
                        print(f"  ✅ Found TAB edge at {edge_pos}")
                    elif edge_type == 'blank':
                        blank_pieces.append((i, edge_pos, piece))
                        print(f"  ✅ Found BLANK edge at {edge_pos}")
        
        print(f"\n📊 Summary:")
        print(f"  TAB edges found: {len(tab_pieces)}")
        print(f"  BLANK edges found: {len(blank_pieces)}")
        
        # Save detailed analysis
        analysis = {
            "puzzle_id": puzzle_id,
            "total_pieces": len(pieces),
            "tab_edges": len(tab_pieces),
            "blank_edges": len(blank_pieces),
            "pieces_analysis": []
        }
        
        for piece in pieces:
            piece_analysis = {
                "id": piece.get('id'),
                "edges": piece.get('edges', {}),
                "has_image_data": bool(piece.get('imageData')),
                "image_data_length": len(piece.get('imageData', ''))
            }
            analysis["pieces_analysis"].append(piece_analysis)
        
        # Save analysis to file
        with open('puzzle_shape_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Analysis saved to puzzle_shape_analysis.json")
        
        # Save full puzzle data for inspection
        with open('full_puzzle_data.json', 'w', encoding='utf-8') as f:
            json.dump(puzzle_details, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Full puzzle data saved to full_puzzle_data.json")
        
        # Test image decoding for a few pieces
        print(f"\n🖼️ Testing image decoding...")
        for i, piece in enumerate(pieces[:2]):  # Test first 2 pieces
            image_data = piece.get('imageData', '')
            if image_data and image_data.startswith('data:image/'):
                try:
                    # Extract base64 data
                    base64_data = image_data.split(',')[1]
                    image_bytes = base64.b64decode(base64_data)
                    
                    # Load as PIL image
                    image = Image.open(io.BytesIO(image_bytes))
                    
                    # Save for inspection
                    image.save(f'piece_{i}_shape.png')
                    print(f"  ✅ Piece {i} image saved as piece_{i}_shape.png")
                    print(f"     Size: {image.size}")
                    
                except Exception as e:
                    print(f"  ❌ Failed to decode piece {i} image: {e}")
        
        return puzzle_details
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        return None

if __name__ == "__main__":
    test_puzzle_shape_generation()