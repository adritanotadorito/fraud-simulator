import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { WS_URL } from '../lib/api'

// Real WebSocket mode — no more mock data
const MAX_FEED_LENGTH = 200

const WebSocketContext = createContext(null)

export function WebSocketProvider({ children }) {
  const [connectionStatus, setConnectionStatus] = useState('connecting')
  const [events, setEvents] = useState([])
  const [latestEvent, setLatestEvent] = useState(null)
  const wsRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)

  const pushEvent = useCallback((evt) => {
    setLatestEvent(evt)
    setEvents((prev) => {
      const next = [evt, ...prev]
      if (next.length > MAX_FEED_LENGTH) next.length = MAX_FEED_LENGTH
      return next
    })
  }, [])

  // Connect to real WebSocket endpoint
  useEffect(() => {
    let cancelled = false

    function connect() {
      setConnectionStatus((prev) => (prev === 'live' ? 'reconnecting' : 'connecting'))
      try {
        const ws = new WebSocket(WS_URL)
        wsRef.current = ws

        ws.onopen = () => {
          if (cancelled) return
          setConnectionStatus('live')
        }

        ws.onmessage = (msg) => {
          if (cancelled) return
          try {
            const parsed = JSON.parse(msg.data)
            pushEvent(parsed)
          } catch (err) {
            console.error('WS: failed to parse event', err)
          }
        }

        ws.onclose = () => {
          if (cancelled) return
          setConnectionStatus('offline')
          reconnectTimeoutRef.current = setTimeout(connect, 3000)
        }

        ws.onerror = () => {
          ws.close()
        }
      } catch (e) {
        // WebSocket constructor can fail if URL is invalid
        setConnectionStatus('offline')
        reconnectTimeoutRef.current = setTimeout(connect, 5000)
      }
    }

    connect()

    return () => {
      cancelled = true
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current)
      wsRef.current?.close()
    }
  }, [pushEvent])

  const value = {
    connectionStatus,
    events,
    latestEvent,
    isMock: false,
  }

  return <WebSocketContext.Provider value={value}>{children}</WebSocketContext.Provider>
}

export function useLiveFeed() {
  const ctx = useContext(WebSocketContext)
  if (!ctx) throw new Error('useLiveFeed must be used within a WebSocketProvider')
  return ctx
}
