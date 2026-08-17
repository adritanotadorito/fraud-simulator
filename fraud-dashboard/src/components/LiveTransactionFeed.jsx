import { useLiveFeed } from '../context/WebSocketContext'
import { severityOf } from '../lib/severity'

function timeAgo(iso) {
  const diff = Math.max(0, Date.now() - new Date(iso).getTime())
  const s = Math.floor(diff / 1000)
  if (s < 5) return 'just now'
  if (s < 60) return `${s}s ago`
  return `${Math.floor(s / 60)}m ago`
}

function FeedRow({ evt, onSelect, isSelected }) {
  const { transaction, shieldgpt, fraudgpt } = evt
  const sev = severityOf(shieldgpt.decision)

  const glowStyles = {
    ALLOW: 'hover:border-safe/50 hover:shadow-[0_0_16px_rgba(16,185,129,0.16)]',
    FLAG: 'hover:border-flag/50 hover:shadow-[0_0_16px_rgba(245,158,11,0.16)]',
    BLOCK: 'hover:border-block/50 hover:shadow-[0_0_16px_rgba(244,63,94,0.16)]',
  }[shieldgpt.decision] || 'hover:border-text/40 hover:shadow-[0_0_16px_rgba(255,255,255,0.08)]'

  return (
    <button
      onClick={() => onSelect(evt)}
      className={`group relative flex w-full items-center gap-3 rounded-md border ${
        isSelected
          ? 'border-text/60 bg-panel-raised shadow-[0_0_12px_rgba(255,255,255,0.06)]'
          : 'border-border bg-panel'
      } px-3 py-2.5 text-left transition-all duration-200 ease-out hover:scale-[1.025] hover:z-10 hover:bg-panel-raised ${glowStyles}`}
    >
      <span className={`h-1.5 w-1.5 shrink-0 rounded-full transition-transform duration-200 group-hover:scale-150 ${sev.dot}`} />

      <div className="min-w-0 flex-1">
        <div className="truncate font-sans text-xs font-medium text-text group-hover:text-white">
          {transaction.merchant || 'Unknown Merchant'}
        </div>
        <div className="flex items-center gap-1.5 font-mono text-[11px] text-text-dim group-hover:text-text-muted">
          <span className="truncate">{transaction.transaction_id}</span>
          {fraudgpt && (
            <>
              <span>·</span>
              <span className="truncate font-normal text-text-muted">{fraudgpt.persona}</span>
            </>
          )}
        </div>
      </div>

      <div className="shrink-0 font-mono text-xs font-medium text-text">
        ₹{transaction.amount.toLocaleString('en-IN')}
      </div>

      <div className="shrink-0 rounded border border-border bg-panel-raised px-1.5 py-0.5 font-mono text-[10px] text-text-muted group-hover:border-border/80">
        <span className={sev.text}>{sev.label}</span>
      </div>

      <div className="w-12 shrink-0 text-right font-mono text-[11px] text-text-dim">
        {timeAgo(transaction.timestamp)}
      </div>
    </button>
  )
}

export default function LiveTransactionFeed({ limit = 25, onSelect, selectedId }) {
  const { events, connectionStatus } = useLiveFeed()
  const rows = events.slice(0, limit)

  return (
    <div className="flex h-full flex-col rounded-xl border border-border bg-panel-raised">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h2 className="font-sans text-sm font-semibold text-text">Live Transaction Feed</h2>
        <div className="flex items-center gap-2">
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              connectionStatus === 'live' ? 'bg-safe' : 'bg-flag'
            }`}
          />
          <span className="font-mono text-xs text-text-muted capitalize">{connectionStatus}</span>
        </div>
      </div>

      <div className="flex-1 space-y-1.5 overflow-y-auto p-3">
        {rows.length === 0 && (
          <p className="py-8 text-center font-mono text-xs text-text-dim">
            Waiting for the first event…
          </p>
        )}
        {rows.map((evt) => (
          <FeedRow
            key={evt.event_id}
            evt={evt}
            onSelect={onSelect}
            isSelected={selectedId === evt.event_id}
          />
        ))}
      </div>
    </div>
  )
}
