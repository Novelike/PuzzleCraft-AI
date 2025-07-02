# UUID/DateTime 직렬화 수정 요약

## 문제 분석

오류 로그에서 인증 서비스의 `/me` 엔드포인트가 유효성 검사 오류로 실패하는 것을 확인했습니다:

```
fastapi.exceptions.ResponseValidationError: 2 validation errors:
  {'type': 'string_type', 'loc': ('response', 'id'), 'msg': 'Input should be a valid string', 'input': UUID('c9e63600-a6ce-4d14-bd4e-d971654b26b7')}
  {'type': 'string_type', 'loc': ('response', 'created_at'), 'msg': 'Input should be a valid string', 'input': datetime.datetime(2025, 7, 2, 1, 41, 49, 216198)}
```

**근본 원인**: `/me` 엔드포인트가 `UserResponse` Pydantic 모델 인스턴스를 명시적으로 생성하는 대신 SQLAlchemy `User` 모델을 직접 반환했습니다. 이로 인해 필드 직렬화기가 우회되고 FastAPI가 문자열을 기대할 때 UUID 및 datetime 객체를 받게 되었습니다.

## 구현된 해결책

### 1. 인증 서비스의 `/me` 엔드포인트 수정

**파일**: `backend/auth-service/main.py`

**수정 전** (215번째 줄):
```python
@app.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user  # ❌ SQLAlchemy 모델의 직접 반환
```

**수정 후** (215-223번째 줄):
```python
@app.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=str(current_user.id),  # ✅ 명시적 UUID를 문자열로 변환
        username=current_user.username,
        email=current_user.email,
        profile_image_url=current_user.profile_image_url,
        level=current_user.level,
        total_points=current_user.total_points,
        created_at=current_user.created_at.isoformat() if current_user.created_at else None  # ✅ 명시적 datetime을 ISO 문자열로 변환
    )
```

### 2. UserResponse 모델 구성

`UserResponse` 모델은 이미 백업용 적절한 필드 직렬화기를 가지고 있었습니다:

```python
class UserResponse(BaseModel):
    id: str  # ✅ 문자열 타입
    username: str
    email: str
    profile_image_url: Optional[str]
    level: int
    total_points: int
    created_at: str  # ✅ 문자열 타입

    class Config:
        from_attributes = True

    @field_serializer('id')
    def serialize_id(self, value):
        """UUID를 문자열로 변환"""
        return str(value)

    @field_serializer('created_at')
    def serialize_created_at(self, value):
        """datetime을 ISO 문자열로 변환"""
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)
```

### 3. API Gateway 호환성

API Gateway의 `UserResponse` 모델은 이미 올바르게 구성되어 호환됩니다:

```python
class UserResponse(BaseModel):
    id: str  # ✅ 인증 서비스와 일치
    username: str
    email: str
    profile_image_url: Optional[str]
    level: int
    total_points: int
    created_at: str  # ✅ 인증 서비스와 일치
```

## 테스트 결과

### 단위 테스트 결과 ✅

다음 결과로 `test_pydantic_serialization.py`를 생성하고 실행했습니다:

1. **✅ 명시적 변환(우리의 수정)이 올바르게 작동**
   - UUID가 문자열로 올바르게 변환됨
   - Datetime이 ISO 문자열로 올바르게 변환됨
   - JSON 직렬화 성공

2. **✅ 기존 방식이 예상대로 실패**
   - 발생했던 정확히 동일한 유효성 검사 오류 확인
   - 우리의 수정이 근본 원인을 해결한다는 것을 검증

3. **✅ 필드 직렬화기가 백업으로 작동**
   - UUID 직렬화기가 올바르게 작동
   - Datetime 직렬화기가 올바르게 작동

## 수정 후 예상 동작

### 수정 전:
- `/me` 엔드포인트가 500 Internal Server Error 반환
- 로그에 UUID 및 datetime 타입 불일치와 함께 `ResponseValidationError` 표시

### 수정 후:
- `/me` 엔드포인트가 200 OK 반환
- 응답에 올바르게 직렬화된 데이터 포함:
  ```json
  {
    "id": "c9e63600-a6ce-4d14-bd4e-d971654b26b7",
    "username": "testuser",
    "email": "test@example.com",
    "profile_image_url": null,
    "level": 1,
    "total_points": 0,
    "created_at": "2025-07-02T01:41:49.216198"
  }
  ```

## 테스트 지침

### 1. 서비스 시작
```bash
# 인증 서비스 시작
python backend/auth-service/main.py

# API Gateway 시작 (다른 터미널에서)
python backend/api-gateway/main.py
```

### 2. 인증 서비스 직접 테스트
```bash
python test_uuid_fix.py
```

### 3. API Gateway를 통한 테스트
```bash
# API Gateway를 통한 로그인 테스트
curl -X POST "http://localhost:8000/api/v1/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"username": "your_username", "password": "your_password"}'

# API Gateway를 통한 /me 엔드포인트 테스트
curl -X GET "http://localhost:8000/api/v1/auth/me" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## 추가 참고사항

### Bcrypt 경고 (선택적 수정)
로그에서 bcrypt 버전 경고도 표시되었습니다. 다음을 실행하여 수정할 수 있습니다:
```bash
source /opt/PuzzleCraft-AI/venv/bin/activate
pip install --upgrade --force-reinstall passlib bcrypt
```

### 이 수정이 작동하는 이유
1. **명시적 변환**: UUID를 문자열로, datetime을 ISO 문자열로 수동 변환하여 Pydantic 모델이 기대하는 데이터 타입과 일치하도록 보장
2. **자동 변환 우회**: FastAPI의 자동 모델 변환이 실패했으므로 명시적으로 수행
3. **호환성 유지**: API Gateway가 `id`와 `created_at`에 대해 문자열을 기대하며, 우리의 수정이 이를 제공
4. **견고함**: 필드 직렬화기가 실패하더라도 명시적 변환이 적절한 데이터 타입을 보장

## 수정된 파일
- `backend/auth-service/main.py` - `/me` 엔드포인트 구현 수정
- 검증을 위해 생성된 테스트 파일:
  - `test_pydantic_serialization.py` - 직렬화를 위한 단위 테스트
  - `test_uuid_fix.py` - 통합 테스트 (기존)

## 상태
✅ **완료** - UUID/datetime 직렬화 문제가 해결되었습니다. 실행 중인 서비스로 테스트할 준비가 되었습니다.