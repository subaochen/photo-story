import React, { useState } from 'react'
import { Routes, Route, useNavigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import UploadPage from './pages/UploadPage'
import ProcessingPage from './pages/ProcessingPage'
import ResultsPage from './pages/ResultsPage'
import StoryPage from './pages/StoryPage'
import ExportPage from './pages/ExportPage'
import Header from './components/Header'
import './index.css'
import './App.css'

function App() {
  const [token, setToken] = useState(() => sessionStorage.getItem('token') || '')
  const [currentUser, setCurrentUser] = useState(() => sessionStorage.getItem('currentUser') || '')
  const [currentTaskId, setCurrentTaskId] = useState('')
  const [uploadFiles, setUploadFiles] = useState([])

  const navigate = useNavigate()

  const handleLogin = (token, username) => {
    sessionStorage.setItem('token', token)
    sessionStorage.setItem('currentUser', username)
    setToken(token)
    setCurrentUser(username)
    navigate('/upload')
  }

  const handleLogout = () => {
    sessionStorage.removeItem('token')
    sessionStorage.removeItem('currentUser')
    setToken('')
    setCurrentUser('')
    navigate('/login')
  }

  const handleTaskCreated = (taskId) => {
    setCurrentTaskId(taskId)
    localStorage.setItem('lastTaskId', taskId)
    navigate(`/processing/${taskId}`)
  }

  const handleFilesSelected = (files) => {
    setUploadFiles(files)
  }

  return (
    <div className="app">
      {token && <Header currentUser={currentUser} onLogout={handleLogout} />}
      <Routes>
        <Route
          path="/login"
          element={<LoginPage onLogin={handleLogin} />}
        />
        <Route
          path="/upload"
          element={
            <UploadPage
              token={token}
              onFilesSelected={handleFilesSelected}
              onTaskCreated={handleTaskCreated}
            />
          }
        />
        <Route
          path="/processing/:taskId"
          element={<ProcessingPage token={token} />}
        />
        <Route
          path="/results"
          element={<ResultsPage token={token} />}
        />
        <Route
          path="/story"
          element={<StoryPage token={token} />}
        />
        <Route
          path="/export"
          element={<ExportPage token={token} />}
        />
      </Routes>
    </div>
  )
}

export default App
