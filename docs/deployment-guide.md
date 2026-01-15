# Platform Deployment & Composition Guide

The Platform Core provides the orchestration infrastructure for discovering and composing capabilities. This guide covers deploying the platform and integrating capabilities.

## Platform Core Setup

Platform Core is a lightweight infrastructure layer. It handles:
- **Capability discovery** (via registry scanning)
- **Request routing** to the appropriate capability
- **Resource validation** before deployment
- **Stack composition** (combining multiple capabilities)

### Minimal Deployment

```bash
# Clone the platform
git clone https://github.com/eZansiEdgeAI/ezansi-platform-core.git
cd ezansi-platform-core

# The platform core itself is minimal - it discovers capabilities
# No additional setup needed beyond having Podman installed
podman --version
```

## Deploying Capabilities with the Platform

Capabilities are discovered automatically via the registry. Deploy them independently:

```bash
# Clone a capability
git clone https://github.com/eZansiEdgeAI/ezansi-capability-llm-ollama.git
cd ezansi-capability-llm-ollama

# Deploy the capability
podman-compose up -d
```

The platform will automatically discover it via `capability.json`.

## Composing Multiple Capabilities

Create an experience stack that combines capabilities:

```bash
# Example: Voice assistant combining LLM + STT + TTS

# 1. Deploy all required capabilities
podman-compose -f ollama/podman-compose.yml up -d
podman-compose -f whisper/podman-compose.yml up -d
podman-compose -f piper/podman-compose.yml up -d

# 2. Platform discovers all three via registry
# 3. Route requests through the platform orchestrator
# 4. Compose workflows using the capability contract
```

## Portability & Distribution

### For Capability Containers

See individual capability documentation for container migration strategies:
- **Export/Import** for single-machine transfers
- **Registry push/pull** for multi-machine deployments
- **Rebuild on target** for architecture optimization

### For Platform Core

The platform core is stateless and can be deployed anywhere. Share the configuration:

```bash
# Copy platform to another machine
scp -r ezansi-platform-core user@host:

# Redeploy on target
cd ezansi-platform-core
# No rebuild needed - platform is universal
```

## Cross-Architecture Considerations

- **x86 host → ARM (Raspberry Pi):** Deploy capabilities with `podman build` on target (optimizes for architecture)
- **ARM → ARM (Pi 4 → Pi 5):** Container images usually work across same architecture
- **Mixed fleet:** Use container registry with multi-architecture manifests

## Next Steps

1. Deploy Platform Core on your target system
2. Deploy individual capabilities (see [ezansi-capability-llm-ollama](https://github.com/eZansiEdgeAI/ezansi-capability-llm-ollama) for reference)
3. Platform auto-discovers capabilities via registry
4. Build experience stacks by composing capabilities
