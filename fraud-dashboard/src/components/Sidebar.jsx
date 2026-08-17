import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Clock, Activity, FileBarChart, Share2, ShieldCheck } from 'lucide-react'
import { useLiveFeed } from '../context/WebSocketContext'

// Graph page only shown once Riya's graph engine exists — flip this flag then.
const GRAPH_PAGE_ENABLED = false

const NAV_ITEMS = [
  { to: '/', label: 'Overview', icon: LayoutDashboard, end: true },
  { to: '/timeline', label: 'Attack Timeline', icon: Clock },
  { to: '/monitoring', label: 'Engine Health', icon: Activity },
  { to: '/reports', label: 'Audit Logs', icon: FileBarChart },
  ...(GRAPH_PAGE_ENABLED ? [{ to: '/graph', label: 'Graph Explorer', icon: Share2 }] : []),
]

export default function Sidebar() {
  const { connectionStatus } = useLiveFeed()

  return (
    <aside className="flex h-full w-60 shrink-0 flex-col border-r border-border bg-panel">
      <div className="flex items-center gap-2.5 border-b border-border px-5 py-4">
        <div className="flex h-7 w-7 items-center justify-center rounded-md border border-border bg-panel-raised text-text">
          <ShieldCheck className="h-4 w-4" strokeWidth={2} />
        </div>
        <div className="flex flex-col">
          <span className="font-sans text-xs font-semibold tracking-wide uppercase text-text">
            Risk Console
          </span>
          <span className="font-mono text-[10px] text-text-dim">
            v1.0.0 · Production
          </span>
        </div>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-4">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-panel-raised text-text border border-border/80 shadow-xs'
                  : 'text-text-muted hover:bg-panel-raised/50 hover:text-text'
              }`
            }
          >
            <Icon className="h-4 w-4 shrink-0 text-text-muted" strokeWidth={1.75} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <span className={`inline-flex h-2 w-2 rounded-full ${
            connectionStatus === 'live' ? 'bg-safe' : 'bg-flag'
          }`} />
          <span className="font-mono text-xs text-text-muted">
            {connectionStatus === 'live' ? 'Feed: Active (WS)' : `Status: ${connectionStatus}`}
          </span>
        </div>
      </div>
    </aside>
  )
}
