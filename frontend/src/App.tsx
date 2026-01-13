import { useState, useEffect } from 'react'
import './App.css'
import RuleBuilder from './RuleBuilder'

interface ApiResponse {
    message: string;
    version: string;
    status: string;
}

function App() {
    const [apiStatus, setApiStatus] = useState<ApiResponse | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [activeTab, setActiveTab] = useState<'dashboard' | 'rules'>('dashboard')

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
                <p className="subtitle">Financial Ledger + Rule Engine</p>

                <nav className="tabs">
                    <button
                        className={`tab ${activeTab === 'dashboard' ? 'active' : ''}`}
                        onClick={() => setActiveTab('dashboard')}
                    >
                        Dashboard
                    </button>
                    <button
                        className={`tab ${activeTab === 'rules' ? 'active' : ''}`}
                        onClick={() => setActiveTab('rules')}
                    >
                        Rule Builder
                    </button>
                </nav>
            </header>

            <main className="main-content">
                {activeTab === 'dashboard' ? (
                    <>
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
                            <h2>System Features</h2>
                            <ul>
                                <li>✅ Immutable Financial Ledger</li>
                                <li>✅ Strict Idempotency (Duplicate Prevention)</li>
                                <li>✅ Credit / Debit / Reversal Operations</li>
                                <li>✅ ACID Transactions</li>
                                <li>✅ Rule-Based Referral Engine</li>
                                <li>✅ Visual Rule Builder</li>
                                <li>✅ PostgreSQL Database</li>
                                <li>✅ Comprehensive Test Suite</li>
                            </ul>
                        </div>

                        <div className="info-card">
                            <h2>Quick Links</h2>
                            <div className="links">
                                <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer">
                                    📖 API Documentation (Swagger)
                                </a>
                                <a href="http://localhost:8000/redoc" target="_blank" rel="noopener noreferrer">
                                    📚 API Documentation (ReDoc)
                                </a>
                            </div>
                        </div>
                    </>
                ) : (
                    <RuleBuilder />
                )}
            </main>
        </div>
    )
}

export default App
