import React from 'react'
import { Loader2, Clock, CheckCircle, AlertCircle } from 'lucide-react'

interface LoadingOverlayProps {
  isVisible: boolean
  message?: string
  progress?: number
  step?: string
  estimatedTime?: number
  type?: 'loading' | 'processing' | 'success' | 'error'
  onCancel?: () => void
}

export const LoadingOverlay: React.FC<LoadingOverlayProps> = ({
  isVisible,
  message = '처리 중...',
  progress,
  step,
  estimatedTime,
  type = 'loading',
  onCancel
}) => {
  if (!isVisible) return null

  const getIcon = () => {
    switch (type) {
      case 'success':
        return <CheckCircle className="w-12 h-12 text-green-600" />
      case 'error':
        return <AlertCircle className="w-12 h-12 text-red-600" />
      case 'processing':
      case 'loading':
      default:
        return <Loader2 className="w-12 h-12 animate-spin text-blue-600" />
    }
  }

  const getBackgroundColor = () => {
    switch (type) {
      case 'success':
        return 'bg-green-50 border-green-200'
      case 'error':
        return 'bg-red-50 border-red-200'
      case 'processing':
      case 'loading':
      default:
        return 'bg-white border-gray-200'
    }
  }

  const formatTime = (seconds: number): string => {
    if (seconds < 60) {
      return `${Math.round(seconds)}초`
    } else {
      const minutes = Math.floor(seconds / 60)
      const remainingSeconds = Math.round(seconds % 60)
      return `${minutes}분 ${remainingSeconds}초`
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 backdrop-blur-sm">
      <div className={`rounded-lg p-8 max-w-md w-full mx-4 border-2 shadow-xl ${getBackgroundColor()}`}>
        <div className="text-center">
          <div className="mb-4 flex justify-center">
            {getIcon()}
          </div>
          
          <h3 className="text-lg font-semibold mb-2 text-gray-800">{message}</h3>
          
          {progress !== undefined && (
            <div className="mb-4">
              <div className="bg-gray-200 rounded-full h-3 mb-2 overflow-hidden">
                <div 
                  className={`h-3 rounded-full transition-all duration-500 ease-out ${
                    type === 'error' ? 'bg-red-500' : 
                    type === 'success' ? 'bg-green-500' : 'bg-blue-500'
                  }`}
                  style={{ width: `${Math.min(progress, 100)}%` }}
                />
              </div>
              <p className="text-sm text-gray-600 font-medium">
                {Math.round(progress)}% 완료
              </p>
            </div>
          )}
          
          {step && (
            <p className="text-sm text-gray-500 mb-3 bg-gray-100 rounded-md px-3 py-2">
              <span className="font-medium">현재 단계:</span> {step}
            </p>
          )}

          {estimatedTime && estimatedTime > 0 && (
            <div className="flex items-center justify-center text-sm text-gray-500 mb-4">
              <Clock className="w-4 h-4 mr-1" />
              <span>예상 소요 시간: {formatTime(estimatedTime)}</span>
            </div>
          )}

          {type === 'loading' && onCancel && (
            <button
              onClick={onCancel}
              className="mt-4 px-4 py-2 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-md transition-colors"
            >
              취소
            </button>
          )}

          {type === 'error' && (
            <div className="mt-4 text-sm text-red-600">
              <p>처리 중 오류가 발생했습니다.</p>
              <p>잠시 후 다시 시도해주세요.</p>
            </div>
          )}

          {type === 'success' && (
            <div className="mt-4 text-sm text-green-600">
              <p>처리가 성공적으로 완료되었습니다!</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// 간단한 로딩 스피너 컴포넌트
export const LoadingSpinner: React.FC<{ 
  size?: 'sm' | 'md' | 'lg'
  className?: string 
}> = ({ 
  size = 'md', 
  className = '' 
}) => {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8'
  }

  return (
    <Loader2 className={`animate-spin ${sizeClasses[size]} ${className}`} />
  )
}

// 인라인 로딩 상태 컴포넌트
export const InlineLoading: React.FC<{
  message?: string
  size?: 'sm' | 'md' | 'lg'
}> = ({ 
  message = '로딩 중...', 
  size = 'md' 
}) => {
  return (
    <div className="flex items-center justify-center space-x-2 py-4">
      <LoadingSpinner size={size} className="text-blue-600" />
      <span className="text-gray-600">{message}</span>
    </div>
  )
}