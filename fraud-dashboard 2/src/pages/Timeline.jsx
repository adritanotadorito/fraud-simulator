import { useState, useEffect } from 'react'
import TopBar from '../components/TopBar'
import { Zap, BrainCircuit, RefreshCw } from 'lucide-react'
import { severityOf } from '../lib/severity'
import { useLiveFeed } from '../context/WebSocketContext'

const DEFAULT_SAMPLE_EVENTS = [
  {
    event_id: 'evt_sim_104',
    round: 4,
    persona: 'card_testing',
    outcome: 'BLOCK',
    reasoning: 'FraudGPT attempted rapid micro-transactions across 5 stolen cards. ShieldGPT Rule Engine and XGBoost detected high velocity anomaly and blocked all charges.',
    created_at: new Date().toISOString()
  },
  {
    event_id: 'evt_sim_103',
    round: 3,
    persona: 'device_spoofing',
    outcome: 'FLAG',
    reasoning: 'FraudGPT masked device fingerprint using Android emulator and proxy. ShieldGPT flagged for 3D Secure biometric verification.',
    created_at: new Date(Date.now() - 300000).toISOString()
  },
  {
    event_id: 'evt_sim_102',
    round: 2,
    persona: 'account_takeover',
    outcome: 'BLOCK',
    reasoning: 'FraudGPT attempted credential login from an impossible travel location (Lagos -> NYC in 4 mins). Biometrics and Geo engine blocked session.',
    created_at: new Date(Date.now() - 600000).toISOString()
  }
]

