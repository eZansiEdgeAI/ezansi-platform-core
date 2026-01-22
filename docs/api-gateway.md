# API Gateway Design

## Overview

The API Gateway is the main HTTP server and single entry point for all client requests. It coordinates with the registry, validator, and router to process requests and orchestrate capabilities.

Note: some sections describe desired end-state behavior; verify against current implementation before relying on a specific endpoint.

## Responsibilities

- **Listen** — accept HTTP requests on port 8000
- **Parse** — extract request parameters and validate format
- **Authorize** — check permissions (future feature)
- **Coordinate** — call registry, validator, router in sequence
- **Respond** — return results to client
- **Monitor** — track metrics (latency, errors, throughput)

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

### System endpoints

**Health check:**
```
GET /health
Response: { "status": "healthy", "uptime_s": 3600 }
```

**System status:**
```
GET /status
```

The implementation supports `GET /status?refresh=true` to actively re-check capability health and mark unavailable capabilities as `unhealthy`.

### Registry endpoints

```
GET /registry              # List all capabilities
GET /registry/<type>       # Get specific capability
```

### Validation endpoints

```
POST /validate/capability      # Validate single capability
POST /validate/stack           # Validate deployment stack
GET /constraints               # Get device constraints
```

### Request endpoints

**Generic request:**
```
POST /
Body: { "type": "text-generation", "payload": { ... } }
```

## Configuration

**Environment variables:**
```bash
PORT=8000                     # Gateway port
REGISTRY_PATH=/capabilities    # Where to find capability.json files
LOG_LEVEL=INFO                 # INFO, DEBUG, WARNING, ERROR
CACHE_TTL_SECONDS=30           # Registry cache lifetime
HEALTH_CHECK_INTERVAL=10       # Seconds between health checks
```
