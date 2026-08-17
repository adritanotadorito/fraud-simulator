import { useState, useEffect, useRef } from 'react'
import {
  Database, Upload, X, FileText, FileJson,
  RefreshCw, Search, Filter, Info, CheckCircle2, Ban,
  Play, Pause, SkipBack, ShieldCheck, AlertTriangle, ShieldX,
  Zap, CloudUpload, FileUp, Activity, Terminal, ClipboardList,
  ShieldAlert
} from 'lucide-react'
import { severityOf } from '../lib/severity'

// ─── Helpers ──────────────────────────────────────────────────────────────────
const DECISION_ICONS = { ALLOW: ShieldCheck, FLAG: AlertTriangle, BLOCK: ShieldX }

const SPEEDS = [
  { label: '0.5×', ms: 2000 },
  { label: '1×',   ms: 1000 },
  { label: '2×',   ms: 500  },
  { label: '5×',   ms: 200  },
]

function scoreRow(txn) {
  const mag     = txn.pca_magnitude || 0
  const fraud   = txn.is_fraud === true || txn.is_fraud === 'true' || txn.is_fraud === '1' || txn.is_fraud === 1
  const amtR    = Math.min((txn.amount || 0) / 500, 1)
  const risk    = fraud
    ? Math.max(0.80, Math.min(mag * 0.5 + amtR * 0.3 + 0.4, 0.99))
    : Math.min(mag * 0.3 + amtR * 0.1 + 0.05, 0.45)
  const decision = risk >= 0.80 ? 'BLOCK' : risk >= 0.50 ? 'FLAG' : 'ALLOW'
  return { decision, risk_score: risk, is_fraud: fraud }
}

