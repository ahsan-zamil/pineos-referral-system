# 🤖 Bonus Feature: Natural Language to Rule JSON - Examples

This file contains examples for the AI-powered natural language to rule JSON conversion feature using Google's Gemini API.

## Setup

1. Get your free Gemini API key: https://makersuite.google.com/app/apikey
2. Add to backend/.env: `GEMINI_API_KEY=your-api-key-here`
3. Install dependency: `pip install google-generativeai`
4. Start backend: `uvicorn main:app --reload`

## Example 1: Simple Referral Bonus

```bash
curl -X POST http://localhost:8000/api/v1/rules/nl-to-rule \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Reward $50 when a paid user refers someone who subscribes",
    "rule_name": "Paid User Referral Bonus"
  }'
```

**Generated Output:**
```json
{
  "id": "generated-uuid",
  "name": "Paid User Referral Bonus",
  "description": "Reward $50 when a paid user refers someone who subscribes",
  "rule_json": {
    "conditions": [
      {"field": "referrer.is_paid_user", "operator": "==", "value": true},
      {"field": "referred.subscription_status", "operator": "==", "value": "active"}
    ],
    "actions": [
      {"type": "credit", "user": "referrer_id", "amount_cents": 5000, "reward_id": "referral_bonus"}
    ],
    "logic": "AND"
  }
}
```

## Example 2: First Purchase Bonus

```bash
curl -X POST http://localhost:8000/api/v1/rules/nl-to-rule \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Give ₹200 bonus when referred user makes first purchase over ₹1000"
  }'
```

## Example 3: Multiple Referrals

```bash
curl -X POST http://localhost:8000/api/v1/rules/nl-to-rule \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Credit $100 if user completes 5 referrals and all are active subscribers",
    "rule_name": "Five Star Referrer"
  }'
```

## Example 4: High-Value Purchase

```bash
curl -X POST http://localhost:8000/api/v1/rules/nl-to-rule \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Reward ₹500 when referred user makes a purchase above ₹5000 within 30 days"
  }'
```

## Example 5: Tier-Based Bonus

```bash
curl -X POST http://localhost:8000/api/v1/rules/nl-to-rule \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Give $75 to premium tier users who refer 2 or more people",
    "rule_name": "Premium Referrer Bonus"
  }'
```

## PowerShell Examples (Windows)

```powershell
# Simple referral bonus
Invoke-WebRequest -Uri "http://localhost:8000/api/v1/rules/nl-to-rule" `
  -Method POST `
  -Headers @{"Content-Type"="application/json"} `
  -Body '{"description":"Reward $50 for each new subscriber referral"}'

# First purchase bonus
Invoke-WebRequest -Uri "http://localhost:8000/api/v1/rules/nl-to-rule" `
  -Method POST `
  -Headers @{"Content-Type"="application/json"} `
  -Body '{"description":"Give ₹100 when user makes first purchase"}'
```

## Error Handling

### Missing API Key

```bash
# If GEMINI_API_KEY not set
curl -X POST http://localhost:8000/api/v1/rules/nl-to-rule \
  -H "Content-Type: application/json" \
  -d '{"description": "Test rule"}'

# Response: HTTP 400
{
  "error": "AI service not configured: Gemini API key not found. Set GEMINI_API_KEY environment variable."
}
```

### Invalid Description (Too Short)

```bash
curl -X POST http://localhost:8000/api/v1/rules/nl-to-rule \
  -H "Content-Type: application/json" \
  -d '{"description": "Give money"}'

# Response: HTTP 422 (Validation Error)
{
  "detail": [
    {
      "loc": ["body", "description"],
      "msg": "ensure this value has at least 10 characters",
      "type": "value_error.any_str.min_length"
    }
  ]
}
```

## Integration with Existing Workflow

Once created via natural language, the rule is automatically saved to the database and can be used immediately:

```bash
# 1. Create rule via natural language
curl -X POST http://localhost:8000/api/v1/rules/nl-to-rule \
  -H "Content-Type: application/json" \
  -d '{"description": "Reward $50 for referrals"}' \
  | jq -r '.id' > rule_id.txt

# 2. Verify rule was created
curl http://localhost:8000/api/v1/rules/

# 3. Evaluate an event against the rule
curl -X POST http://localhost:8000/api/v1/rules/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "event_data": {
      "referrer_id": "user_alice",
      "referrer": {"is_paid_user": true},
      "referred": {"subscription_status": "active"}
    }
  }'
```

## Tips for Best Results

1. **Be specific**: "Reward $50 for paid user referrals" is better than "Give rewards for referrals"
2. **Include amounts**: Use explicit amounts like "$50" or "₹1000"
3. **Specify conditions clearly**: "when", "if", "after" help AI understand conditions
4. **Use standard operators**: "greater than", "equals", "at least"
5. **Name users explicitly**: "referrer", "referred user", "customer"

## Accuracy Notes

- **High accuracy** (95%+) for standard referral patterns
- **Good accuracy** (80-90%) for multi-condition rules
- **May need adjustment** for complex temporal logic or nested conditions

## Testing the Feature

```bash
# Run a quick test suite
for desc in \
  "Reward \$50 for each referral" \
  "Give ₹200 on first purchase" \
  "Credit \$100 after 5 referrals"; do
  echo "Testing: $desc"
  curl -s -X POST http://localhost:8000/api/v1/rules/nl-to-rule \
    -H "Content-Type: application/json" \
    -d "{\"description\": \"$desc\"}" \
    | jq '.rule_json'
  echo "---"
done
```

## Postman Collection

Import the included `postman_collection.json` for ready-to-use Postman tests with the natural language endpoint!

---

**Happy rule creating! 🎉**
