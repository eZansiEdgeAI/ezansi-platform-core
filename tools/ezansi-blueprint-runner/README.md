# eZansi Blueprint Runner (external)

This tool is intentionally **outside** platform-core runtime.

It reads a blueprint YAML, resolves required capability types to approved capabilities via a catalog, then clones and starts the needed capability repos using their repo-native compose selector scripts.

## Why

Blueprints are patterns. This runner automates the common “cold start” steps:

- clone/update approved capability repos
- pick an appropriate device/RAM tier profile (auto-detect by default)
- start capability containers (via `podman-compose`)

## Usage (local Python)

From `ezansi-platform-core`:

```bash
python3 tools/ezansi-blueprint-runner/runner.py apply \
  --blueprint /path/to/ezansi-blueprints/blueprints/student-knowledge-rag.yml

# Start the gateway too (recommended for a full runnable stack)
python3 tools/ezansi-blueprint-runner/runner.py apply \
  --blueprint /path/to/ezansi-blueprints/blueprints/student-knowledge-rag.yml \
  --start-platform-core

# Strict mode (fail fast if requested profile is too large)
python3 tools/ezansi-blueprint-runner/runner.py apply \
  --blueprint /path/to/ezansi-blueprints/blueprints/student-knowledge-rag.yml \
  --strict

# Destroy a run
python3 tools/ezansi-blueprint-runner/runner.py destroy \
  --run-dir ./.ezansi-runs/<run-id>
```

## What it creates

- `./.ezansi-runs/<run-id>/` (project-local)
  - `state.json` (what was cloned and started)
  - `repos/` (checked out capability repos)

## Catalog

Defaults to `capabilities/catalog.yml` in this repository.

The catalog is the approval gate: custom capabilities are only runnable once added to the catalog.