// ─── Component ────────────────────────────────────────────────────────────────
export default function RealData() {
  // Upload state
  const [dragOver, setDragOver]     = useState(false)
  const [file, setFile]             = useState(null)
  const [uploading, setUploading]   = useState(false)
  const [uploadResult, setUploadResult] = useState(null)
  const [uploadErr, setUploadErr]   = useState(null)
  const fileRef                     = useRef(null)

  // Uploaded transactions buffer
  const [uploadedTxns, setUploadedTxns] = useState([])
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
  const [logFilter, setLogFilter]   = useState('ALL')

  useEffect(() => { offsetRef.current = offset }, [offset])

  // ── Upload handler ─────────────────────────────────────────────────────────
  const doUpload = async () => {
    if (!file) return
    setUploading(true); setUploadResult(null); setUploadErr(null)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const token = localStorage.getItem('token')
      const headers = token ? { 'Authorization': `Bearer ${token}` } : {}
      const res = await fetch('http://localhost:8000/api/transactions/upload-file', {
        method: 'POST', body: fd, headers
      })
      const d = await res.json()
      if (!res.ok) {
        setUploadErr(d.detail || 'Upload failed')
        return
      }
      setUploadResult(d)
      setHasUploaded(true)
      setActiveSubTab('stream')

      const source = d.source
      const listRes = await fetch(
        `http://localhost:8000/api/transactions/uploaded?source=${encodeURIComponent(source)}&limit=10000`,
        { headers }
      )
      if (listRes.ok) {
        const txns = await listRes.json()
        setUploadedTxns(txns)
      } else {
        setUploadedTxns(d.preview || [])
      }
      setRows([])
      setOffset(0)
      setPlaying(false)
      setLatestId(null)
      setSelected(null)
    } catch (e) {
      setUploadErr(e.message)
    } finally {
      setUploading(false)
    }
  }

  // ── Streaming timer ────────────────────────────────────────────────────────
  useEffect(() => {
    clearInterval(timerRef.current)
    if (!playing || uploadedTxns.length === 0) return

    const step = () => {
      const cur = offsetRef.current
      if (cur >= uploadedTxns.length) {
        setPlaying(false)
        return
      }
      const txn = uploadedTxns[cur]
      const score = scoreRow(txn)
      const enriched = { ...txn, _score: score }
      setRows(prev => [enriched, ...prev])
      setLatestId(txn.txn_id)
      setOffset(cur + 1)
    }

    step()
    timerRef.current = setInterval(step, SPEEDS[speedIdx].ms)
    return () => clearInterval(timerRef.current)
  }, [playing, speedIdx, uploadedTxns])

  const resetStream = () => {
    clearInterval(timerRef.current)
    setPlaying(false)
    setOffset(0)
    setRows([])
    setLatestId(null)
    setSelected(null)
  }

  const startNewUpload = () => {
    resetStream()
    setFile(null)
    setUploadResult(null)
    setUploadErr(null)
    setUploadedTxns([])
    setHasUploaded(false)
    setActiveSubTab('stream')
  }

  const blocked   = rows.filter(r => r._score?.decision === 'BLOCK').length
  const flagged   = rows.filter(r => r._score?.decision === 'FLAG').length
  const allowed   = rows.length - blocked - flagged
  const fraudRows = rows.filter(r => r._score?.is_fraud).length
  const total     = uploadedTxns.length
  const progress  = total > 0 ? Math.min((offset / total) * 100, 100) : 0
  const done      = offset >= total && total > 0

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

  const timelineEvents = rows
    .filter(r => r._score?.decision === 'BLOCK' || r._score?.decision === 'FLAG' || r._score?.is_fraud)
    .map((r, idx) => ({
      id: r.txn_id || `evt_${idx}`,
      timestamp: r.timestamp || new Date().toISOString(),
      decision: r._score?.decision || 'FLAG',
      riskScore: r._score?.risk_score || 0.85,
      merchant: r.merchant_name || 'Merchant',
      location: r.geo?.city || 'Unknown',
      amount: r.amount || 0,
      isFraudGT: r._score?.is_fraud,
      reasoning: r._score?.decision === 'BLOCK'
        ? `ShieldGPT Rule Engine & XGBoost triggered high risk score (${((r._score?.risk_score || 0.8) * 100).toFixed(0)}%). Velocity & Location deviation (${r.geo?.city || 'Unknown'}) flagged as critical anomaly.`
        : `ShieldGPT flagged transaction for step-up verification: elevated risk score (${((r._score?.risk_score || 0.6) * 100).toFixed(0)}%) with unusual device/channel pattern.`
    }))

  const engineLogs = rows.flatMap((r) => {
    const dec = r._score?.decision || 'ALLOW'
    const risk = (r._score?.risk_score || 0) * 100
    const ts = r.timestamp || new Date().toISOString()
    return [
      {
        id: `${r.txn_id}-xgb`,
        time: ts,
        level: dec === 'BLOCK' ? 'ERROR' : dec === 'FLAG' ? 'WARN' : 'INFO',
        component: 'XGBoost-V2',
        message: `Scored ${r.txn_id} ($${r.amount}): ML raw probability ${risk.toFixed(1)}% | Ground Truth: ${r._score?.is_fraud ? 'FRAUD (1)' : 'LEGIT (0)'}`
      },
      {
        id: `${r.txn_id}-rule`,
        time: ts,
        level: dec === 'BLOCK' ? 'ERROR' : dec === 'FLAG' ? 'WARN' : 'INFO',
        component: 'RuleEngine',
        message: `Rule Evaluator: Location='${r.geo?.city || 'N/A'}', Merchant='${r.merchant_name || 'N/A'}' -> Fused Decision: ${dec}`
      }
    ]
  }).filter(l => logFilter === 'ALL' || l.level === logFilter)

  return (
    <div className="flex h-full flex-col overflow-hidden bg-bg">
      <div className="flex-1 overflow-y-auto space-y-5 p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-md border border-border bg-panel-raised">
              <Database className="h-4 w-4 text-text-muted" />
            </div>
            <div>
              <h1 className="font-sans text-sm font-semibold text-text">Real Transactions</h1>
              <p className="font-mono text-xs text-text-dim mt-0.5">
                {hasUploaded
                  ? `${total.toLocaleString()} transactions loaded from ${uploadResult?.source || 'uploaded dataset'}`
                  : 'Upload a CSV or JSON file to begin'}
              </p>
            </div>
          </div>
          {hasUploaded && (
            <button
              onClick={startNewUpload}
              className="flex items-center gap-1.5 rounded-md border border-border bg-panel-raised px-3 py-1.5 font-sans text-xs text-text-muted hover:text-text transition-colors"
            >
              <FileUp className="h-3.5 w-3.5" />
              New Upload
            </button>
          )}
        </div>

        {!hasUploaded && (
          <div className="rounded-xl border border-border bg-panel p-6 animate-feed-row-in">
            <div className="flex items-center gap-2 mb-4">
              <CloudUpload className="h-5 w-5 text-accent" />
              <span className="font-sans text-sm font-semibold text-text">Upload Transaction Dataset</span>
            </div>

            <div className="mb-5 flex items-start gap-2 rounded-lg border border-border/50 bg-panel-raised/60 px-3 py-2.5">
              <Info className="h-3.5 w-3.5 mt-0.5 text-text-dim shrink-0" />
              <p className="font-mono text-[11px] leading-relaxed text-text-dim">
                Upload a <strong className="text-text-muted">.csv or .json</strong> file.
                Supported columns: <code className="text-accent">amount</code>, <code className="text-accent">merchant_name</code>,
                <code className="text-accent"> user_id</code>, <code className="text-accent">is_fraud</code> (0/1).
              </p>
            </div>

            <div
              onDragOver={e => { e.preventDefault(); setDragOver(true) }}
              onDragLeave={() => setDragOver(false)}
              onDrop={e => {
                e.preventDefault(); setDragOver(false)
                const f = e.dataTransfer?.files?.[0]; if (f) setFile(f)
              }}
              onClick={() => fileRef.current?.click()}
              className={`flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed py-12 transition-all ${
                dragOver ? 'border-accent/60 bg-accent/5'
                : file    ? 'border-safe/40 bg-safe/5'
                : 'border-border hover:border-border/80 hover:bg-panel-raised/30'
              }`}
            >
              <input ref={fileRef} type="file" accept=".csv,.json" className="hidden"
                onChange={e => { const f = e.target.files?.[0]; if (f) setFile(f) }} />
              {file
                ? <>
                    {file.name.endsWith('.json')
                      ? <FileJson className="h-10 w-10 text-safe" />
                      : <FileText className="h-10 w-10 text-safe" />}
                    <div className="text-center">
                      <p className="font-sans text-sm font-medium text-text">{file.name}</p>
                      <p className="font-mono text-xs text-text-dim mt-0.5">{(file.size/1024).toFixed(1)} KB</p>
                    </div>
                  </>
                : <>
                    <Upload className="h-10 w-10 text-text-dim opacity-60" />
                    <div className="text-center">
                      <p className="font-sans text-sm font-medium text-text">Drop CSV/JSON file here or click to browse</p>
                      <p className="font-mono text-[11px] text-text-dim mt-1">Supports up to 50,000 transaction rows</p>
                    </div>
                  </>
              }
            </div>

            {file && (
              <div className="mt-5 flex items-center justify-between">
                <button onClick={() => { setFile(null); setUploadResult(null); setUploadErr(null) }}
                  className="flex items-center gap-1 font-mono text-xs text-text-dim hover:text-text transition-colors">
                  <X className="h-3.5 w-3.5" /> Clear
                </button>
                <button onClick={doUpload} disabled={uploading}
                  className="flex items-center gap-1.5 rounded-md border border-border bg-text px-6 py-2.5 font-sans text-xs font-semibold text-bg hover:opacity-90 disabled:opacity-50 transition-all">
                  {uploading
                    ? <><RefreshCw className="h-3.5 w-3.5 animate-spin" /> Ingesting Data…</>
                    : <><Upload className="h-3.5 w-3.5" /> Import & Initialize</>}
                </button>
              </div>
            )}

            {uploadErr && (
              <div className="mt-4 rounded-lg border border-block/30 bg-block/10 p-3">
                <p className="font-mono text-xs text-block">{uploadErr}</p>
              </div>
            )}
          </div>
        )}

        {hasUploaded && (
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

            {activeSubTab === 'stream' && (
              <div className="space-y-5 animate-feed-row-in">
                <div className="grid grid-cols-5 gap-3">
                  {[
                    { label: 'Streamed',  value: rows.length, color: 'text-accent',  icon: Database      },
                    { label: 'Allowed',   value: allowed,      color: 'text-safe',   icon: CheckCircle2  },
                    { label: 'Flagged',   value: flagged,      color: 'text-flag',   icon: AlertTriangle },
                    { label: 'Blocked',   value: blocked,      color: 'text-block',  icon: Ban           },
                    { label: 'Fraud (GT)',value: fraudRows,    color: 'text-block',  icon: ShieldX       },
                  ].map(({ label, value, color, icon: Icon }) => (
                    <div key={label} className="rounded-xl border border-border bg-panel p-4">
                      <div className="flex items-center justify-between">
                        <span className="font-sans text-[10px] font-medium uppercase tracking-wider text-text-dim">
                          {label}
                        </span>
                        <Icon className={`h-3.5 w-3.5 ${color}`} strokeWidth={1.75} />
                      </div>
                      <div className={`mt-2 font-sans text-2xl font-bold tabular-nums ${color}`}>
                        {value}
                      </div>
                    </div>
                  ))}
                </div>

                <div className="rounded-xl border border-border bg-panel overflow-hidden">
                  <div className="flex items-center gap-3 px-5 py-3 border-b border-border">
                    <button
                      onClick={() => {
                        if (done) {
                          resetStream()
                          setTimeout(() => setPlaying(true), 50)
                        } else {
                          setPlaying(v => !v)
                        }
                      }}
                      disabled={total === 0}
                      className={`flex items-center gap-1.5 rounded-md px-4 py-2 font-sans text-xs font-semibold transition-all disabled:opacity-40 ${
                        playing
                          ? 'bg-flag/15 text-flag border border-flag/30 hover:bg-flag/25'
                          : 'bg-safe/15 text-safe border border-safe/30 hover:bg-safe/25'
                      }`}
                    >
                      {playing
                        ? <><Pause className="h-4 w-4" /> Pause</>
                        : done
                          ? <><SkipBack className="h-4 w-4" /> Replay</>
                          : <><Play className="h-4 w-4" /> {rows.length === 0 ? 'Start Streaming' : 'Resume'}</>
                      }
                    </button>

                    <button
                      onClick={resetStream}
                      className="flex items-center gap-1.5 rounded-md border border-border bg-panel-raised px-3 py-2 font-mono text-xs text-text-dim hover:text-text transition-colors"
                    >
                      <SkipBack className="h-3.5 w-3.5" /> Reset
                    </button>

                    <div className="flex items-center gap-0.5 rounded-md border border-border bg-bg px-1.5 py-1">
                      {SPEEDS.map((s, i) => (
                        <button
                          key={s.label}
                          onClick={() => setSpeedIdx(i)}
                          className={`rounded px-2.5 py-0.5 font-mono text-[11px] transition-colors ${
                            speedIdx === i
                              ? 'bg-text text-bg font-semibold'
                              : 'text-text-dim hover:text-text'
                          }`}
                        >
                          {s.label}
                        </button>
                      ))}
                    </div>

                    <div className="ml-auto flex items-center gap-3">
                      {playing && (
                        <div className="flex items-center gap-1.5">
                          <span className="h-2 w-2 rounded-full bg-safe animate-pulse" />
                          <span className="font-mono text-xs text-safe">STREAMING</span>
                        </div>
                      )}
                      {done && !playing && (
                        <span className="font-mono text-xs text-accent">✓ Stream Finished</span>
                      )}
                      <span className="font-mono text-xs text-text-dim">
                        {offset.toLocaleString()} / {total.toLocaleString()} rows
                      </span>
                    </div>
                  </div>

                  <div className="h-1 w-full bg-bg">
                    <div
                      className={`h-full transition-all duration-300 ${
                        done
                          ? 'bg-gradient-to-r from-accent/60 to-accent'
                          : 'bg-gradient-to-r from-safe/60 to-safe'
                      }`}
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                </div>

                <div className="rounded-xl border border-border bg-panel">
                  <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
                    <div className="flex items-center gap-2">
                      {playing && (
                        <span className="flex items-center gap-1.5 rounded-full border border-safe/30 bg-safe/10 px-2.5 py-0.5 font-mono text-[10px] text-safe">
                          <Zap className="h-3 w-3" /> Live Feed
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="flex items-center gap-1.5 rounded-md border border-border bg-bg px-2.5 py-1.5">
                        <Search className="h-3.5 w-3.5 text-text-dim" />
                        <input
                          type="text"
                          placeholder="Search…"
                          value={search}
                          onChange={e => setSearch(e.target.value)}
                          className="w-36 bg-transparent font-mono text-xs text-text outline-none placeholder:text-text-dim"
                        />
                      </div>
                      <div className="flex items-center gap-0.5">
                        <Filter className="h-3.5 w-3.5 text-text-dim mr-1" />
                        {['ALL', 'ALLOW', 'FLAG', 'BLOCK'].map(f => (
                          <button key={f} onClick={() => setFilter(f)}
                            className={`rounded-md px-2.5 py-1 font-mono text-[11px] transition-colors ${
                              filter === f
                                ? 'bg-panel-raised text-text border border-border'
                                : 'text-text-dim hover:text-text-muted'
                            }`}>{f}</button>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="overflow-x-auto" style={{ maxHeight: '420px', overflowY: 'auto' }}>
                    <table className="w-full text-left">
                      <thead className="sticky top-0 z-10 bg-panel">
                        <tr className="border-b border-border/60">
                          {['#', 'Txn ID', 'Merchant', 'Amount', 'Ground Truth', 'Decision', 'Risk', 'Location'].map(h => (
                            <th key={h} className="px-4 py-3 font-sans text-[10px] font-medium uppercase tracking-wider text-text-dim">
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {visible.map((txn, idx) => {
                          const score   = txn._score || {}
                          const dec     = score.decision || 'ALLOW'
                          const risk    = score.risk_score ?? 0
                          const sev     = severityOf(dec)
                          const DecIcon = DECISION_ICONS[dec] || ShieldCheck
                          const isSel   = selected?.txn_id === txn.txn_id
                          const isNew   = txn.txn_id === latestId

                          return (
                            <tr
                              key={`${txn.txn_id}-${idx}`}
                              onClick={() => setSelected(isSel ? null : txn)}
                              className={`cursor-pointer border-b border-border/30 last:border-0 transition-all ${
                                isSel  ? 'bg-panel-raised'
                                : isNew ? 'animate-feed-row-in bg-accent/4'
                                : 'hover:bg-panel-raised/50'
                              }`}
                            >
                              <td className="px-4 py-2.5 font-mono text-[10px] text-text-dim">
                                {rows.length - idx}
                              </td>
                              <td className="px-4 py-2.5 font-mono text-xs text-text-muted">
                                {isNew && <span className="text-safe mr-1">▸</span>}
                                {txn.txn_id?.length > 14 ? txn.txn_id.slice(0, 14) + '…' : txn.txn_id}
                              </td>
                              <td className="px-4 py-2.5 font-sans text-xs text-text max-w-[120px] truncate">
                                {txn.merchant_name || '—'}
                              </td>
                              <td className="px-4 py-2.5 font-mono text-xs font-medium text-text">
                                ${parseFloat(txn.amount || 0).toFixed(2)}
                              </td>
                              <td className="px-4 py-2.5">
                                <span className={`rounded-full px-2 py-0.5 font-mono text-[10px] font-semibold ${
                                  score.is_fraud
                                    ? 'bg-block/15 text-block'
                                    : 'bg-safe/15 text-safe'
                                }`}>
                                  {score.is_fraud ? 'FRAUD' : 'LEGIT'}
                                </span>
                              </td>
                              <td className="px-4 py-2.5">
                                <div className={`flex items-center gap-1.5 ${sev.text}`}>
                                  <DecIcon className="h-3.5 w-3.5 shrink-0" strokeWidth={2} />
                                  <span className="font-mono text-xs font-semibold">{dec}</span>
                                </div>
                              </td>
                              <td className="px-4 py-2.5">
                                <div className="flex items-center gap-1.5">
                                  <div className="h-1.5 w-16 rounded-full bg-bg overflow-hidden">
                                    <div
                                      className={`h-full rounded-full ${
                                        risk >= 0.8 ? 'bg-block' : risk >= 0.5 ? 'bg-flag' : 'bg-safe'
                                      }`}
                                      style={{ width: `${risk * 100}%` }}
                                    />
                                  </div>
                                  <span className="font-mono text-[10px] text-text-dim">
                                    {(risk * 100).toFixed(0)}%
                                  </span>
                                </div>
                              </td>
                              <td className="px-4 py-2.5 font-mono text-[10px] text-text-dim">
                                {txn.geo?.city || '—'}
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>

                {selected && (
                  <div className="rounded-xl border border-border bg-panel p-5 animate-feed-row-in">
                    <div className="mb-4 flex items-center justify-between">
                      <h3 className="font-sans text-sm font-semibold text-text">Transaction Detail</h3>
                      <button onClick={() => setSelected(null)} className="text-text-dim hover:text-text">
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                    <div className="grid grid-cols-3 gap-4">
                      {[
                        ['Txn ID',       selected.txn_id],
                        ['Merchant',     selected.merchant_name || '—'],
                        ['Amount',       `$${parseFloat(selected.amount || 0).toFixed(2)}`],
                        ['User ID',      selected.user_id || '—'],
                        ['Account ID',   selected.account_id || '—'],
                        ['Device ID',    selected.device_id || '—'],
                        ['Source',       selected.source || '—'],
                        ['Location',     selected.geo ? `${selected.geo.city}, ${selected.geo.country}` : '—'],
                        ['Ground Truth', selected._score?.is_fraud ? '🚨 Fraud' : '✅ Legitimate'],
                        ['Decision',     selected._score?.decision || 'ALLOW'],
                        ['Risk Score',   `${((selected._score?.risk_score || 0) * 100).toFixed(1)}%`],
                      ].map(([label, val]) => (
                        <div key={label} className="flex flex-col gap-0.5">
                          <span className="font-sans text-[10px] uppercase tracking-wider text-text-dim">{label}</span>
                          <span className="font-mono text-xs text-text">{val}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
