import { useState, useCallback, useRef, useEffect } from 'react'

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

interface PuzzleData {
  pieces: PuzzlePiece[]
  imageUrl: string
  difficulty: string
  estimatedSolveTime: number
  metadata?: {
    originalImageUrl?: string
    styleType?: string
    pieceCount: number
    createdAt: string
  }
}

interface GameStats {
  completionTime: number
  hintsUsed: number
  score: number
  difficulty: string
  piecesMoved: number
  piecesRotated: number
}

interface SaveData {
  puzzleId: string
  pieces: PuzzlePiece[]
  gameTime: number
  hintsUsed: number
  score: number
  lastSaved: string
}

interface UsePuzzleGameOptions {
  puzzleId: string
  onGameComplete?: (stats: GameStats) => void
  onGameSave?: (saveData: SaveData) => void
  onError?: (error: string) => void
  autoSaveInterval?: number // 자동 저장 간격 (초)
}

export const usePuzzleGame = (options: UsePuzzleGameOptions) => {
  const [puzzleData, setPuzzleData] = useState<PuzzleData | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isGameActive, setIsGameActive] = useState(false)
  const [isCompleted, setIsCompleted] = useState(false)
  const [gameStats, setGameStats] = useState<GameStats>({
    completionTime: 0,
    hintsUsed: 0,
    score: 0,
    difficulty: 'medium',
    piecesMoved: 0,
    piecesRotated: 0
  })

  const autoSaveIntervalRef = useRef<NodeJS.Timeout>()
  const gameStartTimeRef = useRef<number>(0)

  // 자동 저장 설정
  useEffect(() => {
    if (options.autoSaveInterval && isGameActive && !isCompleted) {
      autoSaveIntervalRef.current = setInterval(() => {
        saveGameState()
      }, options.autoSaveInterval * 1000)
    }

    return () => {
      if (autoSaveIntervalRef.current) {
        clearInterval(autoSaveIntervalRef.current)
      }
    }
  }, [isGameActive, isCompleted, options.autoSaveInterval])

  // 퍼즐 로드
  const loadPuzzle = useCallback(async (puzzleId: string) => {
    setIsLoading(true)
    setError(null)

    try {
      // 퍼즐 데이터 API 호출
      const response = await fetch(`/api/v1/puzzles/${puzzleId}`)
      
      if (!response.ok) {
        throw new Error(`퍼즐을 찾을 수 없습니다 (${response.status})`)
      }

      const data = await response.json()
      
      // 퍼즐 데이터 변환
      const puzzleData: PuzzleData = {
        pieces: data.pieces.map((piece: any, index: number) => ({
          ...piece,
          currentPosition: {
            x: Math.random() * 400,
            y: Math.random() * 300
          },
          isPlaced: false,
          isSelected: false,
          rotation: 0
        })),
        imageUrl: data.image_url || data.imageUrl,
        difficulty: data.difficulty || 'medium',
        estimatedSolveTime: data.estimated_solve_time || data.estimatedSolveTime || 30,
        metadata: {
          originalImageUrl: data.original_image_url,
          styleType: data.style_type,
          pieceCount: data.pieces.length,
          createdAt: data.created_at || new Date().toISOString()
        }
      }

      setPuzzleData(puzzleData)
      setIsGameActive(true)
      gameStartTimeRef.current = Date.now()
      
      setGameStats({
        completionTime: 0,
        hintsUsed: 0,
        score: 0,
        difficulty: puzzleData.difficulty,
        piecesMoved: 0,
        piecesRotated: 0
      })

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '퍼즐 로드 중 오류가 발생했습니다'
      setError(errorMessage)
      options.onError?.(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }, [options])

  // 저장된 게임 로드
  const loadSavedGame = useCallback(async (saveData: SaveData) => {
    setIsLoading(true)
    setError(null)

    try {
      // 기본 퍼즐 데이터 로드
      await loadPuzzle(saveData.puzzleId)
      
      // 저장된 상태 복원
      if (puzzleData) {
        const restoredPieces = puzzleData.pieces.map(piece => {
          const savedPiece = saveData.pieces.find(p => p.id === piece.id)
          return savedPiece ? { ...piece, ...savedPiece } : piece
        })

        setPuzzleData(prev => prev ? {
          ...prev,
          pieces: restoredPieces
        } : null)

        setGameStats(prev => ({
          ...prev,
          hintsUsed: saveData.hintsUsed,
          score: saveData.score,
          piecesMoved: prev.piecesMoved,
          piecesRotated: prev.piecesRotated
        }))

        // 게임 시간 조정
        const savedTime = saveData.gameTime
        gameStartTimeRef.current = Date.now() - (savedTime * 1000)
      }

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '저장된 게임 로드 중 오류가 발생했습니다'
      setError(errorMessage)
      options.onError?.(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }, [loadPuzzle, puzzleData, options])

  // 피스 이동
  const movePiece = useCallback((pieceId: string, position: { x: number, y: number }) => {
    if (!puzzleData || !isGameActive || isCompleted) return

    setPuzzleData(prev => {
      if (!prev) return prev

      const updatedPieces = prev.pieces.map(piece =>
        piece.id === pieceId
          ? { ...piece, currentPosition: position }
          : piece
      )

      return { ...prev, pieces: updatedPieces }
    })

    setGameStats(prev => ({
      ...prev,
      piecesMoved: prev.piecesMoved + 1
    }))
  }, [puzzleData, isGameActive, isCompleted])

  // 피스 회전
  const rotatePiece = useCallback((pieceId: string, rotation: number) => {
    if (!puzzleData || !isGameActive || isCompleted) return

    setPuzzleData(prev => {
      if (!prev) return prev

      const updatedPieces = prev.pieces.map(piece =>
        piece.id === pieceId
          ? { ...piece, rotation }
          : piece
      )

      return { ...prev, pieces: updatedPieces }
    })

    setGameStats(prev => ({
      ...prev,
      piecesRotated: prev.piecesRotated + 1
    }))
  }, [puzzleData, isGameActive, isCompleted])

  // 퍼즐 완성
  const completePuzzle = useCallback((completionStats: any) => {
    if (!isGameActive || isCompleted) return

    const completionTime = Math.floor((Date.now() - gameStartTimeRef.current) / 1000)
    
    const finalStats: GameStats = {
      ...gameStats,
      completionTime,
      score: completionStats.score || gameStats.score
    }

    setGameStats(finalStats)
    setIsCompleted(true)
    setIsGameActive(false)

    // 자동 저장 중지
    if (autoSaveIntervalRef.current) {
      clearInterval(autoSaveIntervalRef.current)
    }

    options.onGameComplete?.(finalStats)
  }, [isGameActive, isCompleted, gameStats, options])

  // 게임 일시정지
  const pauseGame = useCallback(() => {
    setIsGameActive(false)
  }, [])

  // 게임 재개
  const resumeGame = useCallback(() => {
    if (!isCompleted) {
      setIsGameActive(true)
    }
  }, [isCompleted])

  // 게임 재시작
  const restartGame = useCallback(() => {
    if (!puzzleData) return

    const resetPieces = puzzleData.pieces.map(piece => ({
      ...piece,
      currentPosition: {
        x: Math.random() * 400,
        y: Math.random() * 300
      },
      isPlaced: false,
      isSelected: false,
      rotation: 0
    }))

    setPuzzleData(prev => prev ? {
      ...prev,
      pieces: resetPieces
    } : null)

    setGameStats({
      completionTime: 0,
      hintsUsed: 0,
      score: 0,
      difficulty: puzzleData.difficulty,
      piecesMoved: 0,
      piecesRotated: 0
    })

    setIsCompleted(false)
    setIsGameActive(true)
    gameStartTimeRef.current = Date.now()
  }, [puzzleData])

  // 게임 상태 저장
  const saveGameState = useCallback(() => {
    if (!puzzleData || !isGameActive) return

    const currentTime = Math.floor((Date.now() - gameStartTimeRef.current) / 1000)
    
    const saveData: SaveData = {
      puzzleId: options.puzzleId,
      pieces: puzzleData.pieces,
      gameTime: currentTime,
      hintsUsed: gameStats.hintsUsed,
      score: gameStats.score,
      lastSaved: new Date().toISOString()
    }

    options.onGameSave?.(saveData)
  }, [puzzleData, isGameActive, gameStats, options])

  // 힌트 사용
  const useHint = useCallback(() => {
    setGameStats(prev => ({
      ...prev,
      hintsUsed: prev.hintsUsed + 1,
      score: Math.max(0, prev.score - 50) // 힌트 사용 시 점수 감점
    }))
  }, [])

  // 점수 업데이트
  const updateScore = useCallback((points: number) => {
    setGameStats(prev => ({
      ...prev,
      score: Math.max(0, prev.score + points)
    }))
  }, [])

  // 현재 게임 시간 계산
  const getCurrentGameTime = useCallback(() => {
    if (!isGameActive) return gameStats.completionTime
    return Math.floor((Date.now() - gameStartTimeRef.current) / 1000)
  }, [isGameActive, gameStats.completionTime])

  // 게임 진행률 계산
  const getGameProgress = useCallback(() => {
    if (!puzzleData) return 0
    const placedPieces = puzzleData.pieces.filter(p => p.isPlaced).length
    return (placedPieces / puzzleData.pieces.length) * 100
  }, [puzzleData])

  // 게임 통계 계산
  const getGameStatistics = useCallback(() => {
    if (!puzzleData) return null

    const totalPieces = puzzleData.pieces.length
    const placedPieces = puzzleData.pieces.filter(p => p.isPlaced).length
    const currentTime = getCurrentGameTime()
    const progress = getGameProgress()

    return {
      totalPieces,
      placedPieces,
      remainingPieces: totalPieces - placedPieces,
      progress,
      currentTime,
      estimatedTimeRemaining: puzzleData.estimatedSolveTime ? 
        Math.max(0, puzzleData.estimatedSolveTime * 60 - currentTime) : null,
      ...gameStats
    }
  }, [puzzleData, getCurrentGameTime, getGameProgress, gameStats])

  return {
    // 상태
    puzzleData,
    isLoading,
    error,
    isGameActive,
    isCompleted,
    gameStats,

    // 액션
    loadPuzzle,
    loadSavedGame,
    movePiece,
    rotatePiece,
    completePuzzle,
    pauseGame,
    resumeGame,
    restartGame,
    saveGameState,
    useHint,
    updateScore,

    // 계산된 값
    getCurrentGameTime,
    getGameProgress,
    getGameStatistics
  }
}