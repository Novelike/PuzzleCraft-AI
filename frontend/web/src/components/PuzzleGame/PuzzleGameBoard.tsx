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
import { PuzzlePiece } from '../../types/puzzle'

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
  } | null
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
  // puzzleData가 null인 경우 early return
  if (!puzzleData) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="text-6xl text-gray-400 mb-4">🧩</div>
          <p className="text-xl text-gray-600">퍼즐 데이터를 로딩 중...</p>
          <p className="text-sm text-gray-500 mt-2">잠시만 기다려주세요</p>
        </div>
      </div>
    )
  }

  const canvasRef = useRef<HTMLCanvasElement>(null)
  const gameAreaRef = useRef<HTMLDivElement>(null)
  const imageCache = useRef<Map<string, HTMLImageElement>>(new Map())
  const [imagesLoaded, setImagesLoaded] = useState(false)

  const [gameState, setGameState] = useState<GameState>({
    pieces: puzzleData.pieces.map((piece, index) => ({
      ...piece,
      currentPosition: { x: Math.random() * 400, y: Math.random() * 300 },
      isPlaced: false,
      isSelected: false,
      zIndex: index,
      connectedPieces: []
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

  // 컴포넌트 마운트 시 디버깅 로그
  useEffect(() => {
    console.log('🎮 PuzzleGameBoard 마운트됨')
    console.log('📊 puzzleData:', puzzleData)
    console.log('🧩 pieces 개수:', puzzleData?.pieces?.length || 0)

    if (puzzleData?.pieces) {
      const piecesWithImages = puzzleData.pieces.filter(p => p.imageData && p.imageData.trim() !== '')
      console.log(`🖼️ 이미지 데이터가 있는 피스: ${piecesWithImages.length}/${puzzleData.pieces.length}`)

      // 첫 번째 피스의 이미지 데이터 샘플 확인
      if (piecesWithImages.length > 0) {
        const firstPiece = piecesWithImages[0]
        console.log('🔍 첫 번째 피스 이미지 데이터 샘플:', firstPiece.imageData.substring(0, 100) + '...')
      }
    }
  }, [puzzleData])

  // 이미지 로딩
  useEffect(() => {
    const loadImages = async () => {
      console.log('🖼️ 퍼즐 피스 이미지 로딩 시작')
      const loadPromises: Promise<void>[] = []

      gameState.pieces.forEach(piece => {
        if (piece.imageData && typeof piece.imageData === 'string') {
          const loadPromise = new Promise<void>((resolve, reject) => {
            const img = new Image()
            img.onload = () => {
              imageCache.current.set(piece.id, img)
              console.log(`✅ 이미지 로드 완료: ${piece.id}`)
              resolve()
            }
            img.onerror = (error) => {
              console.warn(`❌ 이미지 로드 실패: ${piece.id}`, error)
              console.warn(`❌ 실패한 이미지 데이터 샘플:`, piece.imageData.substring(0, 100))
              resolve() // 실패해도 계속 진행
            }
            img.src = piece.imageData
          })
          loadPromises.push(loadPromise)
        } else {
          console.warn(`⚠️ 피스 ${piece.id}에 이미지 데이터가 없습니다`)
        }
      })

      try {
        await Promise.all(loadPromises)
        console.log('🎉 모든 퍼즐 피스 이미지 로딩 완료')
        setImagesLoaded(true)
      } catch (error) {
        console.error('❌ 이미지 로딩 중 오류:', error)
        setImagesLoaded(true) // 오류가 있어도 게임 시작
      }
    }

    if (gameState.pieces.length > 0) {
      loadImages()
    }
  }, [gameState.pieces])

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
  }, [gameState.pieces, selectedPiece, showHints, imagesLoaded])

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
    // drawCompletedArea(ctx) // 제거됨 - 머지 모드에서는 사용하지 않음

    // 퍼즐 피스들 그리기 (zIndex 순으로 정렬)
    const sortedPieces = [...gameState.pieces].sort((a, b) => a.zIndex - b.zIndex)
    sortedPieces.forEach(piece => {
      drawPuzzlePiece(ctx, piece)
    })

    // 힌트 표시
    if (showHints) {
      drawHints(ctx)
    }
  }, [gameState.pieces, showHints, imagesLoaded])

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
    const { currentPosition, width, height, rotation, isSelected, isPlaced, imageData, edges } = piece

    ctx.save()

    // 피스 위치로 이동
    ctx.translate(currentPosition.x + width / 2, currentPosition.y + height / 2)
    ctx.rotate((rotation * Math.PI) / 180)

    // 피스 테두리 스타일
    ctx.strokeStyle = isSelected ? '#3b82f6' : isPlaced ? '#16a34a' : '#d1d5db'
    ctx.lineWidth = isSelected ? 3 : 1

    try {
      // 실제 퍼즐 조각 모양 그리기
      const puzzleShape = generatePuzzleShape(width, height, edges)

      // 클리핑 패스 설정 (퍼즐 조각 모양으로 자르기)
      ctx.beginPath()
      puzzleShape.forEach((point, index) => {
        if (index === 0) {
          ctx.moveTo(point.x - width / 2, point.y - height / 2)
        } else {
          ctx.lineTo(point.x - width / 2, point.y - height / 2)
        }
      })
      ctx.closePath()

      // 캐시된 이미지 사용
      const cachedImage = imageCache.current.get(piece.id)

      if (cachedImage && imagesLoaded) {
        // 퍼즐 조각 모양으로 클리핑
        ctx.clip()

        // 캐시된 이미지 그리기
        ctx.drawImage(cachedImage, -width / 2, -height / 2, width, height)

        // 클리핑 해제를 위해 새로운 패스 시작
        ctx.restore()
        ctx.save()
        ctx.translate(currentPosition.x + width / 2, currentPosition.y + height / 2)
        ctx.rotate((rotation * Math.PI) / 180)

        // 퍼즐 조각 테두리 그리기
        ctx.beginPath()
        puzzleShape.forEach((point, index) => {
          if (index === 0) {
            ctx.moveTo(point.x - width / 2, point.y - height / 2)
          } else {
            ctx.lineTo(point.x - width / 2, point.y - height / 2)
          }
        })
        ctx.closePath()
        ctx.stroke()

        // 배치된 피스에 반투명 오버레이 (제거됨 - 머지 모드에서는 사용하지 않음)
        // if (isPlaced) {
        //   ctx.fillStyle = 'rgba(34, 197, 94, 0.2)'
        //   ctx.fill()
        // }

        // 선택된 피스에 하이라이트
        if (isSelected) {
          ctx.fillStyle = 'rgba(59, 130, 246, 0.3)'
          ctx.fill()
        }
      } else {
        // 이미지가 로드되지 않았거나 캐시에 없는 경우 폴백
        drawFallbackPiece(ctx, piece, width, height)

        // 로딩 인디케이터 표시
        if (!imagesLoaded) {
          ctx.fillStyle = 'rgba(0, 0, 0, 0.1)'
          ctx.fill()

          ctx.fillStyle = '#6b7280'
          ctx.font = '12px Arial'
          ctx.textAlign = 'center'
          ctx.fillText('로딩중...', 0, 0)
        }
      }
    } catch (error) {
      console.warn('퍼즐 피스 이미지 렌더링 실패:', error)
      drawFallbackPiece(ctx, piece, width, height)
    }

    ctx.restore()
  }

  const drawFallbackPiece = (ctx: CanvasRenderingContext2D, piece: PuzzlePiece, width: number, height: number) => {
    const { isSelected, isPlaced, region } = piece

    // 폴백 배경색 (피사체/배경에 따라 다른 색상)
    ctx.fillStyle = region === 'subject' ? '#fef3c7' : '#e0f2fe'
    ctx.fillRect(-width / 2, -height / 2, width, height)

    // 상태에 따른 오버레이 (isPlaced 제거됨 - 머지 모드에서는 사용하지 않음)
    // if (isPlaced) {
    //   ctx.fillStyle = 'rgba(34, 197, 94, 0.3)'
    //   ctx.fillRect(-width / 2, -height / 2, width, height)
    // } else 
    if (isSelected) {
      ctx.fillStyle = 'rgba(59, 130, 246, 0.3)'
      ctx.fillRect(-width / 2, -height / 2, width, height)
    }

    // 테두리
    ctx.strokeRect(-width / 2, -height / 2, width, height)

    // 피스 정보 표시 (디버그용)
    ctx.fillStyle = '#374151'
    ctx.font = '10px Arial'
    ctx.textAlign = 'center'
    ctx.fillText(piece.id.slice(-3), 0, -5)
    ctx.fillText(region, 0, 8)
  }

  // 퍼즐 조각 모양 생성 함수
  const generatePuzzleShape = (width: number, height: number, edges: any) => {
    const points: { x: number, y: number }[] = []
    const tabSize = 0.25 // 탭 크기 (조각 크기의 25%)
    const tabDepth = 0.15 // 탭 깊이

    // edges가 없는 경우 기본값 설정
    const safeEdges = edges || {
      top: 'flat',
      right: 'flat', 
      bottom: 'flat',
      left: 'flat'
    }

    // 시작점 (왼쪽 상단)
    let currentX = 0
    let currentY = 0

    // 상단 가장자리
    points.push({ x: currentX, y: currentY })

    if (safeEdges.top === 'tab' || safeEdges.top === 'knob') {
      // 상단에 튀어나온 탭
      const tabStart = width * 0.3
      const tabEnd = width * 0.7
      const tabHeight = height * tabDepth

      points.push({ x: tabStart, y: currentY })
      points.push({ x: tabStart, y: currentY - tabHeight })
      points.push({ x: tabEnd, y: currentY - tabHeight })
      points.push({ x: tabEnd, y: currentY })
    } else if (safeEdges.top === 'blank' || safeEdges.top === 'hole') {
      // 상단에 들어간 홈
      const tabStart = width * 0.3
      const tabEnd = width * 0.7
      const tabHeight = height * tabDepth

      points.push({ x: tabStart, y: currentY })
      points.push({ x: tabStart, y: currentY + tabHeight })
      points.push({ x: tabEnd, y: currentY + tabHeight })
      points.push({ x: tabEnd, y: currentY })
    }
    // flat인 경우는 직선으로 처리 (추가 점 없음)

    // 우상단 모서리
    currentX = width
    points.push({ x: currentX, y: currentY })

    // 우측 가장자리
    if (safeEdges.right === 'tab' || safeEdges.right === 'knob') {
      // 우측에 튀어나온 탭
      const tabStart = height * 0.3
      const tabEnd = height * 0.7
      const tabWidth = width * tabDepth

      points.push({ x: currentX, y: tabStart })
      points.push({ x: currentX + tabWidth, y: tabStart })
      points.push({ x: currentX + tabWidth, y: tabEnd })
      points.push({ x: currentX, y: tabEnd })
    } else if (safeEdges.right === 'blank' || safeEdges.right === 'hole') {
      // 우측에 들어간 홈
      const tabStart = height * 0.3
      const tabEnd = height * 0.7
      const tabWidth = width * tabDepth

      points.push({ x: currentX, y: tabStart })
      points.push({ x: currentX - tabWidth, y: tabStart })
      points.push({ x: currentX - tabWidth, y: tabEnd })
      points.push({ x: currentX, y: tabEnd })
    }

    // 우하단 모서리
    currentY = height
    points.push({ x: currentX, y: currentY })

    // 하단 가장자리
    if (safeEdges.bottom === 'tab' || safeEdges.bottom === 'knob') {
      // 하단에 튀어나온 탭
      const tabStart = width * 0.7
      const tabEnd = width * 0.3
      const tabHeight = height * tabDepth

      points.push({ x: tabStart, y: currentY })
      points.push({ x: tabStart, y: currentY + tabHeight })
      points.push({ x: tabEnd, y: currentY + tabHeight })
      points.push({ x: tabEnd, y: currentY })
    } else if (safeEdges.bottom === 'blank' || safeEdges.bottom === 'hole') {
      // 하단에 들어간 홈
      const tabStart = width * 0.7
      const tabEnd = width * 0.3
      const tabHeight = height * tabDepth

      points.push({ x: tabStart, y: currentY })
      points.push({ x: tabStart, y: currentY - tabHeight })
      points.push({ x: tabEnd, y: currentY - tabHeight })
      points.push({ x: tabEnd, y: currentY })
    }

    // 좌하단 모서리
    currentX = 0
    points.push({ x: currentX, y: currentY })

    // 좌측 가장자리
    if (safeEdges.left === 'tab' || safeEdges.left === 'knob') {
      // 좌측에 튀어나온 탭
      const tabStart = height * 0.7
      const tabEnd = height * 0.3
      const tabWidth = width * tabDepth

      points.push({ x: currentX, y: tabStart })
      points.push({ x: currentX - tabWidth, y: tabStart })
      points.push({ x: currentX - tabWidth, y: tabEnd })
      points.push({ x: currentX, y: tabEnd })
    } else if (safeEdges.left === 'blank' || safeEdges.left === 'hole') {
      // 좌측에 들어간 홈
      const tabStart = height * 0.7
      const tabEnd = height * 0.3
      const tabWidth = width * tabDepth

      points.push({ x: currentX, y: tabStart })
      points.push({ x: currentX + tabWidth, y: tabStart })
      points.push({ x: currentX + tabWidth, y: tabEnd })
      points.push({ x: currentX, y: tabEnd })
    }

    return points
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

  // 연결된 조각 그룹 찾기
  const getConnectedGroup = (pieceId: string, pieces: PuzzlePiece[]): string[] => {
    const visited = new Set<string>()
    const group: string[] = []

    const dfs = (currentId: string) => {
      if (visited.has(currentId)) return
      visited.add(currentId)
      group.push(currentId)

      const currentPiece = pieces.find(p => p.id === currentId)
      if (currentPiece) {
        currentPiece.connectedPieces.forEach(connectedId => {
          if (!visited.has(connectedId)) {
            dfs(connectedId)
          }
        })
      }
    }

    dfs(pieceId)
    return group
  }

  // 두 조각이 연결 가능한지 확인
  const canConnect = (piece1: PuzzlePiece, piece2: PuzzlePiece): boolean => {
    const distance = Math.sqrt(
      Math.pow(piece1.currentPosition.x - piece2.currentPosition.x, 2) +
      Math.pow(piece1.currentPosition.y - piece2.currentPosition.y, 2)
    )

    const connectionDistance = 50 // 연결 가능한 거리

    if (distance > connectionDistance) return false

    // edges 정보가 있는 경우 실제 퍼즐 조각 호환성 체크
    if (piece1.edges && piece2.edges) {
      return checkEdgeCompatibility(piece1, piece2)
    }

    // edges 정보가 없는 경우 기존 그리드 기반 로직 사용
    const piece1Grid = piece1.id.split('_')[1] ? parseInt(piece1.id.split('_')[1]) : 0
    const piece2Grid = piece2.id.split('_')[1] ? parseInt(piece2.id.split('_')[1]) : 0

    const gridCols = Math.sqrt(gameState.totalPieces)
    const piece1Row = Math.floor(piece1Grid / gridCols)
    const piece1Col = piece1Grid % gridCols
    const piece2Row = Math.floor(piece2Grid / gridCols)
    const piece2Col = piece2Grid % gridCols

    const isAdjacent = (
      (Math.abs(piece1Row - piece2Row) === 1 && piece1Col === piece2Col) ||
      (Math.abs(piece1Col - piece2Col) === 1 && piece1Row === piece2Row)
    )

    return isAdjacent
  }

  // 두 조각의 edges 호환성 체크
  const checkEdgeCompatibility = (piece1: PuzzlePiece, piece2: PuzzlePiece): boolean => {
    const pos1 = piece1.currentPosition
    const pos2 = piece2.currentPosition
    const w1 = piece1.width
    const h1 = piece1.height
    const w2 = piece2.width
    const h2 = piece2.height

    // 두 조각이 어느 방향으로 인접한지 확인
    const deltaX = pos2.x - pos1.x
    const deltaY = pos2.y - pos1.y

    // 우측 연결 (piece1의 right와 piece2의 left)
    if (Math.abs(deltaX - w1) < 20 && Math.abs(deltaY) < 20) {
      return isEdgeCompatible(piece1.edges.right, piece2.edges.left)
    }

    // 좌측 연결 (piece1의 left와 piece2의 right)
    if (Math.abs(deltaX + w2) < 20 && Math.abs(deltaY) < 20) {
      return isEdgeCompatible(piece1.edges.left, piece2.edges.right)
    }

    // 하단 연결 (piece1의 bottom과 piece2의 top)
    if (Math.abs(deltaY - h1) < 20 && Math.abs(deltaX) < 20) {
      return isEdgeCompatible(piece1.edges.bottom, piece2.edges.top)
    }

    // 상단 연결 (piece1의 top과 piece2의 bottom)
    if (Math.abs(deltaY + h2) < 20 && Math.abs(deltaX) < 20) {
      return isEdgeCompatible(piece1.edges.top, piece2.edges.bottom)
    }

    return false
  }

  // 두 edge가 호환되는지 확인 (tab과 blank이 맞아야 함)
  const isEdgeCompatible = (edge1: string, edge2: string): boolean => {
    if (edge1 === 'flat' || edge2 === 'flat') return false
    return (edge1 === 'tab' && edge2 === 'blank') || (edge1 === 'blank' && edge2 === 'tab')
  }

  // 마우스 이벤트 핸들러
  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return

    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top

    // 클릭된 피스 찾기 (회전 상태 고려)
    const clickedPiece = gameState.pieces.find(piece => {
      const { currentPosition, width, height, rotation } = piece
      // 회전 상태에 따른 실제 width/height 계산
      const w = (rotation % 180 === 0) ? width : height
      const h = (rotation % 180 === 0) ? height : width
      return x >= currentPosition.x && x <= currentPosition.x + w &&
             y >= currentPosition.y && y <= currentPosition.y + h
    })

    if (clickedPiece && !clickedPiece.isPlaced) {
      setSelectedPiece(clickedPiece.id)
      setDragOffset({
        x: x - clickedPiece.currentPosition.x,
        y: y - clickedPiece.currentPosition.y
      })

      // 선택된 피스를 맨 앞으로 이동 (zIndex 업데이트)
      setGameState(prev => {
        const maxZIndex = Math.max(...prev.pieces.map(p => p.zIndex))
        const connectedGroup = getConnectedGroup(clickedPiece.id, prev.pieces)

        return {
          ...prev,
          pieces: prev.pieces.map(p => {
            if (connectedGroup.includes(p.id)) {
              // 연결된 그룹 전체를 맨 앞으로
              return {
                ...p,
                isSelected: p.id === clickedPiece.id,
                zIndex: maxZIndex + 1 + connectedGroup.indexOf(p.id)
              }
            }
            return {
              ...p,
              isSelected: false
            }
          })
        }
      })
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
    const newX = e.clientX - rect.left - dragOffset.x
    const newY = e.clientY - rect.top - dragOffset.y

    setGameState(prev => {
      const selectedPieceData = prev.pieces.find(p => p.id === selectedPiece)
      if (!selectedPieceData) return prev

      const connectedGroup = getConnectedGroup(selectedPiece, prev.pieces)
      const deltaX = newX - selectedPieceData.currentPosition.x
      const deltaY = newY - selectedPieceData.currentPosition.y

      return {
        ...prev,
        pieces: prev.pieces.map(piece => {
          if (connectedGroup.includes(piece.id)) {
            // 연결된 그룹 전체를 함께 이동
            return {
              ...piece,
              currentPosition: {
                x: piece.currentPosition.x + deltaX,
                y: piece.currentPosition.y + deltaY
              }
            }
          }
          return piece
        })
      }
    })

    onPieceMove(selectedPiece, { x: newX, y: newY })
  }, [selectedPiece, dragOffset, onPieceMove, gameState.pieces])

  const handleMouseUp = useCallback(() => {
    if (!selectedPiece) return

    const piece = gameState.pieces.find(p => p.id === selectedPiece)
    if (!piece) return

    setGameState(prev => {
      let updatedPieces = [...prev.pieces]

      // 다른 조각들과의 연결 가능성 체크
      const otherPieces = updatedPieces.filter(p => p.id !== selectedPiece && !p.isPlaced)
      const connectablePieces = otherPieces.filter(otherPiece => canConnect(piece, otherPiece))

      // 연결 가능한 조각이 있으면 연결
      if (connectablePieces.length > 0) {
        const targetPiece = connectablePieces[0] // 가장 가까운 조각과 연결

        // 머지 위치 보정: 정확한 상대 위치로 조정
        const dx = targetPiece.correctPosition.x - piece.correctPosition.x
        const dy = targetPiece.correctPosition.y - piece.correctPosition.y

        // 두 조각을 서로의 connectedPieces에 추가하고 위치 보정
        updatedPieces = updatedPieces.map(p => {
          if (p.id === selectedPiece) {
            return {
              ...p,
              currentPosition: {
                x: targetPiece.currentPosition.x - dx,
                y: targetPiece.currentPosition.y - dy
              },
              connectedPieces: [...new Set([...p.connectedPieces, targetPiece.id])],
              isSelected: false
            }
          } else if (p.id === targetPiece.id) {
            return {
              ...p,
              connectedPieces: [...new Set([...p.connectedPieces, selectedPiece])]
            }
          }
          return { ...p, isSelected: false }
        })

        console.log(`🔗 조각 ${selectedPiece}와 ${targetPiece.id}가 연결되었습니다!`)

        // 퍼즐 완성 체크: 모든 조각이 하나의 그룹으로 연결되었는지 확인
        const groupSize = getConnectedGroup(selectedPiece, updatedPieces).length
        if (groupSize === prev.totalPieces) {
          setGameCompleted(true)
          onPuzzleComplete({
            completionTime: prev.gameTime,
            hintsUsed: prev.hintsUsed,
            score: calculateScore(prev.totalPieces, prev.gameTime, prev.hintsUsed),
            difficulty: prev.difficulty
          })
        }
      } else {
        // 연결되지 않으면 그냥 드롭 (스냅 제거)
        updatedPieces = updatedPieces.map(p => ({ ...p, isSelected: false }))
      }

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

    setGameState(prev => {
      // 연결된 그룹 전체를 함께 회전
      const connectedGroup = getConnectedGroup(selectedPiece, prev.pieces)

      return {
        ...prev,
        pieces: prev.pieces.map(piece => {
          if (connectedGroup.includes(piece.id)) {
            // 연결된 그룹의 모든 조각을 함께 회전
            return { ...piece, rotation: (piece.rotation + 90) % 360 }
          }
          return piece
        })
      }
    })

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
        isSelected: false,
        connectedPieces: []  // 이전 연결 모두 리셋
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
