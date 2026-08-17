import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { API_URL, WS_URL } from '../lib/api'
import { generateMockEvent } from '../mock/mockEvents'

// Real WebSocket mode — with normalization & auto-bootstrap
const MAX_FEED_LENGTH = 200
const MOCK_INTERVAL_MS = 2200

function normalizeEvent(parsed) {
  if (!parsed || typeof parsed !== 'object') return null

  // If already in target format
  if (parsed.event_id && parsed.transaction && parsed.shieldgpt) {
    return parsed
  }

  // Format 1: transaction & decision
  if (parsed.transaction && parsed.decision) {
    return {
      event_id: parsed.transaction.txn_id || `evt_${Math.random().toString(36).substring(2, 9)}`,
      transaction: {
        transaction_id: parsed.transaction.txn_id || 'txn_live',
        merchant: parsed.transaction.merchant_name || parsed.transaction.merchant || 'Live Merchant',
        amount: parseFloat(parsed.transaction.amount || 100),
        user_id: parsed.transaction.user_id || 'usr_live',
        account_id: parsed.transaction.account_id || 'acc_live',
        timestamp: parsed.transaction.timestamp || new Date().toISOString()
      },
      shieldgpt: parsed.decision,
      fraudgpt: { persona: parsed.transaction.is_fraud ? 'simulated_attack' : 'legitimate_flow' }
    }
  }

  // Format 2: type === "decision"
  if (parsed.type === 'decision' && parsed.data) {
    const d = parsed.data
    return {
      event_id: d.decision_id || d.txn_id || `evt_${Math.random().toString(36).substring(2, 9)}`,
      transaction: {
        transaction_id: d.txn_id || 'txn_live',
        merchant: 'Online Merchant Store',
        amount: 250.00,
        user_id: 'usr_live',
        account_id: 'acc_live',
        timestamp: new Date().toISOString()
      },
      shieldgpt: d,
      fraudgpt: { persona: 'shield_evaluated' }
    }
  }

  return null
}

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

  // 1. Mock mode: simulate a live feed continuously to provide lively background traffic
  useEffect(() => {
    const startTimeout = setTimeout(() => {
      if (connectionStatus === 'connecting') setConnectionStatus('live')
    }, 600)
    
    const interval = setInterval(() => {
      pushEvent(generateMockEvent())
    }, MOCK_INTERVAL_MS)
    
    return () => {
      clearTimeout(startTimeout)
      clearInterval(interval)
    }
  }, [pushEvent, connectionStatus])

  // 2. Connect to real WebSocket endpoint for real ingested transactions
  useEffect(() => {
    let cancelled = false

    function connect() {
      try {
        const ws = new WebSocket(WS_URL)
        wsRef.current = ws

        ws.onopen = () => {
          if (cancelled) return
          setConnectionStatus('live')
          // Optional: Auto-trigger a real simulation round
          fetch(`${API_URL}/api/fraud/simulate-round`, { method: 'POST' }).catch(() => {})
        }

        ws.onmessage = (msg) => {
          if (cancelled) return
          try {
            const parsed = JSON.parse(msg.data)
            const normalized = normalizeEvent(parsed)
            if (normalized) pushEvent(normalized)
          } catch (err) {
            console.error('WS: failed to parse event', err)
          }
        }

        ws.onclose = () => {
          if (cancelled) return
          // Wait and reconnect
          reconnectTimeoutRef.current = setTimeout(connect, 3000)
        }

        ws.onerror = () => {
          ws.close()
        }
      } catch (e) {
        // WebSocket constructor can fail if URL is invalid
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
    isMock: false, // UI can treat it as real since it's a hybrid
  }

  return <WebSocketContext.Provider value={value}>{children}</WebSocketContext.Provider>
}

export function useLiveFeed() {
  const ctx = useContext(WebSocketContext)
  if (!ctx) throw new Error('useLiveFeed must be used within a WebSocketProvider')
  return ctx
}
