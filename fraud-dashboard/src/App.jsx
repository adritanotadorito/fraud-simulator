import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { WebSocketProvider } from './context/WebSocketContext'
import { AuthProvider } from './context/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import Navbar from './components/Navbar'
import Login from './pages/Login'
import Signup from './pages/Signup'
import UserDashboard from './pages/UserDashboard'
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
                      <Route path="/" element={<UserDashboard />} />
                      <Route path="/admin" element={
                        <ProtectedRoute adminOnly><AdminDashboard /></ProtectedRoute>
                      } />
                      {/* Ops pages — admin only */}
                      <Route path="/ops/overview" element={
                        <ProtectedRoute adminOnly><Dashboard /></ProtectedRoute>
                      } />
                      <Route path="/ops/timeline" element={
                        <ProtectedRoute adminOnly><Timeline /></ProtectedRoute>
                      } />
                      <Route path="/ops/monitoring" element={
                        <ProtectedRoute adminOnly><Monitoring /></ProtectedRoute>
                      } />
                      <Route path="/ops/real-data" element={
                        <ProtectedRoute adminOnly><RealData /></ProtectedRoute>
                      } />
                      <Route path="/ops/reports" element={
                        <ProtectedRoute adminOnly><Reports /></ProtectedRoute>
                      } />
                    </Routes>
                  </main>
                </div>
              </ProtectedRoute>
            } />
          </Routes>
        </BrowserRouter>
      </WebSocketProvider>
    </AuthProvider>
  )
}
