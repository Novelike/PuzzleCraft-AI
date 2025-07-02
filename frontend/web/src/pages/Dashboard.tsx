import React from 'react'
import { Link } from 'react-router-dom'
import { Plus, Play, Trophy, Clock, Star, Loader2 } from 'lucide-react'
import { useUserStats } from '../hooks/useUserStats'

export const Dashboard: React.FC = () => {
  const { stats, loading, error } = useUserStats()

  // TODO: 실제 퍼즐 데이터로 교체
  const recentPuzzles = [
    { id: '1', name: '가족 사진', pieces: 100, completed: true, time: '15:30' },
    { id: '2', name: '풍경 사진', pieces: 200, completed: false, time: null },
    { id: '3', name: '반려동물', pieces: 50, completed: true, time: '08:45' }
  ]

  // 시간을 포맷하는 헬퍼 함수
  const formatTime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    if (hours > 0) {
      return `${hours}시간 ${minutes}분`
    }
    return `${minutes}분`
  }

  const formatBestTime = (seconds: number) => {
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`
  }

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
          <span className="ml-2 text-gray-600">통계를 불러오는 중...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-6xl mx-auto">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
          통계를 불러오는 중 오류가 발생했습니다: {error}
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">대시보드</h1>
        <p className="text-gray-600">퍼즐 활동을 확인하고 새로운 퍼즐을 만들어보세요</p>
      </div>

      {/* 통계 카드 */}
      <div className="grid md:grid-cols-4 gap-6 mb-8">
        <div className="card text-center">
          <Trophy className="h-8 w-8 text-yellow-500 mx-auto mb-2" />
          <div className="text-2xl font-bold text-gray-900">{stats?.total_puzzles_completed || 0}</div>
          <div className="text-sm text-gray-600">완성한 퍼즐</div>
        </div>
        <div className="card text-center">
          <Star className="h-8 w-8 text-green-500 mx-auto mb-2" />
          <div className="text-2xl font-bold text-gray-900">{stats?.current_streak || 0}</div>
          <div className="text-sm text-gray-600">연속 완성</div>
        </div>
        <div className="card text-center">
          <Clock className="h-8 w-8 text-blue-500 mx-auto mb-2" />
          <div className="text-2xl font-bold text-gray-900">
            {stats?.total_play_time ? formatTime(stats.total_play_time) : '0분'}
          </div>
          <div className="text-sm text-gray-600">총 플레이 시간</div>
        </div>
        <div className="card text-center">
          <Trophy className="h-8 w-8 text-purple-500 mx-auto mb-2" />
          <div className="text-2xl font-bold text-gray-900">
            {stats?.best_score || 0}
          </div>
          <div className="text-sm text-gray-600">최고 점수</div>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-8">
        {/* 빠른 액션 */}
        <div className="lg:col-span-1">
          <div className="card">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">빠른 액션</h2>
            <div className="space-y-3">
              <Link
                to="/puzzle/create"
                className="flex items-center p-3 bg-primary-50 rounded-lg hover:bg-primary-100 transition-colors"
              >
                <Plus className="h-5 w-5 text-primary-600 mr-3" />
                <span className="font-medium text-primary-700">새 퍼즐 만들기</span>
              </Link>
              <Link
                to="/leaderboard"
                className="flex items-center p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <Trophy className="h-5 w-5 text-gray-600 mr-3" />
                <span className="font-medium text-gray-700">리더보드 보기</span>
              </Link>
              <Link
                to="/profile"
                className="flex items-center p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <Star className="h-5 w-5 text-gray-600 mr-3" />
                <span className="font-medium text-gray-700">프로필 설정</span>
              </Link>
            </div>
          </div>
        </div>

        {/* 최근 퍼즐 */}
        <div className="lg:col-span-2">
          <div className="card">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold text-gray-900">최근 퍼즐</h2>
              <Link to="/puzzles" className="text-primary-600 hover:text-primary-700 text-sm font-medium">
                모두 보기
              </Link>
            </div>
            <div className="space-y-3">
              {recentPuzzles.map((puzzle) => (
                <div key={puzzle.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center">
                    <div className="w-12 h-12 bg-gradient-to-br from-primary-400 to-purple-500 rounded-lg mr-4"></div>
                    <div>
                      <h3 className="font-medium text-gray-900">{puzzle.name}</h3>
                      <p className="text-sm text-gray-600">{puzzle.pieces}개 조각</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-3">
                    {puzzle.completed ? (
                      <div className="text-right">
                        <div className="text-sm font-medium text-green-600">완료</div>
                        <div className="text-xs text-gray-500">{puzzle.time}</div>
                      </div>
                    ) : (
                      <div className="text-sm text-gray-500">진행 중</div>
                    )}
                    <Link
                      to={`/puzzle/play/${puzzle.id}`}
                      className="flex items-center justify-center w-8 h-8 bg-primary-600 text-white rounded-full hover:bg-primary-700 transition-colors"
                    >
                      <Play className="h-4 w-4" />
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
