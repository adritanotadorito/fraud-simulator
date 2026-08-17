import { useState, useEffect, useRef, useCallback } from 'react'
import {
  Database, Upload, X, FileText, FileJson,
  RefreshCw, Search, Filter, Info, CheckCircle2, Ban,
  Play, Pause, SkipBack, ShieldCheck, AlertTriangle, ShieldX,
  Zap, CloudUpload, FileUp, Activity, Terminal, ClipboardList,
  ShieldAlert, Clock, ChevronRight, Download, Check, FileCheck,
  FolderOpen
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { API_URL } from '../lib/api'

// ─── Helpers ──────────────────────────────────────────────────────────────────
const DECISION_ICONS = { ALLOW: ShieldCheck, FLAG: AlertTriangle, BLOCK: ShieldX }

const SPEEDS = [
  { label: '0.5x', ms: 2000 },
  { label: '1x',   ms: 1000 },
  { label: '2x',   ms: 500  },
  { label: '5x',   ms: 200  },
]

// ─── Component ────────────────────────────────────────────────────────────────
export default function UserDashboard() {
  const { authFetch } = useAuth()

  // Upload state
  const [dragOver, setDragOver]     = useState(false)
  const [file, setFile]             = useState(null)
  const [uploading, setUploading]   = useState(false)
  const [uploadResult, setUploadResult] = useState(null)
  const [uploadErr, setUploadErr]   = useState(null)
  const fileRef                     = useRef(null)

  // My previous uploads
  const [myUploads, setMyUploads]   = useState([])
  const [loadingUploads, setLoadingUploads] = useState(true)

  // Scoring state
  const [scoring, setScoring]       = useState(false)
  const [scoringProgress, setScoringProgress] = useState('')

  // Uploaded transactions buffer
  const [uploadedTxns, setUploadedTxns] = useState([])
  const [decisions, setDecisions]   = useState(new Map())  // txn_id -> decision
  const [hasUploaded, setHasUploaded]   = useState(false)

  // Sub-tab state
  const [activeSubTab, setActiveSubTab] = useState('stream')

  // Stream state
  const [rows, setRows]             = useState([])
  const [offset, setOffset]         = useState(0)
  const [playing, setPlaying]       = useState(false)
  const [speedIdx, setSpeedIdx]     = useState(1)
  const [latestId, setLatestId]     = useState(null)
  const timerRef                    = useRef(null)
  const offsetRef                   = useRef(0)

  // Table state
  const [filter, setFilter]         = useState('ALL')
  const [search, setSearch]         = useState('')
  const [selected, setSelected]     = useState(null)

  // Log filter
  const [logFilter, setLogFilter]   = useState('ALL')

  useEffect(() => { offsetRef.current = offset }, [offset])

  // ── Fetch my previous uploads on mount ──────────────────────────────────
  useEffect(() => {
    authFetch(`${API_URL}/api/transactions/my-uploads`)
      .then(r => r.ok ? r.json() : [])
      .then(setMyUploads)
      .catch(() => setMyUploads([]))
      .finally(() => setLoadingUploads(false))
  }, [authFetch])

  // ── Load a previous upload ─────────────────────────────────────────────
  const loadPreviousUpload = async (source) => {
    setUploading(true); setUploadErr(null)
    try {
      const res = await authFetch(`${API_URL}/api/transactions/uploaded?source=${encodeURIComponent(source)}&limit=10000`)
      if (!res.ok) throw new Error('Failed to load upload')
      const txns = await res.json()
      setUploadedTxns(txns)
      setUploadResult({ source, inserted: txns.length })
      setHasUploaded(true)
      setActiveSubTab('stream')
      setRows([]); setOffset(0); setPlaying(false); setLatestId(null); setSelected(null)

      // Score them
      await scoreDataset(source, txns)
    } catch (e) {
      setUploadErr(e.message)
    } finally {
      setUploading(false)
    }
  }

  // ── Score a dataset via the real backend pipeline ────────────────────────
  const scoreDataset = async (source, txns) => {
    setScoring(true); setScoringProgress(`Scoring ${txns.length} transactions...`)
    try {
      const res = await authFetch(`${API_URL}/api/transactions/score-uploaded?source=${encodeURIComponent(source)}`, {
        method: 'POST',
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || 'Scoring failed')
      }
      const data = await res.json()
      const map = new Map()
      for (const r of (data.results || [])) {
        map.set(r.txn_id, r)
      }
      setDecisions(map)
      setScoringProgress(`Scored ${map.size} transactions`)
    } catch (e) {
      setScoringProgress(`Scoring error: ${e.message}`)
    } finally {
      setScoring(false)
    }
  }

  // ── Upload handler ─────────────────────────────────────────────────────
  const doUpload = async () => {
    if (!file) return
    setUploading(true); setUploadResult(null); setUploadErr(null)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await authFetch(`${API_URL}/api/transactions/upload-file`, {
        method: 'POST', body: fd,
      })
      const d = await res.json()
      if (!res.ok) {
        setUploadErr(d.detail || 'Upload failed')
        return
      }
      setUploadResult(d)
      setHasUploaded(true)
      setActiveSubTab('stream')

      // Fetch uploaded txns
      const source = d.source
      const listRes = await authFetch(
        `${API_URL}/api/transactions/uploaded?source=${encodeURIComponent(source)}&limit=10000`
      )
      const txns = listRes.ok ? await listRes.json() : (d.preview || [])
      setUploadedTxns(txns)
      setRows([]); setOffset(0); setPlaying(false); setLatestId(null); setSelected(null)

      // Score via real backend
      await scoreDataset(source, txns)

      // Refresh uploads list
      authFetch(`${API_URL}/api/transactions/my-uploads`)
        .then(r => r.ok ? r.json() : [])
        .then(setMyUploads)
        .catch(() => {})
    } catch (e) {
      setUploadErr(e.message)
    } finally {
      setUploading(false)
    }
  }

  // ── Streaming timer ───────────────────────────────────────────────────
  useEffect(() => {
    clearInterval(timerRef.current)
    if (!playing || uploadedTxns.length === 0) return

    const step = () => {
      const cur = offsetRef.current
      if (cur >= uploadedTxns.length) { setPlaying(false); return }
      const txn = uploadedTxns[cur]
      const dec = decisions.get(txn.txn_id) || { decision: 'ALLOW', risk_score: 0, confidence: 0, reasons: [], explanation: '' }
      const enriched = { ...txn, _score: dec }
      setRows(prev => [enriched, ...prev])
      setLatestId(txn.txn_id)
      setOffset(cur + 1)
    }

    step()
    timerRef.current = setInterval(step, SPEEDS[speedIdx].ms)
    return () => clearInterval(timerRef.current)
  }, [playing, speedIdx, uploadedTxns, decisions])

  // ── Reset / New Upload ────────────────────────────────────────────────
  const resetStream = () => {
    clearInterval(timerRef.current)
    setPlaying(false); setOffset(0); setRows([]); setLatestId(null); setSelected(null)
  }

  const startNewUpload = () => {
    resetStream()
    setFile(null); setUploadResult(null); setUploadErr(null)
    setUploadedTxns([]); setHasUploaded(false); setDecisions(new Map())
    setActiveSubTab('stream')
  }

  // ── Metrics ───────────────────────────────────────────────────────────
  const blocked   = rows.filter(r => r._score?.decision === 'BLOCK').length
  const flagged   = rows.filter(r => r._score?.decision === 'FLAG').length
  const allowed   = rows.length - blocked - flagged
  const total     = uploadedTxns.length
  const progress  = total > 0 ? Math.min((offset / total) * 100, 100) : 0
  const done      = offset >= total && total > 0

  // ── Filtered table ────────────────────────────────────────────────────
  const visible = rows.filter(r => {
    const dec = r._score?.decision || 'ALLOW'
    const ok  = filter === 'ALL' || dec === filter
    const q   = search.toLowerCase()
    const hit = !q
      || r.txn_id?.toLowerCase().includes(q)
      || r.merchant_name?.toLowerCase().includes(q)
      || String(r.amount).includes(q)
    return ok && hit
  })

  // ── Timeline events from scored rows ──────────────────────────────────
  const timelineEvents = rows
    .filter(r => r._score?.decision === 'BLOCK' || r._score?.decision === 'FLAG')
    .map((r, idx) => ({
      id: r.txn_id || `evt_${idx}`,
      timestamp: r.timestamp || new Date().toISOString(),
      decision: r._score?.decision || 'FLAG',
      riskScore: r._score?.risk_score || 0,
      merchant: r.merchant_name || 'Merchant',
      location: r.geo?.city || 'Unknown',
      amount: r.amount || 0,
      reasoning: r._score?.explanation || r._score?.reasons?.join(', ') || 'No details',
    }))

  // ── Engine Logs from scored rows ──────────────────────────────────────
  const engineLogs = rows.flatMap((r) => {
    const dec = r._score?.decision || 'ALLOW'
    const risk = ((r._score?.risk_score || 0) * 100).toFixed(0)
    const ts = r.timestamp || new Date().toISOString()
    const logs = [
      { ts, level: 'INFO', engine: 'Orchestrator', msg: `Txn ${(r.txn_id || '').slice(0, 12)} | Decision: ${dec} | Risk: ${risk}%` }
    ]
    const es = r._score?.engine_scores || {}
    for (const [eng, data] of Object.entries(es)) {
      if (eng === 'fusion') continue
      const score = typeof data === 'object' ? data.score : data
      if (score !== undefined) {
        const sigs = Array.isArray(data?.signals) ? data.signals.join(', ') : ''
        const level = score > 0.6 ? 'ERROR' : score > 0.3 ? 'WARN' : 'INFO'
        logs.push({ ts, level, engine: eng, msg: `Score: ${(score * 100).toFixed(0)}%${sigs ? ' | ' + sigs : ''}` })
      }
    }
    return logs
  })

  const filteredLogs = logFilter === 'ALL' ? engineLogs : engineLogs.filter(l => l.level === logFilter)

  // ── RENDER ────────────────────────────────────────────────────────────

  // ── My Previous Uploads panel (before upload zone) ────────────────────
  if (!hasUploaded) {
    return (
      <div className="flex h-full flex-col overflow-auto p-6 gap-6">
        {/* Previous uploads */}
        {myUploads.length > 0 && (
          <div className="rounded-lg border border-border bg-panel p-5 space-y-3">
            <div className="flex items-center gap-2 text-text font-sans text-sm font-semibold">
              <FolderOpen className="h-4 w-4 text-text-muted" />
              My Previous Uploads
            </div>
            <div className="space-y-2">
              {myUploads.map(u => (
                <button
                  key={u.source}
                  onClick={() => loadPreviousUpload(u.source)}
                  disabled={uploading}
                  className="flex w-full items-center justify-between rounded-md border border-border bg-panel-raised px-4 py-3 text-left transition hover:bg-border/30 disabled:opacity-50"
                >
                  <div>
                    <div className="font-mono text-xs text-text">{u.source.replace('upload:', '')}</div>
                    <div className="font-mono text-[11px] text-text-dim mt-0.5">
                      {u.row_count} rows | {u.flagged_fraud} flagged | ${u.total_amount?.toLocaleString()}
                    </div>
                  </div>
                  <ChevronRight className="h-4 w-4 text-text-dim" />
                </button>
              ))}
            </div>
          </div>
        )}
        {loadingUploads && myUploads.length === 0 && (
          <div className="text-center font-mono text-xs text-text-dim py-4">Loading uploads...</div>
        )}

        {/* Upload zone */}
        <div className="rounded-lg border border-border bg-panel p-6 space-y-4">
          <div className="flex items-center gap-2 text-text font-sans text-sm font-semibold">
            <CloudUpload className="h-4 w-4 text-text-muted" />
            Upload Transaction Data
          </div>

          <div
            onDragOver={e => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={e => { e.preventDefault(); setDragOver(false); const f = e.dataTransfer.files[0]; if (f) setFile(f) }}
            onClick={() => fileRef.current?.click()}
            className={`flex cursor-pointer flex-col items-center gap-3 rounded-lg border-2 border-dashed px-6 py-12 text-center transition ${
              dragOver ? 'border-accent bg-accent-dim/10' : 'border-border hover:border-text-dim'
            }`}
          >
            <FileUp className="h-8 w-8 text-text-dim" />
            <div>
              <p className="font-sans text-sm text-text-muted">Drop a CSV or JSON file here</p>
              <p className="font-mono text-[11px] text-text-dim mt-1">or click to browse</p>
            </div>
            <input ref={fileRef} type="file" accept=".csv,.json" className="hidden" onChange={e => { if (e.target.files[0]) setFile(e.target.files[0]) }} />
          </div>

          {file && (
            <div className="flex items-center justify-between rounded-md border border-border bg-panel-raised px-4 py-2.5">
              <div className="flex items-center gap-2">
                {file.name.endsWith('.json') ? <FileJson className="h-4 w-4 text-flag" /> : <FileText className="h-4 w-4 text-safe" />}
                <span className="font-mono text-xs text-text">{file.name}</span>
                <span className="font-mono text-[10px] text-text-dim">({(file.size / 1024).toFixed(1)} KB)</span>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={() => setFile(null)} className="text-text-dim hover:text-text"><X className="h-3.5 w-3.5" /></button>
                <button
                  onClick={doUpload}
                  disabled={uploading}
                  className="flex items-center gap-1.5 rounded-md border border-border bg-accent px-3 py-1 font-sans text-xs font-medium text-bg transition hover:bg-accent/90 disabled:opacity-50"
                >
                  {uploading ? <RefreshCw className="h-3 w-3 animate-spin" /> : <Upload className="h-3 w-3" />}
                  {uploading ? 'Uploading...' : 'Upload & Score'}
                </button>
              </div>
            </div>
          )}

          {uploadErr && (
            <div className="rounded-md border border-block/30 bg-block-dim px-3 py-2 font-mono text-xs text-block">{uploadErr}</div>
          )}
        </div>
      </div>
    )
  }

  // ── Post-upload: streaming + analysis view ────────────────────────────
  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Top bar: stats + controls */}
      <div className="shrink-0 border-b border-border bg-panel px-5 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            {/* Progress */}
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs text-text-dim">{offset}/{total}</span>
              <div className="h-1.5 w-24 rounded-full bg-panel-raised overflow-hidden">
                <div className="h-full rounded-full bg-safe transition-all" style={{ width: `${progress}%` }} />
              </div>
              {scoring && <span className="font-mono text-[10px] text-flag animate-pulse">{scoringProgress}</span>}
            </div>
            {/* Decision counts */}
            <div className="flex items-center gap-3 font-mono text-[11px]">
              <span className="text-safe">{allowed} Allow</span>
              <span className="text-flag">{flagged} Flag</span>
              <span className="text-block">{blocked} Block</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Playback controls */}
            <button onClick={resetStream} className="rounded-md border border-border bg-panel-raised p-1.5 text-text-dim hover:text-text" title="Reset">
              <SkipBack className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={() => setPlaying(p => !p)}
              disabled={scoring || done}
              className="rounded-md border border-border bg-panel-raised p-1.5 text-text-dim hover:text-text disabled:opacity-40"
            >
              {playing ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
            </button>
            {/* Speed */}
            <div className="flex items-center rounded-md border border-border bg-panel-raised">
              {SPEEDS.map((s, i) => (
                <button
                  key={i}
                  onClick={() => setSpeedIdx(i)}
                  className={`px-2 py-1 font-mono text-[10px] transition ${i === speedIdx ? 'bg-accent-dim text-text' : 'text-text-dim hover:text-text'}`}
                >
                  {s.label}
                </button>
              ))}
            </div>

            <button onClick={startNewUpload} className="ml-2 flex items-center gap-1 rounded-md border border-border bg-panel-raised px-3 py-1.5 font-sans text-xs text-text-muted hover:text-text transition">
              <Upload className="h-3 w-3" /> New Upload
            </button>
          </div>
        </div>
      </div>

      {/* Sub-tabs */}
      <div className="shrink-0 flex items-center gap-1 border-b border-border bg-panel px-5 py-1.5">
        {[
          { key: 'stream', label: 'Transactions Stream', icon: Activity },
          { key: 'timeline', label: 'Attack Timeline', icon: Clock },
          { key: 'engine', label: 'Engine Logs', icon: Terminal },
          { key: 'audit', label: 'Audit Trail', icon: ClipboardList },
        ].map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActiveSubTab(key)}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1 font-sans text-xs transition ${
              activeSubTab === key
                ? 'bg-panel-raised text-text border border-border/80'
                : 'text-text-muted hover:bg-panel-raised/50 hover:text-text'
            }`}
          >
            <Icon className="h-3 w-3" /> {label}
          </button>
        ))}
      </div>

      {/* Content area */}
      <div className="flex-1 overflow-auto p-4">
        {/* ── Stream Tab ─────────────────────────────────────────────── */}
        {activeSubTab === 'stream' && (
          <div className="space-y-3">
            {/* Filter bar */}
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1 rounded-md border border-border bg-panel-raised px-2 py-1">
                <Search className="h-3 w-3 text-text-dim" />
                <input
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  placeholder="Search..."
                  className="w-40 bg-transparent font-mono text-xs text-text outline-none placeholder:text-text-dim"
                />
              </div>
              {['ALL', 'ALLOW', 'FLAG', 'BLOCK'].map(f => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`rounded-md px-2.5 py-1 font-mono text-[11px] transition ${
                    filter === f ? 'bg-panel-raised text-text border border-border' : 'text-text-dim hover:text-text'
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>

            {/* Table */}
            <div className="overflow-auto rounded-lg border border-border">
              <table className="w-full text-left font-mono text-xs">
                <thead className="bg-panel-raised text-text-dim">
                  <tr>
                    <th className="px-3 py-2 font-medium">Txn ID</th>
                    <th className="px-3 py-2 font-medium">Amount</th>
                    <th className="px-3 py-2 font-medium">Merchant</th>
                    <th className="px-3 py-2 font-medium">Decision</th>
                    <th className="px-3 py-2 font-medium">Risk</th>
                    <th className="px-3 py-2 font-medium">Location</th>
                  </tr>
                </thead>
                <tbody>
                  {visible.slice(0, 200).map((r, i) => {
                    const dec = r._score?.decision || 'ALLOW'
                    const risk = r._score?.risk_score || 0
                    const DecIcon = DECISION_ICONS[dec] || ShieldCheck
                    const isLatest = r.txn_id === latestId
                    return (
                      <tr
                        key={r.txn_id || i}
                        onClick={() => setSelected(r)}
                        className={`cursor-pointer border-t border-border transition ${
                          isLatest ? 'animate-feed-row-in bg-panel-raised' : 'hover:bg-panel-raised/50'
                        } ${selected?.txn_id === r.txn_id ? 'bg-panel-raised ring-1 ring-accent/30' : ''}`}
                      >
                        <td className="px-3 py-2 text-text-muted">{(r.txn_id || '').slice(0, 16)}</td>
                        <td className="px-3 py-2 text-text">${(r.amount || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                        <td className="px-3 py-2 text-text-muted">{r.merchant_name || '-'}</td>
                        <td className="px-3 py-2">
                          <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${
                            dec === 'BLOCK' ? 'bg-block-dim text-block' : dec === 'FLAG' ? 'bg-flag-dim text-flag' : 'bg-safe-dim text-safe'
                          }`}>
                            <DecIcon className="h-3 w-3" /> {dec}
                          </span>
                        </td>
                        <td className="px-3 py-2">
                          <div className="flex items-center gap-1.5">
                            <div className="h-1 w-12 rounded-full bg-panel-raised overflow-hidden">
                              <div className={`h-full rounded-full ${risk > 0.7 ? 'bg-block' : risk > 0.4 ? 'bg-flag' : 'bg-safe'}`}
                                style={{ width: `${risk * 100}%` }} />
                            </div>
                            <span className="text-text-dim">{(risk * 100).toFixed(0)}%</span>
                          </div>
                        </td>
                        <td className="px-3 py-2 text-text-dim">{r.geo?.city || '-'}</td>
                      </tr>
                    )
                  })}
                  {visible.length === 0 && (
                    <tr><td colSpan={6} className="px-3 py-8 text-center text-text-dim">
                      {rows.length === 0 ? 'Press Play to start streaming transactions' : 'No matching transactions'}
                    </td></tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Detail panel */}
            {selected && (
              <div className="rounded-lg border border-border bg-panel p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="font-sans text-sm font-semibold text-text">Transaction Detail</h3>
                  <button onClick={() => setSelected(null)} className="text-text-dim hover:text-text"><X className="h-4 w-4" /></button>
                </div>
                <div className="grid grid-cols-2 gap-3 font-mono text-xs">
                  <div><span className="text-text-dim">ID:</span> <span className="text-text">{selected.txn_id}</span></div>
                  <div><span className="text-text-dim">Amount:</span> <span className="text-text">${selected.amount}</span></div>
                  <div><span className="text-text-dim">Merchant:</span> <span className="text-text">{selected.merchant_name}</span></div>
                  <div><span className="text-text-dim">Decision:</span> <span className={
                    selected._score?.decision === 'BLOCK' ? 'text-block' : selected._score?.decision === 'FLAG' ? 'text-flag' : 'text-safe'
                  }>{selected._score?.decision}</span></div>
                  <div><span className="text-text-dim">Risk Score:</span> <span className="text-text">{((selected._score?.risk_score || 0) * 100).toFixed(1)}%</span></div>
                  <div><span className="text-text-dim">Confidence:</span> <span className="text-text">{((selected._score?.confidence || 0) * 100).toFixed(1)}%</span></div>
                </div>
                {selected._score?.reasons?.length > 0 && (
                  <div>
                    <div className="font-sans text-xs font-medium text-text-muted mb-1">Reasons</div>
                    <ul className="list-disc list-inside font-mono text-[11px] text-text-dim space-y-0.5">
                      {selected._score.reasons.map((r, i) => <li key={i}>{r}</li>)}
                    </ul>
                  </div>
                )}
                {selected._score?.engine_scores && Object.keys(selected._score.engine_scores).length > 0 && (
                  <div>
                    <div className="font-sans text-xs font-medium text-text-muted mb-1">Engine Scores</div>
                    <div className="grid grid-cols-3 gap-2">
                      {Object.entries(selected._score.engine_scores).map(([eng, data]) => {
                        const score = typeof data === 'object' ? data.score : data
                        if (score === undefined) return null
                        return (
                          <div key={eng} className="rounded-md border border-border bg-panel-raised px-2 py-1.5 text-center">
                            <div className="font-mono text-[10px] text-text-dim">{eng}</div>
                            <div className={`font-mono text-sm font-semibold ${score > 0.6 ? 'text-block' : score > 0.3 ? 'text-flag' : 'text-safe'}`}>
                              {(score * 100).toFixed(0)}%
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ── Timeline Tab ────────────────────────────────────────────── */}
        {activeSubTab === 'timeline' && (
          <div className="space-y-3">
            {timelineEvents.length === 0 ? (
              <div className="py-12 text-center font-mono text-xs text-text-dim">No flagged or blocked transactions yet. Start streaming to see the timeline.</div>
            ) : (
              timelineEvents.map((evt, i) => (
                <div key={evt.id} className={`flex gap-4 rounded-lg border p-4 ${
                  evt.decision === 'BLOCK' ? 'border-block/30 bg-block-dim/50' : 'border-flag/30 bg-flag-dim/50'
                }`}>
                  <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
                    evt.decision === 'BLOCK' ? 'bg-block/20 text-block' : 'bg-flag/20 text-flag'
                  }`}>
                    {evt.decision === 'BLOCK' ? <ShieldX className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
                  </div>
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className={`font-sans text-xs font-semibold ${evt.decision === 'BLOCK' ? 'text-block' : 'text-flag'}`}>
                        {evt.decision} - Risk {(evt.riskScore * 100).toFixed(0)}%
                      </span>
                      <span className="font-mono text-[10px] text-text-dim">{evt.timestamp}</span>
                    </div>
                    <div className="font-mono text-xs text-text-muted">
                      {evt.merchant} | {evt.location} | ${evt.amount.toLocaleString()}
                    </div>
                    <p className="font-mono text-[11px] text-text-dim leading-relaxed">{evt.reasoning}</p>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* ── Engine Logs Tab ─────────────────────────────────────────── */}
        {activeSubTab === 'engine' && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              {['ALL', 'INFO', 'WARN', 'ERROR'].map(f => (
                <button
                  key={f}
                  onClick={() => setLogFilter(f)}
                  className={`rounded-md px-2.5 py-1 font-mono text-[11px] transition ${
                    logFilter === f ? 'bg-panel-raised text-text border border-border' : 'text-text-dim hover:text-text'
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>
            <div className="rounded-lg border border-border bg-bg overflow-auto max-h-[60vh]">
              {filteredLogs.length === 0 ? (
                <div className="py-12 text-center font-mono text-xs text-text-dim">No logs yet. Start streaming transactions.</div>
              ) : (
                filteredLogs.slice(0, 500).map((log, i) => (
                  <div key={i} className="flex items-start gap-3 border-b border-border/50 px-3 py-1.5 font-mono text-[11px]">
                    <span className="shrink-0 text-text-dim w-14">{log.ts?.slice(11, 19) || '--:--:--'}</span>
                    <span className={`shrink-0 w-10 font-semibold ${
                      log.level === 'ERROR' ? 'text-block' : log.level === 'WARN' ? 'text-flag' : 'text-text-dim'
                    }`}>{log.level}</span>
                    <span className="shrink-0 w-20 text-text-muted">{log.engine}</span>
                    <span className="text-text-dim">{log.msg}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* ── Audit Tab ──────────────────────────────────────────────── */}
        {activeSubTab === 'audit' && (
          <div className="space-y-3">
            <div className="rounded-lg border border-border bg-panel p-4">
              <h3 className="font-sans text-sm font-semibold text-text mb-3">Upload Audit Trail</h3>
              <div className="space-y-2 font-mono text-xs">
                {uploadResult && (
                  <div className="flex items-center gap-2 text-safe">
                    <Check className="h-3.5 w-3.5" />
                    <span>Uploaded {uploadResult.inserted} transactions from {uploadResult.source}</span>
                  </div>
                )}
                {decisions.size > 0 && (
                  <div className="flex items-center gap-2 text-safe">
                    <FileCheck className="h-3.5 w-3.5" />
                    <span>Scored {decisions.size} transactions via ShieldGPT pipeline</span>
                  </div>
                )}
                <div className="flex items-center gap-2 text-text-muted">
                  <Activity className="h-3.5 w-3.5" />
                  <span>Streamed {rows.length} of {total} transactions</span>
                </div>
                <div className="flex items-center gap-2 text-text-dim">
                  <ShieldAlert className="h-3.5 w-3.5" />
                  <span>{blocked} blocked | {flagged} flagged | {allowed} allowed</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
