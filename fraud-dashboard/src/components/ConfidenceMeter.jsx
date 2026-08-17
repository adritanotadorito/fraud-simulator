import { toPercent } from '../lib/format'

export default function ConfidenceMeter({ event }) {
  const rawConf = event?.shieldgpt?.confidence ?? 0.85
  const confidence = Math.round((parseFloat(rawConf) || 0) * (rawConf <= 1 ? 100 : 1))
  const label = confidence >= 90 ? 'High Precision' : confidence >= 70 ? 'Moderate' : 'Low Precision'

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-border bg-panel p-4 justify-between">
      <div className="flex items-center justify-between border-b border-border pb-2">
        <span className="font-sans text-[11px] font-medium uppercase tracking-wider text-text-dim">Engine Confidence</span>
        <span className="rounded-md border border-border bg-panel-raised px-2 py-0.5 font-mono text-xs text-text-muted">
          Multi-Signal
        </span>
      </div>

      <div className="flex items-baseline gap-2">
        <span className="font-mono text-3xl font-bold tracking-tight text-text">{confidence.toFixed(0)}%</span>
        <span className="text-xs font-medium text-text-muted">{label}</span>
      </div>

      <div className="h-1.5 w-full overflow-hidden rounded-full bg-border">
        <div
          className="h-full rounded-full bg-text transition-all duration-600 ease-out"
          style={{ width: `${confidence}%` }}
        />
      </div>

      <div className="flex items-center justify-between font-mono text-xs text-text-dim">
        <span>Model Ensemble</span>
        <span>Weighted Voting</span>
      </div>
    </div>
  )
}
