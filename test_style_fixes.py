import requests
import json
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service URLs
API_GATEWAY_URL = "http://localhost:8000"
STYLE_TRANSFER_URL = "http://localhost:8007"

def test_style_transfer_service():
    """Test the style transfer service directly"""
    logger.info("Testing style transfer service directly...")

    try:
        # Test available styles endpoint
        response = requests.get(f"{STYLE_TRANSFER_URL}/available-styles", timeout=10)
        if response.status_code == 200:
            styles_data = response.json()
            logger.info(f"Available styles: {styles_data}")
            return styles_data
        else:
            logger.error(f"Failed to get styles: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error testing style transfer service: {e}")
        return None

def test_api_gateway_styles():
    """Test the API gateway styles endpoint"""
    logger.info("Testing API gateway styles endpoint...")

    try:
        response = requests.get(f"{API_GATEWAY_URL}/api/v1/style/styles", timeout=10)
        if response.status_code == 200:
            styles_data = response.json()
            logger.info(f"API Gateway styles: {styles_data}")
            return styles_data
        else:
            logger.error(f"Failed to get styles from API gateway: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error testing API gateway: {e}")
        return None

def test_style_preview_with_dummy_image():
    """Test style preview with a dummy image"""
    logger.info("Testing style preview with dummy image...")

    # Create a simple test image (1x1 pixel PNG)
    import io
    from PIL import Image

    # Create a small test image
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    # Test styles to try
    test_styles = ['watercolor', 'cartoon', 'pixel_art', 'sketch', 'anime', 'oil_painting']

    results = {}

    for style in test_styles:
        logger.info(f"Testing style: {style}")
        try:
            # Reset image bytes
            img_bytes.seek(0)

            files = {'file': ('test.png', img_bytes, 'image/png')}
            data = {'style_type': style}

            response = requests.post(
                f"{STYLE_TRANSFER_URL}/preview-style",
                files=files,
                data=data,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                results[style] = {
                    'success': result.get('success', False),
                    'status': 'working'
                }
                logger.info(f"Style {style}: SUCCESS - {result.get('success', False)}")
            else:
                results[style] = {
                    'success': False,
                    'status': f'failed_with_{response.status_code}',
                    'error': response.text
                }
                logger.error(f"Style {style}: FAILED - {response.status_code} - {response.text}")

        except Exception as e:
            results[style] = {
                'success': False,
                'status': 'exception',
                'error': str(e)
            }
            logger.error(f"Style {style}: EXCEPTION - {e}")

    return results

def main():
    """Run all tests"""
    logger.info("Starting style transfer fix verification...")

    print("=" * 60)
    print("STYLE TRANSFER FIX VERIFICATION")
    print("=" * 60)

    # Test 1: Style Transfer Service Direct
    print("\n1. Testing Style Transfer Service (Direct)")
    print("-" * 40)
    styles_data = test_style_transfer_service()

    # Test 2: API Gateway Styles
    print("\n2. Testing API Gateway Styles Endpoint")
    print("-" * 40)
    gateway_styles = test_api_gateway_styles()

    # Test 3: Style Preview with Dummy Image
    print("\n3. Testing Style Preview with Dummy Image")
    print("-" * 40)
    preview_results = test_style_preview_with_dummy_image()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    if styles_data:
        working_styles = list(styles_data.get('style_names', []))
        print(f"✓ Style Transfer Service: Working styles: {working_styles}")
    else:
        print("✗ Style Transfer Service: Not responding")

    if gateway_styles:
        # Handle both 'id' and 'name' fields for robustness
        gateway_style_ids = []
        for style in gateway_styles.get('styles', []):
            style_id = style.get('id') or style.get('name', 'unknown')
            gateway_style_ids.append(style_id)
        print(f"✓ API Gateway: Available styles: {gateway_style_ids}")
    else:
        print("✗ API Gateway: Not responding")

    if preview_results:
        working_previews = [style for style, result in preview_results.items() if result['success']]
        failing_previews = [style for style, result in preview_results.items() if not result['success']]

        print(f"✓ Working style previews: {working_previews}")
        if failing_previews:
            print(f"✗ Failing style previews: {failing_previews}")
            for style in failing_previews:
                print(f"  - {style}: {preview_results[style]['error']}")

    print("\n" + "=" * 60)
    print("RECOMMENDATIONS")
    print("=" * 60)

    if preview_results:
        oil_painting_result = preview_results.get('oil_painting', {})
        if oil_painting_result.get('success'):
            print("✓ Oil painting style is now working! You can add it back to the default styles.")
        else:
            print("✗ Oil painting style still failing. Keep it excluded from default styles.")
            print(f"  Error: {oil_painting_result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main()
