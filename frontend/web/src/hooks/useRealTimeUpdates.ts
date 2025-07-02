import { useState, useEffect, useCallback, useRef } from 'react'
import { aiServiceClient, PuzzleTaskStatus } from '../services/aiServiceClient'

interface Player {
  id: string
  name: string
  avatar?: string
  joinedAt: string
}

interface RealTimeUpdateOptions {
  gameId?: string
  pollingInterval?: number
  maxRetries?: number
  onStatusChange?: (status: PuzzleTaskStatus) => void
  onComplete?: (result: any) => void
  onError?: (error: string) => void
  onPlayerJoin?: (player: Player) => void
  onPlayerLeave?: (player: Player) => void
}

interface RealTimeState {
  isConnected: boolean
  isPolling: boolean
  taskId: string | null
  status: PuzzleTaskStatus | null
  error: string | null
  retryCount: number
}

export const useRealTimeUpdates = (options: RealTimeUpdateOptions = {}) => {
  const {
    pollingInterval = 2000,
    maxRetries = 5,
    onStatusChange,
    onComplete,
    onError
  } = options

  const [state, setState] = useState<RealTimeState>({
    isConnected: false,
    isPolling: false,
    taskId: null,
    status: null,
    error: null,
    retryCount: 0,
  })

  const pollingRef = useRef<NodeJS.Timeout | null>(null)
  const stopPollingRef = useRef<(() => void) | null>(null)

  // 상태 업데이트 헬퍼
  const updateState = useCallback((updates: Partial<RealTimeState>) => {
    setState(prev => ({ ...prev, ...updates }))
  }, [])

  // 폴링 중단
  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearTimeout(pollingRef.current)
      pollingRef.current = null
    }

    if (stopPollingRef.current) {
      stopPollingRef.current()
      stopPollingRef.current = null
    }

    updateState({
      isPolling: false,
      isConnected: false,
    })
  }, [updateState])

  // 작업 상태 폴링 시작
  const startPolling = useCallback(async (taskId: string) => {
    // 기존 폴링 중단
    stopPolling()

    updateState({
      taskId,
      isPolling: true,
      isConnected: true,
      error: null,
      retryCount: 0,
    })

    try {
      const stopPollingFn = await aiServiceClient.pollTaskStatus(
        taskId,
        (status) => {
          updateState({
            status,
            error: null,
            retryCount: 0,
          })
          onStatusChange?.(status)
        },
        (result) => {
          updateState({
            isPolling: false,
            isConnected: false,
          })
          onComplete?.(result)
        },
        (error) => {
          updateState({
            error,
            isPolling: false,
            isConnected: false,
          })
          onError?.(error)
        },
        pollingInterval
      )

      stopPollingRef.current = stopPollingFn
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '폴링 시작 실패'
      updateState({
        error: errorMessage,
        isPolling: false,
        isConnected: false,
      })
      onError?.(errorMessage)
    }
  }, [pollingInterval, stopPolling, updateState, onStatusChange, onComplete, onError])

  // 수동 상태 확인
  const checkStatus = useCallback(async (taskId?: string) => {
    const targetTaskId = taskId || state.taskId
    if (!targetTaskId) {
      onError?.('작업 ID가 없습니다')
      return null
    }

    try {
      const response = await aiServiceClient.getPuzzleStatus(targetTaskId)

      if (response.success) {
        const status = response.data!
        updateState({ status, error: null })
        onStatusChange?.(status)
        return status
      } else {
        const error = response.error || '상태 확인 실패'
        updateState({ error })
        onError?.(error)
        return null
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '상태 확인 중 오류'
      updateState({ error: errorMessage })
      onError?.(errorMessage)
      return null
    }
  }, [state.taskId, updateState, onStatusChange, onError])

  // 재시도
  const retry = useCallback(async () => {
    if (!state.taskId) {
      onError?.('재시도할 작업 ID가 없습니다')
      return
    }

    if (state.retryCount >= maxRetries) {
      onError?.('최대 재시도 횟수를 초과했습니다')
      return
    }

    updateState({
      retryCount: state.retryCount + 1,
      error: null,
    })

    await startPolling(state.taskId)
  }, [state.taskId, state.retryCount, maxRetries, updateState, startPolling, onError])

  // 연결 상태 확인
  const checkConnection = useCallback(async () => {
    try {
      const response = await aiServiceClient.healthCheck()
      const isHealthy = response.success

      updateState({
        isConnected: isHealthy,
        error: isHealthy ? null : '서비스 연결 실패',
      })

      return isHealthy
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '연결 확인 실패'
      updateState({
        isConnected: false,
        error: errorMessage,
      })
      return false
    }
  }, [updateState])

  // 컴포넌트 언마운트 시 정리
  useEffect(() => {
    return () => {
      stopPolling()
    }
  }, [stopPolling])

  // 주기적 연결 상태 확인 (옵션)
  useEffect(() => {
    let healthCheckInterval: NodeJS.Timeout

    if (state.isPolling) {
      healthCheckInterval = setInterval(() => {
        checkConnection()
      }, 30000) // 30초마다 헬스 체크
    }

    return () => {
      if (healthCheckInterval) {
        clearInterval(healthCheckInterval)
      }
    }
  }, [state.isPolling, checkConnection])

  return {
    // 상태
    ...state,

    // 액션
    startPolling,
    stopPolling,
    checkStatus,
    retry,
    checkConnection,

    // 유틸리티
    canRetry: state.retryCount < maxRetries,
    isActive: state.isPolling && state.isConnected,
    hasError: !!state.error,
  }
}

// WebSocket 기반 실시간 업데이트 (향후 구현용)
export const useWebSocketUpdates = (url?: string) => {
  const [socket, setSocket] = useState<WebSocket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  const connect = useCallback((wsUrl?: string) => {
    const targetUrl = wsUrl || url || 'ws://localhost:8004/ws'

    try {
      const ws = new WebSocket(targetUrl)

      ws.onopen = () => {
        setIsConnected(true)
        setError(null)
        console.log('WebSocket 연결됨')
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          setLastMessage(data)
        } catch (err) {
          console.error('WebSocket 메시지 파싱 실패:', err)
        }
      }

      ws.onclose = () => {
        setIsConnected(false)
        console.log('WebSocket 연결 종료')
      }

      ws.onerror = (event) => {
        setError('WebSocket 연결 오류')
        console.error('WebSocket 오류:', event)
      }

      setSocket(ws)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'WebSocket 연결 실패')
    }
  }, [url])

  const disconnect = useCallback(() => {
    if (socket) {
      socket.close()
      setSocket(null)
      setIsConnected(false)
    }
  }, [socket])

  const sendMessage = useCallback((message: any) => {
    if (socket && isConnected) {
      socket.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket이 연결되지 않음')
    }
  }, [socket, isConnected])

  useEffect(() => {
    return () => {
      disconnect()
    }
  }, [disconnect])

  return {
    socket,
    isConnected,
    lastMessage,
    error,
    connect,
    disconnect,
    sendMessage,
  }
}

export type { RealTimeState, RealTimeUpdateOptions }
