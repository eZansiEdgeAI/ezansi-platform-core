# Repository Analysis: ezansi-platform-core

## Overview

`ezansi-platform-core` is the routing + discovery “hub” for the eZansi Edge AI platform. It is intentionally small and stable: capabilities (LLM, retrieval, TTS, etc.) run as independent Podman containers and advertise themselves via `capability.json`. Platform-core discovers those contracts, validates that a requested “stack” is feasible on the current device, and proxies requests to the correct capability by **service type**.

In practice, platform-core is what experience layers talk to; experience layers do not call capabilities directly.

## Architecture

The runnable implementation is a minimal FastAPI gateway plus a few focused modules:

- **Gateway API**: a small HTTP surface area for health/info, registry inspection, stack validation, and a generic execution endpoint.
- **Registry**: file-based capability discovery by scanning for `capability.json` under a configured registry path.
- **Router**: type-based routing with capability health checks and request forwarding using `httpx`.
- **Validator**: resource validation for “can this stack run here?” using a device constraints file.
- **Overrides**: config-driven endpoint rewrites (useful when capability contracts use `localhost` but the platform container needs `host.containers.internal`, etc.).
- **External tooling**: an optional advisor CLI/container that reads blueprints and prints runnable calls (kept outside the platform runtime).

High-level request path:

1. Client sends `POST /` with `{type, payload}`.
2. Registry resolves the provider for that `type`.
3. Router health-checks the provider.
4. Router executes a request against the provider’s endpoint (preferably using named endpoints from the contract).
5. Platform-core returns a uniform wrapper response (`status`, `type`, `data`, `metadata`).

## Key Components

- **FastAPI app** ([src/ezansi_platform_core/app.py](src/ezansi_platform_core/app.py))
  - Endpoints: `/health`, `/info`, `/registry`, `/registry/{type}`, `/registry/{type}/health`, `/status`, `/constraints`, `/validate/stack`, and `POST /`.
  - Provides a stable, capability-agnostic API.

- **Capability Registry** ([src/ezansi_platform_core/registry.py](src/ezansi_platform_core/registry.py))
  - Discovers capabilities by scanning for `capability.json`.
  - Builds a lookup from `provides` service types → providers.
  - Applies type alias normalization and endpoint overrides.

- **Request Router** ([src/ezansi_platform_core/router.py](src/ezansi_platform_core/router.py))
  - Health checks via `api.health_check`.
  - Forwards requests using `httpx`.
  - Prefers contract-defined named endpoints (`payload.endpoint`), with a limited legacy fallback for common defaults.

- **Resource Validator** ([src/ezansi_platform_core/validator.py](src/ezansi_platform_core/validator.py))
  - Uses device constraints (RAM/CPU/etc.) to validate whether a set of capabilities is compatible.

- **Overrides + constraints config**
  - Overrides: [config/overrides.yaml](config/overrides.yaml)
  - Device constraints: [config/device-constraints.json](config/device-constraints.json)

- **Podman demo wiring**
  - Compose wrapper: [podman-compose.yml](podman-compose.yml)
  - Demo contracts mounted under `./capabilities/**/capability.json`.

- **Advisor (external helper)** ([tools/ezansi-advisor/advisor.py](tools/ezansi-advisor/advisor.py))
  - Reads a blueprint from `ezansi-blueprints`.
  - Checks platform registry + health.
  - Prints runnable `curl` steps or a single bash runner to execute the flow.

## Technologies Used

- **Python**
- **FastAPI** (gateway)
- **httpx** (HTTP client for routing + health checks)
- **Pydantic** (request schema)
- **YAML** (overrides, blueprints in external repo)
- **Podman / podman-compose** (runtime orchestration for local demos)

## Data Flow

### Discovery

- On startup (and periodically, via a cache TTL), the registry scans the configured `REGISTRY_PATH` for `capability.json` files.
- Each contract is parsed into an internal `CapabilityRecord`.
- Platform-core builds a map of service types → provider names, including alias-normalized types.

### Execution

- The client sends a generic request: `POST /` with `{type, payload}`.
- The registry resolves the provider for that service type.
- The router checks health using the contract’s `api.health_check`.
- The router executes the request:
  - Preferred: `payload.endpoint` references a named contract endpoint, optionally with `payload.params` and `payload.json`.
  - Legacy fallback: infer a default path for a small set of common service types.
- The gateway returns a normalized response to the client.

### Validation

- The client (or advisor) calls `POST /validate/stack` with requested types.
- The validator checks device constraints and returns `compatible`, plus details.

## Team and Ownership

The last year of history shows three contributor identities (likely reflecting different authoring environments):

- **GitHub Copilot**: primary driver of rapid iteration and tooling automation.
- **McFuzzySquirrel** / **McSquirrel**: platform direction, operational validation, and integration decisions.

Given the repository’s role as a stable platform foundation, ownership is best treated as “platform team / architecture” rather than capability-specific.
