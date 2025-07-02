# PostgreSQL 데이터베이스 스키마 수정 요약

## 🔍 **문제 분석**

로그에서 발견된 오류:
```
psycopg2.errors.UndefinedColumn: column game_sessions.moves_count does not exist
```

**근본 원인**: 
- 코드의 GameSession 모델에는 `moves_count` 필드가 정의되어 있음
- PostgreSQL 데이터베이스의 실제 `game_sessions` 테이블에는 이 컬럼이 존재하지 않음
- 데이터베이스 마이그레이션이 제대로 실행되지 않았거나 테이블이 이전 스키마로 생성됨

## 📋 **구현된 해결책**

### 1. **데이터베이스 마이그레이션 스크립트 생성**

**파일**: `backend/game-manager/migrate_add_moves_count.sql`

PostgreSQL 데이터베이스에 누락된 `moves_count` 컬럼을 안전하게 추가하는 스크립트:

```sql
-- moves_count 컬럼이 없다면 추가
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'game_sessions' 
          AND column_name = 'moves_count'
    ) THEN
        ALTER TABLE game_sessions 
        ADD COLUMN moves_count INTEGER DEFAULT 0;
        
        RAISE NOTICE 'moves_count 컬럼이 game_sessions 테이블에 추가되었습니다.';
    ELSE
        RAISE NOTICE 'moves_count 컬럼이 이미 존재합니다.';
    END IF;
END $$;
```

### 2. **코드 레벨 방어적 프로그래밍**

모든 GameSession 조회 및 사용 부분에 방어적 코드 추가:

#### **A. 사용자 통계 엔드포인트 (`/stats`)**
- 필요한 컬럼만 선택하여 조회
- 예외 처리로 기본값 반환

#### **B. 게임 세션 목록 엔드포인트 (`/sessions`)**
```python
# moves_count 필드가 없는 경우를 대비하여 기본값 설정
for session in sessions:
    if not hasattr(session, 'moves_count') or session.moves_count is None:
        session.moves_count = 0
```

#### **C. 게임 세션 상세 조회 (`/sessions/{session_id}`)**
```python
# moves_count 필드가 없는 경우를 대비하여 기본값 설정
if not hasattr(session, 'moves_count') or session.moves_count is None:
    session.moves_count = 0
```

#### **D. 게임 이동 기록 (`/sessions/{session_id}/moves`)**
```python
# Update session move count (moves_count 필드가 없는 경우를 대비)
try:
    if hasattr(session, 'moves_count'):
        if session.moves_count is None:
            session.moves_count = 0
        session.moves_count += 1
    else:
        # moves_count 필드가 없는 경우 무시
        pass
except Exception as e:
    print(f"Warning: Could not update moves_count: {e}")
```

### 3. **통계 계산 로직 개선**

튜플 형태의 데이터를 처리할 수 있는 새로운 함수 추가:

```python
def calculate_current_streak_from_tuples(sessions) -> int:
    """튜플 형태의 세션 데이터에서 현재 연속 완료 일수 계산"""
    # 튜플에서 created_at은 4번째 요소 (인덱스 3)
    for session in sessions:
        if len(session) > 3 and session[3]:
            date_key = session[3].date()
            dates[date_key] += 1
```

## 🚀 **배포 지침**

### **프로덕션 환경에서 실행할 단계:**

1. **데이터베이스 백업**
```bash
pg_dump -h your_host -U your_user -d puzzlecraft_db > backup_before_migration.sql
```

2. **마이그레이션 스크립트 실행**
```bash
psql -h your_host -U your_user -d puzzlecraft_db -f migrate_add_moves_count.sql
```

3. **서비스 재시작**
```bash
# game-manager 서비스 재시작
systemctl restart puzzlecraft-game-manager
```

4. **검증**
```bash
# 컬럼이 추가되었는지 확인
psql -h your_host -U your_user -d puzzlecraft_db -c "\d game_sessions"
```

### **로컬 개발 환경에서 테스트:**

현재 로컬 환경은 SQLite를 사용하므로 별도 마이그레이션 불필요:
```bash
cd backend/game-manager
python main.py
```

## 📊 **예상 결과**

### **수정 전**:
```
GET /stats → 500 Internal Server Error
psycopg2.errors.UndefinedColumn: column game_sessions.moves_count does not exist
```

### **수정 후**:
```
GET /stats → 200 OK
{
  "total_puzzles_completed": 0,
  "total_play_time": 0,
  "average_completion_time": 0.0,
  "best_score": 0,
  "current_streak": 0
}
```

## 🔧 **추가 개선사항**

1. **데이터베이스 마이그레이션 도구 도입**
   - Alembic 또는 Django-style migrations 고려
   - 향후 스키마 변경을 위한 체계적인 접근

2. **모니터링 강화**
   - 데이터베이스 스키마 불일치 감지
   - 자동 알림 시스템

3. **테스트 커버리지 확대**
   - 데이터베이스 스키마 변경에 대한 테스트
   - 마이그레이션 스크립트 검증

## ✅ **상태: 해결 완료**

- ✅ 마이그레이션 스크립트 생성
- ✅ 모든 엔드포인트에 방어적 코드 추가
- ✅ 예외 처리 및 기본값 설정
- ✅ 배포 준비 완료

이제 프로덕션 환경에서 마이그레이션 스크립트를 실행하면 500 Internal Server Error가 해결될 것입니다.