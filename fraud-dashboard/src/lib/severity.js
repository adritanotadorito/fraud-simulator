// Single source of truth for decision -> color mapping.
// Used by LiveTransactionFeed now; Risk Gauge / Confidence Meter / Decision
// Badge (D2) should import from here too, so severity colors never drift.

export const SEVERITY = {
  ALLOW: {
    label: 'ALLOW',
    text: 'text-safe font-medium',
    bg: 'bg-panel-raised',
    border: 'border-border',
    dot: 'bg-safe',
  },
  FLAG: {
    label: 'FLAG',
    text: 'text-flag font-medium',
    bg: 'bg-panel-raised',
    border: 'border-border',
    dot: 'bg-flag',
  },
  BLOCK: {
    label: 'BLOCK',
    text: 'text-block font-medium',
    bg: 'bg-panel-raised',
    border: 'border-border',
    dot: 'bg-block',
  },
}

export function severityOf(decision) {
  return SEVERITY[decision] || SEVERITY.ALLOW
}
