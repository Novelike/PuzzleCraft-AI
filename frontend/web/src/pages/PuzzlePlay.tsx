import React, { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { 
  ArrowLeft, 
  Settings, 
  Share2, 
  Download, 
  RotateCcw,
  AlertCircle,
  Loader
} from 'lucide-react'

import { PuzzleGameBoard } from '../components/PuzzleGame/PuzzleGameBoard'
import { usePuzzleGame } from '../hooks/usePuzzleGame'
import { useRealTimeUpdates } from '../hooks/useRealTimeUpdates'

interface PuzzlePlayProps {}

export const PuzzlePlay: React.FC<PuzzlePlayProps> = () => {
  const { puzzleId } = useParams<{ puzzleId: string }>()
  const navigate = useNavigate()

  const [showSettings, setShowSettings] = useState(false)
  const [gameSettings, setGameSettings] = useState({
    soundEnabled: true,
    showTimer: true,
    autoSave: true,
    difficulty: 'medium'
  })

  // 퍼즐 게임 훅 사용
  const puzzleGame = usePuzzleGame({
    puzzleId: puzzleId || '',
    onGameComplete: (stats) => {
      console.log('게임 완료:', stats)
      // 게임 완료 통계 저장
      savePuzzleStats(stats)
    },
    onGameSave: (saveData) => {
      console.log('게임 저장:', saveData)
      // 자동 저장 기능
      if (gameSettings.autoSave) {
        localStorage.setItem(`puzzle_save_${puzzleId}`, JSON.stringify(saveData))
      }
    },
    onError: (error) => {
      console.error('퍼즐 게임 오류:', error)
    }
  })

  // 실시간 업데이트 훅 사용
  const realTimeUpdates = useRealTimeUpdates({
    gameId: puzzleId || '',
    onStatusChange: (status) => {
      console.log('게임 상태 업데이트:', status)
    },
    onPlayerJoin: (player) => {
      console.log('플레이어 참가:', player)
    },
    onPlayerLeave: (player) => {
      console.log('플레이어 퇴장:', player)
    }
  })

  // 컴포넌트 마운트 시 퍼즐 로드
  useEffect(() => {
    if (puzzleId) {
      loadPuzzleData()
    }
  }, [puzzleId])

  const loadPuzzleData = async () => {
    try {
      // 저장된 게임이 있는지 확인
      const savedGame = localStorage.getItem(`puzzle_save_${puzzleId}`)
      if (savedGame && gameSettings.autoSave) {
        const saveData = JSON.parse(savedGame)
        await puzzleGame.loadSavedGame(saveData)
      } else {
        await puzzleGame.loadPuzzle(puzzleId!)
      }
    } catch (error) {
      console.error('퍼즐 로드 실패:', error)
    }
  }

  const savePuzzleStats = async (stats: any) => {
    try {
      // 게임 통계를 서버에 저장
      const response = await fetch('/api/v1/puzzles/save-stats', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          puzzleId,
          stats,
          timestamp: new Date().toISOString()
        })
      })

      if (response.ok) {
        console.log('게임 통계 저장 완료')
      }
    } catch (error) {
      console.error('게임 통계 저장 실패:', error)
    }
  }

  // 게임 이벤트 핸들러들
  const handlePieceMove = useCallback((pieceId: string, position: { x: number, y: number }) => {
    puzzleGame.movePiece(pieceId, position)
  }, [puzzleGame])

  const handlePieceRotate = useCallback((pieceId: string, rotation: number) => {
    puzzleGame.rotatePiece(pieceId, rotation)
  }, [puzzleGame])

  const handlePuzzleComplete = useCallback((gameStats: any) => {
    puzzleGame.completePuzzle(gameStats)
  }, [puzzleGame])

  const handleGamePause = useCallback(() => {
    puzzleGame.pauseGame()
  }, [puzzleGame])

  const handleGameResume = useCallback(() => {
    puzzleGame.resumeGame()
  }, [puzzleGame])

  const handleBackToMenu = () => {
    if (puzzleGame.isGameActive && !puzzleGame.isCompleted) {
      const confirmLeave = window.confirm('게임이 진행 중입니다. 정말 나가시겠습니까?')
      if (!confirmLeave) return
    }
    navigate('/')
  }

  const handleRestartGame = () => {
    const confirmRestart = window.confirm('게임을 다시 시작하시겠습니까? 현재 진행상황이 초기화됩니다.')
    if (confirmRestart) {
      puzzleGame.restartGame()
    }
  }

  const handleShareGame = async () => {
    try {
      if (navigator.share) {
        await navigator.share({
          title: '퍼즐 게임 공유',
          text: '이 퍼즐 게임을 함께 플레이해보세요!',
          url: window.location.href
        })
      } else {
        // 폴백: 클립보드에 복사
        await navigator.clipboard.writeText(window.location.href)
        alert('링크가 클립보드에 복사되었습니다!')
      }
    } catch (error) {
      console.error('공유 실패:', error)
    }
  }

  const handleDownloadPuzzle = () => {
    if (puzzleGame.puzzleData?.imageUrl) {
      const link = document.createElement('a')
      link.href = puzzleGame.puzzleData.imageUrl
      link.download = `puzzle_${puzzleId}.jpg`
      link.click()
    }
  }

  const handleSettingsChange = (newSettings: typeof gameSettings) => {
    setGameSettings(newSettings)
    // 설정을 로컬 스토리지에 저장
    localStorage.setItem('puzzle_game_settings', JSON.stringify(newSettings))
  }

  // 로딩 상태
  if (puzzleGame.isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Loader className="h-12 w-12 text-blue-600 animate-spin mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">퍼즐 로딩 중...</h2>
          <p className="text-gray-600">잠시만 기다려주세요</p>
        </div>
      </div>
    )
  }

  // 에러 상태
  if (puzzleGame.error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md">
          <AlertCircle className="h-12 w-12 text-red-600 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">퍼즐 로드 실패</h2>
          <p className="text-gray-600 mb-6">{puzzleGame.error}</p>
          <div className="flex space-x-3">
            <button 
              onClick={() => window.location.reload()} 
              className="btn-secondary flex-1"
            >
              다시 시도
            </button>
            <button 
              onClick={handleBackToMenu} 
              className="btn-primary flex-1"
            >
              메인으로
            </button>
          </div>
        </div>
      </div>
    )
  }

  // 퍼즐 데이터가 없는 경우
  if (!puzzleGame.puzzleData) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-yellow-600 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">퍼즐을 찾을 수 없습니다</h2>
          <p className="text-gray-600 mb-6">요청하신 퍼즐이 존재하지 않거나 삭제되었습니다.</p>
          <button onClick={handleBackToMenu} className="btn-primary">
            메인으로 돌아가기
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* 헤더 */}
      <div className="bg-white border-b border-gray-200 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={handleBackToMenu}
              className="btn-secondary flex items-center space-x-2"
            >
              <ArrowLeft className="h-4 w-4" />
              <span>메인으로</span>
            </button>

            <div>
              <h1 className="text-lg font-semibold text-gray-900">
                퍼즐 게임
              </h1>
              <p className="text-sm text-gray-600">
                {puzzleGame.puzzleData ? 
                  `${puzzleGame.puzzleData.difficulty} 난이도 • ${puzzleGame.puzzleData.pieces.length}개 피스` : 
                  '퍼즐 정보 로딩 중...'
                }
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={handleRestartGame}
              className="btn-secondary"
              title="게임 다시 시작"
            >
              <RotateCcw className="h-4 w-4" />
            </button>

            <button
              onClick={handleShareGame}
              className="btn-secondary"
              title="게임 공유"
            >
              <Share2 className="h-4 w-4" />
            </button>

            <button
              onClick={handleDownloadPuzzle}
              className="btn-secondary"
              title="이미지 다운로드"
            >
              <Download className="h-4 w-4" />
            </button>

            <button
              onClick={() => setShowSettings(true)}
              className="btn-secondary"
              title="설정"
            >
              <Settings className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* 게임 영역 */}
      <div className="flex-1 flex">
        <div className="flex-1">
          <PuzzleGameBoard
            puzzleData={puzzleGame.puzzleData}
            onPieceMove={handlePieceMove}
            onPieceRotate={handlePieceRotate}
            onPuzzleComplete={handlePuzzleComplete}
            onGamePause={handleGamePause}
            onGameResume={handleGameResume}
          />
        </div>

        {/* 사이드바 (선택사항) - 조건부 렌더링 추가 */}
        {puzzleGame.puzzleData && (
          <div className="w-80 bg-white border-l border-gray-200 p-4 hidden lg:block">
            <div className="space-y-6">
              {/* 퍼즐 정보 */}
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-3">퍼즐 정보</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">난이도:</span>
                    <span className="font-medium capitalize">{puzzleGame.puzzleData.difficulty}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">총 피스:</span>
                    <span className="font-medium">{puzzleGame.puzzleData.pieces.length}개</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">예상 시간:</span>
                    <span className="font-medium">{puzzleGame.puzzleData.estimatedSolveTime}분</span>
                  </div>
                </div>
              </div>

              {/* 원본 이미지 미리보기 */}
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-3">원본 이미지</h3>
                <div className="aspect-square bg-gray-100 rounded-lg overflow-hidden">
                  <img
                    src={puzzleGame.puzzleData.imageUrl}
                    alt="퍼즐 원본"
                    className="w-full h-full object-cover"
                  />
                </div>
              </div>

              {/* 게임 팁 */}
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-3">게임 팁</h3>
                <div className="space-y-2 text-sm text-gray-600">
                  <p>• 모서리와 가장자리 피스부터 맞춰보세요</p>
                  <p>• 색상과 패턴이 비슷한 피스들을 그룹화하세요</p>
                  <p>• 힌트 기능을 적절히 활용하세요</p>
                  <p>• 피스를 회전시켜 올바른 방향을 찾으세요</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 설정 모달 */}
      {showSettings && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">게임 설정</h3>

            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-gray-700">사운드 효과</label>
                <input
                  type="checkbox"
                  checked={gameSettings.soundEnabled}
                  onChange={(e) => handleSettingsChange({
                    ...gameSettings,
                    soundEnabled: e.target.checked
                  })}
                  className="rounded border-gray-300"
                />
              </div>

              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-gray-700">타이머 표시</label>
                <input
                  type="checkbox"
                  checked={gameSettings.showTimer}
                  onChange={(e) => handleSettingsChange({
                    ...gameSettings,
                    showTimer: e.target.checked
                  })}
                  className="rounded border-gray-300"
                />
              </div>

              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-gray-700">자동 저장</label>
                <input
                  type="checkbox"
                  checked={gameSettings.autoSave}
                  onChange={(e) => handleSettingsChange({
                    ...gameSettings,
                    autoSave: e.target.checked
                  })}
                  className="rounded border-gray-300"
                />
              </div>
            </div>

            <div className="flex space-x-3 mt-6">
              <button
                onClick={() => setShowSettings(false)}
                className="btn-secondary flex-1"
              >
                취소
              </button>
              <button
                onClick={() => setShowSettings(false)}
                className="btn-primary flex-1"
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
