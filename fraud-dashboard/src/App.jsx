import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { WebSocketProvider } from './context/WebSocketContext'
import { AuthProvider } from './context/AuthContext'
import { DatasetProvider } from './context/DatasetContext'
import ProtectedRoute from './components/ProtectedRoute'
import Navbar from './components/Navbar'
import Login from './pages/Login'
import Signup from './pages/Signup'
import AdminDashboard from './pages/AdminDashboard'
import Dashboard from './pages/Dashboard'
import Timeline from './pages/Timeline'
import Monitoring from './pages/Monitoring'
import Reports from './pages/Reports'
import RealData from './pages/RealData'

export default function App() {
  return (
    <AuthProvider>
      <WebSocketProvider>
        <DatasetProvider>
          <BrowserRouter>
            <Routes>
              {/* Public routes */}
              <Route path="/login" element={<Login />} />
              <Route path="/signup" element={<Signup />} />

              {/* Protected routes with layout */}
              <Route path="/*" element={
                <ProtectedRoute>
                  <div className="flex h-screen w-screen flex-col overflow-hidden bg-bg text-text">
                    <Navbar />
                    <main className="flex-1 overflow-hidden">
                      <Routes>
                        <Route path="/" element={<Navigate to="/ops/real-data" replace />} />
                        <Route path="/admin" element={
                          <ProtectedRoute adminOnly><AdminDashboard /></ProtectedRoute>
                        } />
                        {/* Ops pages — all authenticated users */}
                        <Route path="/ops/overview"   element={<Dashboard />} />
                        <Route path="/ops/timeline"   element={<Timeline />} />
                        <Route path="/ops/monitoring" element={<Monitoring />} />
                        <Route path="/ops/real-data"  element={<RealData />} />
                        <Route path="/ops/reports"    element={<Reports />} />
                      </Routes>
                    </main>
                  </div>
                </ProtectedRoute>
              } />
            </Routes>
          </BrowserRouter>
        </DatasetProvider>
      </WebSocketProvider>
    </AuthProvider>
  )
}
