import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import AgentChat from './pages/AgentChat'

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<AgentChat />} />
      </Routes>
    </Router>
  )
}

export default App
