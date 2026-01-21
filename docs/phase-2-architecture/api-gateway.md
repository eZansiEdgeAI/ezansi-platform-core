# API Gateway Design

## Overview

The API Gateway is the main HTTP server and single entry point for all client requests. It coordinates with the registry, validator, and router to process requests and orchestrate capabilities.

## Responsibilities

- **Listen** - Accept HTTP requests on port 8000
- **Parse** - Extract request parameters and validate format
- **Authorize** - Check permissions (future feature)
- **Coordinate** - Call registry, validator, router in sequence
- **Respond** - Return results to client
- **Monitor** - Track metrics (latency, errors, throughput)

## Architecture

```
┌──────────────┐
│   Client     │
│   Request    │
└────────┬─────┘
         ↓
┌──────────────────────────────┐
│   API Gateway (port 8000)    │
├──────────────────────────────┤
│ 1. Parse & validate request  │
│ 2. Query Registry            │
│ 3. Run Validator             │
│ 4. Execute via Router        │
│ 5. Return response           │
└─────────────┬────────────────┘
              ↓
    ┌─────────┴──────────┐
    ↓                    ↓
┌─────────┐        ┌──────────┐
│Registry │        │Validator │
└─────────┘        └──────────┘
    ↓
┌────────────┐
│   Router   │
└─────┬──────┘
      ↓
┌──────────────────────┐
│  Capabilities        │
│ (Ollama, Whisper, ...) │
└──────────────────────┘
```

## Endpoints

### System Endpoints

**Health check:**
```
GET /health
Response: { "status": "healthy", "uptime_s": 3600 }
```

**Gateway info:**
```
GET /info
Response: {
  "version": "1.0",
  "platform": "eZansiEdgeAI",
  "capabilities_count": 3,
  "uptime_s": 3600
}
```

**System status:**
```
GET /status
Response: {
  "device": "Raspberry Pi 5 16GB",
  "capabilities": [
    {
      "name": "capability-llm-ollama",
      "status": "healthy",
      "uptime_s": 1800
    },
    ...
  ]
}
```

The implementation supports `GET /status?refresh=true` to actively re-check capability health and mark unavailable capabilities as `unhealthy`.

### Registry Endpoints

```
GET /registry              # List all capabilities
GET /registry/<type>       # Get specific capability
GET /registry/<type>/health # Check capability health
```

### Validation Endpoints

```
POST /validate/capability      # Validate single capability
POST /validate/stack           # Validate deployment stack
GET /constraints               # Get device constraints
```

### Request Endpoints

**Generic request:**
```
POST /
Body: { "type": "text-generation", "prompt": "..." }
```

**Typed endpoints:**
```
POST /generate        # text-generation
POST /transcribe      # speech-to-text
POST /synthesize      # text-to-speech
```

## Request Processing Flow

```python
def handle_request(request):
    1. Parse JSON body
    2. Validate against schema
    3. Check "type" field
    4. Query registry.get_capability(type)
    5. If not found:
       → Return 404 with available types
    6. Check capability health
    7. If unhealthy:
       → Return 503 with retry info
    8. Router.process(request, capability)
    9. Return response or error
```

## Response Format

**Success:**
```json
{
  "status": "success",
  "type": "text-generation",
  "data": {
    "text": "...",
    "tokens": 123
  },
  "metadata": {
    "provider": "capability-llm-ollama",
    "latency_ms": 1234
  }
}
```

**Error:**
```json
{
  "status": "error",
  "type": "text-generation",
  "error": "capability not found",
  "details": "No capability provides 'text-generation'",
  "available_types": ["speech-to-text"],
  "code": "NOT_FOUND"
}
```

## Configuration

**Environment variables:**
```bash
PORT=8000                    # Gateway port
REGISTRY_PATH=/capabilities # Where to find capability.json files
LOG_LEVEL=INFO              # INFO, DEBUG, WARNING, ERROR
CACHE_TTL_SECONDS=30        # Registry cache lifetime
HEALTH_CHECK_INTERVAL=10    # Seconds between health checks
```

**Configuration file (config.yaml):**
```yaml
gateway:
  port: 8000
  host: 0.0.0.0
  log_level: INFO

registry:
  path: /capabilities
  cache_ttl_seconds: 30
  
validator:
  strict_mode: true  # Fail on low headroom
  
router:
  timeout_seconds: 30
  retries: 1
```

## Metrics & Monitoring

**Collected metrics:**
- Request count by endpoint
- Response latency (min, max, avg)
- Error rate by type
- Capability health status
- Response cache hit rate

**Metrics endpoint (optional):**
```
GET /metrics
Response: Prometheus format metrics
```

## Security Considerations

- Input validation (prevent injection)
- Rate limiting (DOS protection)
- Authentication (bearer token, mTLS)
- CORS headers (if needed)
- Request size limits

## Testing Strategy

1. **Unit** - Request parsing, validation logic
2. **Integration** - Full request flow with mock registry
3. **Load** - Concurrent requests, throughput
4. **Failover** - Capability down scenarios
5. **Latency** - End-to-end response time

## Success Criteria

- [ ] Accept requests on port 8000
- [ ] Coordinate all components correctly
- [ ] Return <1s latency for most requests
- [ ] Handle errors gracefully
- [ ] Provide comprehensive metrics
- [ ] Support authentication (v1.1+)
