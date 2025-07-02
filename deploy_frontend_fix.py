#!/usr/bin/env python3
"""
Deployment script for frontend preview image fix
"""

import subprocess
import sys
import os
import time
from pathlib import Path

def run_command(command, cwd=None):
    """Run a command and return the result"""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            cwd=cwd, 
            capture_output=True, 
            text=True,
            timeout=60
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def check_services_running():
    """Check if required services are running"""
    print("Checking if services are running...")
    
    # Check API Gateway
    try:
        import requests
        response = requests.get("http://localhost:8000/docs", timeout=5)
        if response.status_code == 200:
            print("✓ API Gateway is running on port 8000")
            api_gateway_running = True
        else:
            print("✗ API Gateway is not responding properly")
            api_gateway_running = False
    except:
        print("✗ API Gateway is not running on port 8000")
        api_gateway_running = False
    
    # Check Style Transfer Service
    try:
        response = requests.get("http://localhost:8007/docs", timeout=5)
        if response.status_code == 200:
            print("✓ Style Transfer Service is running on port 8007")
            style_service_running = True
        else:
            print("✗ Style Transfer Service is not responding properly")
            style_service_running = False
    except:
        print("✗ Style Transfer Service is not running on port 8007")
        style_service_running = False
    
    return api_gateway_running, style_service_running

def set_environment_variables():
    """Set required environment variables"""
    print("Setting environment variables...")
    
    # For Windows
    if os.name == 'nt':
        commands = [
            'setx API_BASE_URL "https://puzzle.novelike.dev"',
            'setx STYLE_TRANSFER_URL "http://localhost:8007"'
        ]
    else:
        # For Linux/Mac
        commands = [
            'export API_BASE_URL="https://puzzle.novelike.dev"',
            'export STYLE_TRANSFER_URL="http://localhost:8007"'
        ]
    
    for cmd in commands:
        success, stdout, stderr = run_command(cmd)
        if success:
            print(f"✓ Set: {cmd}")
        else:
            print(f"⚠ Warning: Could not set environment variable: {cmd}")
            print(f"  Please set manually: {stderr}")

def restart_api_gateway():
    """Instructions for restarting API Gateway"""
    print("\nAPI Gateway Restart Instructions:")
    print("-" * 40)
    print("To apply the changes, you need to restart the API Gateway service.")
    print("This depends on how you're running the service:")
    print("")
    print("Option 1 - If running with uvicorn directly:")
    print("  1. Stop the current process (Ctrl+C)")
    print("  2. Navigate to backend/api-gateway/")
    print("  3. Run: uvicorn main:app --host 0.0.0.0 --port 8000 --reload")
    print("")
    print("Option 2 - If using Docker:")
    print("  1. docker-compose restart api-gateway")
    print("")
    print("Option 3 - If using PM2 or similar:")
    print("  1. pm2 restart api-gateway")

def verify_changes():
    """Verify that changes are working"""
    print("\nVerification Steps:")
    print("-" * 40)
    print("1. Run the test script:")
    print("   python test_frontend_integration.py")
    print("")
    print("2. Check the frontend:")
    print("   - Open the puzzle creation page")
    print("   - Upload an image")
    print("   - Click on different style preview buttons")
    print("   - Verify that preview images appear")
    print("")
    print("3. Check browser developer tools:")
    print("   - Open Network tab")
    print("   - Look for requests to /api/v1/style/preview")
    print("   - Verify response format includes 'preview_url'")
    print("   - Look for requests to /api/v1/style/image/{filename}")
    print("   - Verify images load successfully")

def main():
    """Main deployment function"""
    print("=" * 60)
    print("FRONTEND PREVIEW IMAGE FIX DEPLOYMENT")
    print("=" * 60)
    
    print("\n📋 CHANGES SUMMARY")
    print("-" * 40)
    print("✓ Modified API Gateway response format")
    print("✓ Added image serving proxy endpoint")
    print("✓ Updated both preview and apply endpoints")
    print("✓ Added proper error handling and logging")
    
    print("\n🔧 STEP 1: Check Services")
    print("-" * 40)
    api_gateway_running, style_service_running = check_services_running()
    
    if not style_service_running:
        print("\n⚠ WARNING: Style Transfer Service is not running!")
        print("Please start it first before proceeding.")
        print("Navigate to backend/style-transfer/ and run:")
        print("python main.py")
        return False
    
    print("\n🔧 STEP 2: Set Environment Variables")
    print("-" * 40)
    set_environment_variables()
    
    print("\n🔧 STEP 3: Restart API Gateway")
    print("-" * 40)
    restart_api_gateway()
    
    print("\n🔧 STEP 4: Verification")
    print("-" * 40)
    verify_changes()
    
    print("\n" + "=" * 60)
    print("EXPECTED RESULTS")
    print("=" * 60)
    print("After applying these changes:")
    print("")
    print("✓ Preview Response Format:")
    print("  {")
    print('    "preview_url": "https://puzzle.novelike.dev/api/v1/style/image/preview_image_watercolor.jpg",')
    print('    "style_type": "watercolor",')
    print('    "processing_time": 2.34,')
    print('    "success": true')
    print("  }")
    print("")
    print("✓ Frontend Behavior:")
    print("  - Style preview buttons will show actual styled images")
    print("  - Images will load through API Gateway proxy")
    print("  - No more 'Internal server error' messages")
    print("  - Smooth user experience with visual feedback")
    
    print("\n" + "=" * 60)
    print("TROUBLESHOOTING")
    print("=" * 60)
    print("If preview images still don't show:")
    print("")
    print("1. Check API_BASE_URL environment variable")
    print("   - Should match your actual domain")
    print("   - For local testing: http://localhost:8000")
    print("   - For production: https://puzzle.novelike.dev")
    print("")
    print("2. Check browser console for errors")
    print("   - CORS issues")
    print("   - Network connectivity")
    print("   - Authentication problems")
    print("")
    print("3. Verify API Gateway logs")
    print("   - Look for 'Style preview successful' messages")
    print("   - Check for any error messages")
    print("")
    print("4. Test with curl:")
    print("   curl -X GET http://localhost:8000/api/v1/style/image/test_image.jpg")

if __name__ == "__main__":
    main()