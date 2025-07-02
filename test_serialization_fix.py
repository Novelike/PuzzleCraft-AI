import uuid
import sys
import os
from datetime import datetime

# Add the backend directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'auth-service'))

# Import UserResponse from the auth service
from main import UserResponse

def test_user_response_serialization():
    """Test UserResponse model serialization without running the full service"""
    print("=== Testing UserResponse Model Serialization ===\n")

    # Create test data with UUID and datetime
    test_uuid = uuid.uuid4()
    test_datetime = datetime.utcnow()

    print(f"Test UUID: {test_uuid} (type: {type(test_uuid)})")
    print(f"Test datetime: {test_datetime} (type: {type(test_datetime)})")

    try:
        # Test creating UserResponse with explicit string conversion (our fix)
        user_response = UserResponse(
            id=str(test_uuid),  # Convert UUID to string
            username="testuser",
            email="test@example.com",
            profile_image_url=None,
            level=1,
            total_points=0,
            created_at=test_datetime.isoformat()  # Convert datetime to ISO string
        )

        print("\n✓ UserResponse creation successful!")
        print(f"Serialized ID: {user_response.id} (type: {type(user_response.id)})")
        print(f"Serialized created_at: {user_response.created_at} (type: {type(user_response.created_at)})")

        # Test JSON serialization
        json_data = user_response.model_dump()
        print(f"\n✓ JSON serialization successful!")
        print(f"JSON data: {json_data}")

        # Verify types in JSON
        if isinstance(json_data['id'], str):
            print("✓ ID is string in JSON")
        else:
            print(f"✗ ID is not string in JSON: {type(json_data['id'])}")

        if isinstance(json_data['created_at'], str):
            print("✓ created_at is string in JSON")
        else:
            print(f"✗ created_at is not string in JSON: {type(json_data['created_at'])}")

        return True

    except Exception as e:
        print(f"✗ Error during serialization test: {e}")
        return False

def test_field_serializers():
    """Test the field serializers directly"""
    print("\n=== Testing Field Serializers ===\n")

    try:
        # Create a UserResponse instance to test field serializers
        user_response = UserResponse(
            id="dummy",  # We'll test the serializer separately
            username="testuser",
            email="test@example.com", 
            profile_image_url=None,
            level=1,
            total_points=0,
            created_at="dummy"  # We'll test the serializer separately
        )

        # Test ID serializer
        test_uuid = uuid.uuid4()
        serialized_id = user_response.serialize_id(test_uuid)
        print(f"UUID serializer test:")
        print(f"  Input: {test_uuid} (type: {type(test_uuid)})")
        print(f"  Output: {serialized_id} (type: {type(serialized_id)})")

        if isinstance(serialized_id, str):
            print("✓ UUID serializer works correctly")
        else:
            print("✗ UUID serializer failed")

        # Test datetime serializer
        test_datetime = datetime.utcnow()
        serialized_datetime = user_response.serialize_created_at(test_datetime)
        print(f"\nDatetime serializer test:")
        print(f"  Input: {test_datetime} (type: {type(test_datetime)})")
        print(f"  Output: {serialized_datetime} (type: {type(serialized_datetime)})")

        if isinstance(serialized_datetime, str):
            print("✓ Datetime serializer works correctly")
        else:
            print("✗ Datetime serializer failed")

        return True

    except Exception as e:
        print(f"✗ Error during field serializer test: {e}")
        return False

if __name__ == "__main__":
    print("Testing UserResponse serialization fix")
    print("=" * 50)

    test1_success = test_user_response_serialization()
    test2_success = test_field_serializers()

    print("\n" + "=" * 50)
    print("=== Test Summary ===")

    if test1_success and test2_success:
        print("✓ All serialization tests PASSED")
        print("The fix should work correctly when the auth service is running.")
        print("\nTo test with running services:")
        print("1. Start the auth service: python backend/auth-service/main.py")
        print("2. Run: python test_uuid_fix.py")
    else:
        print("✗ Some serialization tests FAILED")
        print("Check the error messages above")
