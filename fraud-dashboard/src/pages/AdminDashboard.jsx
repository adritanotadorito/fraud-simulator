import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  Users, Database, ShieldAlert, ShieldX, AlertTriangle,
  LayoutDashboard, Clock, Activity, FileBarChart,
  ChevronRight, RefreshCw, UserCheck, UserX
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { API_URL } from '../lib/api'

export default function AdminDashboard() {
  const { authFetch } = useAuth()

  const [stats, setStats] = useState(null)
  const [users, setUsers] = useState([])
  const [uploads, setUploads] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('overview')

  const fetchAll = async () => {
    setLoading(true)
    try {
      const [statsRes, usersRes, uploadsRes] = await Promise.all([
        authFetch(`${API_URL}/api/admin/stats`),
        authFetch(`${API_URL}/api/admin/users`),
        authFetch(`${API_URL}/api/admin/uploads`),
      ])
      if (statsRes.ok) setStats(await statsRes.json())
      if (usersRes.ok) setUsers(await usersRes.json())
      if (uploadsRes.ok) setUploads(await uploadsRes.json())
    } catch (e) {
      console.error('Admin fetch failed:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchAll() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const toggleRole = async (userId, currentRole) => {
    const newRole = currentRole === 'admin' ? 'user' : 'admin'
    try {
      const res = await authFetch(`${API_URL}/api/admin/users/${userId}/role?role=${newRole}`, { method: 'PATCH' })
      if (res.ok) {
        setUsers(prev => prev.map(u => u.id === userId ? { ...u, role: newRole } : u))
      }
    } catch (e) {
      console.error('Role update failed:', e)
    }
  }

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center text-text-dim font-mono text-sm">
        <RefreshCw className="h-4 w-4 animate-spin mr-2" /> Loading admin panel...
      </div>
    )
  }

  const statCards = [
    { label: 'Total Users', value: stats?.total_users || 0, icon: Users, color: 'text-accent' },
    { label: 'Uploaded Txns', value: stats?.uploaded_transactions || 0, icon: Database, color: 'text-safe' },
    { label: 'Total Decisions', value: stats?.total_decisions || 0, icon: ShieldAlert, color: 'text-flag' },
    { label: 'Blocked', value: stats?.blocked || 0, icon: ShieldX, color: 'text-block' },
    { label: 'Flagged', value: stats?.flagged || 0, icon: AlertTriangle, color: 'text-flag' },
  ]

  const opsLinks = [
    { to: '/', label: 'User Dashboard', icon: Database },
    { to: '/ops/overview', label: 'Live Overview', icon: LayoutDashboard },
    { to: '/ops/timeline', label: 'Attack Timeline', icon: Clock },
    { to: '/ops/monitoring', label: 'Engine Logs', icon: Activity },
    { to: '/ops/reports', label: 'Audit Reports', icon: FileBarChart },
  ]

  return (
    <div className="flex h-full flex-col overflow-auto p-6 gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-sans text-lg font-semibold text-text">Admin Dashboard</h1>
          <p className="font-mono text-xs text-text-dim">Platform management & analytics</p>
        </div>
        <button onClick={fetchAll} className="flex items-center gap-1.5 rounded-md border border-border bg-panel-raised px-3 py-1.5 font-sans text-xs text-text-muted hover:text-text transition">
          <RefreshCw className="h-3 w-3" /> Refresh
        </button>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-5 gap-3">
        {statCards.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="rounded-lg border border-border bg-panel p-4 space-y-2">
            <div className="flex items-center gap-2">
              <Icon className={`h-4 w-4 ${color}`} />
              <span className="font-mono text-[10px] text-text-dim uppercase tracking-wider">{label}</span>
            </div>
            <div className="font-mono text-2xl font-bold text-text">{value.toLocaleString()}</div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-border pb-1">
        {['overview', 'users', 'uploads'].map(t => (
          <button
            key={t}
            onClick={() => setActiveTab(t)}
            className={`rounded-md px-3 py-1.5 font-sans text-xs font-medium transition ${
              activeTab === t
                ? 'bg-panel-raised text-text border border-border/80'
                : 'text-text-muted hover:bg-panel-raised/50 hover:text-text'
            }`}
          >
            {t === 'overview' ? 'Quick Links' : t === 'users' ? `Users (${users.length})` : `Uploads (${uploads.length})`}
          </button>
        ))}
      </div>

      {/* ── Overview Tab ──────────────────────────────────────────────── */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-2 gap-3">
          {opsLinks.map(({ to, label, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              className="flex items-center justify-between rounded-lg border border-border bg-panel px-4 py-3 transition hover:bg-panel-raised"
            >
              <div className="flex items-center gap-3">
                <Icon className="h-4 w-4 text-text-muted" />
                <span className="font-sans text-sm text-text">{label}</span>
              </div>
              <ChevronRight className="h-4 w-4 text-text-dim" />
            </Link>
          ))}
        </div>
      )}

      {/* ── Users Tab ─────────────────────────────────────────────────── */}
      {activeTab === 'users' && (
        <div className="rounded-lg border border-border overflow-hidden">
          <table className="w-full text-left font-mono text-xs">
            <thead className="bg-panel-raised text-text-dim">
              <tr>
                <th className="px-4 py-2.5 font-medium">Name</th>
                <th className="px-4 py-2.5 font-medium">Email</th>
                <th className="px-4 py-2.5 font-medium">Role</th>
                <th className="px-4 py-2.5 font-medium">Created</th>
                <th className="px-4 py-2.5 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map(u => (
                <tr key={u.id} className="border-t border-border hover:bg-panel-raised/50 transition">
                  <td className="px-4 py-2.5 text-text">{u.name || '-'}</td>
                  <td className="px-4 py-2.5 text-text-muted">{u.email}</td>
                  <td className="px-4 py-2.5">
                    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${
                      u.role === 'admin' ? 'bg-flag-dim text-flag' : 'bg-safe-dim text-safe'
                    }`}>
                      {u.role === 'admin' ? <UserCheck className="h-3 w-3" /> : <UserX className="h-3 w-3" />}
                      {u.role}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-text-dim">{u.created_at?.slice(0, 10) || '-'}</td>
                  <td className="px-4 py-2.5 text-right">
                    <button
                      onClick={() => toggleRole(u.id, u.role)}
                      className="rounded-md border border-border bg-panel-raised px-2 py-1 text-[10px] text-text-muted hover:text-text transition"
                    >
                      {u.role === 'admin' ? 'Demote' : 'Promote'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Uploads Tab ───────────────────────────────────────────────── */}
      {activeTab === 'uploads' && (
        <div className="rounded-lg border border-border overflow-hidden">
          <table className="w-full text-left font-mono text-xs">
            <thead className="bg-panel-raised text-text-dim">
              <tr>
                <th className="px-4 py-2.5 font-medium">Source</th>
                <th className="px-4 py-2.5 font-medium">Uploader</th>
                <th className="px-4 py-2.5 font-medium">Rows</th>
                <th className="px-4 py-2.5 font-medium">Flagged</th>
                <th className="px-4 py-2.5 font-medium">Total Amount</th>
                <th className="px-4 py-2.5 font-medium">Last Upload</th>
              </tr>
            </thead>
            <tbody>
              {uploads.map((u, i) => (
                <tr key={i} className="border-t border-border hover:bg-panel-raised/50 transition">
                  <td className="px-4 py-2.5 text-text">{u.source?.replace('upload:', '') || '-'}</td>
                  <td className="px-4 py-2.5 text-text-muted">{u.uploader_email || 'unknown'}</td>
                  <td className="px-4 py-2.5 text-text">{u.row_count}</td>
                  <td className="px-4 py-2.5 text-flag">{u.flagged_fraud}</td>
                  <td className="px-4 py-2.5 text-text">${(u.total_amount || 0).toLocaleString()}</td>
                  <td className="px-4 py-2.5 text-text-dim">{u.last_uploaded?.slice(0, 10) || '-'}</td>
                </tr>
              ))}
              {uploads.length === 0 && (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-text-dim">No uploads yet</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
