import requests
import json
import uuid

# Test the auth service functionality
def test_auth_service():
    base_url = "http://localhost:8001"
    
    # First, let's test the health endpoint
    try:
        health_response = requests.get(f"{base_url}/health")
        print(f"Health check: {health_response.status_code}")
        if health_response.status_code == 200:
            print("✓ Auth service is running")
        else:
            print("✗ Auth service might not be running")
            return
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to auth service. Make sure it's running on port 8001")
        return

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
            print(f"Access token received: {register_result.get('access_token', 'N/A')[:20]}...")
            access_token = register_result.get('access_token')
        elif response.status_code == 400:
            print("✗ Registration failed - user might already exist")
            print(f"Response: {response.text}")
            return
        elif response.status_code == 500:
            print("✗ Registration failed - server error")
            print(f"Response: {response.text}")
            return
        else:
            print(f"✗ Unexpected registration response: {response.status_code}")
            print(f"Response: {response.text}")
            return
            
    except Exception as e:
        print(f"✗ Error during registration test: {e}")
        return

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
            print(f"Access token received: {login_result.get('access_token', 'N/A')[:20]}...")
            access_token = login_result.get('access_token')
        elif response.status_code == 401:
            print("✗ Login failed - invalid credentials")
            print(f"Response: {response.text}")
            return
        elif response.status_code == 500:
            print("✗ Login failed - server error (this indicates schema mismatch)")
            print(f"Response: {response.text}")
            return
        else:
            print(f"✗ Unexpected login response: {response.status_code}")
            print(f"Response: {response.text}")
            return
            
    except Exception as e:
        print(f"✗ Error during login test: {e}")
        return

    # Test getting current user info
    print("\n=== Testing Get Current User ===")
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.get(f"{base_url}/me", headers=headers)
        print(f"Get user info response status: {response.status_code}")
        
        if response.status_code == 200:
            print("✓ Get user info successful!")
            user_info = response.json()
            print(f"User info: {json.dumps(user_info, indent=2)}")
        elif response.status_code == 401:
            print("✗ Get user info failed - unauthorized")
            print(f"Response: {response.text}")
        elif response.status_code == 500:
            print("✗ Get user info failed - server error")
            print(f"Response: {response.text}")
        else:
            print(f"✗ Unexpected get user info response: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"✗ Error during get user info test: {e}")

    print("\n=== Test Summary ===")
    print("If all tests passed, the schema mismatch issue has been resolved!")

if __name__ == "__main__":
    test_auth_service()