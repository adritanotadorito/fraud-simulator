import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { generateMockEvent } from '../mock/mockEvents'

// Flip to false once Riya's real WebSocket endpoint is up.
// Real endpoint URL comes from VITE_WS_URL (set in .env, see .env.example).
const USE_MOCK = true
const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8080/ws/feed'
const MAX_FEED_LENGTH = 200
const MOCK_INTERVAL_MS = 2200

const WebSocketContext = createContext(null)

export function WebSocketProvider({ children }) {
  const [connectionStatus, setConnectionStatus] = useState('connecting') // connecting | live | reconnecting | offline
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

  // --- Mock mode: simulate a live feed so every downstream component can be
  // built and demoed before Riya's backend event stream exists.
  useEffect(() => {
    if (!USE_MOCK) return
    setConnectionStatus('connecting')
    const startTimeout = setTimeout(() => setConnectionStatus('live'), 600)
    const interval = setInterval(() => {
      pushEvent(generateMockEvent())
    }, MOCK_INTERVAL_MS)
    return () => {
      clearTimeout(startTimeout)
      clearInterval(interval)
    }
  }, [pushEvent])

  // --- Real mode: connect to Riya's WebSocket stub / production endpoint.
  useEffect(() => {
    if (USE_MOCK) return

    let cancelled = false

    function connect() {
      setConnectionStatus((prev) => (prev === 'live' ? 'reconnecting' : 'connecting'))
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
    isMock: USE_MOCK,
  }

  return <WebSocketContext.Provider value={value}>{children}</WebSocketContext.Provider>
}

export function useLiveFeed() {
  const ctx = useContext(WebSocketContext)
  if (!ctx) throw new Error('useLiveFeed must be used within a WebSocketProvider')
  return ctx
}
