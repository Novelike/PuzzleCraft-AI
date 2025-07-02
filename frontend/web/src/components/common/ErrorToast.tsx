import React from 'react'
import { X, AlertCircle, CheckCircle, Info, AlertTriangle } from 'lucide-react'
import { useError } from '../../contexts/ErrorContext'

interface ToastProps {
  id: string
  message: string
  type: 'error' | 'warning' | 'info' | 'success'
  onClose: (id: string) => void
}

const Toast: React.FC<ToastProps> = ({ id, message, type, onClose }) => {
  const getIcon = () => {
    switch (type) {
      case 'error':
        return <AlertCircle className="w-5 h-5 text-red-500" />
      case 'warning':
        return <AlertTriangle className="w-5 h-5 text-yellow-500" />
      case 'info':
        return <Info className="w-5 h-5 text-blue-500" />
      case 'success':
        return <CheckCircle className="w-5 h-5 text-green-500" />
      default:
        return <Info className="w-5 h-5 text-gray-500" />
    }
  }

  const getBackgroundColor = () => {
    switch (type) {
      case 'error':
        return 'bg-red-50 border-red-200'
      case 'warning':
        return 'bg-yellow-50 border-yellow-200'
      case 'info':
        return 'bg-blue-50 border-blue-200'
      case 'success':
        return 'bg-green-50 border-green-200'
      default:
        return 'bg-gray-50 border-gray-200'
    }
  }

  const getTextColor = () => {
    switch (type) {
      case 'error':
        return 'text-red-800'
      case 'warning':
        return 'text-yellow-800'
      case 'info':
        return 'text-blue-800'
      case 'success':
        return 'text-green-800'
      default:
        return 'text-gray-800'
    }
  }

  return (
    <div className={`
      flex items-start space-x-3 p-4 rounded-lg border shadow-lg max-w-md w-full
      transform transition-all duration-300 ease-in-out
      hover:shadow-xl
      ${getBackgroundColor()}
    `}>
      <div className="flex-shrink-0 mt-0.5">
        {getIcon()}
      </div>
      
      <div className="flex-1 min-w-0">
        <p className={`text-sm font-medium ${getTextColor()}`}>
          {message}
        </p>
      </div>
      
      <button
        onClick={() => onClose(id)}
        className={`
          flex-shrink-0 ml-2 p-1 rounded-md transition-colors
          hover:bg-white hover:bg-opacity-50
          ${getTextColor()}
        `}
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  )
}

export const ErrorToastContainer: React.FC = () => {
  const { errors, removeError } = useError()

  if (errors.length === 0) return null

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2">
      {errors.map((error) => (
        <Toast
          key={error.id}
          id={error.id}
          message={error.message}
          type={error.type}
          onClose={removeError}
        />
      ))}
    </div>
  )
}

// 개별 토스트 메시지 컴포넌트들
export const ErrorToast: React.FC<{ message: string; onClose?: () => void }> = ({ 
  message, 
  onClose 
}) => (
  <div className="flex items-center space-x-2 p-3 bg-red-50 border border-red-200 rounded-md">
    <AlertCircle className="w-5 h-5 text-red-500" />
    <span className="text-red-800 text-sm">{message}</span>
    {onClose && (
      <button onClick={onClose} className="ml-auto text-red-500 hover:text-red-700">
        <X className="w-4 h-4" />
      </button>
    )}
  </div>
)

export const SuccessToast: React.FC<{ message: string; onClose?: () => void }> = ({ 
  message, 
  onClose 
}) => (
  <div className="flex items-center space-x-2 p-3 bg-green-50 border border-green-200 rounded-md">
    <CheckCircle className="w-5 h-5 text-green-500" />
    <span className="text-green-800 text-sm">{message}</span>
    {onClose && (
      <button onClick={onClose} className="ml-auto text-green-500 hover:text-green-700">
        <X className="w-4 h-4" />
      </button>
    )}
  </div>
)

export const WarningToast: React.FC<{ message: string; onClose?: () => void }> = ({ 
  message, 
  onClose 
}) => (
  <div className="flex items-center space-x-2 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
    <AlertTriangle className="w-5 h-5 text-yellow-500" />
    <span className="text-yellow-800 text-sm">{message}</span>
    {onClose && (
      <button onClick={onClose} className="ml-auto text-yellow-500 hover:text-yellow-700">
        <X className="w-4 h-4" />
      </button>
    )}
  </div>
)

export const InfoToast: React.FC<{ message: string; onClose?: () => void }> = ({ 
  message, 
  onClose 
}) => (
  <div className="flex items-center space-x-2 p-3 bg-blue-50 border border-blue-200 rounded-md">
    <Info className="w-5 h-5 text-blue-500" />
    <span className="text-blue-800 text-sm">{message}</span>
    {onClose && (
      <button onClick={onClose} className="ml-auto text-blue-500 hover:text-blue-700">
        <X className="w-4 h-4" />
      </button>
    )}
  </div>
)