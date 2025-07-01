import React, { useState, useEffect } from 'react'
import { 
  Brain, 
  Eye, 
  Type, 
  Palette, 
  CheckCircle, 
  AlertCircle, 
  Clock, 
  Zap,
  RefreshCw,
  TrendingUp
} from 'lucide-react'

interface AIProcessingStep {
  id: string
  name: string
  description: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  estimatedTime?: number
  result?: any
  error?: string
}

interface AIProcessingPanelProps {
  isProcessing: boolean
  currentStep: string
  progress: number
  steps: AIProcessingStep[]
  onRetry?: (stepId: string) => void
  onCancel?: () => void
  estimatedTimeRemaining?: number
}

export const AIProcessingPanel: React.FC<AIProcessingPanelProps> = ({
  isProcessing,
  currentStep,
  progress,
  steps,
  onRetry,
  onCancel,
  estimatedTimeRemaining
}) => {
  const [elapsedTime, setElapsedTime] = useState(0)

  useEffect(() => {
    let interval: NodeJS.Timeout
    if (isProcessing) {
      interval = setInterval(() => {
        setElapsedTime(prev => prev + 1)
      }, 1000)
    } else {
      setElapsedTime(0)
    }

    return () => {
      if (interval) clearInterval(interval)
    }
  }, [isProcessing])

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const getStepIcon = (step: AIProcessingStep) => {
    switch (step.id) {
      case 'complexity_analysis':
        return <Brain className="h-5 w-5" />
      case 'ocr_processing':
        return <Type className="h-5 w-5" />
      case 'segmentation':
        return <Eye className="h-5 w-5" />
      case 'style_transfer':
        return <Palette className="h-5 w-5" />
      case 'puzzle_generation':
        return <Zap className="h-5 w-5" />
      default:
        return <Brain className="h-5 w-5" />
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'failed':
        return <AlertCircle className="h-4 w-4 text-red-500" />
      case 'processing':
        return <RefreshCw className="h-4 w-4 text-blue-500 animate-spin" />
      default:
        return <Clock className="h-4 w-4 text-gray-400" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-50 border-green-200'
      case 'failed':
        return 'bg-red-50 border-red-200'
      case 'processing':
        return 'bg-blue-50 border-blue-200'
      default:
        return 'bg-gray-50 border-gray-200'
    }
  }

  const completedSteps = steps.filter(step => step.status === 'completed').length
  const totalSteps = steps.length

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-blue-100 rounded-lg">
            <Brain className="h-6 w-6 text-blue-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">AI 처리 진행상황</h3>
            <p className="text-sm text-gray-600">
              {isProcessing ? '퍼즐 생성을 위한 AI 분석 중...' : 'AI 처리 대기 중'}
            </p>
          </div>
        </div>

        {isProcessing && onCancel && (
          <button
            onClick={onCancel}
            className="btn-outline text-sm"
          >
            취소
          </button>
        )}
      </div>

      {/* 전체 진행률 */}
      {isProcessing && (
        <div className="mb-6">
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm font-medium text-gray-700">
              전체 진행률 ({completedSteps}/{totalSteps})
            </span>
            <span className="text-sm text-gray-600">
              {(progress * 100).toFixed(0)}%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress * 100}%` }}
            />
          </div>
          
          <div className="flex justify-between items-center mt-2 text-xs text-gray-500">
            <span>경과 시간: {formatTime(elapsedTime)}</span>
            {estimatedTimeRemaining && (
              <span>예상 남은 시간: {formatTime(estimatedTimeRemaining)}</span>
            )}
          </div>
        </div>
      )}

      {/* 처리 단계 목록 */}
      <div className="space-y-3">
        {steps.map((step, index) => (
          <div
            key={step.id}
            className={`border rounded-lg p-4 transition-all duration-200 ${getStatusColor(step.status)}`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className={`
                  p-2 rounded-lg
                  ${step.status === 'completed' ? 'bg-green-100 text-green-600' :
                    step.status === 'processing' ? 'bg-blue-100 text-blue-600' :
                    step.status === 'failed' ? 'bg-red-100 text-red-600' :
                    'bg-gray-100 text-gray-400'}
                `}>
                  {getStepIcon(step)}
                </div>
                
                <div className="flex-1">
                  <div className="flex items-center space-x-2">
                    <h4 className="font-medium text-gray-900">{step.name}</h4>
                    {getStatusIcon(step.status)}
                  </div>
                  <p className="text-sm text-gray-600 mt-1">{step.description}</p>
                  
                  {step.status === 'processing' && step.progress > 0 && (
                    <div className="mt-2">
                      <div className="w-full bg-gray-200 rounded-full h-1">
                        <div
                          className="bg-blue-500 h-1 rounded-full transition-all duration-300"
                          style={{ width: `${step.progress * 100}%` }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div className="flex items-center space-x-2">
                {step.status === 'failed' && onRetry && (
                  <button
                    onClick={() => onRetry(step.id)}
                    className="btn-outline text-xs"
                  >
                    재시도
                  </button>
                )}
                
                {step.estimatedTime && step.status === 'processing' && (
                  <span className="text-xs text-gray-500">
                    ~{formatTime(step.estimatedTime)}
                  </span>
                )}
              </div>
            </div>

            {/* 에러 메시지 */}
            {step.status === 'failed' && step.error && (
              <div className="mt-3 p-3 bg-red-100 border border-red-200 rounded-md">
                <p className="text-sm text-red-700">{step.error}</p>
              </div>
            )}

            {/* 결과 미리보기 */}
            {step.status === 'completed' && step.result && (
              <div className="mt-3 p-3 bg-green-100 border border-green-200 rounded-md">
                <div className="flex items-center space-x-2 mb-2">
                  <TrendingUp className="h-4 w-4 text-green-600" />
                  <span className="text-sm font-medium text-green-800">처리 완료</span>
                </div>
                
                {step.id === 'complexity_analysis' && step.result.analysis && (
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <span className="text-green-700">복잡도:</span>
                      <span className="ml-1 font-medium">
                        {(step.result.analysis.overall_score * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div>
                      <span className="text-green-700">추천 조각 수:</span>
                      <span className="ml-1 font-medium">
                        {step.result.analysis.recommendations?.piece_count_range?.[0]}-
                        {step.result.analysis.recommendations?.piece_count_range?.[1]}
                      </span>
                    </div>
                  </div>
                )}

                {step.id === 'ocr_processing' && step.result.text_regions && (
                  <div className="text-xs">
                    <span className="text-green-700">감지된 텍스트:</span>
                    <span className="ml-1 font-medium">
                      {step.result.text_regions.length}개 영역
                    </span>
                  </div>
                )}

                {step.id === 'segmentation' && step.result.segments && (
                  <div className="text-xs">
                    <span className="text-green-700">분할된 영역:</span>
                    <span className="ml-1 font-medium">
                      {step.result.segments.length}개 세그먼트
                    </span>
                  </div>
                )}

                {step.id === 'style_transfer' && step.result.styled_image_url && (
                  <div className="text-xs">
                    <span className="text-green-700">스타일 변환:</span>
                    <span className="ml-1 font-medium text-green-800">완료</span>
                  </div>
                )}

                {step.id === 'puzzle_generation' && step.result.pieces && (
                  <div className="text-xs">
                    <span className="text-green-700">생성된 조각:</span>
                    <span className="ml-1 font-medium">
                      {step.result.pieces.length}개
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* 현재 처리 중인 단계 하이라이트 */}
      {isProcessing && currentStep && (
        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-center space-x-2">
            <RefreshCw className="h-4 w-4 text-blue-600 animate-spin" />
            <span className="text-sm font-medium text-blue-800">
              현재 처리 중: {currentStep}
            </span>
          </div>
        </div>
      )}

      {/* 완료 상태 */}
      {!isProcessing && completedSteps === totalSteps && totalSteps > 0 && (
        <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
          <div className="flex items-center space-x-3">
            <CheckCircle className="h-6 w-6 text-green-600" />
            <div>
              <h4 className="font-medium text-green-800">AI 처리 완료!</h4>
              <p className="text-sm text-green-700">
                모든 AI 분석이 완료되었습니다. 이제 퍼즐을 생성할 수 있습니다.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}