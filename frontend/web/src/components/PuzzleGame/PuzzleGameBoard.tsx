import React, { useState, useEffect, useRef, useCallback } from 'react'
import { 
  RotateCcw, 
  Shuffle, 
  Eye, 
  Lightbulb, 
  Pause, 
  Play, 
  SkipForward,
  Trophy,
  Clock,
  Target,
  Zap
} from 'lucide-react'

interface PuzzlePiece {
  id: string
  x: number
  y: number
  width: number
  height: number
  rotation: number
  imageData: string
  correctPosition: { x: number, y: number }
  currentPosition: { x: number, y: number }
  isPlaced: boolean
  isSelected: boolean
  edges: {
    top: 'flat' | 'knob' | 'hole'
    right: 'flat' | 'knob' | 'hole'
    bottom: 'flat' | 'knob' | 'hole'
    left: 'flat' | 'knob' | 'hole'
  }
  difficulty: 'easy' | 'medium' | 'hard'
  region: 'subject' | 'background'
}

interface GameState {
  pieces: PuzzlePiece[]
  completedPieces: number
  totalPieces: number
  gameTime: number
  isGameActive: boolean
  isPaused: boolean
  hintsUsed: number
  maxHints: number
  score: number
  difficulty: string
}

interface PuzzleGameBoardProps {
  puzzleData: {
    pieces: PuzzlePiece[]
    imageUrl: string
    difficulty: string
    estimatedSolveTime: number
  }
  onPieceMove: (pieceId: string, position: { x: number, y: number }) => void
  onPieceRotate: (pieceId: string, rotation: number) => void
  onPuzzleComplete: (gameStats: any) => void
  onGamePause: () => void
  onGameResume: () => void
}

