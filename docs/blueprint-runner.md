# Blueprint Runner (Clone + Start)

The **Blueprint Runner** is an external tool that turns a *blueprint* (pattern) into a *running stack*:

- resolves required capability **types** to approved capabilities
- clones/updates required capability repos
- selects a device/RAM profile (auto-detect by default)
- starts capabilities using their repo-native `podman-compose` selector scripts
- (optionally) starts **platform-core** so the blueprint flow can run through the gateway

This tool is intentionally **outside** platform-core runtime.

## Where it lives

- Tool: `tools/ezansi-blueprint-runner/runner.py`
- Approved catalog: `capabilities/catalog.yml`
- Decision record: `docs/decisions/0001-blueprint-runner.md`

## Quickstart

Prereqs:

- `podman` and `podman-compose`
- `python3`

Example (run the Student Knowledge RAG blueprint):

```bash
# From ezansi-platform-core repo root
python3 tools/ezansi-blueprint-runner/runner.py apply \
  --blueprint /path/to/ezansi-blueprints/blueprints/student-knowledge-rag.yml \
  --start-platform-core

# Run state is stored in:
#   ./.ezansi-runs/<run-id>/state.json
```

Destroy a run:

```bash
python3 tools/ezansi-blueprint-runner/runner.py destroy \
  --run-dir ./.ezansi-runs/<run-id>
```

## Catalog-driven approval

The runner **only** starts capabilities that exist in the approved catalog (`capabilities/catalog.yml`).

Why:

- keeps “what is runnable” curated by the organization
- decouples blueprints (patterns) from repo URLs and implementation details

When a blueprint requires a type that has no approved capability, the correct action is:

- add/approve a capability in the catalog (and vendoring its contract under `./capabilities/...`) or
- change the blueprint to use types that exist

## Device/RAM profiles

The runner uses a canonical set of profiles (examples):

- `rpi4-8g`, `rpi5-8g`, `rpi5-16g`
- `amd64-24g`, `amd64-32g`

Default behavior:

- **auto-detect** host arch + RAM and pick an appropriate profile
- if a requested profile is too large, it will **downgrade** when possible and warn
- `--strict` makes this fail fast instead

## Blueprint compatibility checklist

A future blueprint will work with the runner if:

1. It has `requires_types` (type-based routing) and the types match platform-core conventions.
2. Each required type is provided by **exactly one** approved capability in `capabilities/catalog.yml`, **or** the blueprint specifies a stable provider via `capability_hints`.
3. The blueprint’s `flow` only calls platform-core (`POST /`) and uses named endpoints that exist in the chosen capability contracts.
4. The chosen capability repos can be started using the catalog’s start rule (today: `scripts/choose-compose.sh`).

Optional but recommended:

- add `target_device.profile: auto` (or a specific profile) for clearer expected behavior

## Notes / limitations

- Some capability compose presets use fixed `container_name`. This prevents running multiple independent copies of the same capability concurrently on one host.
  - The runner will treat already-running fixed-name containers as “existing” and continue.
- Today the runner starts `requires_types`. (Optional types can be added later as a flag.)
