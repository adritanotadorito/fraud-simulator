import { useEffect, useState } from 'react'
import TopBar from '../components/TopBar'
import LiveTransactionFeed from '../components/LiveTransactionFeed'
import RiskGauge from '../components/RiskGauge'
import ConfidenceMeter from '../components/ConfidenceMeter'
import DecisionBadge from '../components/DecisionBadge'
import ExplainableAIPanel from '../components/ExplainableAIPanel'
import { useLiveFeed } from '../context/WebSocketContext'

export default function Dashboard() {
  const { latestEvent } = useLiveFeed()
  const [selectedEvent, setSelectedEvent] = useState(null)

  // Auto-follow the live feed until the user clicks a specific row to inspect.
  const [autoFollow, setAutoFollow] = useState(true)
  useEffect(() => {
    if (autoFollow && latestEvent) setSelectedEvent(latestEvent)
  }, [latestEvent, autoFollow])

  function handleSelect(evt) {
    setAutoFollow(false)
    setSelectedEvent(evt)
  }

  return (
    <div className="flex h-full flex-col">
      <div className="grid flex-1 grid-cols-3 gap-4 overflow-hidden p-6">
        <div className="col-span-2 flex flex-col gap-4 overflow-y-auto pr-1">
          <div className="grid grid-cols-3 gap-4">
            <DecisionBadge event={selectedEvent} />
            <RiskGauge event={selectedEvent} />
            <ConfidenceMeter event={selectedEvent} />
          </div>

          {!autoFollow && (
            <button
              onClick={() => setAutoFollow(true)}
              className="self-start rounded-full border border-accent/40 px-3 py-1 font-mono text-xs text-accent hover:bg-accent/10"
            >
              ↻ Resume following live feed
            </button>
          )}

          <div className="min-h-[280px] flex-1">
            <ExplainableAIPanel event={selectedEvent} />
          </div>
        </div>

        <div className="col-span-1 min-h-0">
          <LiveTransactionFeed onSelect={handleSelect} selectedId={selectedEvent?.event_id} />
        </div>
      </div>
    </div>
  )
}
