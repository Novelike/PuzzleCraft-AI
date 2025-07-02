import React, { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  Settings, 
  Sparkles, 
  Brain, 
  Palette,
  Eye,
  Play,
  AlertCircle,
  CheckCircle
} from 'lucide-react'

// AI 통합 컴포넌트 임포트
import { ImageUploader } from '../components/PuzzleCreator/ImageUploader'
import { AIProcessingPanel } from '../components/PuzzleCreator/AIProcessingPanel'
import { StyleSelector } from '../components/PuzzleCreator/StyleSelector'
import { PuzzlePreview } from '../components/PuzzleCreator/PuzzlePreview'

// 훅 임포트
import { usePuzzleGenerator } from '../hooks/usePuzzleGenerator'
import { useRealTimeUpdates } from '../hooks/useRealTimeUpdates'
import { useStyleTransfer } from '../hooks/useStyleTransfer'

export const PuzzleCreate: React.FC = () => {
  const navigate = useNavigate()
  const [currentStep, setCurrentStep] = useState<'upload' | 'analyze' | 'style' | 'preview' | 'generate'>('upload')
  const [selectedStyle, setSelectedStyle] = useState<string>('original')

  // 퍼즐 생성 훅 사용
  const puzzleGenerator = usePuzzleGenerator({
    enableCaching: true,
    onComplete: (result) => {
      console.log('퍼즐 생성 완료:', result)
      // 퍼즐 게임 페이지로 이동
      navigate(`/puzzle/play/${result.puzzle_id}`)
    },
    onError: (error) => {
      console.error('퍼즐 생성 오류:', error)
    },
    onProgress: (progress, step) => {
      console.log(`진행률: ${(progress * 100).toFixed(1)}% - ${step}`)
    }
  })

  // 스타일 변환 훅 사용
  const styleTransfer = useStyleTransfer({
    onPreviewComplete: (result) => {
      console.log('스타일 미리보기 완료:', result)
    },
    onApplyComplete: (result) => {
      console.log('스타일 적용 완료:', result)
      // 스타일이 적용된 이미지로 퍼즐 생성 설정 업데이트
      puzzleGenerator.updatePuzzleSettings({
        styled_image_url: result.styled_image_url,
        style_type: selectedStyle
      })
      setCurrentStep('preview')
    },
    onError: (error) => {
      console.error('스타일 변환 오류:', error)
    }
  })

  // 실시간 업데이트 훅 사용
  const realTimeUpdates = useRealTimeUpdates({
    onStatusChange: (status) => {
      console.log('상태 업데이트:', status)
    }
  })

  // 파일 선택 핸들러
  const handleFileSelect = useCallback((file: File) => {
    puzzleGenerator.selectFile(file)
    if (file) {
      setCurrentStep('analyze')
    }
  }, [puzzleGenerator])

  // 이미지 분석 요청
  const handleAnalysisRequest = useCallback(async (file: File) => {
    const result = await puzzleGenerator.analyzeComplexity(file)
    if (result) {
      // 난이도 프로필도 자동 생성
      await puzzleGenerator.generateDifficultyProfile(result)
      setCurrentStep('style')
    }
  }, [puzzleGenerator])

  // 스타일 선택
  const handleStyleSelect = useCallback((styleId: string) => {
    setSelectedStyle(styleId)
    puzzleGenerator.updatePuzzleSettings({
      style_type: styleId === 'original' ? undefined : styleId
    })
  }, [puzzleGenerator])

  // 스타일 미리보기 요청
  const handleStylePreviewRequest = useCallback(async (styleId: string) => {
    if (!puzzleGenerator.currentFile) return

    try {
      await styleTransfer.generatePreview(puzzleGenerator.currentFile, styleId)
    } catch (error) {
      console.error('스타일 미리보기 실패:', error)
    }
  }, [puzzleGenerator.currentFile, styleTransfer])

  // 스타일 적용
  const handleStyleApply = useCallback(async (styleId: string) => {
    if (!puzzleGenerator.currentFile) return

    try {
      await styleTransfer.applyStyle(puzzleGenerator.currentFile, styleId)
      // onApplyComplete 콜백에서 자동으로 preview 단계로 이동됨
    } catch (error) {
      console.error('스타일 적용 실패:', error)
    }
  }, [puzzleGenerator.currentFile, styleTransfer])

  // 퍼즐 미리보기 생성
  const handlePreviewGeneration = useCallback(async () => {
    const result = await puzzleGenerator.generatePreview()
    if (result) {
      setCurrentStep('generate')
    }
  }, [puzzleGenerator])

  // 퍼즐 생성 시작
  const handlePuzzleGeneration = useCallback(async () => {
    await puzzleGenerator.generatePuzzle()
  }, [puzzleGenerator])

  // 퍼즐 게임 시작
  const handleStartPuzzle = useCallback(() => {
    if (puzzleGenerator.generationResult) {
      navigate(`/puzzle/play/${puzzleGenerator.generationResult.puzzle_id}`)
    } else {
      // 미리보기만 있는 경우 간단한 퍼즐로 시작
      navigate('/puzzle/play/preview')
    }
  }, [puzzleGenerator.generationResult, navigate])

  // 단계별 완료 상태 확인
  const getStepStatus = (step: string) => {
    switch (step) {
      case 'upload':
        return puzzleGenerator.selectedFile ? 'completed' : 'current'
      case 'analyze':
        return puzzleGenerator.hasAnalysis ? 'completed' : 
               puzzleGenerator.selectedFile ? 'current' : 'pending'
      case 'style':
        return selectedStyle ? 'completed' : 
               puzzleGenerator.hasAnalysis ? 'current' : 'pending'
      case 'preview':
        return puzzleGenerator.previewData ? 'completed' : 
               selectedStyle ? 'current' : 'pending'
      case 'generate':
        return puzzleGenerator.hasResult ? 'completed' : 
               puzzleGenerator.previewData ? 'current' : 'pending'
      default:
        return 'pending'
    }
  }

  return (
    <div className="max-w-6xl mx-auto">
      {/* 헤더 */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">AI 퍼즐 생성기</h1>
        <p className="text-gray-600">
          AI 기술을 활용하여 이미지를 분석하고 최적화된 퍼즐을 자동으로 생성합니다
        </p>
      </div>

      {/* 진행 단계 표시 */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          {[
            { id: 'upload', name: '이미지 업로드', icon: <Eye className="h-5 w-5" /> },
            { id: 'analyze', name: 'AI 분석', icon: <Brain className="h-5 w-5" /> },
            { id: 'style', name: '스타일 선택', icon: <Palette className="h-5 w-5" /> },
            { id: 'preview', name: '미리보기', icon: <Eye className="h-5 w-5" /> },
            { id: 'generate', name: '퍼즐 생성', icon: <Sparkles className="h-5 w-5" /> },
          ].map((step, index) => {
            const status = getStepStatus(step.id)
            return (
              <div key={step.id} className="flex items-center">
                <div
                  className={`
                    flex items-center justify-center w-10 h-10 rounded-full border-2 transition-colors
                    ${status === 'completed' 
                      ? 'bg-green-500 border-green-500 text-white' 
                      : status === 'current'
                        ? 'bg-blue-500 border-blue-500 text-white'
                        : 'bg-gray-100 border-gray-300 text-gray-400'
                    }
                  `}
                >
                  {status === 'completed' ? (
                    <CheckCircle className="h-5 w-5" />
                  ) : (
                    step.icon
                  )}
                </div>
                <div className="ml-3">
                  <p className={`text-sm font-medium ${
                    status === 'completed' ? 'text-green-600' :
                    status === 'current' ? 'text-blue-600' : 'text-gray-500'
                  }`}>
                    {step.name}
                  </p>
                </div>
                {index < 4 && (
                  <div className={`flex-1 h-0.5 mx-4 ${
                    status === 'completed' ? 'bg-green-500' : 'bg-gray-300'
                  }`} />
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* 에러 표시 */}
      {puzzleGenerator.error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-center space-x-2">
            <AlertCircle className="h-5 w-5 text-red-600" />
            <span className="text-red-800 font-medium">오류 발생</span>
          </div>
          <p className="text-red-700 mt-1">{puzzleGenerator.error}</p>
        </div>
      )}

      <div className="space-y-8">
        {/* 1단계: 이미지 업로드 */}
        <div className="card">
          <ImageUploader
            onFileSelect={handleFileSelect}
            onAnalysisRequest={handleAnalysisRequest}
            selectedFile={puzzleGenerator.selectedFile}
            isAnalyzing={puzzleGenerator.isAnalyzing}
            analysisResult={puzzleGenerator.complexityAnalysis}
          />
        </div>

        {/* 2단계: AI 처리 패널 */}
        {puzzleGenerator.selectedFile && (
          <div className="card">
            <AIProcessingPanel
              isProcessing={puzzleGenerator.isGenerating}
              currentStep={puzzleGenerator.currentStep}
              progress={puzzleGenerator.progress}
              steps={puzzleGenerator.processingSteps}
              estimatedTimeRemaining={puzzleGenerator.estimatedTimeRemaining}
              onCancel={puzzleGenerator.cancelGeneration}
            />
          </div>
        )}

        {/* 3단계: 스타일 선택 */}
        {puzzleGenerator.hasAnalysis && currentStep !== 'upload' && (
          <div className="card">
            <StyleSelector
              selectedStyle={selectedStyle}
              onStyleSelect={handleStyleSelect}
              onPreviewRequest={handleStylePreviewRequest}
              onApplyStyle={handleStyleApply}
              isGeneratingPreview={styleTransfer.isGeneratingPreview}
              isApplyingStyle={styleTransfer.isApplyingStyle}
              previewResults={styleTransfer.previewResults}
              originalImageUrl={puzzleGenerator.imageUrl || undefined}
              error={styleTransfer.error}
            />
          </div>
        )}

        {/* 4단계: 퍼즐 미리보기 */}
        {(currentStep === 'preview' || currentStep === 'generate') && puzzleGenerator.imageUrl && (
          <div className="card">
            <PuzzlePreview
              imageUrl={puzzleGenerator.imageUrl}
              pieceCount={puzzleGenerator.puzzleSettings.piece_count || 50}
              difficulty={puzzleGenerator.difficultyProfile?.difficulty_score || 0.5}
              puzzleType={puzzleGenerator.puzzleSettings.puzzle_type || 'classic'}
              isGeneratingPreview={puzzleGenerator.isGeneratingPreview}
              previewData={puzzleGenerator.previewData}
              onGeneratePreview={handlePreviewGeneration}
              onStartPuzzle={handleStartPuzzle}
            />
          </div>
        )}

        {/* 5단계: 최종 퍼즐 생성 */}
        {currentStep === 'generate' && !puzzleGenerator.isGenerating && !puzzleGenerator.hasResult && (
          <div className="card">
            <div className="text-center py-8">
              <div className="mb-6">
                <Sparkles className="h-16 w-16 text-blue-600 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  AI 퍼즐 생성 준비 완료
                </h3>
                <p className="text-gray-600">
                  모든 설정이 완료되었습니다. 이제 AI가 최적화된 퍼즐을 생성합니다.
                </p>
              </div>

              {/* 설정 요약 */}
              {puzzleGenerator.difficultyProfile && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6 text-left max-w-md mx-auto">
                  <h4 className="font-medium text-blue-900 mb-3">생성 설정 요약</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-blue-700">추천 조각 수:</span>
                      <span className="font-medium">{puzzleGenerator.difficultyProfile.recommended_piece_count}개</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-blue-700">난이도:</span>
                      <span className="font-medium capitalize">{puzzleGenerator.difficultyProfile.skill_level}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-blue-700">예상 시간:</span>
                      <span className="font-medium">{puzzleGenerator.difficultyProfile.estimated_solve_time}분</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-blue-700">스타일:</span>
                      <span className="font-medium">{selectedStyle === 'original' ? '원본' : selectedStyle}</span>
                    </div>
                  </div>
                </div>
              )}

              <button
                onClick={handlePuzzleGeneration}
                className="btn-primary text-lg px-8 py-3 flex items-center mx-auto"
              >
                <Sparkles className="h-5 w-5 mr-2" />
                AI 퍼즐 생성 시작
              </button>
            </div>
          </div>
        )}

        {/* 완료 상태 */}
        {puzzleGenerator.hasResult && (
          <div className="card">
            <div className="text-center py-8">
              <CheckCircle className="h-16 w-16 text-green-600 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                퍼즐 생성 완료!
              </h3>
              <p className="text-gray-600 mb-6">
                AI가 최적화된 퍼즐을 성공적으로 생성했습니다.
              </p>
              <button
                onClick={handleStartPuzzle}
                className="btn-primary text-lg px-8 py-3 flex items-center mx-auto"
              >
                <Play className="h-5 w-5 mr-2" />
                퍼즐 게임 시작
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
