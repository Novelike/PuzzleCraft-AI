import requests
import json

# Test the login functionality
def test_login():
    # First, let's test the health endpoint
    try:
        health_response = requests.get("http://localhost:8001/health")
        print(f"Health check: {health_response.status_code}")
        if health_response.status_code == 200:
            print("Auth service is running")
        else:
            print("Auth service might not be running")
            return
    except requests.exceptions.ConnectionError:
        print("Cannot connect to auth service. Make sure it's running on port 8001")
        return

    # Test login with a sample user
    login_data = {
        "username": "1",  # Using the same username from the error log
        "password": "testpassword"
    }
    
    try:
        response = requests.post("http://localhost:8001/login", json=login_data)
        print(f"Login response status: {response.status_code}")
        print(f"Login response: {response.text}")
        
        if response.status_code == 200:
            print("Login successful!")
        elif response.status_code == 401:
            print("Login failed - invalid credentials (this is expected if user doesn't exist)")
        elif response.status_code == 500:
            print("Login failed - server error (this indicates our fix might not be complete)")
        else:
            print(f"Unexpected response: {response.status_code}")
            
    except Exception as e:
        print(f"Error during login test: {e}")

if __name__ == "__main__":
    test_login()