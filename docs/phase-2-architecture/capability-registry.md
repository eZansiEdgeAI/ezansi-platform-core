# Capability Registry Design

## Overview

The Capability Registry is the service discovery component. It automatically detects available capabilities and maintains a catalog of what services are available, where to reach them, and what resources they require.

## Responsibilities

- **Discovery** - Scan for `capability.json` files from deployed capabilities
- **Validation** - Verify capability contracts are valid
- **Cataloging** - Maintain in-memory registry of available services
- **Querying** - Provide REST API to search for capabilities
- **Health Monitoring** - Track which capabilities are running

## Design

### Input: Capability Contracts

Each capability provides a `capability.json` that declares:

```json
{
  "name": "capability-llm-ollama",
  "version": "1.0",
  "description": "Ollama LLM service",
  "provides": ["text-generation"],
  "api": {
    "endpoint": "http://localhost:11434",
    "type": "REST",
    "health_check": "/api/tags"
  },
  "resources": {
    "ram_mb": 6000,
    "cpu_cores": 4,
    "storage_mb": 8000
  },
  "container": {
    "image": "docker.io/ollama/ollama",
    "port": 11434
  },

  // Optional metadata (informational)
  // Prefer these for multi-target capabilities.
  "target_platforms": ["Raspberry Pi 4/5", "AMD64 (x86-64)"],
  "supported_architectures": ["arm64", "amd64"],

  // Optional (deprecated): older single-target field, kept for backwards compatibility.
  "target_platform": "Raspberry Pi 4/5"
}
```

The registry should treat `target_platform`, `target_platforms`, and `supported_architectures` as optional and non-blocking. These fields are useful for UI/selection and documentation, but discovery and routing should not depend on them.

### Discovery Method

**v1 (File-based):**
- Scan `/capabilities/*/capability.json`
- Load all contracts on startup
- Reload periodically (e.g., every 30s)

**v2+ (API-based):**
- Query central registry service
- Pull from remote repository
- Support for private registries

### Registry Data Structure

```python
registry = {
  "text-generation": {
    "provider": "capability-llm-ollama",
    "endpoint": "http://localhost:11434",
    "health_check": "/api/tags",
    "resources": {...}
  },
  "speech-to-text": {
    "provider": "capability-stt-whisper",
    "endpoint": "http://localhost:9000",
    "health_check": "/health",
    "resources": {...}
  }
}
```

### API Endpoints

**List all capabilities:**
```
GET /registry
Response: [
  {
    "name": "capability-llm-ollama",
    "provides": ["text-generation"],
    "endpoint": "http://localhost:11434",
    "status": "healthy"
  },
  ...
]
```

**Get specific capability:**
```
GET /registry/text-generation
Response: {
  "provider": "capability-llm-ollama",
  "endpoint": "http://localhost:11434",
  "resources": {...}
}
```

**Check capability health:**
```
GET /registry/text-generation/health
Response: { "status": "healthy", "uptime_ms": 12345 }
```

## Implementation Considerations

### Error Handling

- Invalid JSON contract → log warning, skip
- Unreachable endpoint → mark as unhealthy
- Resource constraints conflicting → warn operator
- Duplicate capability names → use latest version

### Performance

- Cache registry in memory
- Background health check thread (one per capability)
- Lazy loading if 10+ capabilities

### Security

- Validate endpoint URLs (prevent SSRF)
- Don't expose sensitive environment vars
- Require authentication for modifying registry (v2+)

## Testing Strategy

1. **Unit** - Parse capability.json, validate schema
2. **Integration** - Discover running containers, build registry
3. **E2E** - Full lifecycle: deploy capability → discover → query

## Success Criteria

- [ ] Auto-discover all deployed capabilities
- [ ] Maintain accurate endpoint registry
- [ ] Respond to registry queries in <100ms
- [ ] Handle capability startup/shutdown gracefully
- [ ] Expose comprehensive REST API
