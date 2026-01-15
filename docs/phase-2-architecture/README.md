# Phase 2: Platform Core Architecture

This directory contains the detailed design for Phase 2 development of the eZansiEdgeAI platform.

## Overview

Phase 2 builds the orchestration layer (`ezansi-platform-core`) that discovers and composes multiple capabilities into learning stacks.

## Components

- **[Capability Registry](capability-registry.md)** - Auto-discovers and catalogs capabilities
- **[Request Router](request-router.md)** - Routes requests to appropriate capability
- **[Resource Validator](resource-validator.md)** - Validates device constraints
- **[API Gateway](api-gateway.md)** - Single entry point for all requests
- **[Stack Composition](stack-composition.md)** - How to create and deploy capability stacks

## Quick Architecture

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
Capability Endpoint (Ollama, Whisper, etc.)
```

## File Structure

```
ezansi-platform-core/
├── src/
│   ├── registry.py            # Capability discovery
│   ├── router.py              # Request routing
│   ├── validator.py           # Resource checking
│   └── gateway.py             # HTTP server
├── config/
│   └── device-constraints.json
├── examples/
│   ├── stack-voice-assistant.yml
│   └── stack-document-qa.yml
├── tests/
├── docs/
│   └── phase-2-architecture/  # This directory
└── docker-compose.yml         # Run everything
```

## Next Steps

1. **Design Review** - Validate architecture with team
2. **Implementation** - Build registry, router, validator, gateway
3. **Testing** - Unit and integration tests
4. **Integration** - Wire with existing capabilities
5. **Documentation** - User and developer guides

See [Development Roadmap](../../docs/development-roadmap.md) for full Phase 2 plan.
