import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { API_URL } from '../lib/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem('fs_user')
      return stored ? JSON.parse(stored) : null
    } catch { return null }
  })
  const [token, setToken] = useState(() => localStorage.getItem('fs_token') || null)
  const [loading, setLoading] = useState(true)

  // Validate token on mount
  useEffect(() => {
    if (!token) { setLoading(false); return }
    fetch(`${API_URL}/api/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => { if (!r.ok) throw new Error('invalid'); return r.json() })
      .then(u => { setUser(u); localStorage.setItem('fs_user', JSON.stringify(u)) })
      .catch(() => { logout() })
      .finally(() => setLoading(false))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const persist = (tok, usr) => {
    setToken(tok); setUser(usr)
    localStorage.setItem('fs_token', tok)
    localStorage.setItem('fs_user', JSON.stringify(usr))
  }

  const logout = useCallback(() => {
    setToken(null); setUser(null)
    localStorage.removeItem('fs_token')
    localStorage.removeItem('fs_user')
  }, [])

  const signup = async (name, email, password) => {
    const res = await fetch(`${API_URL}/api/auth/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || 'Signup failed')
    persist(data.token, data.user)
    return data.user
  }

  const login = async (email, password) => {
    const res = await fetch(`${API_URL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || 'Login failed')
    persist(data.token, data.user)
    return data.user
  }

  /** Fetch wrapper that auto-attaches Bearer token and logs out on 401 */
  const authFetch = useCallback(async (url, options = {}) => {
    const headers = { ...options.headers }
    if (token) headers.Authorization = `Bearer ${token}`
    // Only set Content-Type for non-FormData bodies
    if (options.body && !(options.body instanceof FormData)) {
      headers['Content-Type'] = headers['Content-Type'] || 'application/json'
    }
    const res = await fetch(url, { ...options, headers })
    if (res.status === 401) { logout(); throw new Error('Session expired') }
    return res
  }, [token, logout])

  const value = {
    user, token, loading,
    login, signup, logout, authFetch,
    isAdmin: user?.role === 'admin',
    isAuthenticated: !!user && !!token,
    API_URL,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be inside AuthProvider')
  return ctx
}
