# ADR 0001: Blueprint Clone + Start Runner

Date: 2026-01-24
Status: Accepted

## Context

Blueprints in `ezansi-blueprints` intentionally describe *patterns*:

- required capability **types** (e.g., `text-generation`, `vector-search`)
- an execution flow that calls **platform-core** only

Today, users must manually:

- clone capability repos
- choose the correct compose preset(s) for their device/RAM tier
- start containers (often via `podman-compose`)

This manual setup makes it hard for new users to reliably get from a blueprint to a running stack.

## Decision

We will add a platform-core *external tool* (“blueprint runner”) that can:

1. Read a blueprint YAML.
2. Resolve required capability **types** to approved capabilities via a platform-maintained catalog.
3. Clone/update required repos into a **project-local** runs directory.
4. Select a **RAM-tier-aware device profile** (auto-detect by default).
5. Start each capability using its existing repo-native preflight/selector script (e.g., `scripts/choose-compose.sh`).
6. Persist run state to support `status` and `destroy`.

## Key choices (and why)

### 1) Stable capability IDs in blueprint hints
- Blueprint optional hints will reference capabilities by stable ID (the contract `name`, e.g., `ollama-llm`).
- Why: repo URLs and implementation details can change; the stable ID remains the “interface contract” identifier.

### 2) Approved catalog (platform registry) gates capabilities
- Custom/new capabilities are only runnable once added to the platform catalog.
- Why: ensures compatibility, reduces surprise breakage, and centralizes mapping from types → repos → deployment rules.

### 3) Runs directory is project-local
- Runs are created under `./.ezansi-runs/<run-id>` by default.
- Why: avoids polluting developer checkouts, makes runs reproducible per project, and keeps teardown state nearby.

### 4) RAM tiers are first-class, but selection is best-effort by default
- Default behavior is permissive:
  - auto-detect host and select the closest supported profile that fits
  - if a requested profile is too large, downgrade when possible and warn
- `--strict` mode fails fast when requirements aren’t met.
- Why: many users do not know their hardware details; best-effort reduces friction while still offering strict reproducibility.

### 5) Start logic delegates to repo-native selectors
- The runner will call each capability’s existing preflight scripts (e.g., `scripts/choose-compose.sh`) rather than re-implementing selection logic.
- Why: keeps orchestration aligned with capability repo evolution (compose conventions, multi-arch changes, resource policies).

### 6) Branch refs like `main` allowed (“latest”)
- Catalog defaults may use moving refs like `main`.
- Runner warns when using a non-pinned ref.
- Why: new users want “get me the latest working stack”; pinning can be added later for reproducible labs.

## Consequences

- Platform-core remains focused on discovery/validation/routing; the runner lives under `tools/`.
- The catalog becomes the central place to encode:
  - approved capability IDs
  - repo URLs and default refs
  - how to start each capability per device profile
- Some capability repos may need small standardization over time (e.g., consistent selector args, named endpoints).

## Alternatives considered

- Put repo URLs directly in blueprints: rejected as it couples patterns to implementation and bypasses approval.
- Add a single universal compose convention across repos: rejected initially; too disruptive. The catalog/selector approach adapts to current reality.
- Keep strict-by-default: rejected; user experience is worse for novices and heterogeneous hardware.