export const PuzzleGameBoard: React.FC<PuzzleGameBoardProps> = ({
  puzzleData,
  onPieceMove,
  onPieceRotate,
  onPuzzleComplete,
  onGamePause,
  onGameResume
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const gameAreaRef = useRef<HTMLDivElement>(null)
  const [gameState, setGameState] = useState<GameState>({
    pieces: puzzleData.pieces.map(piece => ({
      ...piece,
      currentPosition: { x: Math.random() * 400, y: Math.random() * 300 },
      isPlaced: false,
      isSelected: false
    })),
    completedPieces: 0,
    totalPieces: puzzleData.pieces.length,
    gameTime: 0,
    isGameActive: true,
    isPaused: false,
    hintsUsed: 0,
    maxHints: Math.floor(puzzleData.pieces.length / 10),
    score: 0,
    difficulty: puzzleData.difficulty
  })

  const [selectedPiece, setSelectedPiece] = useState<string | null>(null)
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 })
  const [showHints, setShowHints] = useState(false)
  const [gameCompleted, setGameCompleted] = useState(false)

  // 게임 타이머
  useEffect(() => {
    let interval: NodeJS.Timeout
    if (gameState.isGameActive && !gameState.isPaused && !gameCompleted) {
      interval = setInterval(() => {
        setGameState(prev => ({
          ...prev,
          gameTime: prev.gameTime + 1
        }))
      }, 1000)
    }
    return () => {
      if (interval) clearInterval(interval)
    }
  }, [gameState.isGameActive, gameState.isPaused, gameCompleted])

  // 캔버스 렌더링
  useEffect(() => {
    if (canvasRef.current) {
      drawPuzzleBoard()
    }
  }, [gameState.pieces, selectedPiece, showHints])

  const drawPuzzleBoard = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // 캔버스 크기 설정
    const container = gameAreaRef.current
    if (container) {
      canvas.width = container.clientWidth
      canvas.height = container.clientHeight
    }

    // 배경 클리어
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    // 배경 그리드 그리기
    drawGrid(ctx, canvas.width, canvas.height)

    // 완성된 영역 표시
    drawCompletedArea(ctx)

    // 퍼즐 피스들 그리기
    gameState.pieces.forEach(piece => {
      drawPuzzlePiece(ctx, piece)
    })

    // 힌트 표시
    if (showHints) {
      drawHints(ctx)
    }
  }, [gameState.pieces, showHints])

  const drawGrid = (ctx: CanvasRenderingContext2D, width: number, height: number) => {
    ctx.strokeStyle = '#e5e7eb'
    ctx.lineWidth = 1
    
    // 세로선
    for (let x = 0; x <= width; x += 50) {
      ctx.beginPath()
      ctx.moveTo(x, 0)
      ctx.lineTo(x, height)
      ctx.stroke()
    }
    
    // 가로선
    for (let y = 0; y <= height; y += 50) {
      ctx.beginPath()
      ctx.moveTo(0, y)
      ctx.lineTo(width, y)
      ctx.stroke()
    }
  }

  const drawCompletedArea = (ctx: CanvasRenderingContext2D) => {
    // 완성된 퍼즐 영역을 하이라이트
    const completedPieces = gameState.pieces.filter(p => p.isPlaced)
    
    completedPieces.forEach(piece => {
      ctx.fillStyle = 'rgba(34, 197, 94, 0.1)'
      ctx.fillRect(
        piece.correctPosition.x - 2,
        piece.correctPosition.y - 2,
        piece.width + 4,
        piece.height + 4
      )
    })
  }

  const drawPuzzlePiece = (ctx: CanvasRenderingContext2D, piece: PuzzlePiece) => {
    const { currentPosition, width, height, rotation, isSelected, isPlaced } = piece

    ctx.save()
    
    // 피스 위치로 이동
    ctx.translate(currentPosition.x + width / 2, currentPosition.y + height / 2)
    ctx.rotate((rotation * Math.PI) / 180)
    
    // 피스 배경
    ctx.fillStyle = isPlaced ? '#dcfce7' : isSelected ? '#dbeafe' : '#ffffff'
    ctx.strokeStyle = isSelected ? '#3b82f6' : isPlaced ? '#16a34a' : '#d1d5db'
    ctx.lineWidth = isSelected ? 3 : 1
    
    // 피스 모양 그리기 (간단한 직사각형으로 시작)
    ctx.fillRect(-width / 2, -height / 2, width, height)
    ctx.strokeRect(-width / 2, -height / 2, width, height)
    
    // 피스 ID 표시 (디버그용)
    if (isSelected) {
      ctx.fillStyle = '#1f2937'
      ctx.font = '12px Arial'
      ctx.textAlign = 'center'
      ctx.fillText(piece.id, 0, 0)
    }
    
    ctx.restore()
  }

  const drawHints = (ctx: CanvasRenderingContext2D) => {
    gameState.pieces.forEach(piece => {
      if (!piece.isPlaced) {
        // 올바른 위치에 반투명 가이드 표시
        ctx.fillStyle = 'rgba(59, 130, 246, 0.3)'
        ctx.strokeStyle = '#3b82f6'
        ctx.lineWidth = 2
        ctx.setLineDash([5, 5])
        
        ctx.fillRect(
          piece.correctPosition.x,
          piece.correctPosition.y,
          piece.width,
          piece.height
        )
        ctx.strokeRect(
          piece.correctPosition.x,
          piece.correctPosition.y,
          piece.width,
          piece.height
        )
        
        ctx.setLineDash([])
      }
    })
  }

  // 마우스 이벤트 핸들러
  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return

    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top

    // 클릭된 피스 찾기
    const clickedPiece = gameState.pieces.find(piece => {
      const { currentPosition, width, height } = piece
      return x >= currentPosition.x && x <= currentPosition.x + width &&
             y >= currentPosition.y && y <= currentPosition.y + height
    })

    if (clickedPiece && !clickedPiece.isPlaced) {
      setSelectedPiece(clickedPiece.id)
      setDragOffset({
        x: x - clickedPiece.currentPosition.x,
        y: y - clickedPiece.currentPosition.y
      })
      
      // 선택된 피스를 맨 앞으로
      setGameState(prev => ({
        ...prev,
        pieces: prev.pieces.map(p => ({
          ...p,
          isSelected: p.id === clickedPiece.id
        }))
      }))
    } else {
      setSelectedPiece(null)
      setGameState(prev => ({
        ...prev,
        pieces: prev.pieces.map(p => ({ ...p, isSelected: false }))
      }))
    }
  }, [gameState.pieces])

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!selectedPiece) return

    const canvas = canvasRef.current
    if (!canvas) return

    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left - dragOffset.x
    const y = e.clientY - rect.top - dragOffset.y

    setGameState(prev => ({
      ...prev,
      pieces: prev.pieces.map(piece =>
        piece.id === selectedPiece
          ? { ...piece, currentPosition: { x, y } }
          : piece
      )
    }))

    onPieceMove(selectedPiece, { x, y })
  }, [selectedPiece, dragOffset, onPieceMove])

  const handleMouseUp = useCallback(() => {
    if (!selectedPiece) return

    const piece = gameState.pieces.find(p => p.id === selectedPiece)
    if (!piece) return

    // 스냅 거리 계산
    const snapDistance = 30
    const distanceToCorrect = Math.sqrt(
      Math.pow(piece.currentPosition.x - piece.correctPosition.x, 2) +
      Math.pow(piece.currentPosition.y - piece.correctPosition.y, 2)
    )

    if (distanceToCorrect < snapDistance) {
      // 올바른 위치에 스냅
      setGameState(prev => {
        const updatedPieces = prev.pieces.map(p =>
          p.id === selectedPiece
            ? {
                ...p,
                currentPosition: p.correctPosition,
                isPlaced: true,
                isSelected: false
              }
            : p
        )

        const newCompletedCount = updatedPieces.filter(p => p.isPlaced).length
        const newScore = calculateScore(newCompletedCount, prev.gameTime, prev.hintsUsed)

        // 퍼즐 완성 체크
        if (newCompletedCount === prev.totalPieces) {
          setGameCompleted(true)
          onPuzzleComplete({
            completionTime: prev.gameTime,
            hintsUsed: prev.hintsUsed,
            score: newScore,
            difficulty: prev.difficulty
          })
        }

        return {
          ...prev,
          pieces: updatedPieces,
          completedPieces: newCompletedCount,
          score: newScore
        }
      })
    } else {
      // 선택 해제
      setGameState(prev => ({
        ...prev,
        pieces: prev.pieces.map(p => ({ ...p, isSelected: false }))
      }))
    }

    setSelectedPiece(null)
  }, [selectedPiece, gameState.pieces, onPuzzleComplete])

  const calculateScore = (completed: number, time: number, hints: number) => {
    const baseScore = completed * 100
    const timeBonus = Math.max(0, 1000 - time)
    const hintPenalty = hints * 50
    return Math.max(0, baseScore + timeBonus - hintPenalty)
  }

  // 게임 컨트롤 함수들
  const handleRotatePiece = () => {
    if (!selectedPiece) return
    
    setGameState(prev => ({
      ...prev,
      pieces: prev.pieces.map(piece =>
        piece.id === selectedPiece
          ? { ...piece, rotation: (piece.rotation + 90) % 360 }
          : piece
      )
    }))
    
    const piece = gameState.pieces.find(p => p.id === selectedPiece)
    if (piece) {
      onPieceRotate(selectedPiece, (piece.rotation + 90) % 360)
    }
  }

  const handleShufflePieces = () => {
    setGameState(prev => ({
      ...prev,
      pieces: prev.pieces.map(piece => ({
        ...piece,
        currentPosition: {
          x: Math.random() * 400,
          y: Math.random() * 300
        },
        rotation: Math.floor(Math.random() * 4) * 90,
        isPlaced: false,
        isSelected: false
      })),
      completedPieces: 0
    }))
  }

  const handleShowHints = () => {
    if (gameState.hintsUsed < gameState.maxHints) {
      setShowHints(true)
      setGameState(prev => ({
        ...prev,
        hintsUsed: prev.hintsUsed + 1
      }))
      
      // 3초 후 힌트 숨기기
      setTimeout(() => setShowHints(false), 3000)
    }
  }

  const handlePauseResume = () => {
    if (gameState.isPaused) {
      setGameState(prev => ({ ...prev, isPaused: false }))
      onGameResume()
    } else {
      setGameState(prev => ({ ...prev, isPaused: true }))
      onGamePause()
    }
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="flex flex-col h-full">
      {/* 게임 헤더 */}
      <div className="bg-white border-b border-gray-200 p-4">
        <div className="flex items-center justify-between">
          {/* 게임 정보 */}
          <div className="flex items-center space-x-6">
            <div className="flex items-center space-x-2">
              <Target className="h-5 w-5 text-blue-600" />
              <span className="text-sm font-medium">
                {gameState.completedPieces}/{gameState.totalPieces} 완성
              </span>
            </div>
            
            <div className="flex items-center space-x-2">
              <Clock className="h-5 w-5 text-green-600" />
              <span className="text-sm font-medium">{formatTime(gameState.gameTime)}</span>
            </div>
            
            <div className="flex items-center space-x-2">
              <Trophy className="h-5 w-5 text-yellow-600" />
              <span className="text-sm font-medium">{gameState.score}점</span>
            </div>
          </div>

          {/* 게임 컨트롤 */}
          <div className="flex items-center space-x-2">
            <button
              onClick={handleRotatePiece}
              disabled={!selectedPiece}
              className="btn-secondary disabled:opacity-50"
              title="선택된 피스 회전"
            >
              <RotateCcw className="h-4 w-4" />
            </button>
            
            <button
              onClick={handleShufflePieces}
              className="btn-secondary"
              title="피스 섞기"
            >
              <Shuffle className="h-4 w-4" />
            </button>
            
            <button
              onClick={handleShowHints}
              disabled={gameState.hintsUsed >= gameState.maxHints}
              className="btn-secondary disabled:opacity-50"
              title={`힌트 보기 (${gameState.hintsUsed}/${gameState.maxHints})`}
            >
              <Lightbulb className="h-4 w-4" />
            </button>
            
            <button
              onClick={handlePauseResume}
              className="btn-primary"
            >
              {gameState.isPaused ? (
                <Play className="h-4 w-4" />
              ) : (
                <Pause className="h-4 w-4" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* 게임 영역 */}
      <div 
        ref={gameAreaRef}
        className="flex-1 relative bg-gray-50 overflow-hidden"
      >
        <canvas
          ref={canvasRef}
          className="absolute inset-0 cursor-pointer"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
        />
        
        {/* 일시정지 오버레이 */}
        {gameState.isPaused && (
          <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center">
            <div className="bg-white rounded-lg p-6 text-center">
              <Pause className="h-12 w-12 text-gray-600 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">게임 일시정지</h3>
              <p className="text-gray-600 mb-4">계속하려면 재생 버튼을 클릭하세요</p>
              <button onClick={handlePauseResume} className="btn-primary">
                <Play className="h-4 w-4 mr-2" />
                계속하기
              </button>
            </div>
          </div>
        )}

        {/* 완성 축하 오버레이 */}
        {gameCompleted && (
          <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center">
            <div className="bg-white rounded-lg p-8 text-center max-w-md">
              <Trophy className="h-16 w-16 text-yellow-500 mx-auto mb-4" />
              <h3 className="text-2xl font-bold text-gray-900 mb-2">축하합니다!</h3>
              <p className="text-gray-600 mb-4">퍼즐을 완성했습니다!</p>
              
              <div className="bg-gray-50 rounded-lg p-4 mb-6">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600">완성 시간:</span>
                    <div className="font-semibold">{formatTime(gameState.gameTime)}</div>
                  </div>
                  <div>
                    <span className="text-gray-600">최종 점수:</span>
                    <div className="font-semibold">{gameState.score}점</div>
                  </div>
                  <div>
                    <span className="text-gray-600">사용한 힌트:</span>
                    <div className="font-semibold">{gameState.hintsUsed}개</div>
                  </div>
                  <div>
                    <span className="text-gray-600">난이도:</span>
                    <div className="font-semibold capitalize">{gameState.difficulty}</div>
                  </div>
                </div>
              </div>
              
              <div className="flex space-x-3">
                <button 
                  onClick={() => window.location.reload()} 
                  className="btn-secondary flex-1"
                >
                  다시 플레이
                </button>
                <button 
                  onClick={() => window.history.back()} 
                  className="btn-primary flex-1"
                >
                  새 퍼즐
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 진행률 바 */}
      <div className="bg-white border-t border-gray-200 p-2">
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div 
            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
            style={{ 
              width: `${(gameState.completedPieces / gameState.totalPieces) * 100}%` 
            }}
          />
        </div>
        <div className="text-xs text-gray-600 mt-1 text-center">
          {Math.round((gameState.completedPieces / gameState.totalPieces) * 100)}% 완성
        </div>
      </div>
    </div>
  )
}