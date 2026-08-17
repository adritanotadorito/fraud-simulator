// Backend contract note: ml/inference.py returns final_risk / xgboost_score
// as floats 0-1. ShieldGPT's confidence has shown up as a string like "97%"
// in the sample payload in the pipeline doc. This helper normalizes either
// shape to a 0-100 number so components don't care which one arrives.
export function toPercent(value) {
  if (value === null || value === undefined) return 0
  if (typeof value === 'string') {
    const parsed = parseFloat(value.replace('%', ''))
    return Number.isFinite(parsed) ? parsed : 0
  }
  return value <= 1 ? Math.round(value * 1000) / 10 : Math.round(value)
}
