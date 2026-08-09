import { useEffect, useState } from 'react'
import { toPercent } from '../lib/format'
import { severityOf } from '../lib/severity'

// Semicircular gauge, 0-100. Needle transitions smoothly on value change;
// a subtle radar-sweep pulse plays behind it to tie into the SOC "scanning" theme.
export default function RiskGauge({ event }) {
  const [displayValue, setDisplayValue] = useState(0)
  const finalRisk = event ? toPercent(event.ml.final_risk) : 0
  const decision = event?.shieldgpt?.decision || 'ALLOW'
  const sev = severityOf(decision)

  useEffect(() => {
    const timeout = setTimeout(() => setDisplayValue(finalRisk), 50)
    return () => clearTimeout(timeout)
  }, [finalRisk])

  const angle = -90 + (displayValue / 100) * 180
  const radius = 68
  const cx = 100
  const cy = 80

  const arcColor =
    decision === 'ALLOW' ? 'var(--color-safe)' : decision === 'FLAG' ? 'var(--color-flag)' : 'var(--color-block)'

  return (
    <div className="flex flex-col items-center justify-between gap-2 rounded-xl border border-border bg-panel p-4">
      <div className="flex w-full items-center justify-between border-b border-border pb-2">
        <span className="font-sans text-[11px] font-medium uppercase tracking-wider text-text-dim">Risk Score</span>
        <span className="font-mono text-xs text-text-muted">Hybrid Engine</span>
      </div>

      <div className="relative flex flex-col items-center my-1">
        <svg viewBox="0 0 200 115" className="w-48 overflow-visible">
          {/* Track */}
          <path
            d={`M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`}
            fill="none"
            stroke="var(--color-border)"
            strokeWidth="7"
            strokeLinecap="round"
          />
          {/* Value arc */}
          <path
            d={`M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`}
            fill="none"
            stroke={arcColor}
            strokeWidth="7"
            strokeLinecap="round"
            strokeDasharray={`${(displayValue / 100) * Math.PI * radius} ${Math.PI * radius}`}
            style={{ transition: 'stroke-dasharray 0.6s ease-out, stroke 0.3s' }}
          />
          {/* Needle */}
          <g style={{ transform: `rotate(${angle}deg)`, transformOrigin: `${cx}px ${cy}px`, transition: 'transform 0.6s ease-out' }}>
            <line x1={cx} y1={cy} x2={cx} y2={cy - radius + 14} stroke="var(--color-text)" strokeWidth="2" strokeLinecap="round" />
          </g>
          <circle cx={cx} cy={cy} r="3" fill="var(--color-text)" />

          {/* Score percentage text below needle pivot */}
          <text
            x={cx}
            y={cy + 26}
            textAnchor="middle"
            fill="var(--color-text)"
            className="font-mono text-2xl font-bold tracking-tight"
            style={{ fontVariantNumeric: 'tabular-nums' }}
          >
            {displayValue.toFixed(0)}%
          </text>
        </svg>
      </div>

      <div className="rounded-md border border-border bg-panel-raised px-2.5 py-0.5 font-mono text-[11px] text-text-muted">
        Evaluation: <span className="text-text font-medium">{finalRisk < 35 ? 'Low' : finalRisk < 70 ? 'Elevated' : 'High Risk'}</span>
      </div>
    </div>
  )
}
