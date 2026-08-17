import os

filepath = 'fraud-dashboard/src/pages/RealData.jsx'
with open(filepath, 'r') as f:
    lines = f.readlines()

# 1. Add imports at the top
for i, line in enumerate(lines):
    if "import { API_URL }" in line:
        lines.insert(i+1, "import { useAuth } from '../context/AuthContext'\n")
        lines.insert(i+2, "import Timeline from './Timeline'\n")
        lines.insert(i+3, "import Monitoring from './Monitoring'\n")
        break

# 2. Add const { authFetch } = useAuth()
for i, line in enumerate(lines):
    if "export default function RealData() {" in line:
        lines.insert(i+1, "  const { authFetch } = useAuth()\n")
        break

content = "".join(lines)

# 3. Fix authFetch in doUpload
upload_old = """      const fd = new FormData()
      fd.append('file', file)
      const token = localStorage.getItem('token')
      const headers = token ? { 'Authorization': `Bearer ${token}` } : {}
      const res = await fetch(`${API_URL}/api/transactions/upload-file`, {
        method: 'POST', body: fd, headers
      })"""
upload_new = """      const fd = new FormData()
      fd.append('file', file)
      const res = await authFetch(`${API_URL}/api/transactions/upload-file`, {
        method: 'POST', body: fd
      })"""
content = content.replace(upload_old, upload_new)

listres_old = """      const listRes = await fetch(
        `${API_URL}/api/transactions/uploaded?source=${encodeURIComponent(source)}&limit=10000`,
        { headers }
      )"""
listres_new = """      const listRes = await authFetch(
        `${API_URL}/api/transactions/uploaded?source=${encodeURIComponent(source)}&limit=10000`
      )"""
content = content.replace(listres_old, listres_new)

# 4. activeSubTab defaults to 'data'
content = content.replace("const [activeSubTab, setActiveSubTab] = useState('stream')", "const [activeSubTab, setActiveSubTab] = useState('data')")
content = content.replace("setActiveSubTab('stream')", "setActiveSubTab('data')")


# 5. Fix tabs in the render loop.
# Currently the tabs are: 'stream', 'timeline', 'engine', 'audit'
# Let's just modify the `hasUploaded &&` tabs to instead be always visible top-level tabs.
render_code = """  return (
    <div className="flex h-full flex-col overflow-hidden bg-bg">
      <div className="flex-1 overflow-y-auto space-y-5 p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-md border border-border bg-panel-raised">
              <Database className="h-4 w-4 text-text-muted" />
            </div>
            <div>
              <h1 className="font-sans text-sm font-semibold text-text">Real & Simulated Data</h1>
              <p className="font-mono text-xs text-text-dim mt-0.5">
                Unified environment for live events, datasets, and simulations
              </p>
            </div>
          </div>
          {activeSubTab === 'data' && hasUploaded && (
            <button
              onClick={startNewUpload}
              className="flex items-center gap-1.5 rounded-md border border-border bg-panel-raised px-3 py-1.5 font-sans text-xs text-text-muted hover:text-text transition-colors"
            >
              <FileUp className="h-3.5 w-3.5" />
              New Upload
            </button>
          )}
        </div>

        <div className="flex items-center border-b border-border">
          {[
            { id: 'data',     label: 'Data Upload & Stream', icon: Database },
            { id: 'timeline', label: 'Attack Simulator',     icon: ShieldAlert },
            { id: 'engine',   label: 'Engine Logs',          icon: Terminal },
          ].map((tab) => {
            const Icon = tab.icon
            const isActive = activeSubTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => setActiveSubTab(tab.id)}
                className={`flex items-center gap-2 border-b-2 px-5 py-3 font-sans text-xs font-semibold transition-all ${
                  isActive
                    ? 'border-accent text-accent bg-accent/5'
                    : 'border-transparent text-text-dim hover:text-text-muted hover:bg-panel-raised/40'
                }`}
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span>{tab.label}</span>
              </button>
            )
          })}
        </div>

        {activeSubTab === 'data' && (
          <div className="space-y-5">
            {!hasUploaded && ("""

# Replace from `  return (` up to `            {!hasUploaded && (`
start_idx = content.find("  return (\n    <div className=\"flex h-full flex-col overflow-hidden bg-bg\">")
end_idx = content.find("            <div className=\"rounded-xl border border-border bg-panel p-6 animate-feed-row-in\">")

before_return = content[:start_idx]
after_upload_box = content[end_idx:]

# The after_upload_box has:
#             <div className="rounded-xl border border-border bg-panel p-6 animate-feed-row-in">
#               ...
#               ...
#         )}
# 
#         {hasUploaded && (
#           <div className="space-y-5">
#             <div className="flex items-center border-b border-border">
#                ... OLD TABS ...
#             </div>
#             {activeSubTab === 'stream' && (
#                ... STREAM VIEW ...

# We need to remove the old tabs and the `hasUploaded &&` and `{activeSubTab === 'stream' && (` block wrappers.
# So I'll do string replacements on `after_upload_box`

after_upload_box = after_upload_box.replace("""        {hasUploaded && (
          <div className="space-y-5">
            <div className="flex items-center border-b border-border">
              {[
                { id: 'stream',   label: 'Transactions Stream', icon: Activity,      badge: rows.length },
                { id: 'timeline', label: 'Attack Timeline',     icon: ShieldAlert,   badge: timelineEvents.length, badgeColor: 'text-block bg-block/15' },
                { id: 'engine',   label: 'Engine Logs',         icon: Terminal,      badge: engineLogs.length },
                { id: 'audit',    label: 'Audit Logs',          icon: ClipboardList, badge: 'VERIFIED', badgeColor: 'text-safe bg-safe/15' },
              ].map((tab) => {
                const Icon = tab.icon
                const isActive = activeSubTab === tab.id
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveSubTab(tab.id)}
                    className={`flex items-center gap-2 border-b-2 px-5 py-3 font-sans text-xs font-semibold transition-all ${
                      isActive
                        ? 'border-accent text-accent bg-accent/5'
                        : 'border-transparent text-text-dim hover:text-text-muted hover:bg-panel-raised/40'
                    }`}
                  >
                    <Icon className="h-4 w-4 shrink-0" />
                    <span>{tab.label}</span>
                    {tab.badge !== undefined && (
                      <span className={`ml-1 rounded-full px-2 py-0.5 font-mono text-[10px] font-bold ${
                        tab.badgeColor || (isActive ? 'bg-accent/20 text-accent' : 'bg-panel-raised text-text-dim')
                      }`}>
                        {tab.badge}
                      </span>
                    )}
                  </button>
                )
              })}
            </div>

            {activeSubTab === 'data' && (""", """            {hasUploaded && (""")

# Add the timeline and monitoring components right before the closing divs
new_end = """              </div>
            )}
          </div>
        )}

        {activeSubTab === 'timeline' && (
          <div className="min-h-[600px] -m-6 h-[calc(100vh-160px)]">
            <Timeline />
          </div>
        )}

        {activeSubTab === 'engine' && (
          <div className="min-h-[600px] -m-6 h-[calc(100vh-160px)]">
            <Monitoring />
          </div>
        )}

      </div>
    </div>
  )
}
"""

after_upload_box = after_upload_box.replace("""              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
""", new_end)

final_content = before_return + render_code + after_upload_box

with open(filepath, 'w') as f:
    f.write(final_content)

print("Done")
