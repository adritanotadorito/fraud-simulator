import { ShieldAlert, CheckSquare } from 'lucide-react'
import { toPercent } from '../lib/format'

export default function ExplainableAIPanel({ event }) {
  if (!event) {
    return (
      <div className="flex h-full items-center justify-center rounded-xl border border-border bg-panel p-6 text-sm text-text-dim">
        Select a transaction from the live feed to inspect engine breakdown.
      </div>
    )
  }

  const { transaction, ml, shieldgpt, fraudgpt } = event
  const confidence = toPercent(shieldgpt.confidence)

  return (
    <div className="flex h-full flex-col gap-4 rounded-xl border border-border bg-panel p-5">
      <div className="flex items-center justify-between border-b border-border pb-3">
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-md border border-border bg-panel-raised text-text-muted">
            <ShieldAlert className="h-3.5 w-3.5" />
          </div>
          <div>
            <h2 className="font-sans text-sm font-medium text-text">Risk Decision Breakdown</h2>
            <p className="font-mono text-xs text-text-dim">
              Txn ID: {transaction.transaction_id}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-md border border-border bg-panel-raised px-2.5 py-1 font-mono text-xs text-text-muted">
            Confidence: <strong className="text-text font-medium">{confidence.toFixed(0)}%</strong>
          </span>
        </div>
      </div>

      {fraudgpt && (
        <div className="rounded-md border border-border bg-panel-raised px-3 py-2">
          <span className="font-mono text-xs text-text-muted font-medium">
            Simulated Attack Vector: <strong className="text-text font-normal">{fraudgpt.persona}</strong> · Round #{fraudgpt.round}
          </span>
        </div>
      )}

      <div>
        <p className="mb-1.5 font-mono text-[10px] uppercase tracking-wider text-text-dim font-medium">Evaluation Detail</p>
        <p className="text-xs leading-relaxed text-text-muted bg-panel-raised p-3 rounded-md border border-border">
          "{shieldgpt.explanation}"
        </p>
      </div>

      <div>
        <p className="mb-1 font-mono text-[10px] uppercase tracking-wider text-text-dim font-medium">Recommended Action</p>
        <p className="text-xs font-medium text-text">{shieldgpt.recommended_action}</p>
      </div>

      <div className="flex-1">
        <div className="mb-2 flex items-center justify-between">
          <p className="font-mono text-[10px] uppercase tracking-wider text-text-dim font-medium">Trigger Signals</p>
          <span className="font-mono text-xs text-text-dim">Rule Check</span>
        </div>

        {ml.top_factors.length === 0 ? (
          <div className="flex items-center gap-2 text-xs text-text-muted bg-panel-raised p-2.5 rounded-md border border-border">
            <CheckSquare className="h-3.5 w-3.5 text-text-dim shrink-0" />
            Normal activity profile. No suspicious flags or device anomalies detected.
          </div>
        ) : (
          <ul className="space-y-1.5">
            {ml.top_factors.map((factor) => (
              <li key={factor} className="flex items-center gap-2 text-xs text-text-muted bg-panel-raised px-2.5 py-1.5 rounded-md border border-border">
                <CheckSquare className="h-3.5 w-3.5 shrink-0 text-text-dim" />
                {factor}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="grid grid-cols-3 gap-2 border-t border-border pt-3 font-mono text-xs text-text-dim">
        <div>XGBoost Prob: <span className="text-text font-semibold">{(ml.xgboost_score * 100).toFixed(0)}%</span></div>
        <div>Isolation Forest: <span className="text-text font-semibold">{ml.isolation_score === -1 ? 'Anomaly' : 'Normal'}</span></div>
        <div>Rule Score: <span className="text-text font-semibold">{(ml.rule_score * 100).toFixed(0)}%</span></div>
      </div>
    </div>
  )
}
