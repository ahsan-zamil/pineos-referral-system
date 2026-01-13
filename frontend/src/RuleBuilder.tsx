import { useState, useEffect } from 'react'
import './RuleBuilder.css'

interface RuleCondition {
    field: string
    operator: string
    value: any
}

interface RuleAction {
    type: string
    user: string
    amount_cents: number
    reward_id: string
}

interface Rule {
    id?: string
    name: string
    description: string
    rule_json: {
        conditions: RuleCondition[]
        actions: RuleAction[]
        logic: string
    }
    is_active?: number
}

export default function RuleBuilder() {
    const [rules, setRules] = useState<Rule[]>([])
    const [selectedRule, setSelectedRule] = useState<Rule | null>(null)
    const [loading, setLoading] = useState(false)

    // New rule form state
    const [newRule, setNewRule] = useState<Rule>({
        name: '',
        description: '',
        rule_json: {
            conditions: [],
            actions: [],
            logic: 'AND'
        }
    })

    useEffect(() => {
        fetchRules()
    }, [])

    const fetchRules = async () => {
        try {
            const response = await fetch('http://localhost:8000/api/v1/rules/')
            const data = await response.json()
            setRules(data)
        } catch (error) {
            console.error('Error fetching rules:', error)
        }
    }

    const addCondition = () => {
        setNewRule({
            ...newRule,
            rule_json: {
                ...newRule.rule_json,
                conditions: [
                    ...newRule.rule_json.conditions,
                    { field: '', operator: '==', value: '' }
                ]
            }
        })
    }

    const updateCondition = (index: number, key: string, value: any) => {
        const updatedConditions = [...newRule.rule_json.conditions]
        updatedConditions[index] = { ...updatedConditions[index], [key]: value }
        setNewRule({
            ...newRule,
            rule_json: { ...newRule.rule_json, conditions: updatedConditions }
        })
    }

    const removeCondition = (index: number) => {
        setNewRule({
            ...newRule,
            rule_json: {
                ...newRule.rule_json,
                conditions: newRule.rule_json.conditions.filter((_, i) => i !== index)
            }
        })
    }

    const addAction = () => {
        setNewRule({
            ...newRule,
            rule_json: {
                ...newRule.rule_json,
                actions: [
                    ...newRule.rule_json.actions,
                    { type: 'credit', user: 'referrer_id', amount_cents: 0, reward_id: '' }
                ]
            }
        })
    }

    const updateAction = (index: number, key: string, value: any) => {
        const updatedActions = [...newRule.rule_json.actions]
        updatedActions[index] = { ...updatedActions[index], [key]: value }
        setNewRule({
            ...newRule,
            rule_json: { ...newRule.rule_json, actions: updatedActions }
        })
    }

    const removeAction = (index: number) => {
        setNewRule({
            ...newRule,
            rule_json: {
                ...newRule.rule_json,
                actions: newRule.rule_json.actions.filter((_, i) => i !== index)
            }
        })
    }

    const createRule = async () => {
        setLoading(true)
        try {
            const response = await fetch('http://localhost:8000/api/v1/rules/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newRule)
            })

            if (response.ok) {
                await fetchRules()
                // Reset form
                setNewRule({
                    name: '',
                    description: '',
                    rule_json: { conditions: [], actions: [], logic: 'AND' }
                })
                alert('Rule created successfully!')
            } else {
                const error = await response.json()
                alert(`Error: ${error.error || 'Failed to create rule'}`)
            }
        } catch (error) {
            console.error('Error creating rule:', error)
            alert('Failed to create rule')
        } finally {
            setLoading(false)
        }
    }

    const seedExamples = async () => {
        setLoading(true)
        try {
            await fetch('http://localhost:8000/api/v1/rules/seed-examples', {
                method: 'POST'
            })
            await fetchRules()
            alert('Example rules created!')
        } catch (error) {
            console.error('Error seeding examples:', error)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="rule-builder">
            <header className="rule-builder-header">
                <h1>🎯 Rule Engine Builder</h1>
                <p>Create and manage referral rules with visual condition/action nodes</p>
            </header>

            <div className="rule-builder-content">
                {/* Existing Rules List */}
                <section className="rules-list-section">
                    <div className="section-header">
                        <h2>Existing Rules</h2>
                        <button onClick={seedExamples} disabled={loading} className="btn-secondary">
                            📋 Load Examples
                        </button>
                    </div>

                    <div className="rules-list">
                        {rules.length === 0 ? (
                            <p className="empty-state">No rules yet. Create one below or load examples.</p>
                        ) : (
                            rules.map((rule) => (
                                <div
                                    key={rule.id}
                                    className={`rule-card ${selectedRule?.id === rule.id ? 'selected' : ''}`}
                                    onClick={() => setSelectedRule(rule)}
                                >
                                    <h3>{rule.name}</h3>
                                    <p className="rule-description">{rule.description}</p>
                                    <div className="rule-stats">
                                        <span className="badge">{rule.rule_json.conditions.length} conditions</span>
                                        <span className="badge">{rule.rule_json.actions.length} actions</span>
                                        <span className="badge">{rule.rule_json.logic}</span>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </section>

                {/* Rule Visualization */}
                {selectedRule && (
                    <section className="rule-visualization">
                        <h2>Rule Flow: {selectedRule.name}</h2>
                        <div className="flow-diagram">
                            <div className="flow-node start-node">
                                <div className="node-header">START</div>
                                <div className="node-content">Event Triggered</div>
                            </div>

                            <div className="flow-arrow">↓</div>

                            <div className="flow-node conditions-node">
                                <div className="node-header">
                                    CONDITIONS ({selectedRule.rule_json.logic})
                                </div>
                                <div className="node-content">
                                    {selectedRule.rule_json.conditions.map((cond, i) => (
                                        <div key={i} className="condition-item">
                                            <code>{cond.field} {cond.operator} {JSON.stringify(cond.value)}</code>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div className="flow-arrow">↓</div>

                            <div className="flow-node actions-node">
                                <div className="node-header">ACTIONS</div>
                                <div className="node-content">
                                    {selectedRule.rule_json.actions.map((action, i) => (
                                        <div key={i} className="action-item">
                                            <strong>{action.type.toUpperCase()}</strong>
                                            <br />
                                            User: {action.user}
                                            <br />
                                            Amount: ₹{action.amount_cents / 100}
                                            <br />
                                            Reward: {action.reward_id}
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div className="flow-arrow">↓</div>

                            <div className="flow-node end-node">
                                <div className="node-header">END</div>
                                <div className="node-content">Ledger Updated</div>
                            </div>
                        </div>

                        <div className="rule-json">
                            <h3>Rule JSON:</h3>
                            <pre>{JSON.stringify(selectedRule.rule_json, null, 2)}</pre>
                        </div>
                    </section>
                )}

                {/* Create New Rule Form */}
                <section className="create-rule-section">
                    <h2>Create New Rule</h2>

                    <div className="form-group">
                        <label>Rule Name *</label>
                        <input
                            type="text"
                            value={newRule.name}
                            onChange={(e) => setNewRule({ ...newRule, name: e.target.value })}
                            placeholder="e.g., Paid User Referral Bonus"
                        />
                    </div>

                    <div className="form-group">
                        <label>Description</label>
                        <textarea
                            value={newRule.description}
                            onChange={(e) => setNewRule({ ...newRule, description: e.target.value })}
                            placeholder="Describe what this rule does..."
                        />
                    </div>

                    <div className="form-group">
                        <label>Logic</label>
                        <select
                            value={newRule.rule_json.logic}
                            onChange={(e) => setNewRule({
                                ...newRule,
                                rule_json: { ...newRule.rule_json, logic: e.target.value }
                            })}
                        >
                            <option value="AND">AND (All conditions must match)</option>
                            <option value="OR">OR (Any condition can match)</option>
                        </select>
                    </div>

                    {/* Conditions */}
                    <div className="form-section">
                        <div className="section-title">
                            <h3>Conditions</h3>
                            <button onClick={addCondition} className="btn-add">+ Add Condition</button>
                        </div>

                        {newRule.rule_json.conditions.map((condition, index) => (
                            <div key={index} className="condition-row">
                                <input
                                    type="text"
                                    value={condition.field}
                                    onChange={(e) => updateCondition(index, 'field', e.target.value)}
                                    placeholder="Field (e.g., referrer.is_paid_user)"
                                />

                                <select
                                    value={condition.operator}
                                    onChange={(e) => updateCondition(index, 'operator', e.target.value)}
                                >
                                    <option value="==">==</option>
                                    <option value="!=">!=</option>
                                    <option value=">">&gt;</option>
                                    <option value="<">&lt;</option>
                                    <option value=">=">&gt;=</option>
                                    <option value="<=">&lt;=</option>
                                    <option value="in">in</option>
                                    <option value="contains">contains</option>
                                </select>

                                <input
                                    type="text"
                                    value={condition.value}
                                    onChange={(e) => {
                                        // Try to parse as JSON for booleans/numbers
                                        let value = e.target.value
                                        try {
                                            value = JSON.parse(e.target.value)
                                        } catch { }
                                        updateCondition(index, 'value', value)
                                    }}
                                    placeholder="Value (true, false, number, or string)"
                                />

                                <button onClick={() => removeCondition(index)} className="btn-remove">
                                    ✕
                                </button>
                            </div>
                        ))}
                    </div>

                    {/* Actions */}
                    <div className="form-section">
                        <div className="section-title">
                            <h3>Actions</h3>
                            <button onClick={addAction} className="btn-add">+ Add Action</button>
                        </div>

                        {newRule.rule_json.actions.map((action, index) => (
                            <div key={index} className="action-row">
                                <select
                                    value={action.type}
                                    onChange={(e) => updateAction(index, 'type', e.target.value)}
                                >
                                    <option value="credit">Credit</option>
                                    <option value="debit">Debit</option>
                                </select>

                                <input
                                    type="text"
                                    value={action.user}
                                    onChange={(e) => updateAction(index, 'user', e.target.value)}
                                    placeholder="User field (e.g., referrer_id)"
                                />

                                <input
                                    type="number"
                                    value={action.amount_cents}
                                    onChange={(e) => updateAction(index, 'amount_cents', parseInt(e.target.value))}
                                    placeholder="Amount in cents"
                                />

                                <input
                                    type="text"
                                    value={action.reward_id}
                                    onChange={(e) => updateAction(index, 'reward_id', e.target.value)}
                                    placeholder="Reward ID"
                                />

                                <button onClick={() => removeAction(index)} className="btn-remove">
                                    ✕
                                </button>
                            </div>
                        ))}
                    </div>

                    <button
                        onClick={createRule}
                        disabled={loading || !newRule.name || newRule.rule_json.conditions.length === 0 || newRule.rule_json.actions.length === 0}
                        className="btn-primary btn-create"
                    >
                        {loading ? 'Creating...' : 'Create Rule'}
                    </button>

                    {/* JSON Preview */}
                    <details className="json-preview">
                        <summary>Preview JSON</summary>
                        <pre>{JSON.stringify(newRule, null, 2)}</pre>
                    </details>
                </section>
            </div>
        </div>
    )
}
