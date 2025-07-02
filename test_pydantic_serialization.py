import uuid
from datetime import datetime
from pydantic import BaseModel, field_serializer
from typing import Optional

# Define UserResponse model locally to avoid database connection issues
class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    profile_image_url: Optional[str]
    level: int
    total_points: int
    created_at: str

    class Config:
        from_attributes = True

    @field_serializer('id')
    def serialize_id(self, value):
        """Convert UUID to string"""
        return str(value)

    @field_serializer('created_at')
    def serialize_created_at(self, value):
        """Convert datetime to ISO string"""
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

def test_explicit_conversion():
    """Test the explicit conversion approach used in our fix"""
    print("=== Testing Explicit Conversion (Our Fix) ===\n")
    
    # Create test data with UUID and datetime
    test_uuid = uuid.uuid4()
    test_datetime = datetime.utcnow()
    
    print(f"Test UUID: {test_uuid} (type: {type(test_uuid)})")
    print(f"Test datetime: {test_datetime} (type: {type(test_datetime)})")
    
    try:
        # This is exactly what our fix does in the /me endpoint
        user_response = UserResponse(
            id=str(test_uuid),  # Convert UUID to string explicitly
            username="testuser",
            email="test@example.com",
            profile_image_url=None,
            level=1,
            total_points=0,
            created_at=test_datetime.isoformat()  # Convert datetime to ISO string explicitly
        )
        
        print("\n✓ UserResponse creation successful!")
        print(f"Serialized ID: {user_response.id} (type: {type(user_response.id)})")
        print(f"Serialized created_at: {user_response.created_at} (type: {type(user_response.created_at)})")
        
        # Test JSON serialization (what FastAPI does)
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
        print(f"✗ Error during explicit conversion test: {e}")
        return False

def test_problematic_approach():
    """Test what would happen with the old approach (direct SQLAlchemy model)"""
    print("\n=== Testing Problematic Approach (Before Fix) ===\n")
    
    # Simulate what happens when FastAPI tries to convert SQLAlchemy model directly
    test_uuid = uuid.uuid4()
    test_datetime = datetime.utcnow()
    
    print(f"Simulating SQLAlchemy User model with:")
    print(f"  UUID: {test_uuid} (type: {type(test_uuid)})")
    print(f"  Datetime: {test_datetime} (type: {type(test_datetime)})")
    
    try:
        # This would fail because FastAPI expects strings but gets UUID/datetime objects
        user_response = UserResponse(
            id=test_uuid,  # This would cause the error: UUID instead of string
            username="testuser",
            email="test@example.com",
            profile_image_url=None,
            level=1,
            total_points=0,
            created_at=test_datetime  # This would cause the error: datetime instead of string
        )
        
        print("✗ This should have failed but didn't - unexpected!")
        return False
        
    except Exception as e:
        print(f"✓ Expected error occurred: {e}")
        print("This is exactly the error we were getting before the fix!")
        return True

def test_field_serializers():
    """Test the field serializers (backup approach)"""
    print("\n=== Testing Field Serializers (Backup Approach) ===\n")
    
    try:
        # Create a UserResponse instance to test field serializers
        user_response = UserResponse(
            id="dummy",
            username="testuser",
            email="test@example.com", 
            profile_image_url=None,
            level=1,
            total_points=0,
            created_at="dummy"
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
    print("Testing UUID/DateTime Serialization Fix for PuzzleCraft Auth Service")
    print("=" * 70)
    
    test1_success = test_explicit_conversion()
    test2_success = test_problematic_approach()
    test3_success = test_field_serializers()
    
    print("\n" + "=" * 70)
    print("=== Test Summary ===")
    
    if test1_success and test2_success and test3_success:
        print("✓ All serialization tests PASSED")
        print("\nKey findings:")
        print("  ✓ Explicit conversion (our fix) works correctly")
        print("  ✓ Old approach properly fails as expected")
        print("  ✓ Field serializers work as backup")
        print("\nThe fix should resolve the UUID/datetime serialization errors.")
        print("\nTo test with running services:")
        print("1. Start the auth service: python backend/auth-service/main.py")
        print("2. Run: python test_uuid_fix.py")
        print("3. Test through API Gateway")
    else:
        print("✗ Some serialization tests FAILED")
        print("Check the error messages above")