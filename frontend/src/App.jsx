import { BrowserRouter, Route, Routes } from 'react-router-dom'
import HomePage from './pages/HomePage'
import ResultsPage from './pages/ResultsPage'
import ThemeToggle from './components/ThemeToggle'

export default function App() {
  return (
    <BrowserRouter>
      <ThemeToggle />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/results/:sessionId" element={<ResultsPage />} />
      </Routes>
    </BrowserRouter>
  )
}
