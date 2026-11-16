import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import Navbar from './components/layout/Navbar'
import Dashboard from './pages/Dashboard'
import CreateCampaign from './pages/CreateCampaign'
import Workspace from './pages/Workspace'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <div className="min-h-screen bg-surface-base">
          <Navbar />
          <main className="pt-16 pb-20 sm:pb-0">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/create" element={<CreateCampaign />} />
              <Route path="/workspace/:projectId" element={<Workspace />} />
            </Routes>
          </main>
        </div>
      </AuthProvider>
    </BrowserRouter>
  )
}
