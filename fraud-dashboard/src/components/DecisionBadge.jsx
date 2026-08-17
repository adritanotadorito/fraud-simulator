import { ShieldCheck, AlertTriangle, ShieldX } from 'lucide-react'
import { severityOf } from '../lib/severity'

const ICONS = { ALLOW: ShieldCheck, FLAG: AlertTriangle, BLOCK: ShieldX }

export default function DecisionBadge({ event }) {
  const decision = event?.shieldgpt?.decision || 'ALLOW'
  const sev = severityOf(decision)
  const Icon = ICONS[decision]

  const statusLabel = decision === 'ALLOW' ? 'PASSED / APPROVED' : decision === 'FLAG' ? 'REVIEW REQUIRED' : 'AUTOMATIC BLOCK'

  return (
    <div className="flex flex-col items-center justify-between gap-2 rounded-xl border border-border bg-panel p-4">
      <div className="flex w-full items-center justify-between border-b border-border pb-2">
        <span className="font-sans text-[11px] font-medium uppercase tracking-wider text-text-dim">Engine Decision</span>
        <span className="font-mono text-xs text-text-muted">Automated Policy</span>
      </div>

      <div className="flex w-full items-center justify-center gap-2.5 rounded-md border border-border bg-panel-raised py-3 my-1">
        <span className={`h-2 w-2 rounded-full ${sev.dot}`} />
        <span className={`font-sans text-sm font-semibold tracking-wide ${sev.text}`}>{statusLabel}</span>
      </div>

      {event ? (
        <span className="font-mono text-xs text-text-dim">ID: {event.transaction.transaction_id}</span>
      ) : (
        <span className="font-mono text-xs text-text-dim">Awaiting transaction</span>
      )}
    </div>
  )
}
