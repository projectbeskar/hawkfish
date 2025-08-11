import { useState, useEffect } from 'react'
import { apiClient } from './utils/api'
import Login from './components/Login'
import Dashboard from './components/Dashboard'

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // Check if we have a stored token
    const token = apiClient.getToken()
    if (token) {
      // Try to validate the token by making a simple API call
      apiClient.getSystems(1, 1)
        .then(() => {
          setIsAuthenticated(true)
        })
        .catch(() => {
          // Token is invalid, clear it
          apiClient.clearToken()
        })
        .finally(() => {
          setIsLoading(false)
        })
    } else {
      setIsLoading(false)
    }
  }, [])

  const handleLogin = () => {
    setIsAuthenticated(true)
  }

  const handleLogout = () => {
    apiClient.clearToken()
    setIsAuthenticated(false)
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-lg text-gray-600">Loading...</div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Login onLogin={handleLogin} />
  }

  return <Dashboard onLogout={handleLogout} />
}

export default App
