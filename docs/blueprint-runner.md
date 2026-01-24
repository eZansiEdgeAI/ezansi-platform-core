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

## Smoke test (end-to-end)

Once `apply` succeeds and the containers are running, you can do a quick request/response check through **platform-core**.

### 1) Verify platform-core is up

If you just rebuilt platform-core and `podman-compose up -d --build` fails with “container name is already in use”, remove the existing container first:

```bash
cd /path/to/ezansi-platform-core
podman-compose down

# If it still complains (because container_name is fixed), force remove:
podman rm -f ezansi-platform-core

podman-compose up -d --build
```

```bash
curl -sS http://localhost:8000/health
curl -sS http://localhost:8000/info

# Optional: refresh and see which capabilities are healthy
curl -sS 'http://localhost:8000/status?refresh=true'

# You can also probe a specific provider health check:
curl -sS http://localhost:8000/registry/text-generation/health
curl -sS http://localhost:8000/registry/vector-search/health
```

If you prefer pretty JSON output, pipe to `python3 -m json.tool`:

```bash
curl -sS http://localhost:8000/info | python3 -m json.tool
```

### 2) Send a text-generation request through the gateway

This routes by `type` and then calls the capability contract endpoint `generate`.

```bash
curl -sS http://localhost:8000/ \
  -H 'Content-Type: application/json' \
  -d '{
    "type": "text-generation",
    "payload": {
      "endpoint": "generate",
      "json": {
        "model": "tinyllama",
        "prompt": "Say hello in one short sentence.",
        "stream": false
      }
    }
  }'
```

You should get a JSON response that includes `status: success` and the model output under `data`. 

If you get an error response, re-run with headers so you can see the HTTP status:

```bash
curl -i http://localhost:8000/ \
  -H 'Content-Type: application/json' \
  -d '{"type":"text-generation","payload":{"endpoint":"generate","json":{"model":"tinyllama","prompt":"Hello","stream":false}}}'
```

Common causes:

- `503` with `code: UNREACHABLE` or `code: UNHEALTHY`: platform-core can’t reach the capability endpoint. Check `GET /registry` to confirm what endpoint platform-core is trying to call.
- `200` with `status: error` and Ollama returns `model not found`: pull the model inside the Ollama container (or change `model`).

Inspect what platform-core thinks the provider endpoints are:

```bash
curl -sS http://localhost:8000/registry | python3 -m json.tool
curl -sS http://localhost:8000/registry/text-generation | python3 -m json.tool
```

### 3) (Optional) Test retrieval/embeddings through the gateway

Note: on cold start, the very first request can fail while a capability is still warming up.
If you see a one-off failure, run `GET /status?refresh=true`, wait ~1–2 seconds, and retry.

Ingest a couple documents (routes to the `vector-search` provider):

```bash
curl -sS http://localhost:8000/ \
  -H 'Content-Type: application/json' \
  -d '{
    "type": "vector-search",
    "payload": {
      "endpoint": "ingest",
      "params": {"collection": "smoke"},
      "json": {
        "documents": [
          {"id": "doc-1", "text": "The sky is blue."},
          {"id": "doc-2", "text": "Bananas are yellow."}
        ]
      }
    }
  }'
```

Query for a match:

```bash
curl -sS http://localhost:8000/ \
  -H 'Content-Type: application/json' \
  -d '{
    "type": "vector-search",
    "payload": {
      "endpoint": "query",
      "params": {"collection": "smoke"},
      "json": {"query": "What color are bananas?", "top_k": 2}
    }
  }'
```

Embeddings directly (routes to the `text-embeddings` provider):

```bash
curl -sS http://localhost:8000/ \
  -H 'Content-Type: application/json' \
  -d '{
    "type": "text-embeddings",
    "payload": {
      "endpoint": "embeddings",
      "json": {"texts": ["hello world"]}
    }
  }'
```

### Debugging tip: call capabilities directly

If the gateway request fails, check the provider endpoints directly:

```bash
curl -sS http://localhost:11434/api/tags     # ollama-llm health
curl -sS http://localhost:8801/health        # chromadb-retrieval health
```
