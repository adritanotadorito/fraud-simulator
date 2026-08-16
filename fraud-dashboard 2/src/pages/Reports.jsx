import { useState, useEffect } from 'react'
import TopBar from '../components/TopBar'
import { FileText, Download, ShieldX, AlertTriangle, ShieldCheck, Filter } from 'lucide-react'
import { severityOf } from '../lib/severity'
import { toPercent } from '../lib/format' // Fix: needed to handle confidence as string ("71%") or float (0.71)
import { useLiveFeed } from '../context/WebSocketContext'

const DEFAULT_INCIDENTS = [
  { decision_id: 'dec_101', txn_id: 'txn_1020', decision: 'FLAG', risk_score: 0.40, confidence: 0.88, reasons: ['New / unrecognized device', 'High transaction velocity', 'Merchant category flagged in threat_intel'] },
  { decision_id: 'dec_102', txn_id: 'txn_1019', decision: 'ALLOW', risk_score: 0.08, confidence: 0.95, reasons: ['Normal behavioral pattern', 'Known trusted device'] },
  { decision_id: 'dec_103', txn_id: 'txn_1013', decision: 'FLAG', risk_score: 0.62, confidence: 0.82, reasons: ['Unusual amount spike', 'Geolocation distance anomaly'] },
  { decision_id: 'dec_104', txn_id: 'txn_1008', decision: 'BLOCK', risk_score: 0.94, confidence: 0.96, reasons: ['Impossible travel speed (Lagos -> NYC)', 'Known compromised IP', 'Rooted Android device emulator'] },
  { decision_id: 'dec_105', txn_id: 'txn_1005', decision: 'BLOCK', risk_score: 0.89, confidence: 0.91, reasons: ['Card testing velocity threshold exceeded', 'Credential stuffing pattern'] }
]

export default function Reports() {
  const { events: liveFeedEvents } = useLiveFeed()
  const [dbDecisions, setDbDecisions] = useState([])
  const [filter, setFilter] = useState('ALL')
  const [loading, setLoading] = useState(false)

  async function fetchDecisions() {
    setLoading(true)
    try {
      const res = await fetch('http://localhost:8000/api/reports/recent?limit=50')
      if (res.ok) {
        const data = await res.json()
        if (data.decisions && data.decisions.length > 0) {
          setDbDecisions(data.decisions)
          setLoading(false)
          return
        }
      }
    } catch (err) {
      console.error('Failed to fetch report decisions:', err)
    }
    setDbDecisions(DEFAULT_INCIDENTS)
    setLoading(false)
  }

  useEffect(() => {
    fetchDecisions()
  }, [])

  function handleExport(format) {
    window.open(`http://localhost:8000/api/reports/generate?format=${format}`, '_blank')
  }

  // Combine live stream feed events with baseline database incidents
  const liveIncidentsFormatted = liveFeedEvents.map((evt, idx) => ({
    decision_id: `dec_live_${idx}`,
    txn_id: evt.transaction?.transaction_id || `txn_live_${idx}`,
    decision: evt.shieldgpt?.decision || 'ALLOW',
    risk_score: evt.ml?.final_risk || 0.15,
    confidence: evt.shieldgpt?.confidence || 0.88,
    reasons: evt.ml?.top_factors || [evt.shieldgpt?.explanation || 'Baseline evaluation']
  }))

  const combinedDecisions = [...liveIncidentsFormatted, ...dbDecisions]

  const filteredDecisions = combinedDecisions.filter(d => {
    if (filter === 'ALL') return true
    return d.decision === filter
  })

  return (
    <div className="flex h-full flex-col overflow-hidden bg-bg">
      <div className="flex-1 space-y-6 overflow-y-auto p-6">
        {/* Export Banner */}
        <div className="flex items-center justify-between rounded-xl border border-border bg-panel p-4.5">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-md border border-border bg-panel-raised text-text-muted">
              <FileText className="h-4 w-4" />
            </div>
            <div>
              <h2 className="font-sans text-sm font-medium text-text">Audit Log Export</h2>
              <p className="text-xs text-text-dim mt-0.5">Download structured decision records, risk factor summaries, and compliance audit trail files.</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleExport('json')}
              className="flex items-center gap-1.5 rounded-md border border-border bg-panel-raised px-3 py-1.5 font-mono text-xs text-text-muted hover:text-text hover:bg-border/40 transition-colors"
            >
              <Download className="h-3.5 w-3.5" />
              JSON
            </button>
            <button
              onClick={() => handleExport('csv')}
              className="flex items-center gap-1.5 rounded-md border border-border bg-panel-raised px-3 py-1.5 font-mono text-xs text-text-muted hover:text-text hover:bg-border/40 transition-colors"
            >
              <Download className="h-3.5 w-3.5" />
              CSV
            </button>
            <button
              onClick={() => handleExport('pdf')}
              className="flex items-center gap-1.5 rounded-md border border-border bg-text px-3 py-1.5 font-sans text-xs font-medium text-bg hover:opacity-90 transition-colors"
            >
              <Download className="h-3.5 w-3.5" />
              Export PDF
            </button>
          </div>
        </div>

        {/* Filter Bar & Table */}
        <div className="rounded-xl border border-border bg-panel p-5">
          <div className="mb-4 flex items-center justify-between border-b border-border/80 pb-4">
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-accent" />
              <h3 className="font-sans text-sm font-semibold text-text">Fraud Incident Log</h3>
            </div>
            <div className="flex gap-2">
              {['ALL', 'BLOCK', 'FLAG', 'ALLOW'].map(f => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`rounded-lg px-3 py-1 font-mono text-xs font-medium transition-colors ${
                    filter === f
                      ? 'bg-accent text-bg font-semibold'
                      : 'bg-panel-raised text-text-muted hover:text-text'
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs">
              <thead>
                <tr className="border-b border-border/60 text-text-dim">
                  <th className="pb-3 pt-1 font-semibold">Txn ID</th>
                  <th className="pb-3 pt-1 font-semibold">Decision</th>
                  <th className="pb-3 pt-1 font-semibold">Risk Score</th>
                  <th className="pb-3 pt-1 font-semibold">Confidence</th>
                  <th className="pb-3 pt-1 font-semibold">Top Reasons</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/40">
                {filteredDecisions.length === 0 ? (
                  <tr>
                    <td colSpan="5" className="py-8 text-center text-text-dim">
                      {loading ? 'Loading incidents...' : 'No incident logs found matching filter.'}
                    </td>
                  </tr>
                ) : (
                  filteredDecisions.map((d, i) => {
                    const sev = severityOf(d.decision)
                    return (
                      <tr key={d.decision_id || i} className="hover:bg-panel-raised/50">
                        <td className="py-3 text-text font-medium">{d.txn_id}</td>
                        <td className="py-3">
                          <span className={`inline-flex items-center gap-1 rounded px-2 py-0.5 font-bold ${sev.bg} ${sev.text}`}>
                            {d.decision}
                          </span>
                        </td>
                        <td className="py-3 text-text">{(d.risk_score * 100).toFixed(0)}%</td>
                        {/* OLD: <td className="py-3 text-text-muted">{((d.confidence || 0.8) * 100).toFixed(0)}%</td> */}
                        {/* BUG: mockEvents returns confidence as a string like "71%", so * 100 gives NaN */}
                        <td className="py-3 text-text-muted">{toPercent(d.confidence || 0.8).toFixed(0)}%</td>
                        <td className="py-3 text-text-dim truncate max-w-xs">
                          {d.reasons ? d.reasons.join(', ') : 'Normal baseline'}
                        </td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