export default function Timeline() {
  const { events: liveFeedEvents } = useLiveFeed()
  const [dbEvents, setDbEvents] = useState([])
  const [memory, setMemory] = useState(null)
  const [loading, setLoading] = useState(false)
  const [simulating, setSimulating] = useState(false)

  async function fetchData() {
    setLoading(true)
    try {
      const [eventsRes, memoryRes] = await Promise.all([
        fetch('http://localhost:8000/api/fraud/events?limit=50'),
        fetch('http://localhost:8000/api/fraud/memory')
      ])
      if (eventsRes.ok) {
        const data = await eventsRes.json()
        setDbEvents(data)
      }
      if (memoryRes.ok) {
        const memData = await memoryRes.json()
        setMemory(memData)
      }
    } catch (err) {
      console.error('Failed to fetch fraud timeline data:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  async function handleSimulateAttack() {
    setSimulating(true)
    try {
      const res = await fetch('http://localhost:8000/api/fraud/simulate-round', { method: 'POST' })
      if (res.ok) {
        await fetchData()
      }
    } catch (err) {
      console.error('Failed to trigger attack round:', err)
    } finally {
      setSimulating(false)
    }
  }

  // Combine DB events with live feed events dynamically
  const liveEventsFormatted = liveFeedEvents
    .filter((e) => e?.fraudgpt || e?.shieldgpt?.decision !== 'ALLOW')
    .map((e, idx) => ({
      event_id: e.event_id || e.transaction?.transaction_id || `evt_live_${idx}`,
      round: e.fraudgpt?.round || (liveFeedEvents.length - idx),
      persona: e.fraudgpt?.persona || 'card_testing',
      outcome: e.shieldgpt?.decision || 'FLAG',
      reasoning: e.shieldgpt?.explanation || 'ShieldGPT flagged transaction anomaly from live stream stream.',
      created_at: e.transaction?.timestamp || new Date().toISOString()
    }))

  const combinedEvents = [...liveEventsFormatted, ...(dbEvents.length > 0 ? dbEvents : DEFAULT_SAMPLE_EVENTS)]
  const totalBlocked = combinedEvents.filter(e => (e.outcome || e.decision) === 'BLOCK').length
  const defenseRate = combinedEvents.length > 0 ? ((totalBlocked / combinedEvents.length) * 100).toFixed(1) : '85.4'

  return (
    <div className="flex h-full flex-col overflow-hidden bg-bg">
      <div className="flex-1 space-y-6 overflow-y-auto p-6">
        {/* Header Action Banner */}
        <div className="flex items-center justify-between rounded-xl border border-border bg-panel p-4.5">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-md border border-border bg-panel-raised text-text-muted">
              <Zap className="h-4 w-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-sans text-sm font-medium text-text">Simulation Console</h2>
                <span className="rounded-md border border-border bg-panel-raised px-2 py-0.5 font-mono text-xs font-normal text-text-muted">
                  {combinedEvents.length} Rounds Evaluated
                </span>
              </div>
              <p className="text-xs text-text-dim mt-0.5">
                Stress-test rule thresholds and evaluate defense responses against multi-persona scenario loads.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2.5">
            <button
              onClick={fetchData}
              disabled={loading}
              className="flex items-center gap-1.5 rounded-md border border-border bg-panel-raised px-3 py-1.5 font-mono text-xs text-text-muted hover:text-text hover:bg-border/40 transition-colors"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            <button
              onClick={handleSimulateAttack}
              disabled={simulating}
              className="flex items-center gap-1.5 rounded-md border border-border bg-text px-3.5 py-1.5 font-sans text-xs font-medium text-bg hover:opacity-90 disabled:opacity-50 transition-colors"
            >
              <Zap className="h-3.5 w-3.5" />
              {simulating ? 'Running Simulation...' : 'Run Simulation'}
            </button>
          </div>
        </div>

        {/* AI Strategy Memory Weights */}
        <div className="rounded-xl border border-border bg-panel p-5">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <BrainCircuit className="h-4 w-4 text-accent" />
              <h3 className="font-sans text-sm font-semibold text-text">FraudGPT Persona Memory & Weights</h3>
            </div>
            <span className="font-mono text-xs text-text-dim">
              Overall Defense Block Rate: {defenseRate}%
            </span>
          </div>

          <div className="grid grid-cols-4 gap-3">
            {Object.entries(memory?.persona_weights || {
              account_takeover: 0.7,
              credential_stuffing: 0.5,
              card_testing: 0.4,
              device_spoofing: 0.6,
              money_mule: 0.8,
              social_engineering: 0.9,
              low_and_slow: 0.85
            }).map(([persona, weight]) => (
              <div key={persona} className="rounded-lg border border-border/80 bg-panel-raised p-3">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-medium text-text capitalize">
                    {persona.replace('_', ' ')}
                  </span>
                  <span className="font-mono text-xs font-bold text-accent">w={weight}</span>
                </div>
                <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-bg">
                  <div
                    className="h-full rounded-full bg-accent transition-all duration-500"
                    style={{ width: `${Math.min(weight * 100, 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Timeline Stepper */}
        <div className="rounded-xl border border-border bg-panel p-5">
          <h3 className="mb-4 font-sans text-sm font-semibold text-text">Attack History & Round Timeline</h3>

          <div className="relative space-y-6 pl-6 before:absolute before:left-2.5 before:top-3 before:bottom-3 before:w-0.5 before:bg-border">
            {combinedEvents.map((evt, idx) => {
              const outcome = (evt.outcome || evt.decision || 'ALLOW').toUpperCase()
              const sev = severityOf(outcome)

              return (
                <div key={evt.event_id || idx} className="animate-feed-row-in relative flex items-start gap-4">
                  {/* Circle Node */}
                  <div className={`absolute -left-6 top-1 flex h-5 w-5 items-center justify-center rounded-full border-2 border-bg ${sev.bg}`}>
                    <span className={`h-2 w-2 rounded-full ${sev.dot}`} />
                  </div>

                  <div className="flex-1 rounded-xl border border-border bg-panel-raised p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="rounded-md bg-accent/10 px-2 py-0.5 font-mono text-xs font-semibold text-accent">
                          Round #{evt.round || (combinedEvents.length - idx)}
                        </span>
                        <span className="font-mono text-xs font-bold text-text uppercase tracking-wide">
                          {evt.persona ? evt.persona.replace('_', ' ') : 'Card Testing Bot'}
                        </span>
                      </div>
                      <span className={`rounded-full px-2.5 py-0.5 font-mono text-xs font-semibold ${sev.bg} ${sev.text}`}>
                        {outcome}
                      </span>
                    </div>

                    {evt.reasoning && (
                      <p className="mt-2 text-xs text-text-muted italic leading-relaxed">
                        "{evt.reasoning}"
                      </p>
                    )}

                    <div className="mt-3 flex items-center justify-between border-t border-border/60 pt-2 font-mono text-[11px] text-text-dim">
                      <span>Event ID: {evt.event_id}</span>
                      <span>
                        {evt.created_at
                          ? new Date(evt.created_at).toLocaleTimeString()
                          : `${(idx + 1) * 3} mins ago`}
                      </span>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
