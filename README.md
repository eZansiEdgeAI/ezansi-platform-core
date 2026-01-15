# ezansi-platform-core

The stable, reusable foundation for the ezAnsi AI edge computing platform. This repository contains the core orchestration, discovery, and composition infrastructure that enables independent AI capabilities to work together seamlessly.

## Architecture Overview

The platform is built on a **LEGO brick model**:
- **Platform Core** (this repo): Stable foundation, rarely changes
- **Capabilities** (separate repos): Pluggable AI services (LLM, STT, TTS, Vision, etc.)
- **Experience Stacks** (composed): User-facing applications combining multiple capabilities

### Three-Layer Design

```
┌─────────────────────────────────────┐
│  Experience Stacks                  │  Composed applications (voice assistant, etc.)
│  (voice-assistant, chat-ui, etc)    │
└────────────────┬────────────────────┘
                 │
┌────────────────▼────────────────────┐
│  Platform Core (this repo)          │  Orchestration, discovery, routing
│  - Registry                         │
│  - Capability Loader                │
│  - Request Router                   │
│  - Resource Manager                 │
└────────────────┬────────────────────┘
                 │
┌────────────────▼────────────────────┐
│  Capabilities (separate repos)      │  Independent, replaceable modules
│  - ollama (LLM)                     │
│  - whisper (STT)                    │
│  - piper (TTS)                      │
│  - vision (Image processing)        │
└─────────────────────────────────────┘
```

## Capability Contract

All capabilities follow a standardized interface defined in `capability.json`. This enables the platform to:
- Discover what each capability provides
- Validate resource requirements before deployment
- Route requests to the appropriate service
- Compose multiple capabilities into workflows

### Example Capability Contract

```json
{
  "name": "ollama",
  "version": "1.0.0",
  "provides": ["text-generation"],
  "api": {
    "generate": {
      "method": "POST",
      "path": "/api/generate",
      "input": {"prompt": "string", "stream": "boolean"}
    }
  },
  "resources": {
    "ram_mb": 6000,
    "cpu_cores": 4
  }
}
```

See [ezansi-capability-llm-ollama](https://github.com/eZansiEdgeAI/ezansi-capability-llm-ollama) for a complete implementation.

## Current Status

**v1.0.0 (Minimal/Stable)**
- ✅ Capability contract specification
- 🟡 Registry (file-based discovery)
- 🟡 Request router (basic orchestration)
- ⏳ Resource manager
- ⏳ Health monitoring
- ⏳ Stack composition engine

This is intentionally minimal. The platform grows only when capabilities need platform features.

## When to Update Platform-Core

Update this repo when:
- Multiple capabilities reveal a common platform need
- Contract specification needs refinement (discovered through real-world capability testing)
- Platform bugs are discovered
- New composition patterns emerge
- Testing reveals platform limitations

**Do NOT update when:**
- Adding new capabilities (they should work with existing platform)
- Building capability-specific features (stay in capability repo)
- Just keeping pace with capability development

## Development Guidelines

### Adding a New Capability

1. Create separate repo: `ezansi-capability-<name>-<service>`
2. Implement `capability.json` contract following the spec
3. Containerize with Podman
4. Include deployment docs, health checks, test suite
5. Platform auto-discovers it via registry

### Updating Platform Features

1. Only if **multiple capabilities need it**
2. Design against the capability contract, not specific implementations
3. Keep breaking changes minimal
4. Update all existing capabilities' documentation

### Testing

- Unit tests for platform components
- Integration tests with real capabilities
- Performance testing on target hardware (Raspberry Pi)

## Quick Links

- [ezansi-capability-llm-ollama](https://github.com/eZansiEdgeAI/ezansi-capability-llm-ollama) - First capability (reference implementation)
- [Capability Contract Specification](https://github.com/eZansiEdgeAI/ezansi-capability-llm-ollama/blob/main/docs/capability-contract-spec.md)
- [Architecture Deep Dive](https://github.com/eZansiEdgeAI/ezansi-capability-llm-ollama/blob/main/docs/architecture.md)
- [Deployment & Portability Guide](docs/deployment-guide.md)

## License

Same as parent project.
