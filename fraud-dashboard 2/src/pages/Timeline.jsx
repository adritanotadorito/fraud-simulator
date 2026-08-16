import { useState, useEffect } from 'react'
import {
  Zap, BrainCircuit, RefreshCw, Plus, X, Trash2, Sliders, Play, Check, ShieldAlert, Sparkles, ChevronDown
} from 'lucide-react'
import { severityOf } from '../lib/severity'
import { useLiveFeed } from '../context/WebSocketContext'

const DEFAULT_PERSONAS = {
  account_takeover: { label: 'Account Takeover', weight: 0.7, description: 'Stolen credentials login attempt from foreign IP/device' },
  credential_stuffing: { label: 'Credential Stuffing', weight: 0.5, description: 'Automated rapid login attempts across multiple accounts' },
  card_testing: { label: 'Card Testing', weight: 0.4, description: 'Rapid micro-transactions at multiple merchants' },
  device_spoofing: { label: 'Device Spoofing', weight: 0.6, description: 'Masking device fingerprint using emulator or proxy' },
  money_mule: { label: 'Money Mule', weight: 0.8, description: 'Moving illicit funds through rapid account transfers' },
  social_engineering: { label: 'Social Engineering', weight: 0.9, description: 'Coercing user into legitimate-looking transfer' },
  low_and_slow: { label: 'Low And Slow', weight: 0.85, description: 'Gradual small fraud attempts to bypass velocity rules' }
}

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

  // Selected persona for manual simulation run
  const [selectedPersona, setSelectedPersona] = useState('ALL')

  // Custom user-defined parameters / personas
  const [customParams, setCustomParams] = useState(() => {
    try {
      const saved = localStorage.getItem('fraud_custom_parameters')
      return saved ? JSON.parse(saved) : {}
    } catch (_) {
      return {}
    }
  })

  // Add Parameter Modal State
  const [showAddModal, setShowAddModal] = useState(false)
  const [newParamName, setNewParamName] = useState('')
  const [newParamWeight, setNewParamWeight] = useState(0.75)
  const [newParamDesc, setNewParamDesc] = useState('')
  const [addError, setAddError] = useState('')

  // Edit weight state
  const [editingParam, setEditingParam] = useState(null)
  const [editWeightVal, setEditWeightVal] = useState(0.7)

  // Save custom params to localStorage
  useEffect(() => {
    try {
      localStorage.setItem('fraud_custom_parameters', JSON.stringify(customParams))
    } catch (_) {}
  }, [customParams])

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

  async function handleSimulateAttack(targetPersona = null) {
    const personaToRun = targetPersona || (selectedPersona !== 'ALL' ? selectedPersona : null)
    setSimulating(true)
    try {
      const url = personaToRun
        ? `http://localhost:8000/api/fraud/simulate-round?persona=${encodeURIComponent(personaToRun)}`
        : 'http://localhost:8000/api/fraud/simulate-round'
      const res = await fetch(url, { method: 'POST' })
      if (res.ok) {
        await fetchData()
      }
    } catch (err) {
      console.error('Failed to trigger attack round:', err)
    } finally {
      setSimulating(false)
    }
  }

  // Handle adding a new parameter
  const handleAddParameter = (e) => {
    e.preventDefault()
    if (!newParamName.trim()) {
      setAddError('Parameter name is required')
      return
    }

    const key = newParamName.trim().toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '')
    if (!key) {
      setAddError('Please enter a valid parameter name')
      return
    }

    if (DEFAULT_PERSONAS[key] || customParams[key]) {
      setAddError('A parameter with this name already exists')
      return
    }

    const newParam = {
      label: newParamName.trim(),
      weight: parseFloat(newParamWeight) || 0.7,
      description: newParamDesc.trim() || 'Custom attack scenario parameter',
      isCustom: true,
      createdAt: new Date().toISOString()
    }

    setCustomParams(prev => ({ ...prev, [key]: newParam }))
    setNewParamName('')
    setNewParamWeight(0.75)
    setNewParamDesc('')
    setAddError('')
    setShowAddModal(false)
  }

  // Delete a custom parameter
  const handleDeleteParameter = (key) => {
    setCustomParams(prev => {
      const updated = { ...prev }
      delete updated[key]
      return updated
    })
  }

  // Update weight of a parameter
  const handleSaveWeight = (key) => {
    const weightVal = Math.max(0, Math.min(1, parseFloat(editWeightVal) || 0.5))
    if (customParams[key]) {
      setCustomParams(prev => ({
        ...prev,
        [key]: { ...prev[key], weight: weightVal }
      }))
    }
    setEditingParam(null)
  }

  // Merge backend memory weights with custom parameter weights
  const mergedWeights = {}
  
  // 1. Standard personas
  const backendWeights = memory?.persona_weights || {}
  Object.entries(DEFAULT_PERSONAS).forEach(([key, info]) => {
    mergedWeights[key] = {
      key,
      label: info.label,
      weight: backendWeights[key] ?? info.weight,
      description: info.description,
      isCustom: false
    }
  })

  // 2. Custom parameters
  Object.entries(customParams).forEach(([key, info]) => {
    mergedWeights[key] = {
      key,
      label: info.label || key.replace(/_/g, ' '),
      weight: info.weight ?? 0.7,
      description: info.description || 'Custom parameter',
      isCustom: true
    }
  })

  // Format events
  const liveEventsFormatted = liveFeedEvents
    .filter((e) => e?.fraudgpt || e?.shieldgpt?.decision !== 'ALLOW')
    .map((e, idx) => ({
      event_id: e.event_id || e.transaction?.transaction_id || `evt_live_${idx}`,
      round: e.fraudgpt?.round || (liveFeedEvents.length - idx),
      persona: e.fraudgpt?.persona || 'card_testing',
      outcome: e.shieldgpt?.decision || 'FLAG',
      reasoning: e.shieldgpt?.explanation || 'ShieldGPT flagged transaction anomaly from live stream.',
      created_at: e.transaction?.timestamp || new Date().toISOString()
    }))

  const combinedEvents = [...liveEventsFormatted, ...(dbEvents.length > 0 ? dbEvents : DEFAULT_SAMPLE_EVENTS)]
  const totalBlocked = combinedEvents.filter(e => (e.outcome || e.decision) === 'BLOCK').length
  const defenseRate = combinedEvents.length > 0 ? ((totalBlocked / combinedEvents.length) * 100).toFixed(1) : '85.4'

  return (
    <div className="flex h-full flex-col overflow-hidden bg-bg">
      <div className="flex-1 space-y-6 overflow-y-auto p-6">
        
        {/* Header Action Banner */}
        <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-border bg-panel p-4.5">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-md border border-border bg-panel-raised text-text-muted">
              <Zap className="h-4 w-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-sans text-sm font-semibold text-text">Simulation Console</h2>
                <span className="rounded-md border border-border bg-panel-raised px-2 py-0.5 font-mono text-xs text-text-muted">
                  {combinedEvents.length} Rounds Evaluated
                </span>
              </div>
              <p className="text-xs text-text-dim mt-0.5">
                Stress-test rule thresholds and evaluate defense responses against multi-persona scenario loads.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            {/* Persona Selector Dropdown */}
            <div className="relative flex items-center rounded-md border border-border bg-bg px-2.5 py-1.5">
              <Sliders className="h-3.5 w-3.5 text-text-dim mr-2" />
              <select
                value={selectedPersona}
                onChange={e => setSelectedPersona(e.target.value)}
                className="bg-transparent font-mono text-xs text-text outline-none cursor-pointer pr-4"
              >
                <option value="ALL" className="bg-panel text-text">All Personas (Random / Bandit)</option>
                {Object.values(mergedWeights).map(p => (
                  <option key={p.key} value={p.key} className="bg-panel text-text">
                    {p.label} (w={p.weight}) {p.isCustom ? '★ Custom' : ''}
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={fetchData}
              disabled={loading}
              className="flex items-center gap-1.5 rounded-md border border-border bg-panel-raised px-3 py-1.5 font-mono text-xs text-text-muted hover:text-text hover:bg-border/40 transition-colors"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>

            <button
              onClick={() => handleSimulateAttack()}
              disabled={simulating}
              className="flex items-center gap-1.5 rounded-md border border-border bg-text px-4 py-1.5 font-sans text-xs font-semibold text-bg hover:opacity-90 disabled:opacity-50 transition-colors shadow-sm"
            >
              <Zap className="h-3.5 w-3.5 fill-current" />
              {simulating ? 'Running Simulation...' : 'Run Simulation'}
            </button>
          </div>
        </div>

        {/* ── FraudGPT Persona Memory & Weights Section ── */}
        <div className="rounded-xl border border-border bg-panel p-5">
          <div className="mb-4 flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <BrainCircuit className="h-4.5 w-4.5 text-accent" />
              <h3 className="font-sans text-sm font-semibold text-text">FraudGPT Persona Memory & Weights</h3>
              <span className="rounded-full bg-accent/10 border border-accent/20 px-2.5 py-0.5 font-mono text-[10px] text-accent font-semibold">
                {Object.keys(mergedWeights).length} Parameters
              </span>
            </div>
            
            <div className="flex items-center gap-3">
              <span className="font-mono text-xs text-text-dim">
                Defense Block Rate: <strong className="text-safe">{defenseRate}%</strong>
              </span>
              <button
                onClick={() => { setShowAddModal(true); setAddError(''); }}
                className="flex items-center gap-1.5 rounded-md border border-accent/40 bg-accent/10 px-3 py-1.5 font-sans text-xs font-semibold text-accent hover:bg-accent/20 transition-all"
              >
                <Plus className="h-3.5 w-3.5" />
                Add Parameter
              </button>
            </div>
          </div>

          {/* Grid of Parameters / Personas */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {Object.values(mergedWeights).map((param) => {
              const weightVal = param.weight
              const isEditing = editingParam === param.key
              
              return (
                <div
                  key={param.key}
                  className={`group relative rounded-xl border p-3.5 transition-all duration-200 ${
                    param.isCustom
                      ? 'border-accent/40 bg-panel-raised/90 hover:border-accent'
                      : 'border-border/80 bg-panel-raised hover:border-border'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="font-sans text-xs font-semibold text-text capitalize">
                          {param.label}
                        </span>
                        {param.isCustom && (
                          <span className="rounded bg-accent/15 px-1.5 py-0.2 font-mono text-[9px] font-bold text-accent uppercase">
                            Custom
                          </span>
                        )}
                      </div>
                      <p className="font-sans text-[11px] text-text-dim mt-1 line-clamp-2 leading-snug">
                        {param.description}
                      </p>
                    </div>

                    <div className="flex items-center gap-1 shrink-0">
                      {param.isCustom && (
                        <button
                          onClick={() => handleDeleteParameter(param.key)}
                          title="Delete Parameter"
                          className="opacity-0 group-hover:opacity-100 p-1 text-text-dim hover:text-block transition-opacity"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Weight Slider / Bar */}
                  <div className="mt-3">
                    <div className="flex items-center justify-between font-mono text-xs mb-1">
                      <span className="text-[10px] text-text-dim uppercase tracking-wider">Weight</span>
                      {isEditing ? (
                        <div className="flex items-center gap-1">
                          <input
                            type="number"
                            step="0.05"
                            min="0"
                            max="1"
                            value={editWeightVal}
                            onChange={e => setEditWeightVal(e.target.value)}
                            className="w-12 bg-bg border border-border rounded px-1 text-xs text-accent text-right outline-none"
                          />
                          <button
                            onClick={() => handleSaveWeight(param.key)}
                            className="p-0.5 text-safe hover:bg-safe/10 rounded"
                          >
                            <Check className="h-3 w-3" />
                          </button>
                          <button
                            onClick={() => setEditingParam(null)}
                            className="p-0.5 text-text-dim hover:bg-panel rounded"
                          >
                            <X className="h-3 w-3" />
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1">
                          <span
                            onClick={() => {
                              if (param.isCustom) {
                                setEditingParam(param.key)
                                setEditWeightVal(param.weight)
                              }
                            }}
                            className={`font-bold ${param.isCustom ? 'cursor-pointer hover:underline text-accent' : 'text-accent'}`}
                            title={param.isCustom ? "Click to edit weight" : "System learned weight"}
                          >
                            w={weightVal}
                          </span>
                        </div>
                      )}
                    </div>

                    {/* Progress indicator */}
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-bg">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${
                          weightVal >= 0.8 ? 'bg-block' : weightVal >= 0.5 ? 'bg-accent' : 'bg-safe'
                        }`}
                        style={{ width: `${Math.min(weightVal * 100, 100)}%` }}
                      />
                    </div>
                  </div>

                  {/* Quick simulate persona button */}
                  <div className="mt-3 border-t border-border/40 pt-2 flex justify-end">
                    <button
                      onClick={() => handleSimulateAttack(param.key)}
                      disabled={simulating}
                      className="flex items-center gap-1 font-mono text-[10px] text-text-dim hover:text-accent transition-colors"
                    >
                      <Play className="h-2.5 w-2.5 fill-current" /> Simulate
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* ── Add Parameter Modal ── */}
        {showAddModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-feed-row-in">
            <div className="w-full max-w-md rounded-xl border border-border bg-panel p-6 shadow-2xl space-y-4">
              <div className="flex items-center justify-between border-b border-border pb-3">
                <div className="flex items-center gap-2">
                  <Plus className="h-4.5 w-4.5 text-accent" />
                  <h3 className="font-sans text-sm font-semibold text-text">Add Custom Parameter / Persona</h3>
                </div>
                <button
                  onClick={() => setShowAddModal(false)}
                  className="text-text-dim hover:text-text"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <form onSubmit={handleAddParameter} className="space-y-4">
                <div>
                  <label className="block font-sans text-xs font-medium text-text-muted mb-1">
                    Parameter / Persona Name <span className="text-block">*</span>
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Synthetic Identity Fraud"
                    value={newParamName}
                    onChange={e => setNewParamName(e.target.value)}
                    className="w-full rounded-md border border-border bg-bg px-3 py-2 font-mono text-xs text-text outline-none focus:border-accent placeholder:text-text-dim"
                    autoFocus
                  />
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="font-sans text-xs font-medium text-text-muted">
                      Weight ($w$)
                    </label>
                    <span className="font-mono text-xs font-bold text-accent">
                      w = {newParamWeight}
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0.0"
                    max="1.0"
                    step="0.05"
                    value={newParamWeight}
                    onChange={e => setNewParamWeight(parseFloat(e.target.value))}
                    className="w-full accent-accent cursor-pointer"
                  />
                  <div className="flex justify-between font-mono text-[10px] text-text-dim mt-1">
                    <span>0.0 (Low Risk)</span>
                    <span>0.5 (Medium)</span>
                    <span>1.0 (High Threat)</span>
                  </div>
                </div>

                <div>
                  <label className="block font-sans text-xs font-medium text-text-muted mb-1">
                    Scenario Description
                  </label>
                  <textarea
                    rows={2}
                    placeholder="e.g. Fraudster combines real SSN with fake details to build synthetic credit profiles."
                    value={newParamDesc}
                    onChange={e => setNewParamDesc(e.target.value)}
                    className="w-full rounded-md border border-border bg-bg px-3 py-2 font-sans text-xs text-text outline-none focus:border-accent placeholder:text-text-dim resize-none"
                  />
                </div>

                {addError && (
                  <p className="font-mono text-xs text-block bg-block/10 border border-block/20 rounded p-2">
                    {addError}
                  </p>
                )}

                <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
                  <button
                    type="button"
                    onClick={() => setShowAddModal(false)}
                    className="rounded-md border border-border bg-panel-raised px-4 py-2 font-sans text-xs font-medium text-text-muted hover:text-text transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="flex items-center gap-1.5 rounded-md border border-border bg-accent/90 px-5 py-2 font-sans text-xs font-semibold text-bg hover:bg-accent transition-colors"
                  >
                    <Plus className="h-3.5 w-3.5" />
                    Save Parameter
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* ── Timeline Stepper ── */}
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
                          {evt.persona ? evt.persona.replace(/_/g, ' ') : 'Card Testing Bot'}
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
