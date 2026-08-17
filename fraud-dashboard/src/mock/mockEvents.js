// Mock live-event generator — shaped to match the REAL contract from the
// ml/ pipeline doc (FraudGPT -> Digital Twin -> XGBoost/IsolationForest ->
// Rule Engine -> Fusion Engine -> ShieldGPT). This is intentional: once
// Riya's FastAPI endpoint is live, the WebSocket message should already
// look like this, so no component code needs to change — just flip
// USE_MOCK to false in WebSocketContext.jsx.

const MERCHANTS = [
  'Amazon.in', 'Zomato', 'Flipkart', 'PayZone ATM', 'Swiggy', 'IRCTC',
  'Uber', 'BigBasket', 'Croma Electronics', 'MakeMyTrip', 'Unknown POS #4471',
]

// Personas FraudGPT picks from (per prompts.py) — mocked here until the
// real FraudGPT call is wired up on the backend.
const PERSONAS = [
  'Card Testing Bot', 'Synthetic Identity Ring', 'Account Takeover Specialist',
  'Velocity Abuser', 'Geo-Spoofing Mule', 'Micro-Transaction Prober',
]

const RULE_REASONS = [
  'High transaction amount',
  'New / unrecognized device',
  'High geo velocity (impossible travel)',
  'High biometric deviation',
  'High transaction velocity',
  'Merchant category flagged in threat_intel',
]

let txnCounter = 1000

function pick(arr) {
  return arr[Math.floor(Math.random() * arr.length)]
}

function pickN(arr, n) {
  return [...arr].sort(() => 0.5 - Math.random()).slice(0, n)
}

function round2(n) {
  return Math.round(n * 100) / 100
}

export function generateMockEvent() {
  txnCounter += 1

  // Roughly mirrors real-world class imbalance: mostly clean traffic.
  const r = Math.random()
  const tier = r < 0.7 ? 'low' : r < 0.9 ? 'mid' : 'high'

  const xgboost_score =
    tier === 'low' ? round2(Math.random() * 0.3) :
    tier === 'mid' ? round2(0.3 + Math.random() * 0.35) :
    round2(0.65 + Math.random() * 0.35)

  const isolation_score = tier === 'high' && Math.random() < 0.6 ? -1 : 1
  const rule_score =
    tier === 'low' ? round2(Math.random() * 0.2) :
    tier === 'mid' ? round2(0.2 + Math.random() * 0.35) :
    round2(0.5 + Math.random() * 0.5)

  // Same weighted formula as fusion.py
  const final_risk = round2(
    0.55 * xgboost_score +
    0.20 * (isolation_score === -1 ? 1 : 0) +
    0.15 * rule_score +
    0.10 * Math.random() * (tier === 'high' ? 1 : 0.3) // threat_intel placeholder
  )

  const decision = final_risk < 0.35 ? 'ALLOW' : final_risk < 0.7 ? 'FLAG' : 'BLOCK'
  const confidencePct = 60 + Math.floor(Math.random() * 39)

  const isAttackRound = decision !== 'ALLOW' && Math.random() < 0.65
  const flaggedReasons = decision === 'ALLOW' ? [] : pickN(RULE_REASONS, 1 + Math.floor(Math.random() * 3))

  const explanation =
    decision === 'ALLOW'
      ? 'ShieldGPT evaluated transaction as legitimate. User behavioral profile aligns with normal transaction history score.'
      : decision === 'FLAG'
      ? `ShieldGPT flagged this transaction for step-up verification: ${flaggedReasons[0]?.toLowerCase()}, combined with an elevated fusion risk score.`
      : `ShieldGPT blocked this transaction: ${flaggedReasons.join(', ').toLowerCase()} pushed the fused risk score above the automated block threshold.`

  const recommended_action =
    decision === 'ALLOW' ? 'No action needed — monitor as usual.' :
    decision === 'FLAG' ? 'Require 3D Secure / biometric step-up authentication.' :
    'Temporarily block transaction and require multi-factor re-verification.'

  return {
    event_id: `evt_${txnCounter}`,
    transaction: {
      transaction_id: `txn_${txnCounter}`,
      user_id: `user_${100 + Math.floor(Math.random() * 40)}`,
      account_id: `acc_${200 + Math.floor(Math.random() * 40)}`,
      device_id: `dev_${Math.floor(Math.random() * 999)}`,
      amount: +(Math.random() * 48000 + 100).toFixed(2),
      currency: 'INR',
      merchant: pick(MERCHANTS),
      timestamp: new Date().toISOString(),
    },
    fraudgpt: isAttackRound
      ? {
          persona: pick(PERSONAS),
          round: 1 + Math.floor(Math.random() * 5),
        }
      : null,
    ml: {
      xgboost_score,
      isolation_score,
      rule_score,
      final_risk,
      top_factors: flaggedReasons,
    },
    shieldgpt: {
      decision, // ALLOW | FLAG | BLOCK
      confidence: `${confidencePct}%`,
      explanation,
      recommended_action,
    },
  }
}
