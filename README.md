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

## Deployment & Portability

### Moving Containers Between Machines

You can deploy fully-loaded containers to any Linux system with Podman. Choose the approach that fits your needs:

#### Option 1: Export & Import (Single Machine Transfer)

For transferring a fully-loaded container to another machine:

```bash
# On source machine - save the container image
podman save <image-name>:latest -o <image-name>-image.tar

# Transfer the file to target machine
scp <image-name>-image.tar user@raspberrypi:/home/user/

# On target machine - load and run
podman load -i <image-name>-image.tar
podman run -d <image-name>:latest
```

**Best for:** Air-gapped systems, Raspberry Pi deployments, one-off transfers
**Trade-off:** Large file size (5-10GB+ with pre-loaded models), slower transfer

#### Option 2: Container Registry (Multiple Machines)

For deploying to multiple systems efficiently:

```bash
# On source machine
podman tag <image-name>:latest myregistry.com/<image-name>:latest
podman push myregistry.com/<image-name>:latest

# On any target machine
podman pull myregistry.com/<image-name>:latest
podman run -d myregistry.com/<image-name>:latest
```

**Best for:** Fleet deployments, multiple Raspberry Pis, CI/CD pipelines
**Trade-off:** Requires a registry (Docker Hub, Podman registry, etc.)

#### Option 3: Rebuild on Target (Optimized)

Copy the `Containerfile` and build locally on the target system:

```bash
# Transfer Containerfile and config
scp -r <capability-repo> user@raspberrypi:

# On target machine
cd <capability-repo>
podman build -t <image-name>:latest .
podman run -d <image-name>:latest
```

**Best for:** Optimizing for target architecture, minimal initial transfer, bandwidth-constrained environments
**Trade-off:** Slower first startup (models download/compile on target)

### Cross-Architecture Considerations

- **x86 → ARM (Raspberry Pi):** Use Option 3 (rebuild) for best compatibility
- **ARM → ARM (Pi 4 → Pi 5):** Options 1-2 work well, same architecture
- **Mixed fleet:** Use Option 2 (registry) with multi-architecture builds

## Quick Links

- [ezansi-capability-llm-ollama](https://github.com/eZansiEdgeAI/ezansi-capability-llm-ollama) - First capability (reference implementation)
- [Capability Contract Specification](https://github.com/eZansiEdgeAI/ezansi-capability-llm-ollama/blob/main/docs/capability-contract-spec.md)
- [Architecture Deep Dive](https://github.com/eZansiEdgeAI/ezansi-capability-llm-ollama/blob/main/docs/architecture.md)

## License

Same as parent project.
