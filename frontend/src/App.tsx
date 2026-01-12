import { useState, useEffect } from 'react'
import './App.css'

interface ApiResponse {
    message: string;
    version: string;
    status: string;
}

function App() {
    const [apiStatus, setApiStatus] = useState<ApiResponse | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        fetch('http://localhost:8000/')
            .then(res => res.json())
            .then(data => {
                setApiStatus(data)
                setLoading(false)
            })
            .catch(err => {
                setError(err.message)
                setLoading(false)
            })
    }, [])

    return (
        <div className="app">
            <header className="header">
                <h1>🌲 PineOS Referral System</h1>
                <p className="subtitle">Welcome to the PineOS Referral Challenge</p>
            </header>

            <main className="main-content">
                <div className="status-card">
                    <h2>Backend API Status</h2>
                    {loading && <p className="loading">Connecting to backend...</p>}
                    {error && <p className="error">Error: {error}</p>}
                    {apiStatus && (
                        <div className="status-info">
                            <p className="status-success">✓ Connected</p>
                            <p><strong>Message:</strong> {apiStatus.message}</p>
                            <p><strong>Version:</strong> {apiStatus.version}</p>
                            <p><strong>Status:</strong> {apiStatus.status}</p>
                        </div>
                    )}
                </div>

                <div className="info-card">
                    <h2>Getting Started</h2>
                    <p>This is the initial setup for the PineOS referral system.</p>
                    <ul>
                        <li>✓ Backend: FastAPI running on port 8000</li>
                        <li>✓ Frontend: React + TypeScript + Vite on port 5173</li>
                        <li>⏳ Next: Implement referral features</li>
                    </ul>
                </div>
            </main>
        </div>
    )
}

export default App
