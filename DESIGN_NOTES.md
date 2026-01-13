# Design Notes - PineOS Referral System

This document provides detailed design notes, architectural decisions, and implementation details for the take-home challenge.

---

## 🎯 Core Design Principles

### 1. Correctness Over Performance

**Decision:** Prioritize transaction correctness and data integrity over raw speed.

**Implementation:**
- Row-level locking (`SELECT ... FOR UPDATE`) prevents race conditions
- ACID transactions ensure consistency
- Idempotency prevents duplicate operations

**Tradeoff:** Slightly slower under high concurrency, but eliminates data corruption risk.

### 2. Immutability as First Principle

**Decision:** Ledger entries are append-only, never modified or deleted.

**Benefits:**
- Complete audit trail for regulatory compliance
- Easier debugging (full history preserved)
- Natural event sourcing pattern
- Prevents accidental data corruption

**Implementation:**
```python
class LedgerEntry(Base):
    # No UPDATE or DELETE operations allowed
    # Corrections via new REVERSAL entries
```

### 3. Idempotency via Request Hashing

**Problem:** Network retries can cause duplicate credits.

**Solution:** Hash(request_body + idempotency_key) for duplicate detection.

**Why not just idempotency key?**
- Same key with different request should error (prevents key reuse)
- Hash ensures exact request match

**Example:**
```python
# Request 1: key=ABC, amount=100 → Creates entry
# Request 2: key=ABC, amount=100 → Returns existing (idempotent)
# Request 3: key=ABC, amount=200 → Error 409 (key conflict)
```

---

## 🗄️ Database Design Decisions

### 1. PostgreSQL Choice

**Why PostgreSQL over MySQL/MongoDB?**
- **JSONB**: Native JSON support with indexing (metadata storage)
- **Row Locking**: `FOR UPDATE` prevents race conditions
- **ACID**: Strong transaction guarantees
- **Mature**: Battle-tested for financial systems

### 2. Money Storage (Cents vs Decimal)

**Decision:** `BIGINT` (cents) instead of `DECIMAL(10,2)` (dollars)

**Reasoning:**
```python
# Problem with decimals:
0.1 + 0.2 = 0.30000000000000004  # Floating point error

# Solution with integers:
10 + 20 = 30  # Exact arithmetic
```

**Industry Standard:**
- Stripe API uses cents
- PayPal uses cents
- All major payment processors use smallest currency unit

### 3. Materialized Balances

**Why separate `user_balances` table?**

**Without materialized balances:**
```sql
SELECT SUM(
  CASE entry_type
    WHEN 'CREDIT' THEN amount_cents
    WHEN 'DEBIT' THEN -amount_cents
    WHEN 'REVERSAL' THEN /* complex logic */
  END
) FROM ledger_entries WHERE user_id = ?
-- Slow for millions of entries
```

**With materialized balances:**
```sql
SELECT balance_cents FROM user_balances WHERE user_id = ?
-- O(1) lookup
```

**Consistency maintained:**
```python
# Atomic transaction
with db.transaction():
    create_ledger_entry()
    update_balance()
# Both or neither
```

### 4. Optimistic Locking (version field)

**Purpose:** Detect concurrent balance updates.

**How it works:**
```python
# User A reads: balance=100, version=5
# User B reads: balance=100, version=5

# User A updates: SET balance=150, version=6 WHERE version=5 ✓
# User B updates: SET balance=120, version=6 WHERE version=5 ✗ (version already 6)
```

**Current Implementation:**
- Uses row-level locking instead (`FOR UPDATE`)
- Version field kept for future optimistic locking migration

---

## 🔐 Security & Correctness

### Idempotency Security

**Threat:** Malicious actors reusing idempotency keys.

**Protection:**
1. **Hash validation**: Different request with same key → 409 error
2. **Key expiration**: Could add TTL to idempotency records
3. **User scoping**: Could scope keys per user

**Example Attack:**
```bash
# Attacker intercepts Alice's request
curl -H "Idempotency-Key: alice-key-123" \
  -d '{"user_id": "alice", "amount_cents": 1000}'

# Attacker tries to reuse key for themselves
curl -H "Idempotency-Key: alice-key-123" \
  -d '{"user_id": "attacker", "amount_cents": 1000000}'
# → HTTP 409: Request hash mismatch
```

### Race Condition Prevention

**Scenario:** Two simultaneous credits for same user.

**Without locking:**
```python
# Thread 1: Read balance=100
# Thread 2: Read balance=100
# Thread 1: Write balance=150 (100+50)
# Thread 2: Write balance=120 (100+20)
# Final: 120 (lost 50!) ❌
```

**With row locking:**
```python
# Thread 1: Lock row, read balance=100
# Thread 2: Wait on lock...
# Thread 1: Write balance=150, release lock
# Thread 2: Read balance=150, write balance=170
# Final: 170 ✓
```

