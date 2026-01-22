# Platform Core Architecture

This document describes the platform-core architecture: discovery, validation, and routing of capability requests.

## Components

- **[Capability registry](capability-registry.md)** — auto-discovers and catalogs capabilities
- **[Request router](request-router.md)** — routes requests to the selected capability
- **[Resource validator](resource-validator.md)** — validates device constraints
- **[API gateway](api-gateway.md)** — single entry point for all requests
- **[Stack composition](stack-composition.md)** — how stacks compose capabilities via platform-core

## Architecture diagram (Mermaid)

```mermaid
flowchart LR
    U[Client\n(curl / app)] -->|HTTP| G[API Gateway\nFastAPI :8000]

    C[Capability contracts\n./capabilities/**/capability.json] --> R[Capability Registry\n(discovery + catalog)]
    G --> R
    R --> RT[Request Router\n(select provider + proxy)]

    RT -->|provider: llm| O[Ollama capability]
    RT -->|provider: retrieval| RC[ChromaDB Retrieval capability]
    RC --> CH[(ChromaDB)]

    subgraph Podman / podman-compose
        G
        O
        RC
        CH
    end
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
