import requests
import json
import logging
from pathlib import Path
import io
from PIL import Image

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service URLs
API_GATEWAY_URL = "http://localhost:8000"
STYLE_TRANSFER_URL = "http://localhost:8007"

def create_test_image():
    """Create a simple test image"""
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes

def test_preview_response_format():
    """Test that the preview endpoint returns the expected format"""
    logger.info("Testing preview response format...")
    
    try:
        img_bytes = create_test_image()
        
        files = {'file': ('test.png', img_bytes, 'image/png')}
        data = {'style_type': 'watercolor'}
        
        # Test with a mock token (you may need to adjust this)
        headers = {'Authorization': 'Bearer test_token'}
        
        response = requests.post(
            f"{API_GATEWAY_URL}/api/v1/style/preview",
            files=files,
            data=data,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Preview response: {result}")
            
            # Check if the response has the expected format
            expected_fields = ['preview_url', 'style_type', 'processing_time', 'success']
            missing_fields = [field for field in expected_fields if field not in result]
            
            if not missing_fields:
                logger.info("✓ Preview response format is correct!")
                
                # Check if preview_url has the correct format
                preview_url = result.get('preview_url', '')
                if '/api/v1/style/image/' in preview_url:
                    logger.info("✓ Preview URL format is correct!")
                    return True, result
                else:
                    logger.error(f"✗ Preview URL format incorrect: {preview_url}")
                    return False, result
            else:
                logger.error(f"✗ Missing fields in response: {missing_fields}")
                return False, result
        else:
            logger.error(f"Preview request failed: {response.status_code} - {response.text}")
            return False, None
            
    except Exception as e:
        logger.error(f"Error testing preview: {e}")
        return False, None

def test_image_serving():
    """Test that the image serving endpoint works"""
    logger.info("Testing image serving endpoint...")
    
    try:
        # First get a preview to get an image filename
        success, preview_result = test_preview_response_format()
        
        if success and preview_result:
            preview_url = preview_result.get('preview_url', '')
            
            # Extract filename from URL
            if '/api/v1/style/image/' in preview_url:
                filename = preview_url.split('/api/v1/style/image/')[-1]
                
                # Test direct image access
                image_response = requests.get(f"{API_GATEWAY_URL}/api/v1/style/image/{filename}")
                
                if image_response.status_code == 200:
                    content_type = image_response.headers.get('content-type', '')
                    if 'image' in content_type:
                        logger.info("✓ Image serving works correctly!")
                        return True
                    else:
                        logger.error(f"✗ Wrong content type: {content_type}")
                        return False
                else:
                    logger.error(f"✗ Image serving failed: {image_response.status_code}")
                    return False
            else:
                logger.error("✗ Could not extract filename from preview URL")
                return False
        else:
            logger.error("✗ Could not get preview result for image serving test")
            return False
            
    except Exception as e:
        logger.error(f"Error testing image serving: {e}")
        return False

def test_style_apply_format():
    """Test that the apply endpoint returns the expected format"""
    logger.info("Testing apply response format...")
    
    try:
        img_bytes = create_test_image()
        
        files = {'file': ('test.png', img_bytes, 'image/png')}
        data = {'style_type': 'watercolor', 'iterations': 100}
        
        # Test with a mock token (you may need to adjust this)
        headers = {'Authorization': 'Bearer test_token'}
        
        response = requests.post(
            f"{API_GATEWAY_URL}/api/v1/style/apply",
            files=files,
            data=data,
            headers=headers,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Apply response: {result}")
            
            # Check if the response has the expected format
            expected_fields = ['styled_image_url', 'style_type', 'processing_time']
            missing_fields = [field for field in expected_fields if field not in result]
            
            if not missing_fields:
                logger.info("✓ Apply response format is correct!")
                
                # Check if styled_image_url has the correct format
                styled_url = result.get('styled_image_url', '')
                if '/api/v1/style/image/' in styled_url:
                    logger.info("✓ Styled image URL format is correct!")
                    return True
                else:
                    logger.error(f"✗ Styled image URL format incorrect: {styled_url}")
                    return False
            else:
                logger.error(f"✗ Missing fields in response: {missing_fields}")
                return False
        else:
            logger.error(f"Apply request failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error testing apply: {e}")
        return False

def main():
    """Run all frontend integration tests"""
    logger.info("Starting frontend integration tests...")
    
    print("=" * 60)
    print("FRONTEND INTEGRATION TESTS")
    print("=" * 60)
    
    # Test 1: Preview Response Format
    print("\n1. Testing Preview Response Format")
    print("-" * 40)
    preview_success, _ = test_preview_response_format()
    
    # Test 2: Image Serving
    print("\n2. Testing Image Serving")
    print("-" * 40)
    image_serving_success = test_image_serving()
    
    # Test 3: Apply Response Format
    print("\n3. Testing Apply Response Format")
    print("-" * 40)
    apply_success = test_style_apply_format()
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if preview_success:
        print("✓ Preview endpoint: Response format correct")
    else:
        print("✗ Preview endpoint: Response format incorrect")
    
    if image_serving_success:
        print("✓ Image serving: Working correctly")
    else:
        print("✗ Image serving: Not working")
    
    if apply_success:
        print("✓ Apply endpoint: Response format correct")
    else:
        print("✗ Apply endpoint: Response format incorrect")
    
    print("\n" + "=" * 60)
    print("FRONTEND COMPATIBILITY")
    print("=" * 60)
    
    if preview_success and image_serving_success:
        print("✓ Frontend should now be able to display preview images!")
        print("✓ The response format matches what the frontend expects.")
        print("✓ Images are accessible through the API Gateway proxy.")
    else:
        print("✗ Frontend integration may still have issues.")
        print("Please check the failing tests above.")
    
    print("\n" + "=" * 60)
    print("NEXT STEPS")
    print("=" * 60)
    print("1. Restart the API Gateway service")
    print("2. Set the API_BASE_URL environment variable:")
    print("   export API_BASE_URL=https://puzzle.novelike.dev")
    print("3. Test the frontend style preview functionality")
    print("4. Check browser network tab for image loading")

if __name__ == "__main__":
    main()