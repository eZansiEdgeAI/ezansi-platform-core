# Capability Registry Design

## Overview

The Capability Registry is the service discovery component. It automatically detects available capabilities and maintains a catalog of what services are available, where to reach them, and what resources they require.

## Responsibilities

- **Discovery** — scan for `capability.json` files from deployed capabilities
- **Validation** — verify capability contracts are valid
- **Cataloging** — maintain in-memory registry of available services
- **Querying** — provide REST API to search for capabilities
- **Health monitoring** — track which capabilities are running

## Design

### Input: capability contracts

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
  "target_platforms": ["Raspberry Pi 4/5", "AMD64 (x86-64)"],
  "supported_architectures": ["arm64", "amd64"],
  "target_platform": "Raspberry Pi 4/5"
}
```

The registry should treat `target_platform`, `target_platforms`, and `supported_architectures` as optional and non-blocking. These fields are useful for UI/selection and documentation, but discovery and routing should not depend on them.

### Discovery method

**v1 (file-based):**

- Scan `/capabilities/*/capability.json`
- Load all contracts on startup
- Reload periodically (e.g., every 30s)

### API endpoints

**List all capabilities:**

```
GET /registry
```

**Get specific capability:**

```
GET /registry/text-generation
```
