import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Clock, Activity, FileBarChart, ShieldCheck, Database, Settings, LogOut } from 'lucide-react'
import { useLiveFeed } from '../context/WebSocketContext'
import { useAuth } from '../context/AuthContext'

export default function Navbar() {
  const { connectionStatus } = useLiveFeed()
  const { user, isAdmin, logout } = useAuth()

  const NAV_ITEMS = [
    { to: '/ops/overview',  label: 'Live Overview',         icon: LayoutDashboard },
    { to: '/ops/timeline',  label: 'Attack Simulator',      icon: Clock },
    { to: '/ops/monitoring',label: 'Engine Logs',           icon: Activity },
    { to: '/ops/real-data', label: 'Real & Simulated Data', icon: Database },
    { to: '/ops/reports',   label: 'Reports',               icon: FileBarChart },
    ...(isAdmin ? [
      { to: '/admin', label: 'Admin Portal', icon: Settings },
    ] : []),
  ]

  return (
    <header className="flex h-14 w-full shrink-0 items-center justify-between border-b border-border bg-panel px-6">
      {/* Left: Logo & Brand */}
      <div className="flex items-center gap-3">
        <div className="flex h-7 w-7 items-center justify-center rounded-md border border-border bg-panel-raised text-text">
          <ShieldCheck className="h-4 w-4" strokeWidth={2} />
        </div>
        <div className="flex flex-col">
          <span className="font-sans text-xs font-semibold tracking-wide uppercase text-text">
            Risk Operations
          </span>
          <span className="font-mono text-[9px] text-text-dim">
            Fraud Shield AI
          </span>
        </div>
      </div>

      {/* Center: Horizontal Navigation Tabs */}
      <nav className="flex items-center gap-1">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex items-center gap-2 rounded-md px-3 py-1.5 font-sans text-xs font-medium transition-colors ${
                isActive
                  ? 'bg-panel-raised text-text border border-border/80 shadow-xs'
                  : 'text-text-muted hover:bg-panel-raised/50 hover:text-text'
              }`
            }
          >
            <Icon className="h-3.5 w-3.5 shrink-0 text-text-muted" strokeWidth={1.75} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Right: User info, feed status, logout */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5 rounded-md border border-border bg-panel-raised px-2.5 py-1 font-mono text-[11px] text-text-muted">
          <span className={`h-1.5 w-1.5 rounded-full ${
            connectionStatus === 'live' ? 'bg-safe' : 'bg-flag'
          }`} />
          <span>{connectionStatus === 'live' ? 'WS: Live' : connectionStatus}</span>
        </div>

        {user && (
          <div className="flex items-center gap-2">
            <span className="font-mono text-[11px] text-text-dim">{user.email}</span>
            {isAdmin && (
              <span className="rounded-full bg-flag-dim px-1.5 py-0.5 font-mono text-[9px] text-flag font-semibold uppercase">
                admin
              </span>
            )}
            <button
              onClick={logout}
              className="flex items-center gap-1 rounded-md border border-border bg-panel-raised px-2 py-1 font-mono text-[11px] text-text-dim hover:text-text transition"
              title="Sign out"
            >
              <LogOut className="h-3 w-3" />
            </button>
          </div>
        )}
      </div>
    </header>
  )
}
