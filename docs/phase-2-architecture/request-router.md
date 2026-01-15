# Request Router Design

## Overview

The Request Router accepts client requests and routes them to the appropriate capability based on what service is requested. It acts as a dispatcher that knows how to reach each capability from the registry.

## Responsibilities

- **Accept requests** - Handle incoming HTTP requests for various services
- **Identify capability** - Determine which capability is needed
- **Validate request** - Check request format matches capability API
- **Proxy request** - Forward to capability endpoint
- **Transform response** - Convert response back to client format
- **Error handling** - Return appropriate error if capability unavailable

## Request Flow

```
Client: {"type": "text-generation", "prompt": "Hello"}
    ↓
Router checks registry: "text-generation" → "capability-llm-ollama"
    ↓
Router validates request schema against API spec
    ↓
Router proxies to: http://localhost:11434/api/generate
    ↓
Capability returns response
    ↓
Router returns to client
```

## Design

### Request Format

All requests include a `type` field indicating which capability is needed:

```json
POST /
{
  "type": "text-generation",
  "prompt": "Explain quantum computing",
  "model": "mistral:latest",
  "stream": true
}
```

The router uses `type` to:
1. Query registry for matching capability
2. Transform request to capability's native format
3. Send to capability's endpoint

### Routing Table

```python
routes = {
  "text-generation": {
    "capability": "capability-llm-ollama",
    "endpoint": "http://localhost:11434/api/generate",
    "transform": llm_transform_request,
    "reverse_transform": llm_transform_response
  },
  "speech-to-text": {
    "capability": "capability-stt-whisper",
    "endpoint": "http://localhost:9000/transcribe",
    "transform": stt_transform_request,
    "reverse_transform": stt_transform_response
  }
}
```

### API Endpoints

**Generic request:**
```
POST / 
Body: {"type": "...", ...}
Response: capability-specific response
```

**Typed endpoints (convenience):**
```
POST /generate          # text-generation
POST /transcribe        # speech-to-text
POST /synthesize        # text-to-speech
```

## Transform Functions

Different capabilities have different APIs. Transformers normalize the request/response:

**Request Transform Example:**
```python
def llm_transform_request(request):
  # Client: {"type": "text-generation", "prompt": "..."}
  # LLM API expects: {"model": "mistral", "prompt": "..."}
  return {
    "model": request.get("model", "mistral:latest"),
    "prompt": request["prompt"],
    "stream": request.get("stream", false)
  }
```

**Response Transform Example:**
```python
def llm_transform_response(response):
  # LLM returns: {"response": "...", "eval_count": 123}
  # Client expects: {"type": "text-generation", "text": "..."}
  return {
    "type": "text-generation",
    "text": response["response"],
    "tokens": response.get("eval_count", 0)
  }
```

## Load Balancing (Future)

If multiple capabilities provide the same service:

```python
routes["text-generation"] = [
  {"capability": "llm-ollama", "weight": 0.7},
  {"capability": "llm-gpt4all", "weight": 0.3}
]

# Router picks one based on weight/availability
```

## Error Handling

**Capability not found:**
```json
{
  "error": "text-generation capability not available",
  "available_types": ["speech-to-text"]
}
```

**Capability unhealthy:**
```json
{
  "error": "text-generation capability is not responding",
  "retry_after_seconds": 30
}
```

**Request validation error:**
```json
{
  "error": "invalid request",
  "details": "missing required field: 'prompt'"
}
```

## Testing Strategy

1. **Unit** - Test transform functions with mock data
2. **Integration** - Route requests to real capabilities
3. **Load** - Simulate concurrent requests
4. **Failover** - Test behavior when capability is down

## Success Criteria

- [ ] Route requests to correct capability
- [ ] Transform requests/responses correctly
- [ ] Return <100ms latency for routing decision
- [ ] Handle capability failures gracefully
- [ ] Support both generic and typed endpoints
