import React, { useState, useEffect, useRef } from 'react'
import { 
  Eye, 
  Grid, 
  Settings, 
  Download, 
  RefreshCw, 
  ZoomIn, 
  ZoomOut,
  RotateCcw,
  Shuffle,
  Play,
  Info
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
  edges: {
    top: 'flat' | 'knob' | 'hole'
    right: 'flat' | 'knob' | 'hole'
    bottom: 'flat' | 'knob' | 'hole'
    left: 'flat' | 'knob' | 'hole'
  }
}

interface PuzzlePreviewProps {
  imageUrl: string
  pieceCount: number
  difficulty: number
  puzzleType: string
  isGeneratingPreview: boolean
  previewData?: {
    pieces: PuzzlePiece[]
    gridInfo: {
      rows: number
      cols: number
      pieceWidth: number
      pieceHeight: number
    }
    metadata: {
      estimatedSolveTime: number
      difficultyScore: number
      challengeFactors: string[]
    }
  }
  onGeneratePreview: () => void
  onStartPuzzle: () => void
}

export const PuzzlePreview: React.FC<PuzzlePreviewProps> = ({
  imageUrl,
  pieceCount,
  difficulty,
  puzzleType,
  isGeneratingPreview,
  previewData,
  onGeneratePreview,
  onStartPuzzle
}) => {
  const [viewMode, setViewMode] = useState<'assembled' | 'scattered' | 'grid'>('assembled')
  const [zoom, setZoom] = useState(1)
  const [showPieceNumbers, setShowPieceNumbers] = useState(false)
  const [selectedPiece, setSelectedPiece] = useState<string | null>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    if (previewData && canvasRef.current) {
      drawPuzzlePreview()
    }
  }, [previewData, viewMode, zoom, showPieceNumbers])

  const drawPuzzlePreview = () => {
    const canvas = canvasRef.current
    if (!canvas || !previewData) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // 캔버스 크기 설정
    const containerWidth = canvas.parentElement?.clientWidth || 400
    const containerHeight = 300
    canvas.width = containerWidth
    canvas.height = containerHeight

    // 배경 클리어
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    // 이미지 로드 및 그리기
    const img = new Image()
    img.onload = () => {
      const { gridInfo, pieces } = previewData

      switch (viewMode) {
        case 'assembled':
          drawAssembledView(ctx, img, canvas.width, canvas.height)
          break
        case 'scattered':
          drawScatteredView(ctx, pieces, canvas.width, canvas.height)
          break
        case 'grid':
          drawGridView(ctx, pieces, gridInfo, canvas.width, canvas.height)
          break
      }
    }
    img.src = imageUrl
  }

  const drawAssembledView = (ctx: CanvasRenderingContext2D, img: HTMLImageElement, width: number, height: number) => {
    // 완성된 퍼즐 모습 (원본 이미지)
    const scale = Math.min(width / img.width, height / img.height) * zoom
    const scaledWidth = img.width * scale
    const scaledHeight = img.height * scale
    const x = (width - scaledWidth) / 2
    const y = (height - scaledHeight) / 2

    ctx.drawImage(img, x, y, scaledWidth, scaledHeight)

    // 퍼즐 조각 경계선 표시
    if (previewData) {
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.8)'
      ctx.lineWidth = 2
      ctx.shadowColor = 'rgba(0, 0, 0, 0.3)'
      ctx.shadowBlur = 2

      const { gridInfo } = previewData
      const pieceWidth = scaledWidth / gridInfo.cols
      const pieceHeight = scaledHeight / gridInfo.rows

      // 세로선
      for (let i = 1; i < gridInfo.cols; i++) {
        ctx.beginPath()
        ctx.moveTo(x + i * pieceWidth, y)
        ctx.lineTo(x + i * pieceWidth, y + scaledHeight)
        ctx.stroke()
      }

      // 가로선
      for (let i = 1; i < gridInfo.rows; i++) {
        ctx.beginPath()
        ctx.moveTo(x, y + i * pieceHeight)
        ctx.lineTo(x + scaledWidth, y + i * pieceHeight)
        ctx.stroke()
      }
    }
  }

  const drawScatteredView = (ctx: CanvasRenderingContext2D, pieces: PuzzlePiece[], width: number, height: number) => {
    // 흩어진 퍼즐 조각들
    pieces.forEach((piece, index) => {
      if (index > 20) return // 성능을 위해 처음 20개만 표시

      const x = (Math.random() * (width - 60)) * zoom
      const y = (Math.random() * (height - 60)) * zoom
      const size = 40 * zoom

      // 조각 배경
      ctx.fillStyle = selectedPiece === piece.id ? '#3B82F6' : '#E5E7EB'
      ctx.fillRect(x, y, size, size)

      // 조각 번호
      if (showPieceNumbers) {
        ctx.fillStyle = '#374151'
        ctx.font = `${12 * zoom}px Arial`
        ctx.textAlign = 'center'
        ctx.fillText((index + 1).toString(), x + size / 2, y + size / 2 + 4)
      }

      // 선택된 조각 하이라이트
      if (selectedPiece === piece.id) {
        ctx.strokeStyle = '#3B82F6'
        ctx.lineWidth = 3
        ctx.strokeRect(x - 2, y - 2, size + 4, size + 4)
      }
    })
  }

  const drawGridView = (ctx: CanvasRenderingContext2D, pieces: PuzzlePiece[], gridInfo: any, width: number, height: number) => {
    // 격자 형태로 조각 배치
    const cols = Math.min(gridInfo.cols, 8) // 최대 8열
    const rows = Math.ceil(pieces.length / cols)
    const cellWidth = width / cols
    const cellHeight = height / rows

    pieces.forEach((piece, index) => {
      if (index >= cols * rows) return

      const col = index % cols
      const row = Math.floor(index / cols)
      const x = col * cellWidth + 5
      const y = row * cellHeight + 5
      const size = Math.min(cellWidth - 10, cellHeight - 10) * zoom

      // 조각 배경
      ctx.fillStyle = selectedPiece === piece.id ? '#3B82F6' : '#F3F4F6'
      ctx.fillRect(x, y, size, size)

      // 조각 테두리
      ctx.strokeStyle = '#D1D5DB'
      ctx.lineWidth = 1
      ctx.strokeRect(x, y, size, size)

      // 조각 번호
      ctx.fillStyle = '#374151'
      ctx.font = `${Math.min(12, size / 4)}px Arial`
      ctx.textAlign = 'center'
      ctx.fillText((index + 1).toString(), x + size / 2, y + size / 2 + 4)
    })
  }

  const handleCanvasClick = (event: React.MouseEvent<HTMLCanvasElement>) => {
    if (!previewData || viewMode === 'assembled') return

    const canvas = canvasRef.current
    if (!canvas) return

    const rect = canvas.getBoundingClientRect()
    const x = event.clientX - rect.left
    const y = event.clientY - rect.top

    // 클릭된 조각 찾기 (간단한 구현)
    const pieceIndex = Math.floor(x / (canvas.width / Math.min(previewData.gridInfo.cols, 8)))
    if (pieceIndex < previewData.pieces.length) {
      setSelectedPiece(previewData.pieces[pieceIndex].id)
    }
  }

  const formatTime = (minutes: number) => {
    const hours = Math.floor(minutes / 60)
    const mins = minutes % 60
    return hours > 0 ? `${hours}시간 ${mins}분` : `${mins}분`
  }

  const getDifficultyText = (score: number) => {
    if (score < 0.3) return '쉬움'
    if (score < 0.6) return '보통'
    if (score < 0.8) return '어려움'
    return '매우 어려움'
  }

  const getDifficultyColor = (score: number) => {
    if (score < 0.3) return 'text-green-600 bg-green-100'
    if (score < 0.6) return 'text-yellow-600 bg-yellow-100'
    if (score < 0.8) return 'text-orange-600 bg-orange-100'
    return 'text-red-600 bg-red-100'
  }

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-green-100 rounded-lg">
            <Eye className="h-6 w-6 text-green-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">퍼즐 미리보기</h3>
            <p className="text-sm text-gray-600">
              생성될 퍼즐의 모습을 미리 확인하세요
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          {!previewData && (
            <button
              onClick={onGeneratePreview}
              disabled={isGeneratingPreview}
              className="btn-secondary flex items-center space-x-2 disabled:opacity-50"
            >
              {isGeneratingPreview ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  <span>생성 중...</span>
                </>
              ) : (
                <>
                  <Eye className="h-4 w-4" />
                  <span>미리보기 생성</span>
                </>
              )}
            </button>
          )}

          {previewData && (
            <button
              onClick={onStartPuzzle}
              className="btn-primary flex items-center space-x-2"
            >
              <Play className="h-4 w-4" />
              <span>퍼즐 시작</span>
            </button>
          )}
        </div>
      </div>

      {/* 미리보기 영역 */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        {previewData ? (
          <>
            {/* 컨트롤 바 */}
            <div className="border-b border-gray-200 p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  {/* 보기 모드 */}
                  <div className="flex items-center space-x-2">
                    <span className="text-sm font-medium text-gray-700">보기:</span>
                    <select
                      value={viewMode}
                      onChange={(e) => setViewMode(e.target.value as any)}
                      className="text-sm border border-gray-300 rounded px-2 py-1"
                    >
                      <option value="assembled">완성된 모습</option>
                      <option value="scattered">흩어진 조각</option>
                      <option value="grid">격자 배열</option>
                    </select>
                  </div>

                  {/* 줌 컨트롤 */}
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => setZoom(Math.max(0.5, zoom - 0.1))}
                      className="p-1 hover:bg-gray-100 rounded"
                    >
                      <ZoomOut className="h-4 w-4" />
                    </button>
                    <span className="text-sm text-gray-600 min-w-[3rem] text-center">
                      {Math.round(zoom * 100)}%
                    </span>
                    <button
                      onClick={() => setZoom(Math.min(2, zoom + 0.1))}
                      className="p-1 hover:bg-gray-100 rounded"
                    >
                      <ZoomIn className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  {/* 조각 번호 표시 */}
                  <label className="flex items-center space-x-2 text-sm">
                    <input
                      type="checkbox"
                      checked={showPieceNumbers}
                      onChange={(e) => setShowPieceNumbers(e.target.checked)}
                      className="rounded border-gray-300"
                    />
                    <span>번호 표시</span>
                  </label>

                  {/* 새로고침 */}
                  <button
                    onClick={onGeneratePreview}
                    className="p-2 hover:bg-gray-100 rounded"
                    title="미리보기 새로고침"
                  >
                    <RefreshCw className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>

            {/* 캔버스 */}
            <div className="relative bg-gray-50" style={{ height: '400px' }}>
              <canvas
                ref={canvasRef}
                onClick={handleCanvasClick}
                className="w-full h-full cursor-pointer"
              />
              
              {selectedPiece && (
                <div className="absolute top-4 left-4 bg-white border border-gray-200 rounded-lg p-3 shadow-lg">
                  <div className="flex items-center space-x-2">
                    <Info className="h-4 w-4 text-blue-600" />
                    <span className="text-sm font-medium">조각 정보</span>
                  </div>
                  <p className="text-xs text-gray-600 mt-1">
                    선택된 조각: {selectedPiece}
                  </p>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="h-64 flex items-center justify-center bg-gray-50">
            <div className="text-center">
              <Eye className="h-12 w-12 text-gray-400 mx-auto mb-3" />
              <p className="text-gray-600 mb-4">미리보기를 생성하여 퍼즐을 확인하세요</p>
              <button
                onClick={onGeneratePreview}
                disabled={isGeneratingPreview}
                className="btn-primary flex items-center space-x-2 mx-auto disabled:opacity-50"
              >
                {isGeneratingPreview ? (
                  <>
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    <span>생성 중...</span>
                  </>
                ) : (
                  <>
                    <Eye className="h-4 w-4" />
                    <span>미리보기 생성</span>
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 퍼즐 정보 */}
      {previewData && (
        <div className="grid md:grid-cols-2 gap-6">
          {/* 기본 정보 */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-center space-x-2 mb-3">
              <Grid className="h-5 w-5 text-blue-600" />
              <h4 className="font-medium text-blue-900">퍼즐 정보</h4>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-blue-700">조각 수:</span>
                <span className="font-medium">{previewData.pieces.length}개</span>
              </div>
              <div className="flex justify-between">
                <span className="text-blue-700">격자 크기:</span>
                <span className="font-medium">
                  {previewData.gridInfo.rows} × {previewData.gridInfo.cols}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-blue-700">퍼즐 타입:</span>
                <span className="font-medium capitalize">{puzzleType}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-blue-700">예상 소요 시간:</span>
                <span className="font-medium">
                  {formatTime(previewData.metadata.estimatedSolveTime)}
                </span>
              </div>
            </div>
          </div>

          {/* 난이도 정보 */}
          <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
            <div className="flex items-center space-x-2 mb-3">
              <Settings className="h-5 w-5 text-orange-600" />
              <h4 className="font-medium text-orange-900">난이도 분석</h4>
            </div>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-orange-700 text-sm">난이도 점수:</span>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${getDifficultyColor(previewData.metadata.difficultyScore)}`}>
                  {getDifficultyText(previewData.metadata.difficultyScore)}
                </span>
              </div>
              
              {previewData.metadata.challengeFactors.length > 0 && (
                <div>
                  <p className="text-orange-700 text-sm mb-2">도전 요소:</p>
                  <div className="flex flex-wrap gap-1">
                    {previewData.metadata.challengeFactors.map((factor, index) => (
                      <span
                        key={index}
                        className="px-2 py-1 bg-orange-100 text-orange-700 text-xs rounded"
                      >
                        {factor}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 액션 버튼 */}
      {previewData && (
        <div className="flex justify-center space-x-4">
          <button
            onClick={onGeneratePreview}
            className="btn-outline flex items-center space-x-2"
          >
            <RefreshCw className="h-4 w-4" />
            <span>다시 생성</span>
          </button>
          
          <button
            onClick={onStartPuzzle}
            className="btn-primary flex items-center space-x-2"
          >
            <Play className="h-4 w-4" />
            <span>퍼즐 게임 시작</span>
          </button>
        </div>
      )}
    </div>
  )
}