import { useEffect, useState } from 'react'
import './App.css'

type Health = { status: string }

function App() {
  const [health, setHealth] = useState('Checking…')

  useEffect(() => {
    const controller = new AbortController()
    fetch('/api/health', { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error('Health check failed')
        const data: Health = await response.json()
        setHealth(data.status)
      })
      .catch(() => {
        if (!controller.signal.aborted) setHealth('API unavailable')
      })
    return () => controller.abort()
  }, [])

  return (
    <main>
      <h1>AgentOS</h1>
      <p>React + TypeScript + FastAPI</p>
      <p role="status">API health: <strong>{health}</strong></p>
    </main>
  )
}

export default App
