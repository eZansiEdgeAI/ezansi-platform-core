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
git clone https://github.com/eZansiEdgeAI/ezansi-platform-core.git
cd ezansi-platform-core

podman --version

# Run the gateway (registry + routing + validation)
podman-compose up -d

# Verify
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8000/registry
curl -fsS 'http://localhost:8000/status?refresh=true'
```

The gateway runs on port `8000` and discovers capability contracts by scanning `REGISTRY_PATH` (defaults to `/capabilities` inside the container).
By default, `podman-compose.yml` mounts `./capabilities` into the container.

## Deploying Capabilities with the Platform

Capabilities are discovered automatically via the registry. Deploy them independently:

```bash
# Clone a capability
git clone https://github.com/eZansiEdgeAI/ezansi-capability-llm-ollama.git
cd ezansi-capability-llm-ollama

# Deploy the capability
podman-compose up -d
```

The platform discovers capabilities via `capability.json` contracts.

### Making contracts visible to the platform

For now, the gateway uses file-based discovery. Make sure the platform can read your contracts by mounting or copying them under the platform's `./capabilities` folder:

```bash
cd ezansi-platform-core
mkdir -p capabilities/ollama-llm
cp ../ezansi-capability-llm-ollama/capability.json capabilities/ollama-llm/capability.json
```

Note: when the platform runs in a container, capability `api.endpoint` values like `http://localhost:11434` may need to be overridden for container networking.
The demo setup enables `config/overrides.yaml` (via `OVERRIDES_PATH`) so you can keep contracts portable while the platform routes to `http://host.containers.internal:<port>` internally.

## Composing Multiple Capabilities

Create an experience stack that combines capabilities:

```bash
# Example: LLM + Retrieval (RAG building blocks)

# 1) Deploy required capabilities
cd ezansi-capability-llm-ollama && podman-compose up -d
cd ../ezansi-capability-retrieval-chromadb && podman-compose up -d

# 2) Make contracts available to the platform gateway (file discovery)
cd ../ezansi-platform-core
mkdir -p capabilities/ollama-llm capabilities/chromadb-retrieval
cp ../ezansi-capability-llm-ollama/capability.json capabilities/ollama-llm/capability.json
cp ../ezansi-capability-retrieval-chromadb/capability.json capabilities/chromadb-retrieval/capability.json

# 3) Route requests via the platform by service type
curl -fsS http://localhost:8000/registry

# LLM example (text-generation)
curl -sS -X POST http://localhost:8000/ \
	-H 'Content-Type: application/json' \
	-d '{"type":"text-generation","payload":{"endpoint":"generate","json":{"model":"llama3","prompt":"Hello","stream":false}}}'

# Retrieval example (vector-search)
# NOTE: retrieval calls target a named endpoint from the capability contract.
curl -sS -X POST http://localhost:8000/ \
	-H 'Content-Type: application/json' \
	-d '{"type":"vector-search","payload":{"endpoint":"query","params":{"collection":"student"},"json":{"query":"What is photosynthesis?","top_k":3}}}'
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
