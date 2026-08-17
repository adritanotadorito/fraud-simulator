/**
 * DatasetContext.jsx
 * Persists uploaded dataset state across route changes so navigating
 * away and back to Real & Simulated Data doesn't lose the loaded data.
 */
import { createContext, useContext, useState, useRef } from 'react'

const DatasetContext = createContext(null)

export function DatasetProvider({ children }) {
  // Upload metadata
  const [uploadResult, setUploadResult] = useState(null)
  const [hasUploaded, setHasUploaded]   = useState(false)

  // The full list of uploaded transactions (from the server)
  const [uploadedTxns, setUploadedTxns] = useState([])

  // Streamed rows accumulated so far
  const [rows, setRows]         = useState([])
  const [offset, setOffset]     = useState(0)
  const [latestId, setLatestId] = useState(null)
  const [speedIdx, setSpeedIdx] = useState(1)

  // Whether streaming was active when the user navigated away
  // (we pause on unmount and auto-offer to resume on remount)
  const [wasPlaying, setWasPlaying] = useState(false)

  const reset = () => {
    setUploadResult(null)
    setHasUploaded(false)
    setUploadedTxns([])
    setRows([])
    setOffset(0)
    setLatestId(null)
    setSpeedIdx(1)
    setWasPlaying(false)
  }

  return (
    <DatasetContext.Provider value={{
      uploadResult, setUploadResult,
      hasUploaded, setHasUploaded,
      uploadedTxns, setUploadedTxns,
      rows, setRows,
      offset, setOffset,
      latestId, setLatestId,
      speedIdx, setSpeedIdx,
      wasPlaying, setWasPlaying,
      reset,
    }}>
      {children}
    </DatasetContext.Provider>
  )
}

export function useDataset() {
  const ctx = useContext(DatasetContext)
  if (!ctx) throw new Error('useDataset must be used inside DatasetProvider')
  return ctx
}