---

## 🎨 API Design Decisions

### HTTP Status Codes for Idempotency

**Decision:** Return different status codes for new vs duplicate requests.

**Implementation:**
- **201 Created**: New entry created
- **200 OK**: Duplicate request, cached response returned

**Benefits:**
- Client can detect if operation was actually executed
- Useful for metrics (how many retries?)
- Debugging easier (logs show duplicate rate)

**Alternative Considered:**
- Always return 200 (GitHub API approach)
- Rejected: Less informative for clients

### UUID vs Auto-Increment IDs

**Decision:** Use UUID v4 for `ledger_entry.id`

**Why not auto-increment?**
```python
# Auto-increment exposes info
id=1000 → "Only 1000 transactions total"
id=5234 → "About 5000 transactions today"

# UUID hides info
id=f3b4c8d9-... → No information leak
```

**Other Benefits:**
- Globally unique (multi-region deployments)
- Can generate client-side
- No sequence lock contention

---

## 🧩 Rule Engine Design

### JSON-Based Rules

**Why JSON instead of Python code?**

**JSON Rules:**
```json
{
  "conditions": [{"field": "user.is_paid", "operator": "==", "value": true}],
  "actions": [{"type": "credit", "amount_cents": 5000}]
}
```

**Pros:**
- **Non-engineers can create**: Marketing team can define rules
- **Stored in DB**: Versionable, auditable
- **No deployment**: Change rules without code deployment
- **Sandboxed**: No arbitrary code execution

**Cons:**
- Limited expressiveness (but sufficient for most use cases)
- Requires rule evaluation engine

### Operator Support

**Implemented:**
- `==`, `!=`, `>`, `<`, `>=`, `<=`
- `in`, `not_in`, `contains`

**Why these?**
- Cover 95% of use cases
- Simple to evaluate
- Safe (no code injection)

**Not implemented (but could add):**
- `regex`, `starts_with`, `ends_with`
- Complex aggregations (`COUNT`, `SUM`)
- Temporal logic (`within_last_30_days`)

### Rule Idempotency

**Challenge:** Same event shouldn't trigger reward twice.

**Solution:** Generate idempotency key from:
```python
idempotency_key = uuid5(
    namespace="rule_engine",
    name=f"{rule_id}:{user_id}:{event_id}"
)
```

**Benefits:**
- Same event + same rule = same idempotency key
- Ledger service deduplicates automatically
- No separate rule execution tracking needed

---

## 🧪 Testing Strategy

### Test Pyramid

**Unit Tests (80%):**
- Idempotency logic
- Balance calculations
- Reversal linking
- Hash computation

**Integration Tests (15%):**
- Full API endpoints
- Database transactions
- Rule evaluation

**End-to-End Tests (5%):**
- Docker Compose setup
- Frontend → Backend → DB

### Critical Tests

**1. Idempotency Test** (Most Important)
```python
def test_duplicate_credit_returns_same_response():
    # First request
    response1 = post_credit(idempotency_key="ABC")
    # Second request (duplicate)
    response2 = post_credit(idempotency_key="ABC")
    
    assert response1.entry_id == response2.entry_id
    assert balance == 100  # Not 200!
```

**Why critical?**
- Core requirement of challenge
- Real-world financial system risk
- Easy to get wrong

**2. Balance Correctness Test**
```python
def test_balance_consistency():
    credit(user, 100)
    credit(user, 50)
    debit(user, 30)
    
    assert get_balance(user) == 120
```

**Why critical?**
- Money arithmetic must be exact
- Tests transaction atomicity
- Validates materialized balance

### Test Database

**Decision:** Use separate test database.

**Why?**
- Clean slate for each test
- No contamination from dev data
- Can drop/recreate tables freely

**Implementation:**
```python
# conftest.py
@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(engine)  # Create tables
    yield session
    Base.metadata.drop_all(engine)    # Drop tables
```

---

## 🚀 Deployment Considerations

### Docker Compose for Development

**Why not Kubernetes for this challenge?**
- Overkill for single-instance demo
- Faster to set up
- Easier for reviewers to run

**Production would use:**
- Kubernetes for orchestration
- Managed PostgreSQL (AWS RDS)
- Redis for caching
- Prometheus for monitoring

### Environment Variables

**Decision:** Use `.env` files for configuration.

**Why not hardcode?**
- Secrets not in source control
- Different configs per environment
- Standard practice

**Sensitive values:**
- `DATABASE_URL` (credentials)
- `SECRET_KEY` (JWT signing)
- `OPENAI_API_KEY` (optional LLM feature)

### Migration Strategy

**Decision:** Alembic for schema migrations.

**Why Alembic?**
- Industry standard for SQLAlchemy
- Version-controlled schema changes
- Rollback support
- Auto-generation from models

