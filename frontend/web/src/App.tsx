import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import { ErrorProvider } from './contexts/ErrorContext'
import { Navbar } from './components/layout/Navbar'
import { ErrorToastContainer } from './components/common/ErrorToast'
import { Home } from './pages/Home'
import { Login } from './pages/Login'
import { Register } from './pages/Register'
import { Dashboard } from './pages/Dashboard'
import { PuzzleCreate } from './pages/PuzzleCreate'
import { PuzzleGame } from './pages/PuzzleGame'

function App() {
  return (
    <ErrorProvider>
      <AuthProvider>
        <Router>
          <div className="min-h-screen bg-gray-50">
            <Navbar />
            <main className="container mx-auto px-4 py-8">
              <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/puzzle/create" element={<PuzzleCreate />} />
                <Route path="/puzzle/play/:id" element={<PuzzleGame />} />
              </Routes>
            </main>
            {/* 전역 에러 토스트 컨테이너 */}
            <ErrorToastContainer />
          </div>
        </Router>
      </AuthProvider>
    </ErrorProvider>
  )
}

export default App
