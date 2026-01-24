# ezansi-platform-core

Platform Core is the “baseplate” for eZansiEdgeAI: a small HTTP gateway that lets teachers and students snap AI “capability” services together like LEGO bricks and run them as repeatable classroom/lab stacks on edge devices (e.g., Raspberry Pi).

## What this is (LEGO bricks for learning)

**Mental model:**

- **Capabilities = LEGO bricks** (LLM, retrieval, TTS, etc.)
- **Contracts = the studs** (each brick declares what it provides in `capability.json`)
- **Blueprints = the instructions** (how you combine bricks into a stack)
- **Platform Core = the baseplate/gateway** (discovers bricks + routes requests)

**What problem does this solve?**

In a lab/classroom, you don’t want every student project hard-coding ports, URLs, and provider-specific request formats. Platform Core gives you one stable entry point and does discovery + routing from contracts, so you can swap bricks without rewriting clients.

**What’s the benefit to you?**

- One stable endpoint for the whole class: `http://localhost:8000`
- Less “glue code” in student projects; more time experimenting
- Repeatable cold-start workflow with Podman/podman-compose

If you want the bigger picture, see [docs/stack-composition.md](docs/stack-composition.md) (blueprints) and [docs/architecture.md](docs/architecture.md) (diagram).

## Start here

If you’re new to the concept, do this first:

- Manual cold-start E2E (recommended): [docs/cold-start-walkthrough.md](docs/cold-start-walkthrough.md)

Then explore:

- Deployment details: [docs/deployment-guide.md](docs/deployment-guide.md)
- Design docs: [docs/README.md](docs/README.md)

## What you get

- A gateway on `http://localhost:8000`
- File-based discovery of capability contracts from `./capabilities/**/capability.json`
- Request routing via `POST /` using `{ "type": ..., "payload": ... }`
- Stack validation via `POST /validate/stack`

## Quickstart (gateway only)

This starts just the platform gateway. For a full “LLM + retrieval” demo stack, use the manual E2E guide above.

```bash
cd ezansi-platform-core
podman-compose up -d --build

# Verify
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8000/registry
```

Notes:

- By default the gateway mounts `./capabilities` into the container as `/capabilities`.
- If capability contracts use `http://localhost:<port>`, the gateway can still reach host-published capability ports via `config/overrides.yaml` (enabled by default via `OVERRIDES_PATH`).

## Full demo stack (recommended)

To run a real end-to-end flow (capabilities + platform-core gateway), follow:

- [docs/cold-start-walkthrough.md](docs/cold-start-walkthrough.md)

## Blueprint-driven cold start (recommended)

To go from a blueprint (pattern) to a running stack (capabilities + gateway) with minimal manual setup, use the external Blueprint Runner:

- Docs: [docs/blueprint-runner.md](docs/blueprint-runner.md)

That guide includes:

- cold start (build/pull images)
- bring up Ollama + ChromaDB Retrieval
- copy contracts into `./capabilities`
- run `./scripts/smoke-test.sh`
- execute one real LLM and retrieval request through the gateway

## Architecture at a glance

```mermaid
flowchart LR
	U[You\n(curl / app)] -->|HTTP| G[Platform Core Gateway\nFastAPI :8000]

	C[Capability contracts\n./capabilities/**/capability.json] --> R[Capability Registry\n(discovery + catalog)]
	G --> R
	R --> RT[Request Router\n(select provider + proxy)]

	RT -->|provider: llm| O[Ollama capability service]
	RT -->|provider: retrieval| RC[ChromaDB Retrieval capability service]
	RC --> CH[(ChromaDB)]

	subgraph Podman / podman-compose
		G
		O
		RC
		CH
	end
```

In practice:

- `podman-compose up -d --build` starts the gateway (and capabilities in the full stack)
- You copy/mount capability contracts into `./capabilities/` so the registry can discover them
- You send all requests to the gateway (`POST /`), and it routes to the right capability

## How it works (1 minute)

- Capabilities are separate repos/services that declare what they provide in `capability.json`.
- Platform Core scans contracts, builds a registry, and routes `POST /` requests to the selected provider.
- The router prefers `payload.endpoint` (a named endpoint from the contract) rather than hard-coded paths.

If you want the deeper design docs, start at [docs/README.md](docs/README.md).

## Testing (optional)

Manual cold-start walkthrough: [docs/cold-start-walkthrough.md](docs/cold-start-walkthrough.md)

Automated tests (pytest): [tests/TEST_GUIDE.md](tests/TEST_GUIDE.md)

## Related repos

- LLM capability: https://github.com/eZansiEdgeAI/ezansi-capability-llm-ollama
- Retrieval capability: https://github.com/eZansiEdgeAI/ezansi-capability-retrieval-chromadb

## License

Same as parent project.
