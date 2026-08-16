import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { WebSocketProvider } from './context/WebSocketContext'
import Navbar from './components/Navbar'
import Dashboard from './pages/Dashboard'
import Timeline from './pages/Timeline'
import Monitoring from './pages/Monitoring'
import Reports from './pages/Reports'
import RealData from './pages/RealData'

export default function App() {
  return (
    <WebSocketProvider>
      <BrowserRouter>
        <div className="flex h-screen w-screen flex-col overflow-hidden bg-bg text-text">
          <Navbar />
          <main className="flex-1 overflow-hidden">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/real-data" element={<RealData />} />
              <Route path="/timeline" element={<Timeline />} />
              <Route path="/monitoring" element={<Monitoring />} />
              <Route path="/reports" element={<Reports />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </WebSocketProvider>
  )
}

