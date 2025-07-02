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

def test_style_preview_without_auth():
    """Test style preview without authentication"""
    logger.info("Testing style preview without authentication...")
    
    try:
        img_bytes = create_test_image()
        
        files = {'file': ('test.png', img_bytes, 'image/png')}
        data = {'style_type': 'watercolor'}
        
        # Test WITHOUT authentication headers
        response = requests.post(
            f"{API_GATEWAY_URL}/api/v1/style/preview",
            files=files,
            data=data,
            timeout=30
        )
        
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response text: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✓ Style preview successful without auth: {result}")
            return True, result
        elif response.status_code == 403:
            logger.error("✗ Still getting 403 Forbidden - auth fix not working")
            return False, None
        elif response.status_code == 401:
            logger.error("✗ Still getting 401 Unauthorized - auth fix not working")
            return False, None
        else:
            logger.error(f"✗ Unexpected status code: {response.status_code}")
            return False, None
            
    except Exception as e:
        logger.error(f"Error testing preview without auth: {e}")
        return False, None

def test_style_apply_without_auth():
    """Test style apply without authentication"""
    logger.info("Testing style apply without authentication...")
    
    try:
        img_bytes = create_test_image()
        
        files = {'file': ('test.png', img_bytes, 'image/png')}
        data = {'style_type': 'watercolor', 'iterations': 100}
        
        # Test WITHOUT authentication headers
        response = requests.post(
            f"{API_GATEWAY_URL}/api/v1/style/apply",
            files=files,
            data=data,
            timeout=60
        )
        
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response text: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✓ Style apply successful without auth: {result}")
            return True, result
        elif response.status_code == 403:
            logger.error("✗ Still getting 403 Forbidden - auth fix not working")
            return False, None
        elif response.status_code == 401:
            logger.error("✗ Still getting 401 Unauthorized - auth fix not working")
            return False, None
        else:
            logger.error(f"✗ Unexpected status code: {response.status_code}")
            return False, None
            
    except Exception as e:
        logger.error(f"Error testing apply without auth: {e}")
        return False, None

def test_available_styles():
    """Test available styles endpoint (should not require auth)"""
    logger.info("Testing available styles endpoint...")
    
    try:
        response = requests.get(f"{API_GATEWAY_URL}/api/v1/style/styles", timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✓ Available styles: {result}")
            return True, result
        else:
            logger.error(f"✗ Failed to get styles: {response.status_code} - {response.text}")
            return False, None
            
    except Exception as e:
        logger.error(f"Error testing available styles: {e}")
        return False, None

def main():
    """Run authentication fix tests"""
    logger.info("Starting authentication fix verification...")
    
    print("=" * 60)
    print("AUTHENTICATION FIX VERIFICATION")
    print("=" * 60)
    
    # Test 1: Available Styles (baseline test)
    print("\n1. Testing Available Styles Endpoint")
    print("-" * 40)
    styles_success, styles_data = test_available_styles()
    
    # Test 2: Style Preview without Auth
    print("\n2. Testing Style Preview without Authentication")
    print("-" * 40)
    preview_success, preview_data = test_style_preview_without_auth()
    
    # Test 3: Style Apply without Auth
    print("\n3. Testing Style Apply without Authentication")
    print("-" * 40)
    apply_success, apply_data = test_style_apply_without_auth()
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if styles_success:
        print("✓ Available styles endpoint: Working")
    else:
        print("✗ Available styles endpoint: Failed")
    
    if preview_success:
        print("✓ Style preview without auth: Working")
    else:
        print("✗ Style preview without auth: Failed")
    
    if apply_success:
        print("✓ Style apply without auth: Working")
    else:
        print("✗ Style apply without auth: Failed")
    
    print("\n" + "=" * 60)
    print("AUTHENTICATION FIX STATUS")
    print("=" * 60)
    
    if preview_success and apply_success:
        print("✅ AUTHENTICATION FIX SUCCESSFUL!")
        print("✅ Style preview and apply now work without authentication")
        print("✅ Frontend should now be able to use style features")
    else:
        print("❌ AUTHENTICATION FIX INCOMPLETE")
        print("❌ Some endpoints still require authentication")
        print("❌ Additional fixes may be needed")
    
    print("\n" + "=" * 60)
    print("NEXT STEPS")
    print("=" * 60)
    
    if preview_success and apply_success:
        print("1. ✅ Authentication issue resolved")
        print("2. Test the frontend style preview functionality")
        print("3. Verify that preview images now display correctly")
        print("4. Check that all style types work properly")
    else:
        print("1. ❌ Check API Gateway service restart")
        print("2. Verify the code changes were applied correctly")
        print("3. Check API Gateway logs for any errors")
        print("4. Consider additional authentication bypass methods")

if __name__ == "__main__":
    main()