import React, { createContext, useContext, useState, useCallback } from 'react'

interface ErrorInfo {
  id: string
  message: string
  type: 'error' | 'warning' | 'info' | 'success'
  timestamp: Date
  details?: any
  duration?: number
}

interface ErrorContextType {
  errors: ErrorInfo[]
  addError: (message: string, type?: ErrorInfo['type'], details?: any, duration?: number) => string
  removeError: (id: string) => void
  clearErrors: () => void
  hasErrors: boolean
}

const ErrorContext = createContext<ErrorContextType | undefined>(undefined)

export const ErrorProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [errors, setErrors] = useState<ErrorInfo[]>([])

  const addError = useCallback((
    message: string, 
    type: ErrorInfo['type'] = 'error', 
    details?: any,
    duration?: number
  ): string => {
    const error: ErrorInfo = {
      id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
      message,
      type,
      timestamp: new Date(),
      details,
      duration
    }
    
    setErrors(prev => [...prev, error])
    
    // 자동 제거 (에러가 아닌 경우 또는 duration이 지정된 경우)
    const autoRemoveDuration = duration || (type !== 'error' ? 5000 : 0)
    if (autoRemoveDuration > 0) {
      setTimeout(() => {
        removeError(error.id)
      }, autoRemoveDuration)
    }

    return error.id
  }, [])

  const removeError = useCallback((id: string) => {
    setErrors(prev => prev.filter(error => error.id !== id))
  }, [])

  const clearErrors = useCallback(() => {
    setErrors([])
  }, [])

  const hasErrors = errors.some(error => error.type === 'error')

  return (
    <ErrorContext.Provider value={{ 
      errors, 
      addError, 
      removeError, 
      clearErrors, 
      hasErrors 
    }}>
      {children}
    </ErrorContext.Provider>
  )
}

export const useError = () => {
  const context = useContext(ErrorContext)
  if (!context) {
    throw new Error('useError must be used within an ErrorProvider')
  }
  return context
}

// 편의 함수들
export const useErrorHandler = () => {
  const { addError } = useError()

  const handleError = useCallback((error: any, customMessage?: string) => {
    let message = customMessage || '알 수 없는 오류가 발생했습니다.'
    
    if (error instanceof Error) {
      message = error.message
    } else if (typeof error === 'string') {
      message = error
    } else if (error?.detail) {
      message = error.detail
    } else if (error?.message) {
      message = error.message
    }

    return addError(message, 'error', error)
  }, [addError])

  const handleSuccess = useCallback((message: string, duration = 3000) => {
    return addError(message, 'success', null, duration)
  }, [addError])

  const handleWarning = useCallback((message: string, duration = 4000) => {
    return addError(message, 'warning', null, duration)
  }, [addError])

  const handleInfo = useCallback((message: string, duration = 3000) => {
    return addError(message, 'info', null, duration)
  }, [addError])

  return {
    handleError,
    handleSuccess,
    handleWarning,
    handleInfo
  }
}