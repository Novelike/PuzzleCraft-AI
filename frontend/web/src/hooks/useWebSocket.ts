import { useEffect, useRef, useState, useCallback } from 'react'

interface UseWebSocketOptions {
  onMessage?: (data: any) => void
  onConnect?: () => void
  onDisconnect?: () => void
  onError?: (error: Event) => void
}

export const useWebSocket = (url: string, options: UseWebSocketOptions = {}) => {
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<any>(null)
  const ws = useRef<WebSocket | null>(null)
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null)
  const reconnectAttempts = useRef(0)
  const maxReconnectAttempts = 5

  const connect = useCallback(() => {
    try {
      ws.current = new WebSocket(url)
      
      ws.current.onopen = () => {
        setIsConnected(true)
        reconnectAttempts.current = 0
        options.onConnect?.()
        console.log('WebSocket 연결 성공:', url)
      }
      
      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          setLastMessage(data)
          options.onMessage?.(data)
        } catch (error) {
          console.error('WebSocket 메시지 파싱 오류:', error)
        }
      }
      
      ws.current.onclose = () => {
        setIsConnected(false)
        options.onDisconnect?.()
        console.log('WebSocket 연결 종료')
        
        // 자동 재연결 (최대 시도 횟수 제한)
        if (reconnectAttempts.current < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000)
          reconnectTimeout.current = setTimeout(() => {
            reconnectAttempts.current++
            console.log(`WebSocket 재연결 시도 ${reconnectAttempts.current}/${maxReconnectAttempts}`)
            connect()
          }, delay)
        } else {
          console.error('WebSocket 최대 재연결 시도 횟수 초과')
        }
      }
      
      ws.current.onerror = (error) => {
        console.error('WebSocket 오류:', error)
        options.onError?.(error)
      }
    } catch (error) {
      console.error('WebSocket 연결 실패:', error)
    }
  }, [url, options])

  const disconnect = useCallback(() => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current)
    }
    reconnectAttempts.current = maxReconnectAttempts // 재연결 방지
    ws.current?.close()
  }, [])

  const sendMessage = useCallback((data: any) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      try {
        ws.current.send(JSON.stringify(data))
      } catch (error) {
        console.error('WebSocket 메시지 전송 실패:', error)
      }
    } else {
      console.warn('WebSocket이 연결되지 않음. 메시지 전송 실패')
    }
  }, [])

  useEffect(() => {
    connect()
    return () => disconnect()
  }, [connect, disconnect])

  return {
    isConnected,
    lastMessage,
    sendMessage,
    disconnect,
    reconnectAttempts: reconnectAttempts.current
  }
}