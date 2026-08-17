import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { ShieldCheck, LogIn, Eye, EyeOff } from 'lucide-react'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPwd, setShowPwd] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(''); setLoading(true)
    try {
      await login(email, password)
      navigate('/')
    } catch (err) {
      setError(err.message || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg px-4">
      <div className="w-full max-w-sm space-y-6">
        {/* Brand */}
        <div className="flex flex-col items-center gap-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-panel-raised">
            <ShieldCheck className="h-5 w-5 text-text" strokeWidth={2} />
          </div>
          <h1 className="font-sans text-lg font-semibold text-text">Fraud Shield AI</h1>
          <p className="font-mono text-xs text-text-dim">Sign in to continue</p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4 rounded-lg border border-border bg-panel p-6">
          {error && (
            <div className="rounded-md border border-block/30 bg-block-dim px-3 py-2 font-mono text-xs text-block">
              {error}
            </div>
          )}

          <div className="space-y-1.5">
            <label className="block font-sans text-xs font-medium text-text-muted" htmlFor="login-email">Email</label>
            <input
              id="login-email"
              type="email"
              required
              value={email}
              onChange={e => setEmail(e.target.value)}
              className="w-full rounded-md border border-border bg-panel-raised px-3 py-2 font-mono text-sm text-text outline-none transition focus:border-accent placeholder:text-text-dim"
              placeholder="you@example.com"
            />
          </div>

          <div className="space-y-1.5">
            <label className="block font-sans text-xs font-medium text-text-muted" htmlFor="login-password">Password</label>
            <div className="relative">
              <input
                id="login-password"
                type={showPwd ? 'text' : 'password'}
                required
                value={password}
                onChange={e => setPassword(e.target.value)}
                className="w-full rounded-md border border-border bg-panel-raised px-3 py-2 pr-9 font-mono text-sm text-text outline-none transition focus:border-accent placeholder:text-text-dim"
                placeholder="Min 6 characters"
              />
              <button type="button" onClick={() => setShowPwd(p => !p)} className="absolute right-2.5 top-2.5 text-text-dim hover:text-text">
                {showPwd ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-md border border-border bg-accent px-4 py-2 font-sans text-sm font-medium text-bg transition hover:bg-accent/90 disabled:opacity-50"
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <p className="text-center font-mono text-xs text-text-dim">
          No account?{' '}
          <Link to="/signup" className="text-text-muted hover:text-text underline underline-offset-2">
            Sign up
          </Link>
        </p>
      </div>
    </div>
  )
}
