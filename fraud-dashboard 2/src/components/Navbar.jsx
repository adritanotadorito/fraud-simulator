import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Clock, Activity, FileBarChart, ShieldCheck } from 'lucide-react'
import { useLiveFeed } from '../context/WebSocketContext'

const NAV_ITEMS = [
  { to: '/', label: 'Overview', icon: LayoutDashboard, end: true },
  { to: '/timeline', label: 'Attack Timeline', icon: Clock },
  { to: '/monitoring', label: 'Engine Logs', icon: Activity },
  { to: '/reports', label: 'Audit Logs', icon: FileBarChart },
]

export default function Navbar() {
  const { connectionStatus } = useLiveFeed()

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

      {/* Right: Environment & Feed Status */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5 rounded-md border border-border bg-panel-raised px-2.5 py-1 font-mono text-[11px] text-text-muted">
          <span className={`h-1.5 w-1.5 rounded-full ${
            connectionStatus === 'live' ? 'bg-safe' : 'bg-flag'
          }`} />
          <span>{connectionStatus === 'live' ? 'WS: Live' : connectionStatus}</span>
        </div>
        <span className="font-mono text-xs text-text-dim">
          {new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })}
        </span>
      </div>
    </header>
  )
}
