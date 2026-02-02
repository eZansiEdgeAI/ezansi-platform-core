# ADR 0003: Local Dev Stack Reachability, Fixed Container Names, and LLM Timeouts

- Status: accepted
- Date: 2026-02-03

## Context

During end-to-end testing of the `student-knowledge-rag-tts` blueprint (retrieval → LLM → optional TTS), we ran the stack locally on a Raspberry Pi-class device using Podman.

We hit several practical issues:

1. **Container-to-host reachability**
   - Capability contracts commonly use `http://localhost:<port>` because that works for host-native clients.
   - Platform Core runs in a container in local dev, so `localhost` resolves to *inside the container*, not the host.
   - Result: health checks and requests failed with `UNREACHABLE` unless endpoints were overridden.

2. **Fixed `container_name` collisions**
   - Some compose stacks set `container_name:` explicitly.
   - The blueprint runner starts multiple capability repos; if a stack is already running, Podman rejects reuse of the same container name.

3. **Binary response proxying (TTS)**
   - Text-to-speech returns `audio/wav` and must be proxied as raw bytes.
   - If the gateway wraps binary responses in JSON, clients end up saving JSON (or JSON-escaped bytes) as `.wav`.

4. **LLM inference latency / timeouts**
   - On CPU-only devices, `ollama` generation can take minutes for moderate prompts.
   - Default gateway request timeouts (e.g., 30s or 180s) were too short for realistic RAG prompts.

## Decision

For local development and blueprint-driven testing we will:

1. **Use endpoint overrides for containerized Platform Core**
   - Keep capability contracts portable (often `http://localhost:<port>`).
   - Configure Platform Core to reach host-published ports via `host.containers.internal` using `config/overrides.yaml`.
   - Mount `./config` into the Platform Core container so overrides can be edited without rebuilding.

2. **Handle fixed-name container collisions in the blueprint runner**
   - If a capability’s fixed-name containers are already running, treat that as an “existing stack” and skip starting it.
   - Add an explicit opt-in flag to remove conflicting fixed-name containers when the user wants a fresh run.

3. **Proxy non-JSON responses as raw bytes**
   - For `text-to-speech` responses, proxy `audio/wav` directly so clients can `curl -o speak.wav`.

4. **Increase local dev timeouts and bound generation**
   - Increase Platform Core’s HTTP timeout (local dev defaults) to tolerate slower CPU-only inference.
   - Encourage blueprints to set conservative generation limits (e.g., `options.num_predict`) to keep runs predictable.

## Consequences

- Local dev becomes less “magical” but much more reliable:
  - Platform Core can consistently reach host-published capability ports.
  - Blueprint runs can be repeated without manual container cleanup (or with a single opt-in replace flag).
  - TTS artifacts are real WAV files, not JSON error bodies.
- Higher timeouts may mask true hangs; we mitigate this by bounding generation (`num_predict`) and keeping health checks visible.

## Notes / Follow-ups

- Resource contention (RAM/CPU pressure) is likely a contributor to long generation times; we will revisit sizing and constraints later.
- Longer-term we may want per-type timeouts (e.g., longer for `text-generation`, shorter for health checks) and/or structured backpressure.
