# Backend ↔ AI Integration Contract

## Request Schema
```json
{
  "user_id": "string",
  "session_id": "string",
  "payload": "string",
  "context": {}
}
```

## Response Schema
```json
{
  "status": "success",
  "data": {
    "intent": "string",
    "action": "string"
  }
}
```

## Error Codes
- `AI_5001`: Provider Timeout
- `AI_5002`: Validation Failure

## Retry Rules
- Max Retries: 3
- Backoff: Exponential (Base 2s)
