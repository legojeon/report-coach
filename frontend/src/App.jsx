import { BrowserRouter, Routes, Route } from 'react-router-dom'
import MainPage from './features/MainPage'
import LoginPage from './features/LoginPage'
import SignupPage from './features/SignupPage'
import ProfilePage from './features/ProfilePage'
import PlanPage from './features/PlanPage'
import ListPage from './features/ListPage'
import ChatPage from './features/ChatPage'
import WritePage from './features/WritePage'
import NotePage from './features/NotePage'
import HealthPage from './features/HealthPage'
import './App.css'

function App() {
  return (
    <BrowserRouter
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true
      }}
    >
      <Routes>
        <Route path="/" element={<MainPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/plan" element={<PlanPage />} />
        <Route path="/list" element={<ListPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/write" element={<WritePage />} />
        <Route path="/notes" element={<NotePage />} />
        <Route path="/health" element={<HealthPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
