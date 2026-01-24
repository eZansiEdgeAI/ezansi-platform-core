# Platform Core Architecture

This document describes the platform-core architecture: discovery, validation, and routing of capability requests.

## Components

- **[Capability registry](capability-registry.md)** — auto-discovers and indexes capabilities
- **[Request router](request-router.md)** — routes requests to the selected capability
- **[Resource validator](resource-validator.md)** — validates device constraints
- **[API gateway](api-gateway.md)** — single entry point for all requests
- **[Stack composition](stack-composition.md)** — how stacks compose capabilities via platform-core

## Architecture diagram

```text
                    +----------------------+
                    |  Client (curl / app) |
                    +----------+-----------+
                               |
                               | HTTP
                               v
                    +----------+-----------+
                    |      API Gateway     |
                    |    FastAPI :8000     |
                    +----------+-----------+
                               |
                               | reads ./capabilities/**/capability.json
                               v
                    +----------+-----------+
                    |  Capability Registry |
                    |     (discovery)      |
                    +----------+-----------+
                               |
                               | routes by service type
                               v
                    +----------+-----------+
                    |     Request Router   |
                    |   (select + proxy)   |
                    +-----+-----------+----+
                          |           |
                          |           |
                          v           v
              +-----------+--+   +----+-------------------+
              |   Ollama LLM  |   |  ChromaDB Retrieval   |
              |  capability   |   |      capability       |
              +--------------+   +-----------+------------+
                                               |
                                               v
                                       +-------+-------+
                                       |    ChromaDB    |
                                       +---------------+

All services typically run under Podman / podman-compose.
```

## High-level flow

```
Client Request
    ↓
┌──────────────────────────────┐
│      API Gateway (8000)      │
├──────────────────────────────┤
│ • Route requests             │
│ • Validate against schema    │
└────────┬─────────────────────┘
    ↓
┌──────────────────────────────┐
│   Capability Registry        │
├──────────────────────────────┤
│ • Discover capabilities      │
│ • Find provider for request  │
└────────┬─────────────────────┘
    ↓
┌──────────────────────────────┐
│  Resource Validator          │
├──────────────────────────────┤
│ • Check device resources     │
│ • Validate compatibility     │
└────────┬─────────────────────┘
    ↓
┌──────────────────────────────┐
│   Request Router             │
├──────────────────────────────┤
│ • Proxy to capability        │
│ • Transform response         │
└────────┬─────────────────────┘
    ↓
Capability Endpoint (Ollama, ChromaDB, ...)
```

## File structure (core pieces)

```
ezansi-platform-core/
├── src/
│   └── ezansi_platform_core/
│       ├── registry.py        # capability discovery
│       ├── router.py          # request routing
│       ├── validator.py       # resource checking
│       └── app.py             # FastAPI gateway
├── config/
├── tools/
├── tests/
├── docs/
└── podman-compose.yml
```