**Migration workflow:**
```bash
# 1. Modify models.py
# 2. Generate migration
alembic revision --autogenerate -m "Add user_tier column"
# 3. Review migration
# 4. Apply migration
alembic upgrade head
```

---

## 📊 Scalability Considerations

### Current Bottlenecks

**1. Database writes** (Row locking serializes updates)
- Solution: Shard by user_id
- Solution: Use optimistic locking for read-heavy workloads

**2. Idempotency lookup** (Unique constraint check)
- Solution: Add hash-based sharding
- Solution: Use Bloom filter for fast negatives

**3. Rule evaluation** (Evaluates all rules per event)
- Solution: Index rules by event type
- Solution: Compile rules to bytecode

### Scale Targets

**1 million users, 10 million transactions/month:**
- Current setup handles: ~100 req/s
- With optimizations: ~1000 req/s
- With sharding: ~10,000 req/s

**Optimizations needed at scale:**
- Read replicas for balance lookups
- Write batching (group similar operations)
- Connection pooling (pgbouncer)
- Caching layer (Redis for balances)

---

## 🔮 Future Enhancements

### 1. Event Sourcing

**Current:** Ledger entries are event log, but not full event sourcing.

**Full event sourcing:**
```python
# Store all events
UserSignedUp(user_id="alice", timestamp=...)
ReferralMade(referrer="alice", referred="bob", timestamp=...)

# Rebuild state from events
balance = sum(event.amount for event in events)
```

**Benefits:**
- Time travel (replay events)
- Analytics (count referrals over time)
- Flexible projections

### 2. CQRS (Command Query Responsibility Segregation)

**Idea:** Separate read and write models.

**Write model (commands):**
- CreateCredit
- CreateDebit
- ReverseEntry

**Read model (queries):**
- GetBalance (denormalized)
- GetTransactionHistory (pre-aggregated)

### 3. Webhook System

**Current:** API-driven (pull)
**Future:** Event-driven (push)

```python
# On ledger entry creation
@event_handler("ledger_entry.created")
def notify_webhooks(entry):
    for webhook in get_webhooks(user_id):
        requests.post(webhook.url, json=entry.to_dict())
```

---

## 📝 Code Quality Practices

### Type Hints

**Usage:** All functions have type hints.

```python
def credit(
    request: LedgerCreditRequest,
    idempotency_key: str
) -> Tuple[LedgerEntry, bool]:
```

**Benefits:**
- IDE autocomplete
- Static type checking (mypy)
- Documentation

### Docstrings

**Format:** Google-style docstrings.

```python
def _check_idempotency(self, idempotency_key: str, request_data: dict):
    """
    Check if request is duplicate based on idempotency key.
    
    Args:
        idempotency_key: Unique key for request deduplication
        request_data: Request body dictionary
    
    Returns:
        Existing LedgerEntry if duplicate, None otherwise
    
    Raises:
        HTTPException: If idempotency key exists with different request
    """
```

### Error Handling

**Strategy:** Fail fast, informative errors.

```python
# Bad
except Exception:
    return {"error": "Something went wrong"}

# Good
except IntegrityError as e:
    if "idempotency_key" in str(e):
        # Return existing entry (race condition)
    else:
        raise HTTPException(500, f"Database error: {str(e)}")
```

---

## 🏆 Design Validation

### Requirements Met

✅ **Immutable ledger entries** - Append-only, never modified  
✅ **Credit/debit/reversal flows** - All implemented with tests  
✅ **Reward lifecycle** - Statuses defined (PENDING → CONFIRMED → PAID / REVERSED)  
✅ **Strict idempotency** - Hash-based duplicate detection  
✅ **Money in cents** - Integer storage, no floating-point errors  
✅ **ACID transactions** - Row locking + atomic commits  
✅ **Full auditability** - JSONB metadata, complete history  
✅ **Rule engine** - JSON-defined conditions + actions  
✅ **Visual rule builder** - React UI with flow diagram  

### Design Strengths

1. **Correctness prioritized**: Idempotency and ACID guarantees
2. **Clear abstractions**: Service layer separates business logic
3. **Testable**: 15+ tests covering edge cases
4. **Documented**: Inline comments explain "why" not just "what"
5. **Production patterns**: Migrations, Docker, environment configs

### Known Limitations

1. **No authentication**: All endpoints public (would add JWT)
2. **No rate limiting**: Could DOS with high request volume
3. **Single database**: No replication or sharding
4. **No caching**: Every balance lookup hits DB
5. **No monitoring**: No metrics or alerting

---

**This document reflects the thought process and design decisions made during development. All tradeoffs were conscious choices balancing correctness, simplicity, and time constraints.**

---

*Design Notes - PineOS Referral System Take-Home Challenge*
