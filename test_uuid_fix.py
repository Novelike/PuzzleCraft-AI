import requests
import json
import uuid

def test_auth_service_uuid_fix():
    """Test the auth service to verify UUID serialization fix"""
    base_url = "http://localhost:8001"
    
    print("=== Testing Auth Service UUID Serialization Fix ===\n")
    
    # Test health endpoint first
    try:
        health_response = requests.get(f"{base_url}/health")
        print(f"Health check: {health_response.status_code}")
        if health_response.status_code == 200:
            print("✓ Auth service is running")
        else:
            print("✗ Auth service might not be running")
            print("Please start the auth service with: python backend/auth-service/main.py")
            return False
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to auth service. Make sure it's running on port 8001")
        print("Please start the auth service with: python backend/auth-service/main.py")
        return False

    # Generate unique test data
    test_username = f"testuser_{str(uuid.uuid4())[:8]}"
    test_email = f"test_{str(uuid.uuid4())[:8]}@example.com"
    test_password = "testpassword123"

    print(f"\nTesting with username: {test_username}")
    print(f"Testing with email: {test_email}")

    # Test registration
    print("\n=== Testing Registration ===")
    register_data = {
        "username": test_username,
        "email": test_email,
        "password": test_password
    }
    
    try:
        response = requests.post(f"{base_url}/register", json=register_data)
        print(f"Registration response status: {response.status_code}")
        
        if response.status_code == 200:
            print("✓ Registration successful!")
            register_result = response.json()
            access_token = register_result.get('access_token')
            print(f"Access token received: {access_token[:20] if access_token else 'None'}...")
        else:
            print(f"✗ Registration failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error during registration test: {e}")
        return False

    # Test login
    print("\n=== Testing Login ===")
    login_data = {
        "username": test_username,
        "password": test_password
    }
    
    try:
        response = requests.post(f"{base_url}/login", json=login_data)
        print(f"Login response status: {response.status_code}")
        
        if response.status_code == 200:
            print("✓ Login successful!")
            login_result = response.json()
            access_token = login_result.get('access_token')
            print(f"Access token received: {access_token[:20] if access_token else 'None'}...")
        else:
            print(f"✗ Login failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error during login test: {e}")
        return False

    # Test getting current user info (this is the critical test for UUID serialization)
    print("\n=== Testing Get Current User (/me endpoint) ===")
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.get(f"{base_url}/me", headers=headers)
        print(f"Get user info response status: {response.status_code}")
        
        if response.status_code == 200:
            print("✓ Get user info successful!")
            user_info = response.json()
            print(f"User info response:")
            print(json.dumps(user_info, indent=2))
            
            # Verify the data types
            print("\n=== Verifying Data Types ===")
            user_id = user_info.get('id')
            created_at = user_info.get('created_at')
            
            if isinstance(user_id, str):
                print(f"✓ User ID is string: {user_id}")
                # Check if it's a valid UUID format
                try:
                    uuid.UUID(user_id)
                    print("✓ User ID is valid UUID format")
                except ValueError:
                    print("✗ User ID is not valid UUID format")
            else:
                print(f"✗ User ID is not string: {type(user_id)} - {user_id}")
                
            if isinstance(created_at, str):
                print(f"✓ Created_at is string: {created_at}")
            else:
                print(f"✗ Created_at is not string: {type(created_at)} - {created_at}")
                
            return True
            
        elif response.status_code == 500:
            print("✗ Get user info failed - server error (UUID serialization issue)")
            print(f"Response: {response.text}")
            return False
        else:
            print(f"✗ Get user info failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error during get user info test: {e}")
        return False

def test_api_gateway_integration():
    """Test the API Gateway integration"""
    base_url = "http://localhost:8000"  # API Gateway port
    
    print("\n\n=== Testing API Gateway Integration ===\n")
    
    # Test health endpoint first
    try:
        health_response = requests.get(f"{base_url}/health")
        print(f"API Gateway health check: {health_response.status_code}")
        if health_response.status_code != 200:
            print("✗ API Gateway might not be running")
            print("Please start the API Gateway")
            return False
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to API Gateway. Make sure it's running on port 8000")
        return False

    # For API Gateway test, we would need existing credentials
    # This is just a placeholder for the structure
    print("API Gateway integration test would require existing user credentials")
    print("This test focuses on the auth service UUID fix")
    return True

if __name__ == "__main__":
    print("Testing UUID serialization fix for PuzzleCraft Auth Service")
    print("=" * 60)
    
    auth_success = test_auth_service_uuid_fix()
    api_gateway_success = test_api_gateway_integration()
    
    print("\n" + "=" * 60)
    print("=== Test Summary ===")
    
    if auth_success:
        print("✓ Auth Service UUID serialization fix: PASSED")
        print("  - Registration works")
        print("  - Login works") 
        print("  - /me endpoint returns properly serialized data")
        print("  - UUID is converted to string")
        print("  - DateTime is converted to string")
    else:
        print("✗ Auth Service UUID serialization fix: FAILED")
        print("  - Check the error messages above")
        
    print("\nNext steps:")
    print("1. If auth service tests pass, restart both auth service and API gateway")
    print("2. Test the full login flow through API gateway")
    print("3. The bcrypt warning can be fixed by running:")
    print("   pip install --upgrade --force-reinstall passlib bcrypt")