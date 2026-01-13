# PineOS Referral System - API Examples

This file contains curl commands and example requests for testing the API.

## Health Check

```bash
curl http://localhost:8000/health
```

## Ledger Operations

### 1. Credit a User Account

**Create a new credit:**
```bash
curl -X POST http://localhost:8000/api/v1/ledger/credit \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: 11111111-1111-1111-1111-111111111111" \
  -d '{
    "user_id": "user_123",
    "amount_cents": 10000,
    "reward_id": "welcome_bonus",
    "reward_status": "confirmed",
    "metadata": {
      "source": "welcome_campaign",
      "campaign_id": "welcome_2026"
    }
  }'
```

**Expected Response (201 Created):**
```json
{
  "data": {
    "id": "uuid-here",
    "user_id": "user_123",
    "entry_type": "credit",
    "amount_cents": 10000,
    "reward_id": "welcome_bonus",
    "reward_status": "confirmed",
    "idempotency_key": "11111111-1111-1111-1111-111111111111",
    "related_entry_id": null,
    "metadata": {
      "source": "welcome_campaign",
      "campaign_id": "welcome_2026"
    },
    "created_at": "2026-01-12T12:00:00"
  },
  "is_duplicate": false
}
```

**Retry same request (200 OK with is_duplicate=true):**
```bash
# Same curl command - will return 200 instead of 201
curl -X POST http://localhost:8000/api/v1/ledger/credit \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: 11111111-1111-1111-1111-111111111111" \
  -d '{
    "user_id": "user_123",
    "amount_cents": 10000,
    "reward_id": "welcome_bonus",
    "metadata": {"source": "welcome_campaign"}
  }'
```

### 2. Debit a User Account

```bash
curl -X POST http://localhost:8000/api/v1/ledger/debit \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: 22222222-2222-2222-2222-222222222222" \
  -d '{
    "user_id": "user_123",
    "amount_cents": 3000,
    "metadata": {
      "reason": "reward_redemption",
      "order_id": "ORD_12345"
    }
  }'
```

### 3. Reverse a Ledger Entry

```bash
# First, get an entry ID from a previous credit
ENTRY_ID="<entry-id-from-credit-response>"

curl -X POST http://localhost:8000/api/v1/ledger/reverse \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: 33333333-3333-3333-3333-333333333333" \
  -d "{
    \"entry_id\": \"$ENTRY_ID\",
    \"reason\": \"User not eligible for reward\",
    \"metadata\": {
      \"admin_id\": \"admin_456\",
      \"ticket_id\": \"TICKET_789\"
    }
  }"
```

### 4. Get User Balance

```bash
curl http://localhost:8000/api/v1/ledger/balance/user_123
```

**Expected Response:**
```json
{
  "user_id": "user_123",
  "balance_cents": 7000,
  "balance_dollars": 70.0,
  "version": 3,
  "updated_at": "2026-01-12T12:05:00"
}
```

### 5. Get Ledger Entries

**All entries:**
```bash
curl "http://localhost:8000/api/v1/ledger/entries?limit=10&offset=0"
```

**Entries for specific user:**
```bash
curl "http://localhost:8000/api/v1/ledger/entries?user_id=user_123&limit=10"
```

## Rule Engine

### 1. Create a Rule

```bash
curl -X POST http://localhost:8000/api/v1/rules/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Paid User Referral Bonus",
    "description": "Reward ₹500 when paid user refers someone who subscribes",
    "rule_json": {
      "conditions": [
        {"field": "referrer.is_paid_user", "operator": "==", "value": true},
        {"field": "referred.subscription_status", "operator": "==", "value": "active"}
      ],
      "actions": [
        {
          "type": "credit",
          "user": "referrer_id",
          "amount_cents": 50000,
          "reward_id": "referral_bonus"
        }
      ],
      "logic": "AND"
    }
  }'
```

### 2. Get All Rules

```bash
curl http://localhost:8000/api/v1/rules/
```

### 3. Evaluate an Event Against Rules

```bash
curl -X POST http://localhost:8000/api/v1/rules/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "event_data": {
      "event_id": "evt_123456",
      "referrer_id": "user_alice",
      "referrer": {
        "is_paid_user": true
      },
      "referred": {
        "user_id": "user_bob",
        "subscription_status": "active"
      }
    }
  }'
```

**Expected Response:**
```json
{
  "event_data": {...},
  "rules_evaluated": 2,
  "rules_triggered": 1,
  "results": [
    {
      "rule_id": "uuid-here",
      "rule_name": "Paid User Referral Bonus",
      "conditions_met": true,
      "actions_executed": [
        {
          "success": true,
          "action_type": "credit",
          "entry_id": "uuid-here",
          "user_id": "user_alice",
          "amount_cents": 50000,
          "is_duplicate": false
        }
      ]
    }
  ]
}
```

### 4. Seed Example Rules

```bash
curl -X POST http://localhost:8000/api/v1/rules/seed-examples
```

## Testing Idempotency

### Scenario: Prevent Double Credit

```bash
# Request 1 - Creates entry
curl -X POST http://localhost:8000/api/v1/ledger/credit \
  -H "Idempotency-Key: test-idempotency-001" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user", "amount_cents": 5000}'

# Request 2 - Returns cached response (200 instead of 201)
curl -X POST http://localhost:8000/api/v1/ledger/credit \
  -H "Idempotency-Key: test-idempotency-001" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user", "amount_cents": 5000}'

# Check balance - should be 5000, not 10000
curl http://localhost:8000/api/v1/ledger/balance/test_user
```

## PowerShell Examples (Windows)

```powershell
# Credit
Invoke-WebRequest -Uri "http://localhost:8000/api/v1/ledger/credit" `
  -Method POST `
  -Headers @{"Idempotency-Key"="11111111-1111-1111-1111-111111111111"; "Content-Type"="application/json"} `
  -Body '{"user_id":"user_123","amount_cents":10000}'

# Get Balance
Invoke-WebRequest -Uri "http://localhost:8000/api/v1/ledger/balance/user_123"
```
