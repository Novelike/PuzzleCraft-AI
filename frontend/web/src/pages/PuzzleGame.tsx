import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Clock, RotateCcw, Pause, Play, Home, Settings } from 'lucide-react'

export const PuzzleGame: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  
  const [gameState, setGameState] = useState({
    isPlaying: false,
    isPaused: false,
    timeElapsed: 0,
    completedPieces: 0,
    totalPieces: 100,
    score: 0
  })

  const [showSettings, setShowSettings] = useState(false)

  useEffect(() => {
    // TODO: 퍼즐 데이터 로드
    console.log('Loading puzzle:', id)
  }, [id])

  useEffect(() => {
    let interval: NodeJS.Timeout
    if (gameState.isPlaying && !gameState.isPaused) {
      interval = setInterval(() => {
        setGameState(prev => ({
          ...prev,
          timeElapsed: prev.timeElapsed + 1
        }))
      }, 1000)
    }
    return () => clearInterval(interval)
  }, [gameState.isPlaying, gameState.isPaused])

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  const handleStartGame = () => {
    setGameState(prev => ({ ...prev, isPlaying: true, isPaused: false }))
  }

  const handlePauseGame = () => {
    setGameState(prev => ({ ...prev, isPaused: !prev.isPaused }))
  }

  const handleResetGame = () => {
    setGameState({
      isPlaying: false,
      isPaused: false,
      timeElapsed: 0,
      completedPieces: 0,
      totalPieces: 100,
      score: 0
    })
  }

  const progress = (gameState.completedPieces / gameState.totalPieces) * 100

  return (
    <div className="min-h-screen bg-gray-100">
      {/* 게임 헤더 */}
      <div className="bg-white shadow-sm border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-6">
              <button
                onClick={() => navigate('/dashboard')}
                className="flex items-center text-gray-600 hover:text-primary-600 transition-colors"
              >
                <Home className="h-5 w-5 mr-2" />
                대시보드
              </button>
              
              <div className="flex items-center space-x-4">
                <div className="flex items-center text-gray-700">
                  <Clock className="h-5 w-5 mr-2" />
                  <span className="font-mono text-lg">{formatTime(gameState.timeElapsed)}</span>
                </div>
                
                <div className="text-gray-700">
                  진행률: {gameState.completedPieces}/{gameState.totalPieces} ({progress.toFixed(1)}%)
                </div>
                
                <div className="text-gray-700">
                  점수: {gameState.score.toLocaleString()}
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              {!gameState.isPlaying ? (
                <button onClick={handleStartGame} className="btn-primary flex items-center">
                  <Play className="h-4 w-4 mr-2" />
                  시작
                </button>
              ) : (
                <button onClick={handlePauseGame} className="btn-secondary flex items-center">
                  <Pause className="h-4 w-4 mr-2" />
                  {gameState.isPaused ? '재개' : '일시정지'}
                </button>
              )}
              
              <button onClick={handleResetGame} className="btn-secondary flex items-center">
                <RotateCcw className="h-4 w-4 mr-2" />
                재시작
              </button>
              
              <button
                onClick={() => setShowSettings(!showSettings)}
                className="btn-secondary flex items-center"
              >
                <Settings className="h-4 w-4 mr-2" />
                설정
              </button>
            </div>
          </div>

          {/* 진행률 바 */}
          <div className="mt-4">
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-primary-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              ></div>
            </div>
          </div>
        </div>
      </div>

      {/* 게임 영역 */}
      <div className="container mx-auto px-4 py-6">
        <div className="grid lg:grid-cols-4 gap-6">
          {/* 퍼즐 보드 */}
          <div className="lg:col-span-3">
            <div className="bg-white rounded-xl shadow-sm p-6">
              <div className="aspect-video bg-gray-100 rounded-lg border-2 border-dashed border-gray-300 flex items-center justify-center">
                {gameState.isPaused ? (
                  <div className="text-center">
                    <Pause className="h-16 w-16 text-gray-400 mx-auto mb-4" />
                    <p className="text-xl text-gray-600">게임이 일시정지되었습니다</p>
                    <button onClick={handlePauseGame} className="btn-primary mt-4">
                      게임 재개
                    </button>
                  </div>
                ) : !gameState.isPlaying ? (
                  <div className="text-center">
                    <Play className="h-16 w-16 text-gray-400 mx-auto mb-4" />
                    <p className="text-xl text-gray-600">게임을 시작하려면 시작 버튼을 클릭하세요</p>
                  </div>
                ) : (
                  <div className="text-center">
                    <div className="text-6xl text-gray-400 mb-4">🧩</div>
                    <p className="text-xl text-gray-600">퍼즐 게임 영역</p>
                    <p className="text-sm text-gray-500 mt-2">
                      실제 구현에서는 드래그 앤 드롭 퍼즐 인터페이스가 여기에 표시됩니다
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* 사이드바 */}
          <div className="lg:col-span-1 space-y-6">
            {/* 퍼즐 조각 트레이 */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">퍼즐 조각</h3>
              <div className="grid grid-cols-3 gap-2">
                {Array.from({ length: 9 }, (_, i) => (
                  <div
                    key={i}
                    className="aspect-square bg-gradient-to-br from-primary-100 to-purple-100 rounded-lg border border-gray-200 flex items-center justify-center text-xs text-gray-600"
                  >
                    {i + 1}
                  </div>
                ))}
              </div>
              <p className="text-xs text-gray-500 mt-2 text-center">
                조각을 드래그하여 퍼즐을 맞춰보세요
              </p>
            </div>

            {/* 힌트 */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">힌트</h3>
              <div className="space-y-3">
                <button className="w-full btn-secondary text-sm">
                  테두리 조각 표시
                </button>
                <button className="w-full btn-secondary text-sm">
                  미니맵 보기
                </button>
                <button className="w-full btn-secondary text-sm">
                  색상별 그룹화
                </button>
              </div>
            </div>

            {/* 통계 */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">통계</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">이동 횟수:</span>
                  <span className="font-medium">0</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">정확한 배치:</span>
                  <span className="font-medium">{gameState.completedPieces}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">정확도:</span>
                  <span className="font-medium">100%</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 설정 모달 */}
      {showSettings && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">게임 설정</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  음향 효과
                </label>
                <input type="checkbox" className="rounded border-gray-300 text-primary-600 focus:ring-primary-500" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  자동 저장
                </label>
                <input type="checkbox" className="rounded border-gray-300 text-primary-600 focus:ring-primary-500" defaultChecked />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  힌트 표시
                </label>
                <input type="checkbox" className="rounded border-gray-300 text-primary-600 focus:ring-primary-500" defaultChecked />
              </div>
            </div>
            <div className="flex justify-end space-x-3 mt-6">
              <button
                onClick={() => setShowSettings(false)}
                className="btn-secondary"
              >
                취소
              </button>
              <button
                onClick={() => setShowSettings(false)}
                className="btn-primary"
              >
                저장
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}